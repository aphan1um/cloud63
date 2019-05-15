'''
'
' [COMP90024 Assignment 2]
' File: twitterscript.py
' Description: Main Twitter harvester script file.
'
' For Cloud Team 63:
'  * Akshaya Shankar - 1058281
'  * Andy Phan - 696382
'  * Chenbang Huang - 967186
'  * Prashanth Shrinivasan - 986472
'  * Qian Sun – 1027266
'
'''

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

TWEET_LANGUAGE = 'en'

# Amount of tweets to retrieve for a single query
SEARCH_TWEET_AMOUNT = 1500

# How many tweets until we update query status (last time query as accessed)
# into database 
UPDATE_TIMESTAMP_PERIOD = 350

# Amount of time to sleep after a search API query was completed
TIMEWAIT_AFTER_QUERY = 3

# Amount of seconds to check rate limit (Twitter API) after exceeding
# limit.
RATE_LIMIT_WAIT = 3.2 * 60

# How 'deep' to look for followers, starting from a user who had its
# tweet found from a Search API query
FRIENDS_SEARCH_DEPTH = 5

# Environment variables about CouchDB location, API key to use (via CouchDB
# database) and the geographic area to collect Tweets with search api
DB_URL = os.environ['DB_URL']
TASK_NUMBER = int(os.environ['DB_TASK_NUM'])
GEO_RADIAL = os.environ['GEO_RADIAL']

########################   FUNCTIONS/VARIABLES:   ######################

# change this to Queue or PriorityQueue, depending on how we want to look
# at followers
users_to_scrape = queue.PriorityQueue()
time_to_recheck_ids = 0


def get_auth(api_key, api_secret, access_token, access_secret):
    ''' Setup authentication details for Tweepy's API class. '''
    auth = tweepy.OAuthHandler(api_key, api_secret)
    auth.set_access_token(access_token, access_secret)
    return tweepy.API(auth)


def get_user_timeline(user_data, dbs, api, all_queries, arcgis, user_scrape_lst):
    '''
    Retrieve tweets based on a Twitter user's ID.

    Parameters:
        - user_data:    A 3-tuple (follower depth, twitter ID, query).
                        query can be None to indicate the user was not found
                        by Twitter search API query
        - dbs:          Dictionary of databases from CouchDB
        - api:          Tweepy's API class to access its services
        - all_queries:  A list of queries (from the CouchDB's query database)
        - arcgis:       Class instance to access ArcGIS' geolocator service
        - user_scrape_lst
                        A (thread-safe) queue containing users to search.

    '''
    
    user_id = user_data[1]
    user_depth = user_data[0]
    user_query = user_data[2]
    user_doc = dbs['users'].get(str(user_id))

    if create_user(user_id, dbs['users']) == True or not 'searched_friends' in user_doc:
        # get Twitter user details
        try:
            user_twitter = api.get_user(user_id)
        except tweepy.RateLimitError as e: # rate limit exceeded for timeline API
            while True:
                sleep(RATE_LIMIT_WAIT)
                limit = api.rate_limit_status()['resources']['users'] \
                                    ['/users/show/:id']['remaining']
                if limit > 0:
                    break
        except tweepy.error.TweepError as e:
            print("Tweepy exception (get user API %s): %s" % (user_id, e))
            user_scrape_lst.task_done()
            return

        # get (CouchDB) document about the location of the twitter user
        loc_doc, user_within_states = \
            find_user_location(user_twitter._json['location'], dbs['geocodes'], \
                    arcgis, is_aus=(user_depth == 0))
        
        queries_from_user = {}

        if user_query is not None:
            queries_from_user[user_query] = dbs['queries'].get(user_query)['meta']

        # ensure user is within our desired region (VIC/ACT/NSW/QLD)
        if user_within_states:
            print("** Scraping tweets for name:\t%s (%s)" % (user_twitter.screen_name, user_twitter.id_str))
            cur = tweepy.Cursor(api.user_timeline, id=user_id, tweet_mode='extended').items()

            # from all_queries, prepare a regex expr to search if tweet has
            # any words from all_queries
            cleaned_queries = [r"\b%s\b" % (q.key.lower().replace('"', '')) for q in all_queries]
            re_queries = re.compile("|".join(cleaned_queries))

            for tweet in limit_handled(cur, api, "statuses", "user_timeline", RATE_LIMIT_WAIT):
                print("\nLooking at (user timeline) tweet:\t%d" % tweet.id)            
                init_doc, tweet_within_states = \
                    prepare_twitter_doc(tweet, None, dbs['geocodes'], arcgis)
                
                if tweet_within_states: # ensure tweet within desired region
                    queries_in_tweet = re_queries.findall(tweet._json['full_text'])

                    # if any queries found in user's tweet, preprocess that to
                    # tweet into couchdb
                    for q in queries_in_tweet:
                        q_id = all_queries[cleaned_queries.index(r"\b%s\b" % q)].id
                        q_meta = dbs['queries'].get(q_id)['meta']

                        init_doc['queries'][q_id] = q_meta
                        queries_from_user[q_id] = q_meta

                    doc, added = save_document(dbs['tweets'], tweet.id, init_doc, \
                                            modify_twitter_doc(None))
                    print("Tweet added?\t%s" % added)
            
            print("** Ended scraping for user:\t%s" % (user_twitter.id_str))
    
    
    # if user has alreaady been searched (& has its friends added into
    # couchdb)
    user_doc = dbs['users'].get(str(user_id))
    if 'searched_friends' in user_doc and user_doc['searched_friends']:
        user_scrape_lst.task_done()
        return

    # now find its friends (assuming we're not looking too deep)
    friends = []
    if user_depth + 1 <= FRIENDS_SEARCH_DEPTH:
        friends = get_friends_ids(user_data, api)
        if friends is None: # Twitter friends ID API rate limit exceeded
            user_scrape_lst.put(user_data)
            friends = []
            searched_friends = False
        else:
            for fr in friends:
                user_scrape_lst.put(fr)
            searched_friends = True

    friend_ids = list(map(str, [f_id[1] for f_id in friends]))

    # finalise state of twitter user into database (i.e. user was completely
    # searched and/or its friends' ids were also retrieved)
    if not 'searched_friends' in user_doc:
        finish_user_search(user_id, dbs['users'], friend_ids, \
            twit_data=user_twitter._json, user_loc=loc_doc, \
            queries=queries_from_user, searched_friends=searched_friends, \
            node_depth=user_depth)
    else:
        finish_user_search(user_id, dbs['users'], friend_ids, \
            searched_friends=searched_friends)
    
    user_scrape_lst.task_done()

    
