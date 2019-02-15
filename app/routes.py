from flask import jsonify

from app import app
from app import foursquare

@app.route
@app.route('/')
def index():
  return 'libm up and running!'

@app.route
@app.route('/social/foursquare/search/<string:search_param>')
def search(search_param):
  return jsonify(foursquare.venuSearch(search_param))