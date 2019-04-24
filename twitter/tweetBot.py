import tweepy

# Using: https://boundingbox.klokantech.com/
# With: https://developer.twitter.com/en/docs/tweets/filter-realtime/guides/basic-stream-parameters.html
bounding_box = [112.51, -44.19, 154.34, -9.8] # [72.2,-55.3,168.2,-9.1]

# The four keys needed for twitter bot
# TODO: Credit to https://stackoverflow.com/a/22889470
# TODO: Better store these keys (coming from aphan1)
# TODO: Harvest tweets from followers
consumer_key = "2znfHb14GLJ2x3RfoftrkQoCU"
consumer_secret = "mT8zKjHNrsQhUE2nKd5Ob4uKppWgIZFFUlTylr1VlTqTFv02WK"
access_key = "1121009594254249986-CuuaCvTUYqjKLS2uBROkk1cQMLDI30"
access_secret = "bqwPb7pyqYiKbMA0qhXrfvc5cKJq7WXI6wsvBCQ0Hay7Y"

auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_key, access_secret)
api = tweepy.API(auth)

# TODO: Using http://docs.tweepy.org/en/latest/streaming_how_to.html
class SimpleStreamListener(tweepy.StreamListener):
    def on_status(self, status):
        print("Tweet: " + status.text)

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