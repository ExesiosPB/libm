import requests
import re
import GetOldTweets3 as got
import numpy
import pandas

from eventregistry import *
from textblob import TextBlob
from flask import jsonify

from app import app
from app import foursquare

@app.route('/')
def index():
  return 'libm up and running!'

er = EventRegistry(apiKey="ea65963c-c150-445c-adc2-51948f1b93e3")

@app.route('/news/<string:search_param>')
def newsSearch(search_param):
  query = QueryArticlesIter(
    keywords=search_param
  )
  articles = []
  for article in query.execQuery(er, sortBy="rel", maxItems=1000):
    articles.append(article)

  return jsonify({ "articles": articles})

@app.route('/services_news/<string:service_type>/<string:search_param>')
def newsServicesSearch(service_type, search_param):
  keys = [service_type, search_param]
  query = QueryArticlesIter(
    keywords=keys
  )

  articles = []
  for article in query.execQuery(er, sortBy="sourceImportance", maxItems=1000):
    articles.append(article)

  return jsonify({ "articles": articles })

@app.route('/services_news/nlp/<string:service_type>/<string:search_param>')
def newServicesNLPSearch(service_type, search_param):
  keys = [service_type, search_param]
  query = QueryArticlesIter(keywords=keys)
  
  a = []
  for article in query.execQuery(er, sortBy="rel", maxItems=1000):
    body = article['body']
    
    # We now clean the body
    body = body.lower()
    body = re.sub(r"\d+", "", body) # Remove numbers
    body = re.sub(r'[^\w\s]','', body) # Remove punc
    body = body.strip() # Remove white spaces
    a.append({
      'body': body,
      'image': article['image'],
      'sentiment': article['sentiment'],
      'source': article['source'],
      'title': article['title']
    })

  data = pandas.DataFrame(a)

  # Get word count for every body
  data['wordCount'] = data['body'].apply(lambda x: len(str(x).split(" ")))

  analytics = Analytics(er)
  data['category'] = numpy.array([analytics.categorize(body) for body in data['body']])

  text = ''
  for index, row in data.iterrows():
    text += ' ' + row['body']

  category = analytics.categorize(text)
  data.append(category, ignore_index=True)

  return data.to_json(orient='records')

@app.route('/social/foursquare/search/<string:search_param>')
def search(search_param):
  return jsonify(foursquare.venuSearch(search_param))

'''
These are categories from yelp:

arts, active, auto (Automotive), beautysvc, education, eventservices
financialservices, food, health, hotelstravel, localservices, nightlife
professional, publicservicesgovt, realestate, resturants, shopping

- These are gunna be merged too
(education + localservices + publicservicesgovt + financialservices) => 'Services'
(active + eventservices + nightlife) => 'Attractions'
(food + resturants + shopping) => 'Food & Shopping'
(health) => 'Health'
'''
@app.route('/social/yelp/cat_search/<string:search_param>/cat/<string:category>')
def yelpCatSearch(search_param, category):
  # Need to change food + shopping ['food', 'resturants', 'shopping']
  categories = {
    'Services': ['education', 'localservices', 'publicservicesgovt', 'financialservices'],
    'Attractions': ['active', 'eventservices', 'nightlife'],
    'Food & Shopping': ['resturants'],
    'Health': ['health'],
  }

  results = []
  # Gets the individual categories
  cats = categories[category]
  for c in cats:
    url = "https://api.yelp.com/v3/businesses/search?location={}&categories={}&limit=50".format(search_param, c)
    headers = {"Authorization": "Bearer 0ngzCmEKj_hY5omp-hzGgKuSNKZIJVkSIBXgcwYR4z2fnXrs9IOaclJ9wLzquM06q3wkGUe1eM7Wg1_rQjFGRcD-rX9LKov24F5UiqWiU-ksSVTyI04QX-O4Hm1xXHYx"}
    request = requests.get(url, headers=headers)
    if (request.status_code == 404):
      print(request)
    # print("REQUEST: {}".format(request))
    res = getAllYelpResults(request.json(), url)
    for r in res:
      results.append(r)

  return jsonify({'results': results})

