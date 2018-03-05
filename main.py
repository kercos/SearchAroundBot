# -*- coding: utf-8 -*-

# Set up requests
# see https://cloud.google.com/appengine/docs/standard/python/issue-requests#issuing_an_http_request
import requests_toolbelt.adapters.appengine
requests_toolbelt.adapters.appengine.monkeypatch()
from google.appengine.api import urlfetch
urlfetch.set_default_fetch_deadline(20)
#ignore warnings
import warnings
import urllib3.contrib.appengine
warnings.filterwarnings('ignore', r'urllib3 is using URLFetch', urllib3.contrib.appengine.AppEnginePlatformWarning)


import json
import logging
import urllib
import urllib2
from time import sleep
import requests

from utility import unindent

# standard app engine imports
from google.appengine.api import urlfetch
from google.appengine.ext import deferred
from google.appengine.ext.db import datastore_errors

import key
import person
from person import Person
import utility

import webapp2
import osmQuery
import osmEdit
#from ConversionGrid import GRID
import geoUtils
import multipart
import parameters
import search
import contribution

# ================================
# GLOBAL VARIABLES
# ================================

########################
WORK_IN_PROGRESS = False
########################

# ================================
# STATES
# ================================

STATES = {
    0:   'Initial screen - Search Location',
    1:   'Ask for map',
    2:   'Insert new location',
    21:  'Confirm new location',
    3:   'Remind to vote',
    9:   'Settings',
    91:  'Change search radius',
    92:  'Change search type'
}


# ================================
# BUTTONS
# ================================


CANCEL = u'\U0000274C'.encode('utf-8')
CHECK = u'\U00002705'.encode('utf-8')
LEFT_ARROW = u'\U00002B05'.encode('utf-8')
UNDER_CONSTRUCTION = u'\U0001F6A7'.encode('utf-8')
FROWNING_FACE = u'\U0001F641'.encode('utf-8')
BULLET_RICHIESTA = '🔹'
BULLET_OFFERTA = '🔸'
BULLET_POINT = '🔸'

BUTTON_GAME = "🕹 GAME"
BUTTON_ACCEPT = CHECK + " ACCEPT"
BUTTON_CONFIRM = CHECK + " CONFIRM"
BUTTON_ABORT = CANCEL + " ABORT"
BUTTON_BACK = "⬅ BACK"
BUTTON_NEXT = "➡ NEXT"
BUTTON_EXIT = CANCEL + " EXIT"
BUTTON_PLAY_AGAIN = "🕹  PLAY AGAIN"

BUTTON_YES = CHECK + ' YES'
BUTTON_NO = CANCEL + ' NO'

BUTTON_SETTINGS = "⚙ SETTINGS"
BUTTON_INFO = "ℹ INFO"

BUTTON_SEARCH_RADIUS = "🎯 CHANGE RADIUS"
BUTTON_SEARCH_TYPE = "🏷 CHANGE TYPE"

BUTTON_SEND_LOCATION = {
    'text': "📍 SEND LOCATION",
    'request_location': True,
}



# ================================
# TEXT VARIABLES
# ================================


INFO_TEXT = \
"""
*SearchAroundBot* enables you to search for useful sites in your vicinity. \
Currently it includes *🚰 DRINKING WATER*, *🚽 PUBLIC TOILETS* and *💊 PHARMACIES* as search items. \
New items will be introduced in the future.

🗺 All data has been retrieved from [OpenStreetMap](http://www.openstreetmap.org/) and \
[GoogleMap](https://developers.google.com/maps/).
Users can contribute by suggesting additional locations.

*DISCLAIMER*: By using this service, you acknowledge that you understand that it is solely \
your responsibility to verify any information you may obtain herein.
We expressly disclaim all liability for damages of any kind arising out of use, \
reference to, or reliance on any information provided by this service.

⭐ If you like this bot, please rate it on [StoreBot](telegram.me/storebot?start=SearchAroundBot).
📩 To get in touch with us, please send a message to @kercos.
"""

START_INSTRUCTIONS = "If you want to change the *radius* of the search " \
                     "or the *search item* please press the *⚙ SETTINGS* button."


# ================================
# TELL FUNCTIONS
# ================================

