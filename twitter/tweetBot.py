import tweepy

# Using: https://boundingbox.klokantech.com/
# With: https://developer.twitter.com/en/docs/tweets/filter-realtime/guides/basic-stream-parameters.html
bounding_box = [112.51, -44.19, 154.34, -9.8] # [72.2,-55.3,168.2,-9.1]

# The four keys needed for twitter bot
# TODO: Credit to https://stackoverflow.com/a/22889470
consumer_key = ""
consumer_secret = ""
access_key = ""
access_secret = ""

auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_key, access_secret)
api = tweepy.API(auth)

# TODO: Using https://tweepy.readthedocs.io/en/v3.5.0/streaming_how_to.html
class SimpleStreamListener(tweepy.StreamListener):
    def on_status(self, status):
        print(status.text)

    def on_error(self, status_code):
        if status_code == 420:
            #returning False in on_data disconnects the stream
            return False


########### MAIN CODE HERE: ############
myStreamListener = MyStreamListener()

myStream = tweepy.Stream(auth = api.auth, listener = myStreamListener)
myStream.filter(locations = bounding_box, async = True) # this starts the real-time listener