def get_friends_ids(user_data, api, pages=1):
    '''
    Get all friends IDs of a Twitter user. That is, what other users
    the Twitter user is following.

    Parameters:
        - user_data:    A 3-tuple (follower depth, twitter ID, query).
                        query can be None to indicate the user was not found
                        by Twitter search API query
        - api:          Tweepy API class.
        - pages:        (Optional) Number of pages to look for twitter IDs.

    '''

    global time_to_recheck_ids
    user_id = user_data[1]
    user_depth = user_data[0]

    # if we're still waiting to recheck friend ID API rate limit
    if time_to_recheck_ids > time.time():
        return None
    else:
        limit = api.rate_limit_status()['resources']['friends'] \
                                ['/friends/ids']['remaining']
        if limit == 0:
            time_to_recheck_ids = time.time() + RATE_LIMIT_WAIT
            return None

    cur = tweepy.Cursor(api.friends_ids, id=user_id).pages(1)
    friend_ids = []

    try:
        for ids in cur:
            friend_ids += [(user_depth + 1, id, None) for id in ids]
    except (tweepy.error.RateLimitError, tweepy.error.TweepError) as e:
        print("Tweepy exception (friends API): %s" % e)
        time_to_recheck_ids = time.time() + RATE_LIMIT_WAIT

    return friend_ids


