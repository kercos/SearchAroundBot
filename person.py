# -*- coding: utf-8 -*-

from google.appengine.ext import ndb
import logging
import key

import parameters
import utility

class Person(ndb.Model):
    chat_id = ndb.IntegerProperty()
    name = ndb.StringProperty()
    last_name = ndb.StringProperty()
    username = ndb.StringProperty()
    state = ndb.IntegerProperty(default=-1, indexed=True)
    location = ndb.GeoPtProperty()
    last_state  = ndb.IntegerProperty()
    last_mod = ndb.DateTimeProperty(auto_now=True)
    search_count = ndb.IntegerProperty(default=0)
    vote_reminder_enabled = ndb.BooleanProperty(default=True)
    search_radius = ndb.IntegerProperty(default=1) #km
    search_type = ndb.StringProperty(default=parameters.SEARCH_TYPE_DRINKING_WATER)
    search_locations = ndb.PickleProperty()
    enabled = ndb.BooleanProperty(default=True)

    def getFirstName(self, escapeMarkdown = True):
        if escapeMarkdown:
            return utility.escapeMarkdown(self.name.encode('utf-8'))
        return self.name.encode('utf-8')

    def getLastName(self, escapeMarkdown = True):
        if escapeMarkdown:
            return utility.escapeMarkdown(self.last_name.encode('utf-8'))
        return self.last_name.encode('utf-8')

    def getUsername(self):
        return self.username.encode('utf-8') if self.username else None

    def getUserInfoString(self, escapeMarkdown = True):
        info = self.getFirstName(escapeMarkdown)
        if self.last_name:
            info += ' ' + self.getLastName(escapeMarkdown)
        if self.username:
            info += ' @' + self.getUsername()
        info += ' ({})'.format(self.chat_id)
        return info

    def setEnabled(self, enabled, put=False):
        self.enabled = enabled
        if put:
            self.put()

    def updateUsername(self, username, put=False):
        if (self.username!=username):
            self.username = username
            if put:
                self.put()

    def setState(self, newstate, put=True):
        self.last_state = self.state
        self.state = newstate
        if put:
            self.put()

    def isAdministrator(self):
        result = self.chat_id in key.AMMINISTRATORI_ID
        #logging.debug("Amministratore: " + str(result))
        return result

    def setLocation(self, latitude, longitude, put):
        self.location = ndb.GeoPt(latitude, longitude)
        if put:
            self.put()

    def getSearchType(self):
        return self.search_type.encode('utf-8')

    def getNextSearchRadius(self):
        nextRadiusIndex = parameters.POSSIBLE_RADII.index(self.search_radius) + 1
        if nextRadiusIndex < len(parameters.POSSIBLE_RADII):
            return parameters.POSSIBLE_RADII[nextRadiusIndex]
        return None

    def isAdmin(self):
        return self.chat_id in key.AMMINISTRATORI_ID

    def increaseSearchCount(self, put=False):
        self.search_count += 1
        if put:
            self.put()

    def isTimeToRemindToVote(self):
        return self.vote_reminder_enabled \
               and \
               self.search_count % parameters.REMIND_VOTE_BOT_EVERY_N_SEARCH == 0

def resetSearchType():
    for p in Person.query():
        p.search_type = parameters.SEARCH_TYPE_DRINKING_WATER
        p.put()

def addPerson(chat_id, name, last_name, username):
    p = Person(
        id=str(chat_id),
        chat_id=chat_id,
        name=name,
        last_name = last_name,
        username = username
    )
    p.put()
    return p

def getPersonByChatId(chat_id):
    return Person.get_by_id(str(chat_id))

def getPeopleWithLastName(lastName, number):
    lastName_uni = lastName.decode('utf-8')
    return Person.query(Person.last_name==lastName_uni).fetch(number)