def broadcast(sender, msg, restart_user=False, curs=None, enabledCount = 0):
    #return

    BROADCAST_COUNT_REPORT = utility.unindent(
        """
        Mesage sent to {} people
        Enabled: {}
        Disabled: {}
        """
    )

    users, next_curs, more = Person.query().fetch_page(50, start_cursor=curs)
    try:
        for p in users:
            if p.enabled:
                enabledCount += 1
                if restart_user:
                    restart(p)
                tell(p.chat_id, msg, sleepDelay=True)
    except datastore_errors.Timeout:
        sleep(1)
        deferred.defer(broadcast, sender, msg, restart_user, curs, enabledCount)
        return
    if more:
        deferred.defer(broadcast, sender, msg, restart_user, next_curs, enabledCount)
    else:
        total = Person.query().count()
        disabled = total - enabledCount
        msg_debug = BROADCAST_COUNT_REPORT.format(str(total), str(enabledCount), str(disabled))
        tell(sender.chat_id, msg_debug)


def getInfoCount():
    c = Person.query().count()
    msg = "We are now in {} people subscribed to SearchAroundBot! ".format(str(c))
    return msg


def tell_masters(msg, markdown=False, one_time_keyboard=False):
    for id in key.MASTER_CHAT_ID:
        tell(id, msg, markdown=markdown, one_time_keyboard = one_time_keyboard, sleepDelay=True)

def tellAdministrators(msg):
    for id in key.AMMINISTRATORI_ID:
        tell(id, msg)

def tell(chat_id, msg, kb=None, markdown=True, inlineKeyboardMarkup=False,
         one_time_keyboard=False, sleepDelay=False):
    replyMarkup = {
        'resize_keyboard': True,
        'one_time_keyboard': one_time_keyboard
    }
    if kb:
        if inlineKeyboardMarkup:
            replyMarkup['inline_keyboard'] = kb
        else:
            replyMarkup['keyboard'] = kb
    try:
        resp = urllib2.urlopen(key.BASE_URL + 'sendMessage', urllib.urlencode({
            'chat_id': chat_id,
            'text': msg,  # .encode('utf-8'),
            'disable_web_page_preview': 'true',
            'parse_mode': 'Markdown' if markdown else '',
            # 'reply_to_message_id': str(message_id),
            'reply_markup': json.dumps(replyMarkup),
        })).read()
        logging.info('send response: ')
        logging.info(resp)
    except urllib2.HTTPError, err:
        if err.code == 403:
            p = person.getPersonByChatId(chat_id)
            p.setEnabled(False, put=True)
            logging.info('Disabled user: ' + p.name.encode('utf-8') + ' ' + str(chat_id))
        else:
            logging.debug('Raising unknown err in tell() with msg = ' + msg)
            raise err
    if sleepDelay:
        sleep(0.1)

def tell_person(chat_id, msg, markdown=False):
    tell(chat_id, msg, markdown=markdown)
    p = person.getPersonByChatId(chat_id)
    if p and p.enabled:
        return True
    return False

def sendText(p, text, markdown=False, restartUser=False):
    split = text.split()
    if len(split) < 3:
        tell(p.chat_id, 'Commands should have at least 2 spaces')
        return
    if not split[1].isdigit():
        tell(p.chat_id, 'Second argumnet should be a valid chat_id')
        return
    id = int(split[1])
    text = ' '.join(split[2:])
    if tell_person(id, text, markdown=markdown):
        user = person.getPersonByChatId(id)
        if restartUser:
            restart(user)
        tell(p.chat_id, 'Successfully sent text to ' + user.getFirstName())
    else:
        tell(p.chat_id, 'Problems in sending text')

# ================================
# LEAVE CHAT
# ================================

def leaveChat(chat_id, title):
    try:
        data = {
            'chat_id': chat_id,
        }
        resp = requests.post(key.BASE_URL + 'leaveChat', data)
        logging.info('Leave Chat Response: {}'.format(resp.text))
        tell(key.FEDE_CHAT_ID, 'Bot is leaving (super)group {}'.format(title))
    except urllib2.HTTPError, err:
        logging.info('Unknown exception: ' + str(err))


def sendLocation(chat_id):
    try:
        resp = urllib2.urlopen(key.BASE_URL + 'leaveChat', urllib.urlencode({
            'chat_id': chat_id,
        })).read()
        logging.info('send location: ')
        logging.info(resp)
    except urllib2.HTTPError, err:
        if err.code == 403:
            p = Person.query(Person.chat_id == chat_id).get()
            p.enabled = False
            p.put()
            logging.info('Disabled user: ' + p.getUserInfoString())
        else:
            logging.info('Unknown exception: ' + str(err))