def start_api_search(query_doc, dbs, api, arcgis, user_scrape_lst):
    '''
    Use Twitter's search API to gather tweets by term/query.

    Parameters:
        - query_doc:    Document from CouchDB regarding the query and its
                        meta-data attached.
        - dbs:          Dictionary of databases from CouchDB
        - api:          Tweepy's API class to access its services
        - arcgis:       Class instance to access ArcGIS' geolocator service
        - user_scrape_lst
                        A (thread-safe) queue containing users to search.

    '''
    
    # get query text, and its abbreviations (other ways to say the query)
    queries = [query_doc['_id']]
    if 'abbrev' in query_doc:
        queries += query_doc["abbrev"]

    print("Queries (including abbrevs):\t%s" % queries)
    new_since_ids = defaultdict(int)

    # variables to keep track how many tweets searched & successfully added
    # (without Tweet ID dup issue) from querying term
    total_tweets_iter = 0
    total_tweets_added = 0

    for word in queries:
        print("** Now querying term:\t%s" % word)
        
        # if since_id exists, use that to ensure we look for Twitter
        # posts later than the ones we had previously searched (if we encounter
        # the same query again)
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

            # if we have searched enough tweets, update the time the query
            # was accessed by some Twitter harvester process
            if total_tweets_iter % UPDATE_TIMESTAMP_PERIOD == 0:
                update_query_state(query_doc, dbs['queries'], dbs['geocodes'])
            
            # prepare tweet, as a document to be added in couchdb
            init_doc, within_states = prepare_twitter_doc(tweet, query_doc, \
                                           dbs['geocodes'], arcgis)

            if within_states: # if within (VIC/QLD/NSW/ACT)
                doc, added = save_document(dbs['tweets'], tweet.id, init_doc,
                                        modify_twitter_doc(query_doc))
                if added:
                    total_tweets_added += 1

                # add user to the list to be used for user_timeline API
                user_scrape_lst.put((0, tweet._json['user']['id'], query_doc['_id']))
                print("Tweet added?\t%s" % added)

            new_since_ids[word] = max(new_since_ids[word], tweet._json['id'])

    # at the end update query details (such as last_id, amount added and
    # received from querying term)
    update_query_state(query_doc, dbs['queries'], dbs['geocodes'],
                       last_tweet_ids=new_since_ids,
                       amount_added=total_tweets_added,
                       amount_recv=total_tweets_iter)

    print("Finished query (%d/%d tweets added)): %s" %
          (total_tweets_added, total_tweets_iter, word))


def loop_api_search(dbs, api, arcgis, user_scrape_lst):
    '''
    Function for Twitter's search API continously scrape for queries
    in DB.
    '''
    while True:
        query_doc = find_query(dbs['queries'])
        start_api_search(query_doc, dbs, api, arcgis, user_scrape_lst)
        sleep(TIMEWAIT_AFTER_QUERY)


def loop_user_timeline(dbs, api, arcgis, user_scrape_lst):
    '''
    Function to use Twitter's user_timeline API to continously
    scrape for a specific user's Tweets from the queue: user_scrape_lst
    '''
    # get followers from owner of the API keys4
    print("API under user ID:\t%s" % api.me().id)
    
    # collect Tweets from the user of the API key (if getting friends IDs
    # API has exceeded, keep trying until that certain API isn't rate limited)
    got_my_friends = False
    while not got_my_friends:
        my_friends = get_friends_ids((0, api.me().id, None), api)

        if my_friends is not None:
            for friend in my_friends:
                user_scrape_lst.put(friend)
            got_my_friends = True
        else:
            print("Waiting for friend API to be free...")
            sleep(TIMEWAIT_AFTER_QUERY * 4)
    
    print("Initial user_scrape_lst: %s" % (list(user_scrape_lst.queue)))

    # prepare list of queries from database, to be regexed for each user
    # tweet
    all_queries = [q for q in dbs['queries'].view("queryDD/ids")]

    while True:
        try:
            user_data = user_scrape_lst.get_nowait()
        except queue.Empty: # no user to harvest (queue empty)
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

    # connect to CouchDB instance, prepare certain databases in it
    server = couchdb.Server(DB_URL)
    dbs = {'tweets': server["tweets_final"], 'geocodes': server["geocodes_final"], \
        'queries': server["tweet_queries"], 'api_keys': server["api_keys"], \
        'users': server['tweet_users']}

    # get API key from database
    total_apikeys = dbs['api_keys'].info()['doc_count']
    key_idx = TASK_NUMBER % total_apikeys
    use_key = dbs['api_keys'].get(str(key_idx))

    api = get_auth(use_key['api_key'], use_key['api_secret'], \
                use_key['access_token'], use_key['access_secret'])
    print("[INFO] Using API key set:\n%s" % use_key)

    arcgis = geopy.ArcGIS(username=os.environ['ARCGIS_USERNAME'], \
                        password=os.environ['ARCGIS_PASS'], \
                        referer="cloudteam63")

    # create two threads to use search API and user_timeline API
    # (communicating with each other via queue: users_to_scrape)
    thread_search = Thread(target=loop_api_search, args=(dbs, api, arcgis, users_to_scrape))
    thread_users = Thread(target=loop_user_timeline, args=(dbs, api, arcgis, users_to_scrape))

    thread_search.start()
    thread_users.start()

    thread_search.join()
    thread_users.join()

    print("[INFO] Ending script...")