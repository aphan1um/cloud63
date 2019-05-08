# NOTE: Requires tweepy and couchdb packages (use pip to install)
#
# TODO: Handle  TweepError from Tweepy API [ERROR HANDLING]
#
import tweepy
import couchdb
import time
import geopy
from time import sleep
from random import randint
from twitterutils import *
from collections import defaultdict

########################   ADD CONSTANTS HERE:   ######################
THRESHOLD = 60 * 60     # 1 hour
MAX_QUERIES = 6
GEO_RADIAL = "-36.565842,145.043926,442km"
TWEET_LANGUAGE = 'en'
SEARCH_TWEET_AMOUNT = 25 # TODO: MAKE THIS BIGGER FOR DEBUGGING

arcgis = geopy.ArcGIS(username="aphan1um", password="andyphan1",
                      referer="cloudteam63")


def get_auth():
    auth = tweepy.OAuthHandler('2znfHb14GLJ2x3RfoftrkQoCU', 'mT8zKjHNrsQhUE2nKd5Ob4uKppWgIZFFUlTylr1VlTqTFv02WK')
    auth.set_access_token('1121009594254249986-CuuaCvTUYqjKLS2uBROkk1cQMLDI30', 'bqwPb7pyqYiKbMA0qhXrfvc5cKJq7WXI6wsvBCQ0Hay7Y')
    return tweepy.API(auth)

def find_query(db_queries):
    chosen_doc = None

    print("Preparing to choose a query to search...")

    # in the query database section, look for a phrase/term which hasn't
    # been searched for a while or not at all.
    while True:
        startTime = time.time() - THRESHOLD
        view = db_queries.view("queryDD/last_ran",
                    startkey=str(startTime), descending='true',
                    limit=MAX_QUERIES)
        all_queries = [q for q in view]

        if len(all_queries) == 0:
            print("No idle queries to use for search. Waiting...")
            sleep(10)
            continue

        # select random query
        rand_idx = randint(0, len(all_queries)) - 1
        chosen_query = all_queries[rand_idx].id

        # now attempt to update value
        new_doc = db_queries[chosen_query]
        new_doc["last_ran"] = str(time.time())
        
        # inform DB that we're using this query. TODO: shitty code?
        try:
            db_queries.save(new_doc)
        except couchdb.http.ResourceConflict as e:
            print("Failed to find query. Waiting...")
            sleep(5) # wait for a bit
        else:
            print("Query selected:\t%s" % new_doc['_id'])
            break
    
    return new_doc

def update_query_state(query_doc, last_tweet_ids, db_query, db_geocodes):
    print("Updating timestamp...")

    def f_edit(doc):
        update = False

        # update time
        new_time = time.time()
        if new_time > float(doc['last_ran']):
            print("Time got update: %f" % float(doc['last_ran']))
            doc['last_ran'] = str(new_time)
            update = True

        num_new = 0
        if 'since_ids' not in doc:
            doc['since_ids'] = {}
            num_new += 1
        
        for term, since_id in last_tweet_ids.items():
            if term in doc['since_ids']:
                old_since_id = int(doc['since_ids'][term])
                if since_id > old_since_id:
                    doc['since_ids'][term] = str(since_id)
                    num_new += 1
            else:
                doc['since_ids'][term] = str(since_id)
                num_new += 1

        if num_new > 0:
            update = True

        print("Updating document?\t%s" % update)
        return doc if update else None

    retry_save(db_query, query_doc['_id'], None, f_edit, None)

def execute_api_search(query_doc, db_tweets, db_query, db_geocodes):
    # NOTES:
    #
    # 1. We're guaranteed to at least have a user location, since
    #    we're filtering through Twitter SEARCH API (geocode)
    #
        
    queries = [query_doc['_id']]
    if 'abbrev' in query_doc:
        queries += query_doc["abbrev"]

    print("Queries (including abbrevs):\t%s" % queries)
    new_since_ids = defaultdict(int)

    total_tweets_iter = 0
    total_tweets_added = 0

    for word in queries:
        print("** Now querying term:\t%s" % word)
        
        if 'since_ids' in query_doc and word in query_doc['since_ids']:
            since_id = int(query_doc['since_ids'][word])
        else:
            since_id = 0
        
        cur = tweepy.Cursor(api.search, q=word, lang=TWEET_LANGUAGE,
                            geocode=GEO_RADIAL, tweet_mode='extended',
                            since_id=since_id).items(SEARCH_TWEET_AMOUNT)

        #if tweet.place is not None or tweet.geo is not None or tweet.coordinates is not None:
        for tweet in limit_handled(cur):
            print("\nProcessing tweet ID:\t%d" % tweet.id)
            total_tweets_iter += 1
            init_doc = prepare_twitter_doc(tweet, query_doc, word,
                                           db_geocodes, arcgis)

            if init_doc is not None:
                doc, added = retry_save(db_tweets, tweet.id,
                                        init_doc,
                                        modify_twitter_doc,
                                        notify_twit_save_status)
                if added:
                    total_tweets_added += 1
                print("Tweet added status:\t%s" % added)

            new_since_ids[word] = max(new_since_ids[word],
                                      tweet._json['id_str'])

    # at the end update query details
    update_query_state(query_doc, new_since_ids, db_query, db_geocodes)

    print("Finished query (%d/%d tweets added)): %s" %
          (total_tweets_added, total_tweets_iter, query_doc['_id']))


#########################    MAIN CODE BELOW    #########################

print("Starting script...")

# setup arcgis geopy
api = get_auth()
db_url = "http://user:pass@127.0.0.1:5700/"
server = couchdb.Server(db_url)

db_tweets = server["tweets_new"]
db_geocodes = server["geocodes"]
db_queries = server["tweet_queries"]

while True:
    query_doc = find_query(db_queries)
    execute_api_search(query_doc, db_tweets, db_queries, db_geocodes)

    print("Sleeping a bit...")
    sleep(3) # 3 second sleep

start_api_search()
print("Ending script...")