def getAllYelpResults(firstRequest, url):
  headers = {"Authorization": "Bearer 0ngzCmEKj_hY5omp-hzGgKuSNKZIJVkSIBXgcwYR4z2fnXrs9IOaclJ9wLzquM06q3wkGUe1eM7Wg1_rQjFGRcD-rX9LKov24F5UiqWiU-ksSVTyI04QX-O4Hm1xXHYx"}
  total = firstRequest['total']
  count = total // 50
  results = []

  # Now do the requests
  if count == 0:
    for b in firstRequest['businesses']:
      results.append(b)
  else:
    for i in range(count):
      newUrl = url + "&offset={}".format(50 * i)
      request = requests.get(newUrl, headers=headers)
      if (request.status_code == 200):
        result = request.json()
        for b in result['businesses']:
          results.append(b)

  return results

@app.route('/social/yelp/search/<string:search_param>')
def yelpSearch(search_param):
  url = "https://api.yelp.com/v3/businesses/search?location={}&limit=50".format(search_param)
  headers = {"Authorization": "Bearer 0ngzCmEKj_hY5omp-hzGgKuSNKZIJVkSIBXgcwYR4z2fnXrs9IOaclJ9wLzquM06q3wkGUe1eM7Wg1_rQjFGRcD-rX9LKov24F5UiqWiU-ksSVTyI04QX-O4Hm1xXHYx"}
  request = requests.get(url, headers=headers).json()
  
  # The total amount of results
  total = request['total']
  # So we can only get 50 results at a time
  count = total // 50
  businesses = []
  for i in range(count):
    url = "https://api.yelp.com/v3/businesses/search?location={}&limit=50&offset={}".format(search_param, (50 * i))
    request = requests.get(url, headers=headers).json()
    for b in request['businesses']:
      businesses.append(b)

  return jsonify(businesses)

@app.route('/social/yelp/business/<string:id>')
def yelpBusinessSearch(id):
  url = "https://api.yelp.com/v3/businesses/{}".format(id)
  headers = {"Authorization": "Bearer 0ngzCmEKj_hY5omp-hzGgKuSNKZIJVkSIBXgcwYR4z2fnXrs9IOaclJ9wLzquM06q3wkGUe1eM7Wg1_rQjFGRcD-rX9LKov24F5UiqWiU-ksSVTyI04QX-O4Hm1xXHYx"}
  request = requests.get(url, headers=headers).json()
  return jsonify(request)

@app.route('/social/yelp/reviews/<string:id>')
def yelpReviews(id):
  url = "https://api.yelp.com/v3/businesses/{}/reviews".format(id)
  headers = {"Authorization": "Bearer 0ngzCmEKj_hY5omp-hzGgKuSNKZIJVkSIBXgcwYR4z2fnXrs9IOaclJ9wLzquM06q3wkGUe1eM7Wg1_rQjFGRcD-rX9LKov24F5UiqWiU-ksSVTyI04QX-O4Hm1xXHYx"}
  request = requests.get(url, headers=headers).json()
  return jsonify(request)

@app.route('/location/here/places/<string:search_param>')
def herePlacesSearch(search_param):
  APP_ID = 'nYEQjW3WrequOgHzvhmO'
  APP_CODE = 'ZmHg-w-tGJJCJSlhrsp9oA'
  url = "https://places.api.here.com/places/v1/discover/around?app_id={}&app_code={}&at=53.002666,-2.179404&size=100&pretty".format(APP_ID, APP_CODE)
  request = requests.get(url).json()
  return jsonify(request)

@app.route('/tweets/<string:search_param>')
def getTweets(search_param):
  tweets = scrapeTweets(search_param)
  print(tweets)
  return jsonify({'tweets': tweets})

