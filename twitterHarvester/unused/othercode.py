import tweepy
import couchdb

class SimpleStreamListener(tweepy.StreamListener):
    def on_status(self, status):
        try:
            status._json['_id'] = status._json['id_str']
            tweetDB.save(status._json)
        except couchdb.http.ResourceConflict as e:
            print("Tweet already added: %s" % status._json['_id'])
        else:
            print("Tweet accepted: %s" % status._json['_id'])

    def on_error(self, status_code):
        # TODO: Error handling
        if status_code == 420:
            # returning False in on_data disconnects the stream
            return False

def start_realtime():
    # Using: https://boundingbox.klokantech.com/
    # With: https://developer.twitter.com/en/docs/tweets/filter-realtime/guides/basic-stream-parameters.html
    bounding_box = [112.51, -44.19, 154.34, -9.8] # [72.2,-55.3,168.2,-9.1]

    myStreamListener = SimpleStreamListener()
    myStream = tweepy.Stream(auth = api.auth, listener = myStreamListener)
    # this starts the real-time listener
    myStream.filter(track = ['hamburger', 'pizza'], is_async = False)

def get_auth():
    auth = tweepy.OAuthHandler('2znfHb14GLJ2x3RfoftrkQoCU', 'mT8zKjHNrsQhUE2nKd5Ob4uKppWgIZFFUlTylr1VlTqTFv02WK')
    auth.set_access_token('1121009594254249986-CuuaCvTUYqjKLS2uBROkk1cQMLDI30', 'bqwPb7pyqYiKbMA0qhXrfvc5cKJq7WXI6wsvBCQ0Hay7Y')
    return tweepy.API(auth)



api = get_auth()
db_url = "http://user:pass@127.0.0.1:5700/"
server = couchdb.Server(db_url)
tweetDB = server["debug"]

print("Starting realtime...")
start_realtime()