# TODO: Handle TweepError from Tweepy API [ERROR HANDLING]
import tweepy, couchdb
import time, os
import geopy
from time import sleep
from collections import defaultdict

from twitterdoc import prepare_twitter_doc, modify_twitter_doc
from twitterutils import find_query, update_query_state, save_document

########################   CONSTANTS HERE:   ######################
#GEO_RADIAL = "-36.565842,145.043926,445km"
TWEET_LANGUAGE = 'en'
SEARCH_TWEET_AMOUNT = 1500
UPDATE_TIMESTAMP_PERIOD = 350
TIMEWAIT_AFTER_QUERY = 5

DB_URL = os.environ['DB_URL']
TASK_NUMBER = int(os.environ['DB_TASK_NUM'])
GEO_RADIAL = os.environ['GEO_RADIAL']

def get_auth(api_key, api_secret, access_token, access_secret):
    auth = tweepy.OAuthHandler(api_key, api_secret)
    auth.set_access_token(access_token, access_secret)
    return tweepy.API(auth)

def execute_api_search(query_doc, dbs, api):
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

        for tweet in limit_handled(cur, api):
            print("\nProcessing tweet ID:\t%d" % tweet.id)
            total_tweets_iter += 1
            if total_tweets_iter % UPDATE_TIMESTAMP_PERIOD == 0:
                update_query_state(query_doc, dbs['queries'], dbs['geocodes'])
            
            init_doc = prepare_twitter_doc(tweet, query_doc, \
                                           dbs['geocodes'], arcgis)

            if init_doc is not None:
                doc, added = save_document(dbs['tweets'], tweet.id,
                                        init_doc,
                                        modify_twitter_doc(query_doc, \
                                            dbs['geocodes'], arcgis))
                if added:
                    total_tweets_added += 1
                print("Tweet added status:\t%s" % added)
            else:
                print("[WARNING] Tweet found not within Victoria.")

            new_since_ids[word] = max(new_since_ids[word], tweet._json['id'])
            

    # at the end update query details
    update_query_state(query_doc, dbs['queries'], dbs['geocodes'],
                       last_tweet_ids=new_since_ids,
                       amount_added=total_tweets_added,
                       amount_recv=total_tweets_iter)

    print("Finished query (%d/%d tweets added)): %s" %
          (total_tweets_added, total_tweets_iter, word))


#########################    MAIN CODE BELOW    #########################

# get env variables set within Docker container
print("[INFO] Starting script for process #%d..." % TASK_NUMBER)
print("[INFO] Connecting to database: %s" % DB_URL)

server = couchdb.Server(DB_URL)

dbs = {'tweets': server["tweets"], 'geocodes': = server["geocodes"], \
       'queries': = server["tweet_queries"], 'api_keys' = server["api_keys"] }

total_apikeys = dbs['api_keys'].info()['doc_count']
key_idx = TASK_NUMBER % total_apikeys
use_key = dbs['api_keys'].get(str(key_idx))

api = get_auth(use_key['api_key'], use_key['api_secret'], \
               use_key['access_token'], use_key['access_secret'])
print("[INFO] Using API key set:\n%s" % use_key)


print("[INFO] Preparing ArcGIS...")
arcgis = geopy.ArcGIS(username=os.environ['ARCGIS_USERNAME'], \
                      password=os.environ['ARCGIS_PASS'], \
                      referer="cloudteam63")

while True:
    query_doc = find_query(dbs['queries'])
    execute_api_search(query_doc, dbs, api)

    print("Sleeping for %.2f seconds" % TIMEWAIT_AFTER_QUERY)
    sleep(TIMEWAIT_AFTER_QUERY)

print("[INFO] Ending script...")