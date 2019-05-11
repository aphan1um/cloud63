import tweepy, couchdb
import time, os
import geopy
from time import sleep
from collections import defaultdict

from twitterdoc import prepare_twitter_doc, modify_twitter_doc
from twitterutils import *

from threading import Thread
import queue
import re

########################   CONSTANTS HERE:   ######################

#GEO_RADIAL = "-36.565842,145.043926,445km"
TWEET_LANGUAGE = 'en'
SEARCH_TWEET_AMOUNT = 1500
UPDATE_TIMESTAMP_PERIOD = 350
TIMEWAIT_AFTER_QUERY = 3
RATE_LIMIT_WAIT = 3.2 * 60

FRIENDS_SEARCH_DEPTH = 6

DB_URL = os.environ['DB_URL']
TASK_NUMBER = int(os.environ['DB_TASK_NUM'])
GEO_RADIAL = os.environ['GEO_RADIAL']

########################   FUNCTIONS/VARIABLES:   ######################

users_to_scrape = queue.Queue()
time_to_recheck_ids = 0

def get_auth(api_key, api_secret, access_token, access_secret):
    auth = tweepy.OAuthHandler(api_key, api_secret)
    auth.set_access_token(access_token, access_secret)
    return tweepy.API(auth)

def get_user_timeline(user_data, dbs, api, all_queries, arcgis, user_scrape_lst):
    if create_user(user_data[0], dbs['users']) == True:
        # get Twitter user details
        try:
            user_twitter = api.get_user(user_data[0])
        except tweepy.RateLimitError as e:
            while True:
                sleep(RATE_LIMIT_WAIT)
                limit = api.rate_limit_status()['resources']['users'] \
                                    ['/users/show/:id']['remaining']
                if limit > 0:
                    break
        except tweepy.error.TweepError as e:
            print("Tweepy exception (get user API %s): %s" % (user_data[0], e))
            user_scrape_lst.task_done()
            return

        loc_doc, user_within_states = \
            find_user_location(user_twitter._json['location'], dbs['geocodes'], \
                    arcgis, is_aus=(user_data[2] == 0))
        
        queries_from_user = {}

        if user_data[1] is not None:
            queries_from_user[user_data[1]] = dbs['queries'].get(user_data[1])['meta']

        if user_within_states:
            print("** Scraping tweets for name:\t%s (%s)" % (user_twitter.screen_name, user_twitter.id_str))
            cur = tweepy.Cursor(api.user_timeline, id=user_data[0], tweet_mode='extended').items()

            cleaned_queries = [r"\b%s\b" % (q.key.lower().replace('"', '')) for q in all_queries]
            re_queries = re.compile("|".join(cleaned_queries))

            for tweet in limit_handled(cur, api, "statuses", "user_timeline", RATE_LIMIT_WAIT):
                print("\nLooking at (user timeline) tweet:\t%d" % tweet.id)            
                init_doc, tweet_within_states = \
                    prepare_twitter_doc(tweet, None, dbs['geocodes'], arcgis)
                
                if tweet_within_states:
                    queries_in_tweet = re_queries.findall(tweet._json['full_text'])
                    for q in queries_in_tweet:
                        q_id = all_queries[cleaned_queries.index(r"\b%s\b" % q)].id
                        q_meta = dbs['queries'].get(q_id)['meta']

                        init_doc['queries'][q_id] = q_meta
                        queries_from_user[q_id] = q_meta

                    doc, added = save_document(dbs['tweets'], tweet.id, init_doc, \
                                            modify_twitter_doc(None))
                    print("Tweet added?\t%s" % added)
            
            print("** Ended scraping for user:\t%s" % (user_twitter.id_str))
    
    
    user_doc = dbs['users'].get(str(user_data[0]))
    if 'searched_friends' not in user_doc or user_doc['searched_friends']:
        user_scrape_lst.task_done()
        return

    # now find its followers (assuming we're not looking too deep)
    friends = []
    if user_data[2] + 1 <= FRIENDS_SEARCH_DEPTH:
        friends = get_friends_ids(user_data, api)
        if friends is None:
            user_scrape_lst.put(user_data)
            friends = []
            searched_friends = False
        else:
            for fr in friends:
                user_scrape_lst.put(fr)
            searched_friends = True

    friend_ids = list(map(str, [f_id[0] for f_id in friends]))

    if not 'searched_friends' in user_doc:
        finish_user_search(user_data[0], dbs['users'], friend_ids, \
            twit_data=user_twitter._json, user_loc=loc_doc, \
            queries=queries_from_user, searched_friends=searched_friends, \
            node_depth=user_data[2])
    else:
        finish_user_search(user_data[0], dbs['users'], friend_ids, \
            searched_friends=searched_friends)
    
    user_scrape_lst.task_done()

    
