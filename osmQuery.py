# -*- coding: utf-8 -*-

import json
import logging
import urllib, urllib2
import httplib
import socket

import key
import geoUtils
import jsonUtil
from geoLocation import GeoLocation
import parameters

POSSIBLE_OSM_OVERPASS_BASE_URL = [
    "http://overpass-api.de/api/",
    "http://api.openstreetmap.fr/oapi/interpreter/",
    #"http://overpass.osm.rambler.ru/cgi/",
    #"http://overpass.osm.ch/api/",
]

URL_QUERY_OSM_BASE = POSSIBLE_OSM_OVERPASS_BASE_URL[0] + 'interpreter?data=[out:json];'

URL_QUERY_OSM_NODE = URL_QUERY_OSM_BASE + "node({});out+meta;"

URL_QUERY_OSM_DRINKING_WATER = URL_QUERY_OSM_BASE +\
                           '(' \
                           'node["amenity"="drinking_water"]{0};' \
                           'node["drinking_water"="yes"]{0};' \
                           ');' \
                           'out;'

#'way["amenity"="drinking_water"]{0};' \
#'way["drinking_water"="yes"]{0};' \

URL_QUERY_OSM_TOILET = URL_QUERY_OSM_BASE + \
                       'node["amenity"="toilets"]{0};' \
                       'out;'

#'way["amenity"="toilets"]{0};' \

URL_QUERY_OSM_WHEELCHAIR_TOILET = URL_QUERY_OSM_BASE + \
                                  '(' \
                                  'node["amenity"="toilets"]["wheelchair"="yes"]{0};' \
                                  'node["toilets:wheelchair"="yes"]{0};' \
                                  ');' \
                                  'out;'

URL_QUERY_OSM_PHARMACY = URL_QUERY_OSM_BASE + \
                     'node["amenity"="pharmacy"]{0};' \
                     'out;'

#'way["amenity"="pharmacy"]{0};' \

#https://developers.google.com/places/web-service/search
URL_QUERY_GOOMAP_BASE = 'https://maps.googleapis.com/maps/api/place/nearbysearch/json'
URL_QUERY_GOOMAP_PHARMACY = URL_QUERY_GOOMAP_BASE + \
                            '?location={},{}' \
                            '&radius={}' \
                            '&type=pharmacy' \
                            '&key=' + key.GOOGLE_API_KEY

USE_GOOGLE_FOR_FARMACIES = True

URL_QUERY_TABLE = {
    parameters.SEARCH_TYPE_DRINKING_WATER: URL_QUERY_OSM_DRINKING_WATER,
    parameters.SEARCH_TYPE_TOILET: URL_QUERY_OSM_TOILET,
    parameters.SEARCH_TYPE_WHEELCHAIR_TOILET: URL_QUERY_OSM_WHEELCHAIR_TOILET,
    parameters.SEARCH_TYPE_PHARMACY: URL_QUERY_GOOMAP_PHARMACY if USE_GOOGLE_FOR_FARMACIES else URL_QUERY_OSM_PHARMACY
}

def getJsonNodeById(node_id):
    url = URL_QUERY_OSM_NODE.format(node_id)
    elements = getJsonElementStructureFromOverpass(url)
    if elements:
        return elements[0]
    return None

def isThereLocationInProximity(lat, lon, type):
    elements = getJsonElementsInProximity(lat, lon, type)
    return elements!=None and len(elements)>0

def getJsonElementsInProximity(lat, lon, type):
    radius = parameters.MIN_DISTANCE_FROM_SAME_LOCATION
    assert type in URL_QUERY_TABLE.keys()
    urlTemplate = URL_QUERY_TABLE[type]
    rectCoordStr = getBoxCoordinateStr(lat, lon, radius)
    url = urlTemplate.format(rectCoordStr)
    return getJsonElementStructureFromOverpass(url)

def getSortedLocationsWithinRadious(p, overrided_radius=None):
    lat = p.location.lat
    lon = p.location.lon
    radius = overrided_radius if overrided_radius!=None else p.search_radius
    type = p.getSearchType()
    assert type in URL_QUERY_TABLE.keys()
    urlTemplate = URL_QUERY_TABLE[type]
    if urlTemplate == URL_QUERY_GOOMAP_PHARMACY:
        radius_meter = radius * 1000
        url = urlTemplate.format(lat,lon,radius_meter)
        return getLatLonDistancesFromGoogle(url, lat, lon)
    else:
        rectCoordStr = getBoxCoordinateStr(lat, lon, radius)
        url = urlTemplate.format(rectCoordStr)
        return getLatLonDistancesFromOverpass(url, lat, lon, radius)