# ================================
# SEND LOCATION
# ================================

def sendLocation(chat_id, latitude, longitude):
    try:
        resp = urllib2.urlopen(key.BASE_URL + 'sendLocation', urllib.urlencode({
            'chat_id': chat_id,
            'latitude': latitude,
            'longitude': longitude,
        })).read()
        logging.info('send location: ')
        logging.info(resp)
    except urllib2.HTTPError, err:
        if err.code == 403:
            p = Person.query(Person.chat_id == chat_id).get()
            p.enabled = False
            p.put()
            logging.info('Disabled user: ' + p.getUserInfoString())
        else:
            logging.info('Unknown exception: ' + str(err))


# ================================
# SEND PHOTO
# ================================

def sendPhoto(chat_id, img):
    try:
        resp = multipart.post_multipart(
            key.BASE_URL + 'sendPhoto', [('chat_id', str(chat_id)),],
            [('photo', 'image.jpg', img)]
        )
        logging.info('send photo:')
        logging.info(resp)
    except urllib2.HTTPError, err:
        if err.code == 403:
            p = Person.query(Person.chat_id == chat_id).get()
            p.enabled = False
            p.put()
            logging.info('Disabled user: ' + p.getUserInfoString())
        else:
            logging.info('Unknown exception: ' + str(err))

def sendPhotoFileId(chat_id, file_id):
    try:
        resp = urllib2.urlopen(key.BASE_URL + 'sendLocation', urllib.urlencode({
            'chat_id': chat_id,
            'photo': file_id,
        })).read()
        logging.info('send photo:')
        logging.info(resp)
    except urllib2.HTTPError, err:
        if err.code == 403:
            p = Person.query(Person.chat_id == chat_id).get()
            p.enabled = False
            p.put()
            logging.info('Disabled user: ' + p.getUserInfoString())
        else:
            logging.info('Unknown exception: ' + str(err))


# ================================
# SEND VENUE
# ================================

def sendVenue(chat_id, latitude, longitude, title, address):
    try:
        resp = urllib2.urlopen(key.BASE_URL + 'sendVenue', urllib.urlencode({
            'chat_id': chat_id,
            'latitude': latitude,
            'longitude': longitude,
            'title': title,
            'address': address,
        })).read()
        logging.info('send venue: ')
        logging.info(resp)
    except urllib2.HTTPError, err:
        if err.code == 403:
            p = Person.query(Person.chat_id == chat_id).get()
            p.enabled = False
            p.put()
            logging.info('Disabled user: ' + p.getUserInfoString())
        else:
            logging.info('Unknown exception: ' + str(err))


# ================================
# RESTART
# ================================
def restart(p, msg=None):
    if msg:
        tell(p.chat_id, msg)
    redirectToState(p, 0)


# ================================
# SWITCH TO STATE
# ================================
def redirectToState(p, new_state, **kwargs):
    if p.state != new_state:
        logging.debug("In redirectToState. current_state:{0}, new_state: {1}".format(str(p.state),str(new_state)))
        p.setState(new_state)
    repeatState(p, **kwargs)

# ================================
# REPEAT STATE
# ================================
def repeatState(p, **kwargs):
    methodName = "goToState" + str(p.state)
    method = possibles.get(methodName)
    if not method:
        tell(p.chat_id,
             "We have encountered a problem, and we have send a notification to the administrators. "
             "You will be now redirected to the home screen.")
        tell(key.FEDE_CHAT_ID,
             "Detected error for user {}: unexisting method {}.".format(p.getUserInfoString(), methodName))
        restart(p)
    else:
        method(p, **kwargs)


# ================================
# GO TO STATE 0: Initial Screen - Search Location
# ================================

