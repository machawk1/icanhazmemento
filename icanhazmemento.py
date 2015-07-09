#!/usr/bin/env python

# Code by Mat Kelly <mkelly@cs.odu.edu>

from twython import Twython, TwythonError
import sched, time, sys, re
import urllib2
import httplib

from dateutil import parser

from datetime import datetime
from babel.dates import format_datetime

TWITTER_APP_KEY = 'fFp3rOXOLPA1wwDj6MD6GbaiX'
TWITTER_APP_KEY_SECRET = 'niYMZpwd0OaJGn0z1gpQSnLDWCk6q9GCOINtzmGlTq7E76fw4h'
TWITTER_ACCESS_TOKEN = '3367922674-vsgE7hvQb3EAwaZEBmCrzd8ESSY83zsECp7Xxqc'
TWITTER_ACCESS_TOKEN_SECRET = '1bsKurzp3Af52qf0FLjRrRA6Wfw0uDz2aJFYM3PKtuEmf'

MEMENTO_AGGREGATOR_TIMEGATE = "http://timetravel.mementoweb.org/timegate/"
IA_SAVEWEBPAGE_URI = "http://web.archive.org/save/"

s = sched.scheduler(time.time, time.sleep)

lastTweetIdRespondedTo = -1

# Twitter maximum 2400 tweets per day
# = .027 tweets/sec = 1.67 tweets/min, so check every 101 seconds
HASHTAG_CHECK_RATE = 101 # seconds?

def runLoop(sc):
  global lastTweetIdRespondedTo
  
  t = Twython(app_key=TWITTER_APP_KEY, 
            app_secret=TWITTER_APP_KEY_SECRET, 
            oauth_token=TWITTER_ACCESS_TOKEN, 
            oauth_token_secret=TWITTER_ACCESS_TOKEN_SECRET)
            

  # Get all tweets my the hashtag

  search = t.search(q='#icanhazmemento',   #**supply whatever query you want here**
                  count=100)

  tweets = search['statuses']

  if len(tweets) is 0:
    print "No tweets yet with that hashtag"
    invokeNextPoll()
    return

  
  for tweet in tweets:
    #print tweet['id_str'], '\n', tweet['text'], '\n\n\n'
    if str(tweet['id']) == str(lastTweetIdRespondedTo):
      print "Newest hashtagged tweet has already been replied to."
      invokeNextPoll()
      return
    else:
      print "New tweet w/ id "+str(tweet['id'])+" != "+str(lastTweetIdRespondedTo)
    lastTweetIdRespondedTo = tweet['id']
    
    if 'url' not in tweet['user']['entities']:
      # No URI in tweet
      invokeNextPoll()
      return
    
    
    urls = tweet['user']['entities']['url']['urls']
    dateCreated = tweet['user']['created_at']
 
    #Convert date
    # From Thu Feb 13 12:16:09 +0000 2014 
    # To   Thu, 13 Feb 2014 12:16:09 GMT
    dt = parser.parse(dateCreated)
    format = 'EEE, dd LLL yyyy hh:mm:ss'
    acceptDatetime = format_datetime(dt, format, locale='en') + ' GMT'
  


  
    for url in urls:
      print "URI found in tweet: " + url['expanded_url']
      #print MEMENTO_AGGREGATOR_TIMEGATE + "http://matkelly.com"
      print "Querying aggregator at "
      print " * " + MEMENTO_AGGREGATOR_TIMEGATE + url['expanded_url']
      print " * Accept-Datetime: " + acceptDatetime
      request = urllib2.Request(MEMENTO_AGGREGATOR_TIMEGATE + url['expanded_url'], headers={"Accept-Datetime" : acceptDatetime})
      #request = urllib2.Request(MEMENTO_AGGREGATOR_TIMEGATE + "http://matkelly.com", headers={"Accept-Datetime" : acceptDatetime})
      try:
        response = urllib2.urlopen(request)
      except urllib2.HTTPError, e:
        if e.code == 404:
          print "We got a 404, submitting to the archive."
          print " * " + IA_SAVEWEBPAGE_URI + url['expanded_url']
          request2 = urllib2.Request(IA_SAVEWEBPAGE_URI + url['expanded_url'])
          
          try:
            response2 = urllib2.urlopen(request2)
          except:
            print "There was an error archiving this page. Moving on."
            invokeNextPoll()
            return
          #TODO: logic here to account for when robots blocks IA or the archiving procedure otherwise fails
          
          archiveURI = "http://web.archive.org" + response2.info().getheader("Content-Location")
          print " * " + archiveURI
          
          msg = "Your web page has been archived! " + archiveURI
          
          replyToTweet(t, tweet['id'],msg)
          
          invokeNextPoll()
          return
          
      contents = response.read()

      # Rudimentary parsing rather than regex
      linkHeaderEntities = response.info().getheader("Link").split(",")
      uri_m = ""
      for lhe in linkHeaderEntities:
        if 'rel="memento"' in lhe:
         uri_m = lhe[lhe.index("<")+1:lhe.index(">")]
         break
      #print "Tweet this URI: " + uri_m
      if uri_m is not "":
        msg = "Here is an archived version of your page! " + uri_m
        replyToTweet(t, tweet['id'], msg)
        
    invokeNextPoll()
  
# Extract link from tweet

# Extract date

def replyToTweet(t, tweetId, msg):
  print "Posting tweet in reply to tweetId " + str(tweetId) + " : " + msg
  try:
    a = t.update_status(status=msg, in_reply_to_status_id=tweetId)
    #return HttpResponse("1", content_type='text/plain')
  except TwythonError as e:
    #return HttpResponse(e, content_type='text/plain')
    ''''''

def invokeNextPoll():
  s.enter(5, 1, runLoop, (s,))


if __name__ == "__main__":
  #start timer to call loop
  DELAY = 5 # seconds?
  PRIORITY = 1
  s.enter(DELAY, PRIORITY, runLoop, (s,))
  s.run()