# results should be of the type lat, lon, dist, open (boolean)

MAX_TIMEOUT_SECONDS = 20

def getLatLonDistancesFromOverpass(url, lat, lon, radius):
    elements = getJsonElementStructureFromOverpass(url)
    if elements == None:
        return None
    if elements:
        sortedElementsDistance = [
            (e['lat'], e['lon'], geoUtils.distance((e['lat'], e['lon']), (lat, lon)), True)
            for e in elements]
        sortedElementsDistance.sort(key=lambda e: e[2])
        sortedElementsDistanceSelection = [e for e in sortedElementsDistance if e[2] <= radius]
        logging.debug("Retured elements: " + str(sortedElementsDistanceSelection))
        return sortedElementsDistanceSelection
    return []

def getJsonElementStructureFromOverpass(url):
    #url = urllib.quote(url)
    logging.debug("Query overpass from url: " + url)
    try:
        responseString = urllib2.urlopen(url, timeout=MAX_TIMEOUT_SECONDS).read()
    except (httplib.HTTPException, socket.error) as err:
        logging.debug("Timeout exception in Overpass: {} ".format(str(err)))
        return None
    jsonStructure = jsonUtil.json_loads_byteified(responseString)
    return jsonStructure['elements']

def getLatLonDistancesFromGoogle(url, lat, lon, show_only_open=True):
    #url = urllib.quote(url)
    logging.debug("Query google places API from url: " + url)
    responseString = urllib2.urlopen(url, timeout=MAX_TIMEOUT_SECONDS).read()
    jsonStructure = jsonUtil.json_loads_byteified(responseString)
    elements = jsonStructure['results']
    if elements:
        sortedElementsDistance = []
        for e in elements:
            location = e['geometry']['location']
            loc_lat = location['lat']
            loc_lon = location['lng']
            dist = geoUtils.distance((loc_lat, loc_lon), (lat, lon))
            openNow = e["opening_hours"]["open_now"] if "opening_hours" in e.keys() else False
            sortedElementsDistance.append((loc_lat, loc_lon, dist, openNow))
        sortedElementsDistance.sort(key=lambda e: e[2])
        #logging.debug("Retured elements: " + str(sortedElementsDistance))
        return sortedElementsDistance
    return []

def getBoxCoordinateStr(lat, lon, radius):
    loc = GeoLocation.from_degrees(lat, lon)
    boxMinMaxCorners = loc.bounding_locations(radius)
    boxMinCorners = boxMinMaxCorners[0]
    boxMaxCorners = boxMinMaxCorners[1]
    lat1 = boxMinCorners.deg_lat
    lon1 = boxMinCorners.deg_lon
    lat2 = boxMaxCorners.deg_lat
    lon2 = boxMaxCorners.deg_lon
    rectCoordStr = '({},{},{},{})'.format(lat1, lon1, lat2, lon2)
    return rectCoordStr


MAP_IMG_URL = "http://maps.googleapis.com/maps/api/staticmap?" \
              "&size=400x400" \
              "&maptype=roadmap" \
              "&markers=color:red|{0},{1}" \
              "&key=" + key.GOOGLE_API_KEY

STANDARD_MARKERS_TEMPLATE = "&markers=color:green|{0},{1}"
CLOSED_MARKERS_TEMPLATE = "&markers=color:gray|{0},{1}"

def getMapImgDrinkingWater(p):
    lat = p.location.lat
    lon = p.location.lon
    sortedLocations = p.search_locations
    assert sortedLocations
    url = MAP_IMG_URL.format(lat, lon)
    for e in sortedLocations:
        locationOpen = e[3]
        if locationOpen:
            url += STANDARD_MARKERS_TEMPLATE.format(e[0], e[1])
        else:
            url += CLOSED_MARKERS_TEMPLATE.format(e[0], e[1])
    logging.debug("Sending image from url: " + url)
    img = urllib2.urlopen(url).read()
    return img