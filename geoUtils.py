from geopy.geocoders import Nominatim
from geopy.geocoders import GoogleV3
from geopy.distance import vincenty
from geopy.exc import GeocoderTimedOut
from geopy.exc import GeocoderServiceError
import math
import key
import googlemaps
import logging

#https://raw.githubusercontent.com/dakk/Italia.json/master/italia_comuni.json

GEOLOCATOR = Nominatim()
#GEOLOCATOR = GoogleV3(key.GOOGLE_API_KEY)

def getLocationFromName(locationName):
    try:
        location = GEOLOCATOR.geocode(locationName, timeout=10, exactly_one=True, language='it', region='it') #default one answer for Nominatim (not google)
        return location
    except GeocoderServiceError:
        logging.error('GeocoderServiceError occored')


def getLocationFromPosition(lat, lon):
    try:
        location = GEOLOCATOR.reverse((lat, lon), timeout=10, exactly_one=True, language='it') #default one answer for Nominatim (not google)
        return location
    except GeocoderServiceError:
        logging.error('GeocoderServiceError occored')


def distance(point1, point2):
    #point1 = (41.49008, -71.312796)
    #point2 = (41.499498, -81.695391)
    return vincenty(point1, point2).kilometers


def getLocationTest():
    #location = GEOLOCATOR.geocode("175 5th Avenue NYC") #default one answer for Nominatim (not google)
    #location = GEOLOCATOR.geocode("via garibaldi", exactly_one=False)
    location = GEOLOCATOR.reverse("52.509669, 13.376294", exactly_one=True, language='it')
    #address = location.address
    return location

def getLocationTest1():
    newport_ri = (41.49008, -71.312796)
    cleveland_oh = (41.499498, -81.695391)
    return vincenty(newport_ri, cleveland_oh).kilometers


# ================================
# ================================
# ================================


#gmaps = googlemaps.Client(key=key.GOOGLE_API_KEY)

# def test_Google_Map_Api():
#     # Geocoding an address
#     geocode_result = gmaps.geocode('bari')
#     logging.debug("gmaps geocode result: " + str(geocode_result))
#     return geocode_result

    # Look up an address with reverse geocoding
    #reverse_geocode_result = gmaps.reverse_geocode((40.714224, -73.961452))

"""
GOOGLE_LOCATOR = GoogleV3(key.GOOGLE_API_KEY)

def test_Google_Map_Api():
    geocode_result = GOOGLE_LOCATOR.geocode('bari', exactly_one=True)
    logging.debug("gmaps geocode result: " + str(geocode_result))
    return geocode_result
"""

# ================================
# ================================
# ================================

def formatDistance(dst):
    if (dst>=10):
        return str(round(dst, 0)) + " Km"
    if (dst>=1):
        return str(round(dst, 1)) + " Km"
    return str(int(dst*1000)) + " m"

# ================================
# ================================
# ================================

EARTH_RADIUS = 6371 #Earth's Radius in Kms.

def HaversineDistance(lat1, lon1, lat2, lon2):
    """Method to calculate Distance between two sets of Lat/Lon."""

    #Calculate Distance based in Haversine Formula
    dlat = math.radians(lat2-lat1)
    dlon = math.radians(lon2-lon1)
    a = math.sin(dlat/2) * math.sin(dlat/2) + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2) * math.sin(dlon/2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    d = EARTH_RADIUS * c
    return d