def goToState0(p, input=None, **kwargs):
    location = kwargs['location'] if 'location' in kwargs else None
    giveInstruction = location is None and input is None
    type = p.getSearchType()
    type_symbol = type.split(' ')[0]
    ADD_NEW_BUTTON = "ADD {}".format(type_symbol)
    if giveInstruction:
        radius = p.search_radius
        msg = "Please send me your *📍 LOCATION* and I will give you the closest *{}* " \
              "within a radius of *{} Km*.".format(type, radius)
        kb = [
            [BUTTON_SEND_LOCATION],
            [BUTTON_SETTINGS, BUTTON_INFO]
        ]

        if type in parameters.EDITABLE_SEARCH_TYPES:
            kb[0].append(ADD_NEW_BUTTON)

        tell(p.chat_id, msg, kb)
    else:
        if location != None:
            p.setLocation(location['latitude'], location['longitude'], False)
            sortedLocations = osmQuery.getSortedLocationsWithinRadious(p)
            if sortedLocations==None: # Detected Exception: Deadline exceeded while waiting for HTTP response from URL
                tell(p.chat_id, "I am sorry, the Overpass server seems to be overcrowded at the moment, "
                                "please try again later.")
                restart(p)
            else:
                p.search_locations = sortedLocations
                foundLocation = len(sortedLocations) > 0
                p.increaseSearchCount()
                search.addSearch(p, foundLocation)
                redirectToState(p, 1)
        elif input == '':
            tell(p.chat_id, "Not a valid input.")
        elif input == ADD_NEW_BUTTON:
            redirectToState(p, 2)
        elif input == BUTTON_SETTINGS:
            redirectToState(p, 9)
        elif input == BUTTON_INFO:
            tell(p.chat_id, INFO_TEXT)
        elif p.isAdmin():
            dealWithAdminCommands(p, input)
        else:
            tell(p.chat_id, FROWNING_FACE + " Sorry, I don't understand your request")

def dealWithAdminCommands(p, input):
    inputSplit = input.split(' ')
    commandBodyStartIndex = len(inputSplit[0]) + 1
    if input=='/getInfoCounts':
        msg = getInfoCount()
        tell(p.chat_id, msg)
    elif input == '/testPhoto':
        redirectToState(p, 22)
    elif input.startswith('/sendText'):
        sendText(p, input, markdown=True)
    elif input.startswith('/sendTextRestart'):
        sendText(p, input, markdown=True, restartUser=True)
    elif input.startswith('/deleteContribution'):
        lat = float(inputSplit[1])
        lon = float(inputSplit[2])
        if contribution.deleteContribution(lat, lon):
            tell(p.chat_id, 'Contribution entry deleted successfully')
        else:
            tell(p.chat_id, 'Problems in deleting the contribution')
    elif input.startswith('/broadcast ') and len(input) > commandBodyStartIndex:
        msg = input[commandBodyStartIndex:]
        logging.debug("Starting to broadcast " + msg)
        deferred.defer(broadcast, p, msg, restart_user=False)
    elif input.startswith('/restartBroadcast ') and len(input) > commandBodyStartIndex:
        msg = input[commandBodyStartIndex:]
        logging.debug("Starting to broadcast " + msg)
        deferred.defer(broadcast, p, msg, restart_user=True)
    elif input.startswith('/getPhotoFromFileId'):
        file_id = inputSplit[1]
        sendPhoto(p.chat_id, file_id)
    else:
        tell(p.chat_id, FROWNING_FACE + " Sorry master, I don't understand your request")

# ================================
# GO TO STATE 1: Ask for map
# ================================

