import requests
from datetime import datetime

CLIENT_ID = '2OWPT1X5RNXEE0DGOM5VWO2FBM5R5TNTVPPLH50NCSZAX3QD'
CLIENT_SECRET = 'MR31FALKAQEL2SFUHJKMXJJ2XOTIMJIC5C0Y1UWFGJWWORE1'
DATE = datetime.today().strftime('%Y%m%d')

BASE_URL = 'https://api.foursquare.com/v2'
AUTH_URL_PART = 'client_id={}&client_secret={}&v={}'.format(CLIENT_ID, CLIENT_SECRET, DATE)

# Foursquare has a annoying 50 search result limit so,
# we need to do some query magic to get more than 50 results
# https://stackoverflow.com/questions/14211120/maximum-number-of-results-in-foursquare-api
def venuSearch(search_param):
  url = "{}/venues/search?near={}&limit=50&{}".format(BASE_URL, search_param, AUTH_URL_PART)
  request = requests.get(url)
  
  # We want get lat,lng of search param from response geocode
  res = request.json()
  geocode = res['response']['geocode']
  centerCoords = geocode['feature']['geometry']['center']
  lat = centerCoords['lat']
  lng = centerCoords['lng']

  # Make request, alter latlng then make another request
  venues = []
  count = 1
  finished = False
  while finished == False:
    req = requests.get("{}/venues/search?ll={},{}&limit=50&{}".format(BASE_URL, lat, lng, AUTH_URL_PART))
    res = req.json()
    
    ven = res['response']['venues']
    # Check to see if each new venue is already in list
    for v in ven:
      newVID = v['id']
      if len(venues) == 0:
        venues.append(v)
      else:
        if v in venues:
          break
        else:
          venues.append(v)

    count += 1
    if (count > 10):
      finished = True
    
    # Now adjust lat,lng
    lat += 0.01
    lng -= 0.01

  finalJSON = {
    'venues': venues
  }
  return finalJSON

def venuPhotos(venuID):
  url = "{}/venues/{}/photos?client_id={}&client_secret={}&v={}".format(BASE_URL, venuID, CLIENT_ID, CLIENT_SECRET, DATE)
  
  # Now perform request
  request = requests.get(url)
  return request.json()
