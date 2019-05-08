# NOTE: Requires tweepy and couchdb packages (use pip to install)
# TODO: Handle TweepError from Tweepy API [ERROR HANDLING]
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
THRESHOLD = 60 * 50     # 50 minutes
MAX_QUERIES = 6
GEO_RADIAL = "-36.565842,145.043926,442km"
TWEET_LANGUAGE = 'en'
SEARCH_TWEET_AMOUNT = 1000 # TODO: MAKE THIS BIGGER FOR DEBUGGING
TIMEWAIT_AFTER_QUERY = 5
TIMEWAIT_NO_QUERIES_FOUND = 8

arcgis = geopy.ArcGIS(username="aphan1um", password="andyphan1",
                      referer="cloudteam63")


def get_auth():
    auth = tweepy.OAuthHandler('2znfHb14GLJ2x3RfoftrkQoCU', 'mT8zKjHNrsQhUE2nKd5Ob4uKppWgIZFFUlTylr1VlTqTFv02WK')
    auth.set_access_token('1121009594254249986-CuuaCvTUYqjKLS2uBROkk1cQMLDI30', 'bqwPb7pyqYiKbMA0qhXrfvc5cKJq7WXI6wsvBCQ0Hay7Y')
    return tweepy.API(auth)

def find_query(db_queries):
    chosen_doc = None
    attempts_made = 0

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
            print("[#%d] No idle queries available. Waiting %ds..." % (attempts_made, TIMEWAIT_NO_QUERIES_FOUND))
            attempts_made += 1
            sleep(TIMEWAIT_NO_QUERIES_FOUND)
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

def update_query_state(query_doc, db_query, db_geocodes,
                       last_tweet_ids=None, amount_added=0, amount_recv=1):
    print("Updating timestamp...")

    def f_edit(doc):
        update = False

        # update time (if the query received a lot of results, search it
        # again)
        new_time = time.time() - THRESHOLD * (1 - amount_added/(amount_recv + 15))
        if new_time > float(doc['last_ran']):
            doc['last_ran'] = str(new_time)
            update = True

        if amount_added > 0:
            if 'amount_added' in doc:
                doc['amount_added'] = str(int(doc['amount_added'] + amount_added))
            else:
                doc['amount_added'] = str(amount_added)

        if last_tweet_ids is not None:
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

        return doc if update else None

    retry_save(db_query, query_doc['_id'], None, f_edit, None)

def execute_api_search(query_doc, db_tweets, db_query, db_geocodes, api):
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
        for tweet in limit_handled(cur, api):
            print("\nProcessing tweet ID:\t%d" % tweet.id)
            total_tweets_iter += 1
            init_doc = prepare_twitter_doc(tweet, query_doc, db_geocodes, arcgis)

            if init_doc is not None:
                doc, added = retry_save(db_tweets, tweet.id,
                                        init_doc,
                                        modify_twitter_doc(query_doc, word),
                                        notify_twit_save_status)
                if added:
                    total_tweets_added += 1
                print("Tweet added status:\t%s" % added)

            new_since_ids[word] = max(new_since_ids[word],
                                      tweet._json['id_str'])

    # at the end update query details
    update_query_state(query_doc, db_query, db_geocodes,
                       last_tweet_ids=new_since_ids,
                       amount_added=total_tweets_added,
                       amount_recv=total_tweets_iter)

    print("Finished query (%d/%d tweets added)): %s" %
          (total_tweets_added, total_tweets_iter, word))


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
    execute_api_search(query_doc, db_tweets, db_queries, db_geocodes, api)

    print("Sleeping for %d seconds" % TIMEWAIT_AFTER_QUERY)
    sleep(TIMEWAIT_AFTER_QUERY) # 5 second sleep

print("Ending script...")