@app.route('/sentiment/twitter/<string:search_param>')
def getSentimentTwitter(search_param):
  tweets = scrapeTweets(search_param)

  # Create pandas dataframe
  data = pandas.DataFrame(data=[tweet.text for tweet in tweets], columns=['Tweets'])
  # Add tweet length, date, likes, retweets
  # NOTE: THERE IS A BETTER WAY OFF DOING THIS, WHY ARENT WE DOING IT :(
  data['len'] = numpy.array([len(tweet.text) for tweet in tweets])
  data['date'] = numpy.array([tweet.date for tweet in tweets])
  data['likes'] = numpy.array([tweet.favorites for tweet in tweets])
  data['retweets'] = numpy.array([tweet.retweets for tweet in tweets])

  # Using TextBlob do sentiment, and then store
  data['sentiment'] = numpy.array([getTweetSentiment(tweet.text) for tweet in tweets])
  return data.to_json(orient="records")

def getTweetSentiment(tweet):
  tb = TextBlob(tweet)
  return tb.sentiment.polarity

# Cleans tweet by removing links and special characters
def cleanTweet(tweet):
  return ' '.join(re.sub("(@[A-Za-z0-9]+)([^0-9A-Za-z \t])|(\w+:\/\/\S+)", " ", tweet).split())

def scrapeTweets(search_param):
  # We create the array of the dates we are going to loop through here
  dates = ["2018-12-01", "2018-12-08", "2018-12-15", "2018-12-22", "2018-12-29", "2019-01-05", 
  "2019-01-12", "2019-01-19", "2019-01-26"]

  # Final array to store tweets
  tweets = []

  for i in range(len(dates)):
    # Check if the i is the last
    if (i + 1) != len(dates):
      dateNow = dates[i]
      dateNext = dates[i + 1]

      # Note we cap the tweets at 100
      tweetCriteria = got.manager.TweetCriteria().setQuerySearch(search_param).setSince(dateNow).setUntil(dateNext).setMaxTweets(100)
      # Get tweets and to final array
      ts = got.manager.TweetManager.getTweets(tweetCriteria)
      for t in ts:
        tweets.append(t)

  return tweets

@app.route('/gov/search/<string:search_param>')
def getGovSearch(search_param):
  departments = ["department-for-education", 
  "department-for-transport", 
  "department-of-health-and-social-care"]
  
  data = {}
  for i in range(len(departments)):
    d = departments[i]
    url = "https://www.gov.uk/api/search.json?q={}&filter_organisations={}&count=1000".format(search_param, d)
    request = requests.get(url).json()
    data['d'] = request

  return jsonify(data)

@app.route('/gov/search/<string:service_type>/<string:search_param>')
def getGovTypeSearch(service_type, search_param):
  organisation = 'department-for-transport'
  if (service_type == 'Transport'):
    organisation = 'department-for-transport'
  elif (service_type == 'Health'):
    organisation = 'department-of-health-and-social-care'
  elif (service_type == 'Education'):
    organisation = 'department-for-education'

  url = "https://www.gov.uk/api/search.json?q={}&filter_organisations={}&count=1000".format(search_param, organisation)
  request = requests.get(url).json()

  # Get semantics and categories
  analytics = Analytics(er)
  for i, r in enumerate(request['results']):
    body = r['description']
    sentiment = analytics.sentiment(body)
    request['results'][i]['sentiment'] = sentiment['avgSent']
    request['results'][i]['category'] = analytics.categorize(body)

  return jsonify(request)

@app.route('/companies_house/search/<string:search_param>')
def companiesHouseSearch(search_param):
  url = "https://api.companieshouse.gov.uk/search/companies?q={}".format(search_param)
  request = requests.get(url, auth=("	bOEXn8DV8wlDwRyHSC582fK6SW1W-TVJrLbCmJbE")).json()
  return jsonify(request)

@app.route('/companies_house/company/<string:search_param>')
def companiesHouseCompany(search_param):
  url = "https://api.companieshouse.gov.uk/company/{}".format(search_param)  
  request = requests.get(url, auth=("	bOEXn8DV8wlDwRyHSC582fK6SW1W-TVJrLbCmJbE")).json()
  return jsonify(request)
