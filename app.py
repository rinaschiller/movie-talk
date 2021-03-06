#!/usr/bin/env python

from __future__ import print_function
from future.standard_library import install_aliases
install_aliases()

from urllib.parse import urlparse, urlencode
from urllib.request import urlopen, Request
from urllib.error import HTTPError

import json
import os
import datetime
import unicodedata

local_vars ={}

from flask import Flask
from flask import request
from flask import make_response

# Flask app should start in global layout
app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    req = request.get_json(silent=True, force=True)

    print("Request:")
    print(json.dumps(req, indent=4))

    res = processRequest(req)

    res = json.dumps(res, indent=4)
    # print(res)
    r = make_response(res)
    r.headers['Content-Type'] = 'application/json'
    return r


def processRequest(req):
    if req.get("result").get("action") != "movieData":
        return {}
      
#   base url for initial user query 
    baseurl = "https://api.themoviedb.org/3/search/movie?api_key=9fe2fdf8fcbeeb11ecec17e5e4f0276a&query="
#   Grabs paramter from user intent    
    yql_query = makeYqlQuery(req)
    if yql_query is None:
        return {}
#   Adds user search query to base url and grabs movie ID
    yql_url = baseurl + yql_query
    print(yql_url) 
    result = urlopen(yql_url).read()
    data = json.loads(result)
    movieID = str(data['results'][0]['id'])
    
#   Use movie ID in new link to query more details
    idurl = "https://api.themoviedb.org/3/movie/" + movieID + "?api_key=9fe2fdf8fcbeeb11ecec17e5e4f0276a"
    creditsurl = "https://api.themoviedb.org/3/movie/" + movieID + "/credits?api_key=9fe2fdf8fcbeeb11ecec17e5e4f0276a"
    
    creditsResult = urlopen(creditsurl).read()
    creditsData = json.loads(creditsResult)
    
    result = urlopen(idurl).read()
    data = json.loads(result)    

#   Call function to grab data
    res = makeWebhookResult(data, creditsData, req)
    return res


def makeYqlQuery(req):
    result = req.get("result")
    parameters = result.get("parameters")
    mTitle = parameters.get("title")
    if mTitle is None:
        return None
    #replace all spaces with +
    sTitle,x,y = ""," ","+"
    for char in mTitle:
        sTitle += y if char == x else char
    return sTitle

"""
    notes: Integers need to be converted to strings
"""
def makeWebhookResult(data, creditsData, req):
    result = req.get("result")
    metadata = result.get("metadata")
    intent = metadata.get("intentName")
    parameters = result.get("parameters")
   

#Getting fields from credit data
    #    director
    crew = creditsData.get('crew')
    for d in crew:
        for key in d:
            if d[key] == 'Director':
               director = d.get("name")

    #   Main cast names    
    castNames= []
    cast = creditsData.get('cast')
    count=0
    for d in cast:
      #     gets rid of accents in characters otherwise throws error
      name = unicodedata.normalize('NFD', d.get("name")).encode('ascii', 'ignore')
      castNames.append(name)
      count+=1
      if(count >= 4): #only grabs first four cast names (main cast)
          break
    #    formatting to be list of words with and before last word
    castNames = '{} and {}'.format(', '.join(castNames[:-1]), castNames[-1])
    
    #Identifying actor from character
    character = parameters.get('movie-character')
    for d in cast:
        for key in d:
            if d[key] == character:
                actor = d.get('name')
                
 #Getting fields from movie data    
    mTitle = data.get('title')
    budget = str(format(data.get('budget'),",d"))
    date = data.get('release_date')
    date = datetime.datetime.strptime(date, '%Y-%m-%d').strftime('%m/%d/%Y')
    revenue = format(data.get('revenue'), ",d")
    runtime = '{:d} hours and {:d} minutes'.format(*divmod(data.get('runtime'), 60))

#Speech outputs
    if (intent == "revenue"):
        speech = "The revenue of " + mTitle + " was $" + revenue
    elif (intent == "release-time"):
#        TODO: edit speech depending on past, future dates
        speech = mTitle + " was released on " + date
    elif (intent == "budget"):
        speech = "The movie " + mTitle + " had a budget of $" + budget
    elif (intent == "runtime"):
        speech = "The movie " + mTitle + " has a runtime of " + runtime
    elif(intent == 'director'):
        speech = "The director of " + mTitle + " was " + director
    elif(intent == 'cast'):
        speech = "The main cast of " + mTitle + " is " + castNames
    elif(intent=='identify-actor'):
        speech = character + " is played by " + actor

    print("Response:")
    print(speech)
    
    return {
       "speech": speech,
       "displayText": speech,
       "data": [character, actor],
       "contextOut": [],
       "source": "apiai-movie-db"
    }


if __name__ == '__main__':
   
    port = int(os.getenv('PORT', 5000))

    print("Starting app on port %d" % port)

    app.run(debug=False, port=port, host='0.0.0.0')