def goToState1(p, input=None, **kwargs):
    giveInstruction = input is None
    sortedLocations = p.search_locations
    totalElements = len(sortedLocations)
    type = p.getSearchType()
    radius = p.search_radius
    if giveInstruction:
        if sortedLocations:
            nearestLocation = sortedLocations[0]
            logging.debug("nearest location:" + str(nearestLocation))
            lat = nearestLocation[0]
            lon = nearestLocation[1]
            dist = geoUtils.formatDistance(nearestLocation[2])
            nearestLocationIsClosed = not nearestLocation[3]
            if totalElements == 1:
                tell(p.chat_id,
                     "This is the only {} location within a radius of {} Km "
                     "from the specified location (aerial distance {}):".format(type, radius, dist))
                sendLocation(p.chat_id, lat, lon)
                if nearestLocationIsClosed:
                    tell(p.chat_id, "This location seems to be closed, please go in ⚙ SETTINGS "
                                    "if you want to set a bigger radius for the search.")
                sleep(1)
                restart(p)
            else:
                remainingElementsCount = totalElements-1
                tell(p.chat_id,
                     "This is the nearest {} location found within a radius of {} Km " \
                     "from the specified location (aerial distance {}):".format(type, radius, dist))
                sendLocation(p.chat_id, lat, lon)
                # sendVenue(p.chat_id, lat, lon, "Drinking water", "distance = 200 m")
                sleep(0.5)
                msg = ''
                if nearestLocationIsClosed:
                    msg += "This location seems to be closed. "
                variableString = 'are {} other {} locations'.format(remainingElementsCount,type) \
                    if remainingElementsCount>1 \
                    else 'is 1 other {} location'.format(type)
                tell(p.chat_id, msg + \
                     "There are {} within this radius. "
                     "Shall I send you an image with the map?".format(variableString),
                     kb=[[BUTTON_YES,BUTTON_NO]], one_time_keyboard=True)
        else: # no location found
            nextRadius = p.getNextSearchRadius()
            if nextRadius:
                tell(p.chat_id,
                     "No {} found within a radius of {} Km from the specified location. "
                     "Do you want to increase the search to a radius of {} Km?".format(type, radius, nextRadius),
                     kb = [[BUTTON_YES, BUTTON_NO]], one_time_keyboard=True)
                # "You can go in ⚙ SETTINGS to increase the search radius."
            else:
                tell(p.chat_id,
                     "No {} found within a radius of {} Km from the specified location. ".format(type, radius))
                sleep(1)
                restart(p)

    else:
        if input == '':
            tell(p.chat_id, "Not a valid input.")
        elif input == BUTTON_YES and totalElements>1:
            someAreClosed = any(not e[3] for e in sortedLocations)
            img = osmQuery.getMapImgDrinkingWater(p)
            p.setState(0) #to avoid multiple button presses
            sendPhoto(p.chat_id, img)
            if someAreClosed:
                tell(p.chat_id, "Closed locations are marked in gray.")
            sleep(1)
            redirectToState(p, 3)  # ask to vote (with check)
        elif input == BUTTON_NO and totalElements>1:
            redirectToState(p, 3) #ask to vote (with check)
        elif input == BUTTON_YES and totalElements == 0:
            location = {
                'latitude': p.location.lat,
                'longitude': p.location.lon
            }
            p.search_radius = p.getNextSearchRadius()
            redirectToState(p, 0, location=location)
        elif input == BUTTON_NO and totalElements == 0:
            restart(p)
        else:
            tell(p.chat_id, FROWNING_FACE + " Sorry, I don't understand your request. Press YES or NO.")

# ================================
# GO TO STATE 2: Report new location
# ================================

def goToState2(p, input=None, **kwargs):
    location = kwargs['location'] if 'location' in kwargs else None
    giveInstruction = location is None and input is None
    type = p.getSearchType()
    if giveInstruction:
        msg = "Please send me a precise location of a *{}* " \
              "which is currently not present in our map, using the paper clip below (📎).".format(type)
        tell(p.chat_id, msg, kb=[[BUTTON_BACK]])
    else:
        if location != None:
            p.setLocation(location['latitude'], location['longitude'], False)
            locationsInProximity = osmQuery.getSortedLocationsWithinRadious(
                p, parameters.MIN_DISTANCE_FROM_SAME_LOCATION)
            if locationsInProximity==None:
                logging.debug("")
                msg = "I am sorry, the Overpass server seems to be overcrowded at the moment, " \
                      "and I cannot verify if there is already a {} location in the proximity of your input location. " \
                      "Please try again later.".format(type)
                tell(p.chat_id, msg)
                restart(p)
            elif len(locationsInProximity)>0:
                logging.debug("Detected nearby location")
                msg = "❗ I detected another {} location very close to the input location.".format(type)
                tell(p.chat_id, msg)
                repeatState(p)
            else:
                redirectToState(p, 21)
        elif input == '':
            tell(p.chat_id, "Not a valid input.")
        elif input == BUTTON_BACK:
            restart(p)
        elif input == BUTTON_SEARCH_RADIUS:
            redirectToState(p, 91)
        elif input == BUTTON_SEARCH_TYPE:
            redirectToState(p, 92)
        else:
            tell(p.chat_id, FROWNING_FACE + " Sorry, I don't understand your request")

# ================================
# GO TO STATE 21: Confirm new location
# ================================

