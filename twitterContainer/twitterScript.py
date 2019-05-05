# NOTE: Requires tweepy and couchdb packages (use pip to install)

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

def get_auth():
    auth = tweepy.OAuthHandler('2znfHb14GLJ2x3RfoftrkQoCU', 'mT8zKjHNrsQhUE2nKd5Ob4uKppWgIZFFUlTylr1VlTqTFv02WK')
    auth.set_access_token('1121009594254249986-CuuaCvTUYqjKLS2uBROkk1cQMLDI30', 'bqwPb7pyqYiKbMA0qhXrfvc5cKJq7WXI6wsvBCQ0Hay7Y')
    return tweepy.API(auth)

def limit_handled(cursor):
    while True:
        try:
            yield cursor.next()
        except tweepy.RateLimitError:
            print("[WARNING] Rate limit hit! 15 min wait...")
            time.sleep(15 * 60)

def start_realtime():
    # Using: https://boundingbox.klokantech.com/
    # With: https://developer.twitter.com/en/docs/tweets/filter-realtime/guides/basic-stream-parameters.html
    bounding_box = [112.51, -44.19, 154.34, -9.8] # [72.2,-55.3,168.2,-9.1]

    myStreamListener = SimpleStreamListener()
    myStream = tweepy.Stream(auth = api.auth, listener = myStreamListener)
    # this starts the real-time listener
    myStream.filter(locations = bounding_box, is_async = True)

api = get_auth()

db_url = "http://user:pass@127.0.0.1:5700/"
server = couchdb.Server(db_url)
tweetDB = server["twit"]


#########################    MAIN CODE HERE    #########################

query = 'soda OR butter OR "potato chips" OR "coca cola" OR cookie OR pastry OR unhealthy OR cake OR sugary'
geoc = "-36.565842,145.043926,442km"
total_tweets_counted = 0
total_tweets_accepted = 0

print("Starting script...")

for tweet in limit_handled(tweepy.Cursor(api.search, q=query, lang='en', geocode=geoc, tweet_mode='extended').items()):
    doc = tweet

    if tweet.place is not None or tweet.geo is not None or tweet.coordinates is not None:
        doc._json['_id'] = doc._json['id_str']
        total_tweets_counted += 1

        try:
            tweetDB.save(doc._json)
        except couchdb.http.ResourceConflict as e:
            print("Tweet already added: %s" % doc._json['_id'])
        else:
            print("Tweet accepted: %s" % doc._json['_id'])
            total_tweets_accepted += 1
    else:
        print("Skipped tweet: %s" % doc._json['id'])


print("Ending script... Counted: %d\tAccepted: %d" % (total_tweets_counted, total_tweets_accepted))