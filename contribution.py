# -*- coding: utf-8 -*-

from google.appengine.ext import ndb
import logging
import key
import osmEdit

class Contribution(ndb.Model):
    chat_id = ndb.IntegerProperty()
    date = ndb.DateTimeProperty(auto_now=True)
    location = ndb.GeoPtProperty()
    node_id = ndb.StringProperty()
    search_type = ndb.StringProperty()
    picture_file_id = ndb.StringProperty()

def addContribution(person, node_id, file_id):
    c = Contribution(
        chat_id = person.chat_id,
        location = person.location,
        search_type = person.search_type,
        node_id = node_id,
        picture_file_id = file_id
    )
    c.put()

def deleteContribution(lat, lon):
    loc = ndb.GeoPt(lat, lon)
    c = Contribution.query(Contribution.location==loc).get()
    if c:
        node_id = c.node_id
        if osmEdit.deleteLocation(node_id):
            c.key.delete()
            return True
    return False