def goToState21(p, input=None, **kwargs):

    CONFIRM_TEXT = unindent(
        """\
        I am about to insert a new *{}* location\
        into [OpenStreetMap](http://www.openstreetmap.org/).\
        Please make sure you have sent a *correct* and *accurate* location.

        Are you sure you want to proceed?"""
    )

    giveInstruction = input is None
    type = p.getSearchType()
    if giveInstruction:
        reply_txt = CONFIRM_TEXT.format(type)
        tell(p.chat_id, reply_txt, kb=[[BUTTON_YES, BUTTON_NO]], one_time_keyboard=True)
    else:
        if input == '':
            tell(p.chat_id, "Not a valid input.")
        elif input == BUTTON_YES:
            redirectToState(p, 22) #picture
        elif input == BUTTON_NO:
            restart(p)
        else:
            tell(p.chat_id, FROWNING_FACE + " Sorry, I don't understand your request. Please use the buttons.")

# ================================
# GO TO STATE 22: Ask for picture
# ================================

def goToState22(p, input=None, **kwargs):

    BUTTON_SKIP_PHOTO = "Skip Photo"

    ASK_PICTURE_TEXT = unindent(
        """\
        We encourage our contributors to send a *photo of the new location*.\
        A link to the picture will be attached to the new location created in OpenStreetMap\
        and will serve as supporting evidence for OpenStreetMap validators.

        Could you send me a photo of the {} location?\
        If so please send me the photo using the paper clip below (📎)."""
    )

    THANKS_TEXT = unindent(
        """\
        🙏  Thanks for your contribution!
        The location has been submitted to OpenStreetMap.\
        It will be stortily available in the\
        [online map](http://www.openstreetmap.org/#map=18/{}/{})\
        and in SearchAroundBot."""
    )

    photo = kwargs['photo'] if 'photo' in kwargs else None
    giveInstruction = input is None and photo == None
    type = p.getSearchType()

    if giveInstruction:
        reply_txt = ASK_PICTURE_TEXT.format(type)
        tell(p.chat_id, reply_txt, kb=[[BUTTON_SKIP_PHOTO]], one_time_keyboard=True)
    else:
        if input == BUTTON_SKIP_PHOTO:
            file_id = None
        elif photo:
            logging.debug("Photo field: " + str(photo))
            file_id = photo[-1]['file_id']
        else:
            tell(p.chat_id, "Not a valid type of input. "
                            "Please send me a photo or press the \\'{0}\\' button.".format(BUTTON_SKIP_PHOTO))
            return
        # both with and without picture
        lat = p.location.lat
        lon = p.location.lon
        tell(p.chat_id, THANKS_TEXT.format(lat, lon))
        restart(p)
        photo_url = parameters.PHOTO_BASE_URL + file_id if file_id else None
        node_id = osmEdit.insertNewLocation(lat, lon, p.getSearchType(), p.chat_id, photo_url)
        contribution.addContribution(p, node_id, file_id)
        msg = "User {} has inserted the following new {}: {}, {}. ".format(p.getUserInfoString(), type, lat, lon)
        if photo_url:
            msg += "\nPicure [url]({})".format(photo_url)
        msg += "\n[online map](http://www.openstreetmap.org/#map=18/{}/{}".format(lat,lon)
        tell(key.FEDE_CHAT_ID, msg)
        #sendLocation(key.FEDE_CHAT_ID, p.location.lat, p.location.lon)

# ================================
# GO TO STATE 3: Vote Reminder (with check)
# ================================

RATE_REQUEST = \
"""⭐⭐⭐⭐⭐
Do you like this bot?
If so, please rate it on [StoreBot](telegram.me/storebot?start=SearchAroundBot) 😊
Thanks for your support! 🙏
"""

def goToState3(p, input=None, **kwargs):
    if not p.isTimeToRemindToVote():
        restart(p)
        return
    giveInstruction = input is None
    BUTTON_DONT_ASK_ME_AGAIN = "Don't ask me again"
    BUTTON_REMIND_ME_AGAIN = "Remind me later"
    if giveInstruction:
        tell(p.chat_id, RATE_REQUEST, kb=[[BUTTON_DONT_ASK_ME_AGAIN, BUTTON_REMIND_ME_AGAIN]], one_time_keyboard=True)
    else:
        if input == '':
            tell(p.chat_id, "Not a valid input.")
        elif input == BUTTON_DONT_ASK_ME_AGAIN:
            p.vote_reminder_enabled = False
            restart(p)
        elif input == BUTTON_REMIND_ME_AGAIN:
            restart(p)
        else:
            tell(p.chat_id, FROWNING_FACE + " Sorry, I don't understand your request. Please use the buttons.")


