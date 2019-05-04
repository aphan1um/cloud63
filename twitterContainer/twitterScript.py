import tweepy
from cloudant.client import CouchDB
import sys
import ast

# Using: https://boundingbox.klokantech.com/
# With: https://developer.twitter.com/en/docs/tweets/filter-realtime/guides/basic-stream-parameters.html
bounding_box = [112.51, -44.19, 154.34, -9.8] # [72.2,-55.3,168.2,-9.1]

# The four keys needed for twitter bot
# TODO: Credit to https://stackoverflow.com/a/22889470
# TODO: Harvest tweets from followers instead of real-time (??)
print(sys.argv[2])
print(sys.argv[1])
keys = ast.literal_eval(sys.argv[2])

# STEP: Connect to Twitter REST API services
auth = tweepy.OAuthHandler(keys["consumer_key"], keys["consumer_secret"])
auth.set_access_token(keys["access_key"], keys["access_secret"])
api = tweepy.API(auth)

# STEP: Connect to CouchDB (very prototypey)
# Help from: https://python-cloudant.readthedocs.io/en/latest/getting_started.html
db_url = sys.argv[1]
client = CouchDB("admin", "admin", url = db_url, connect = True)
tweetDB = client.create_database(keys["name"].lower())

if not tweetDB.exists():
    raise Exception("ERROR: Database %s was not created!" % keys["name"].lower())

# TODO: Using http://docs.tweepy.org/en/latest/streaming_how_to.html
class SimpleStreamListener(tweepy.StreamListener):
    def on_status(self, status):
        status._json['_id'] = status._json['id_str']
        tweetDB.create_document(status._json)

    def on_error(self, status_code):
        # TODO: Error handling
        if status_code == 420:
            # returning False in on_data disconnects the stream
            return False


########### MAIN CODE HERE: ############
myStreamListener = SimpleStreamListener()

myStream = tweepy.Stream(auth = api.auth, listener = myStreamListener)

# this starts the real-time listener
myStream.filter(locations = bounding_box, is_async = True)