def get_friends_ids(user_data, api, pages=1):
    global time_to_recheck_ids

    if time_to_recheck_ids > time.time():
        return None
    else:
        limit = api.rate_limit_status()['resources']['friends'] \
                                ['/friends/ids']['remaining']
        if limit == 0:
            time_to_recheck_ids = time.time() + RATE_LIMIT_WAIT
            return None

    cur = tweepy.Cursor(api.friends_ids, id=user_data[0]).pages(1)
    friend_ids = []

    try:
        for ids in cur:
            friend_ids += [(id, None, user_data[2] + 1) for id in ids]
    except (tweepy.error.RateLimitError, tweepy.error.TweepError) as e:
        print("Tweepy exception (friends API): %s" % e)
        time_to_recheck_ids = time.time() + RATE_LIMIT_WAIT

    return friend_ids

#API.friends_ids

def start_api_search(query_doc, dbs, api, arcgis, user_scrape_lst):
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

        for tweet in limit_handled(cur, api, "search", "tweets", RATE_LIMIT_WAIT):
            print("\nProcessing tweet ID:\t%d" % tweet.id)
            total_tweets_iter += 1
            if total_tweets_iter % UPDATE_TIMESTAMP_PERIOD == 0:
                update_query_state(query_doc, dbs['queries'], dbs['geocodes'])
            
            init_doc, within_states = prepare_twitter_doc(tweet, query_doc, \
                                           dbs['geocodes'], arcgis)

            if within_states:
                doc, added = save_document(dbs['tweets'], tweet.id, init_doc,
                                        modify_twitter_doc(query_doc))
                if added:
                    total_tweets_added += 1

                user_scrape_lst.put((tweet._json['user']['id'], query_doc['_id'], 0))
                print("Tweet added?\t%s" % added)

            new_since_ids[word] = max(new_since_ids[word], tweet._json['id'])

    # at the end update query details
    update_query_state(query_doc, dbs['queries'], dbs['geocodes'],
                       last_tweet_ids=new_since_ids,
                       amount_added=total_tweets_added,
                       amount_recv=total_tweets_iter)

    print("Finished query (%d/%d tweets added)): %s" %
          (total_tweets_added, total_tweets_iter, word))


def loop_api_search(dbs, api, arcgis, user_scrape_lst):
    while True:
        query_doc = find_query(dbs['queries'])
        start_api_search(query_doc, dbs, api, arcgis, user_scrape_lst)
        sleep(TIMEWAIT_AFTER_QUERY)


def loop_user_timeline(dbs, api, arcgis, user_scrape_lst):
    # get followers from owner of the API keys4
    print("API under user ID:\t%s" % api.me().id)
    my_friends = get_friends_ids((api.me().id, None, 0), api)

    for friend in my_friends:
        user_scrape_lst.put(friend)
    
    print("Initial user_scrape_lst: %s" % (list(user_scrape_lst.queue)))

    all_queries = [q for q in dbs['queries'].view("queryDD/ids")]

    while True:
        try:
            user_data = user_scrape_lst.get_nowait()
        except queue.Empty:
            print("Friend queue empty currently empty.")
            sleep(TIMEWAIT_AFTER_QUERY/2.1)
            continue
        
        get_user_timeline(user_data, dbs, api, \
                          all_queries, arcgis, user_scrape_lst)
        sleep(TIMEWAIT_AFTER_QUERY)


#########################    MAIN CODE BELOW    #########################

if __name__ == '__main__':
    # get env variables set within Docker container
    print("[INFO] Starting script for process #%d..." % TASK_NUMBER)
    print("[INFO] Connecting to database: %s" % DB_URL)

    server = couchdb.Server(DB_URL)
    dbs = {'tweets': server["tweets_final"], 'geocodes': server["geocodes_final"], \
        'queries': server["tweet_queries"], 'api_keys': server["api_keys"], \
        'users': server['tweet_users']}

    total_apikeys = dbs['api_keys'].info()['doc_count']
    key_idx = TASK_NUMBER % total_apikeys
    use_key = dbs['api_keys'].get(str(key_idx))

    api = get_auth(use_key['api_key'], use_key['api_secret'], \
                use_key['access_token'], use_key['access_secret'])
    print("[INFO] Using API key set:\n%s" % use_key)

    arcgis = geopy.ArcGIS(username=os.environ['ARCGIS_USERNAME'], \
                        password=os.environ['ARCGIS_PASS'], \
                        referer="cloudteam63")

    thread_search = Thread(target=loop_api_search, args=(dbs, api, arcgis, users_to_scrape))
    thread_users = Thread(target=loop_user_timeline, args=(dbs, api, arcgis, users_to_scrape))

    thread_search.start()
    thread_users.start()

    thread_search.join()
    thread_users.join()

    print("[INFO] Ending script...")