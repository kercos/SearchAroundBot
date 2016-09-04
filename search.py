# -*- coding: utf-8 -*-

from google.appengine.ext import ndb
import logging
import key

class Search(ndb.Model):
    chat_id = ndb.IntegerProperty()
    date = ndb.DateTimeProperty(auto_now=True)
    location = ndb.GeoPtProperty()
    search_type = ndb.StringProperty()
    search_radius = ndb.IntegerProperty()
    found_location = ndb.BooleanProperty()

def addSearch(person, found_location):
    s = Search(
        chat_id = person.chat_id,
        location = person.location,
        search_type = person.search_type,
        search_radius = person.search_radius,
        found_location = found_location
    )
    s.put()

