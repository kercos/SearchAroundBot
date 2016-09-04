# -*- coding: utf-8 -*-

import key
import json
import logging
import parameters
import requests
from requests.auth import HTTPBasicAuth
import webapp2
import urllib

import httplib
import base64
import string

import osmQuery

AMENITY_TYPE_TABLE = {
    parameters.SEARCH_TYPE_DRINKING_WATER: u'drinking_water',
    parameters.SEARCH_TYPE_TOILET: u'toilets',
}


CHANGESET_CREATE_XML = \
"""
<osm version="0.6" generator="SearchAroundBot">
  <changeset>
    <tag k="created_by" v="SearchAroundBot"/>
    <tag
        k="comment"
        v="{}"/>
    <tag k="bot" v="yes"/>
  </changeset>
</osm>
"""

NODE_CREATE_XML = \
"""
<osm version="0.6" generator="SearchAroundBot">
  <node lat="{}" lon="{}" changeset="{}">
    <tag
        k="note"
        v="{}"/>
    <tag k="amenity" v="{}"/>
  </node>
</osm>
"""


NODE_DELETE_XML = \
"""\
<osm version="0.6">
  <node lat="{}" lon="{}" id="{}" version="{}" changeset="{}" />
</osm>
"""

"""\
<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<osm>
  <node lat="{}" lon="{}" id="{}" version="{}" changeset="{}" />
</osm>
"""


OSM_API_BASE_URL = 'https://www.openstreetmap.org/api/0.6/'

#-----------------
# DELETE NODE
#-----------------

def deleteLocation(node_id):
    logging.debug("Location deletion")
    nodeJsonData = osmQuery.getJsonNodeById(node_id)
    if nodeJsonData:
        version = nodeJsonData['version']
        lat = nodeJsonData['lat']
        lon = nodeJsonData['lon']
        changeset_comment = "Open changeset to remove node id {} because verified as not accurate.".format(node_id)
        r = requests.put(OSM_API_BASE_URL + 'changeset/create',
                         auth=HTTPBasicAuth(key.OSM_ID, key.OSM_PW),
                         data= CHANGESET_CREATE_XML.format(changeset_comment))
        changeset_id = r.text
        logging.debug("changeset id: " + changeset_id)
        assert r.status_code == 200

        headers = {'Content-Type': 'application/xml'}
        r = requests.delete(OSM_API_BASE_URL + 'node/' + node_id,
                            auth=HTTPBasicAuth(key.OSM_ID, key.OSM_PW),
                            headers = headers,
                            data=NODE_DELETE_XML.format(lat, lon, node_id, version, changeset_id))
        logging.debug("Node deletion request: " + r.text)
        logging.debug("Xml: " + NODE_DELETE_XML.format(lat, lon, node_id, version, changeset_id))
        assert r.status_code == 200

        """
        url = OSM_API_BASE_URL + 'node/' + node_id
        auth = base64.encodestring('%s:%s' % (key.OSM_ID, key.OSM_PW)).replace('\n', '')
        message = NODE_DELETE_XML.format(lat, lon, node_id, version, changeset_id)
        webservice = httplib.HTTP(url)
        webservice.putrequest("DELETE", url)
        webservice.putheader("Content-type", "text/plain")
        webservice.putheader("Authorization", "Basic %s" % auth)
        webservice.endheaders()
        webservice.send(message)
        statuscode, statusmessage, header = webservice.getreply()
        logging.debug("Node deletion request: {} - {}".format(statusmessage, header))
        assert statuscode == 200
        """

        r = requests.put(OSM_API_BASE_URL + 'changeset/{}/close'.format(changeset_id),
                     auth=HTTPBasicAuth(key.OSM_ID, key.OSM_PW))
        assert r.status_code == 200
        return True
    else:
        return False

#-----------------
# NEW NODE
#-----------------

def insertNewLocation(lat, lon, type, user_info, photo_url):
    logging.debug("New location creation")
    amenity_type = AMENITY_TYPE_TABLE[type]
    changeset_comment = "Open changeset to add {} node suggested by Telegram user {} via SearchAroundBot." \
                        "For further information go to https://wiki.openstreetmap.org/wiki/SearchAroundBot " \
                        "or contact kercos@gmail.com.".format(amenity_type, user_info)
    r = requests.put(OSM_API_BASE_URL + 'changeset/create',
                 auth=HTTPBasicAuth(key.OSM_ID, key.OSM_PW),
                 data=CHANGESET_CREATE_XML.format(changeset_comment))
    changeset_id = r.text
    logging.debug("changeset id: " + changeset_id)
    assert r.status_code == 200
    #logging.debug("Changeset create request. changeset_id {} user info {}.".format(changeset_id,user_info))
    photo_url_text = photo_url if photo_url else 'not provided'
    node_comment = "Created by Telegram user: {} via SearchAroundBot " \
                   "(https://wiki.openstreetmap.org/wiki/SearchAroundBot). " \
                   "Photo url: {} ".format(user_info, photo_url_text)
    r = requests.put(OSM_API_BASE_URL + 'node/create',
                     auth=HTTPBasicAuth(key.OSM_ID, key.OSM_PW),
                     data=NODE_CREATE_XML.format(lat, lon, changeset_id, node_comment, amenity_type))
    node_id = r.text
    logging.debug("Node create request. Node id:" + node_id)
    assert r.status_code == 200
    r = requests.put(OSM_API_BASE_URL + 'changeset/{}/close'.format(changeset_id),
                 auth=HTTPBasicAuth(key.OSM_ID, key.OSM_PW))
    #logging.debug("Changeset close request: " + str(r.text))
    assert r.status_code == 200
    return node_id

class DownloadPhotoHandler(webapp2.RequestHandler):

    def get(self, file_id):
        from google.appengine.api import urlfetch
        urlfetch.set_default_fetch_deadline(60)
        logging.debug("rettrieving picture with file id: " + file_id)
        resp = urllib.urlopen(key.BASE_URL + 'getFile', urllib.urlencode({'file_id': file_id})).read()
        logging.debug("response: " + str(resp))
        resp_result = json.loads(resp)['result']
        logging.debug("resp_result: " + str(resp_result))
        file_path = resp_result['file_path'].encode('utf-8')
        file_size = resp_result['file_size']
        extension = file_path[-3:]
        urlFile = key.BASE_URL_FILE + file_path
        logging.debug("Url file: " + urlFile)
        pictureFile = urllib.urlopen(urlFile).read()
        self.response.headers['Content-Type'] = 'image / ' + extension
        self.response.headers['Content-Length'] = str(file_size)
        self.response.out.write(pictureFile)