# ================================
# GO TO STATE 9: Settings
# ================================

def goToState9(p, input=None, **kwargs):
    giveInstruction = input is None
    if giveInstruction:
        reply_txt = "You are in the setting panel. " \
                    "Your current search type is *{}*  and " \
                    "your search radius is *{} Km*.".format(p.getSearchType(), p.search_radius)
        kb = [
            [BUTTON_SEARCH_RADIUS, BUTTON_SEARCH_TYPE],
            [BUTTON_BACK]
        ]

        tell(p.chat_id, reply_txt, kb)
    else:
        if input == '':
            tell(p.chat_id, "Not a valid input.")
        elif input == BUTTON_BACK:
            restart(p)
        elif input == BUTTON_SEARCH_RADIUS:
            redirectToState(p, 91)
        elif input == BUTTON_SEARCH_TYPE:
            redirectToState(p, 92)
        else:
            tell(p.chat_id, FROWNING_FACE + " Sorry, I don't understand your request")

# ================================
# GO TO STATE 91: change search radius
# ================================

def goToState91(p, input=None, **kwargs):
    giveInstruction = input is None
    radius = p.search_radius
    other_radii = [str(x) for x in parameters.POSSIBLE_RADII if x != radius]
    kb = utility.distributeElementMaxSize(other_radii)
    if giveInstruction:
        reply_txt = "Your search radius is *{} Km*. Please specify a new value ".format(radius)
        kb.append([BUTTON_BACK])
        tell(p.chat_id, reply_txt, kb)
    else:
        if input == '':
            tell(p.chat_id, "Not a valid input, please use one of the buttons.")
        elif input == BUTTON_BACK:
            restart(p)
        elif input in other_radii:
            p.search_radius = int(input)
            tell(p.chat_id, "Your new search radius has been set to *{} Km*.".format(input))
            #redirectToState(p, 9)
            restart(p)
        else:
            tell(p.chat_id, FROWNING_FACE + " Sorry, I don't understand your request")

# ================================
# GO TO STATE 92: change search type
# ================================

def goToState92(p, input=None, **kwargs):
    giveInstruction = input is None
    type = p.getSearchType()
    other_types = [x for x in parameters.POSSIBLE_SEARCH_TYPES if x != type]
    kb = utility.distributeElementMaxSize(other_types)
    if giveInstruction:
        reply_txt = "Your currently searching for *{}*. Please select a new type of search.".format(type)
        kb.append([BUTTON_BACK])
        tell(p.chat_id, reply_txt, kb)
    else:
        if input == '':
            tell(p.chat_id, "Not a valid input.")
        elif input == BUTTON_BACK:
            restart(p)
        elif input in other_types:
            p.search_type = input
            tell(p.chat_id, "Your new search type has been set to *{}*.".format(input))
            # redirectToState(p, 9)
            restart(p)
        else:
            tell(p.chat_id, FROWNING_FACE + " Sorry, I don't understand your request")


# ================================
# ================================
# ================================


class MeHandler(webapp2.RequestHandler):
    def get(self):
        urlfetch.set_default_fetch_deadline(60)
        self.response.write(json.dumps(json.load(urllib2.urlopen(key.BASE_URL + 'getMe'))))

class SetWebhookHandler(webapp2.RequestHandler):
    def get(self):
        urlfetch.set_default_fetch_deadline(60)
        allowed_updates = ["message","inline_query", "chosen_inline_result", "callback_query"]
        data = {
            'url': key.WEBHOOK_URL,
            'allowed_updates': json.dumps(allowed_updates),
        }
        resp = requests.post(key.BASE_URL + 'setWebhook', data)
        logging.info('SetWebhook Response: {}'.format(resp.text))
        self.response.write(resp.text)

class GetWebhookInfo(webapp2.RequestHandler):
    def get(self):
        urlfetch.set_default_fetch_deadline(60)
        resp = requests.post(key.BASE_URL + 'getWebhookInfo')
        logging.info('GetWebhookInfo Response: {}'.format(resp.text))
        self.response.write(resp.text)

class DeleteWebhook(webapp2.RequestHandler):
    def get(self):
        urlfetch.set_default_fetch_deadline(60)
        resp = requests.post(key.BASE_URL + 'deleteWebhook')
        logging.info('DeleteWebhook Response: {}'.format(resp.text))
        self.response.write(resp.text)

# ================================
# ================================
# ================================


class WebhookHandler(webapp2.RequestHandler):
    def post(self):
        urlfetch.set_default_fetch_deadline(60)
        body = json.loads(self.request.body)
        logging.info('request body:')
        logging.info(body)
        self.response.write(json.dumps(body))

        # update_id = body['update_id']
        if 'message' not in body:
            return
        message = body['message']
        # message_id = message.get('message_id')
        # date = message.get('date')
        if "chat" not in message:
            return
        # fr = message.get('from')
        chat = message['chat']

        chat_type = chat['type'] if 'type' in chat else None
        chat_title = chat['title'].encode('utf-8') if 'title' in chat else None
        chat_id = chat['id']
        if chat_type=='group' or chat_type=='supergroup':
            leaveChat(chat_id, chat_title)
            return

        if "first_name" not in chat:
            return
        text = message.get('text').encode('utf-8') if "text" in message else ''
        name = chat["first_name"].encode('utf-8')
        last_name = chat["last_name"].encode('utf-8') if "last_name" in chat else None
        username = chat["username"] if "username" in chat else None
        location = message["location"] if "location" in message else None
        contact = message["contact"] if "contact" in message else None
        photo = message["photo"] if "photo" in message else None

        # u'contact': {u'phone_number': u'393496521697', u'first_name': u'Federico', u'last_name': u'Sangati',
        #             u'user_id': 130870321}
        # logging.debug('location: ' + str(location))

        def reply(msg=None, kb=None, markdown=True, inlineKeyboardMarkup=False):
            tell(chat_id, msg, kb=kb, markdown=markdown, inlineKeyboardMarkup=inlineKeyboardMarkup)

        p = person.getPersonByChatId(chat_id)

        if p is None:
            # new user
            logging.info("Text: " + text)
            if text == '/help':
                reply(INFO_TEXT)
            elif text.startswith("/start"):
                p = person.addPerson(chat_id, name, last_name, username)
                reply("Hi {0}, welcome to *SearchAroundBot*! ".format(p.getFirstName()) + START_INSTRUCTIONS)
                restart(p)
                tell_masters("New user: " + p.getUserInfoString())
            else:
                reply("Press on /start if you want to begin. "
                      "If you encounter any problem, please contact @kercos")
        else:
            # known user
            p.updateUsername(username)
            if text == '/state':
                if p.state in STATES:
                    reply("You are in state " + str(p.state) + ": " + STATES[p.state])
                else:
                    reply("You are in state " + str(p.state))
            elif text.startswith("/start"):
                reply("Hi {0}, welcome back to *SearchAroundBot*! ".format(p.getFirstName()) + START_INSTRUCTIONS)
                p.setEnabled(True, put=False)
                restart(p)
            elif WORK_IN_PROGRESS and p.chat_id != key.FEDE_CHAT_ID:
                reply(UNDER_CONSTRUCTION + " The system is under maintanance, try again later.")
            else:
                logging.debug("Sending {0} to state {1}. Input: '{2}'".format(p.getFirstName(), str(p.state), text))
                repeatState(p, input=text, contact=contact, location=location, photo = photo)

    def handle_exception(self, exception, debug_mode):
        logging.exception(exception)
        tell(key.FEDE_CHAT_ID, "❗ Detected Exception: " + str(exception), markdown=False)

app = webapp2.WSGIApplication([
    ('/me', MeHandler),
    #    ('/_ah/channel/connected/', DashboardConnectedHandler),
    #    ('/_ah/channel/disconnected/', DashboardDisconnectedHandler),
    ('/photos/([^/]+)?', osmEdit.DownloadPhotoHandler),
    ('/set_webhook', SetWebhookHandler),
    ('/get_webhook_info', GetWebhookInfo),
    ('/delete_webhook', DeleteWebhook),
    (key.WEBHOOK_PATH, WebhookHandler),
], debug=True)

possibles = globals().copy()
possibles.update(locals())
