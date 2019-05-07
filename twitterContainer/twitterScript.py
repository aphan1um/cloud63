# NOTE: Requires tweepy and couchdb packages (use pip to install)
#
# TODO: Handle  TweepError from Tweepy API [ERROR HANDLING]
#
import tweepy
import couchdb
import time
import pytz, geopy
from time import sleep
from datetime import datetime
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


def normalise_createdat(str_date):
    # Credit to: https://stackoverflow.com/a/18736802 for the snippet.
    ret_date = datetime.strptime(str_date, 
                                '%a %b %d %H:%M:%S +0000 %Y').replace(tzinfo=pytz.UTC)
    
    # turn it into a list to make it easy to search through
    # CouchDB's view queries
    return [ret_date.year, ret_date.month, ret_date.day,
            ret_date.hour, ret_date.minute, ret_date.second]


def find_query(db_queries):
    chosen_doc = None

    print("Preparing to choose a query to search...")

    # in the query database section, look for a phrase/term which hasn't
    # been searched for a while or not at all.
    while True:
        startTime = str(time.time() - THRESHOLD)
        view = db_queries.view("queryDD/last_ran",
                    startkey=str(startTime), descending='true', limit=MAX_QUERIES)
        all_queries = [q.id for q in view]

        if len(all_queries) == 0:
            print("No idle queries to use for search. Waiting...")
            sleep(10)
            continue

        # select random query
        chosen_query = all_queries[randint(0, len(all_queries)) - 1]

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

def norm_location(loc_str):
    return loc_str.lower().replace(',', '')

def find_user_location(loc_str, db_geocodes):
    loc_str_norm = norm_location(loc_str)

    def f_init(geoc):
        return {'position': [geoc.latitude, geoc.longitude],
                'aliases':  list(set([loc_str_norm, norm_location(geoc.address)])),
                'state': geoc.raw['attributes']['RegionAbbr']}

    def f_edit(doc):
        print("Aliases:", doc['aliases'])
        if loc_str_norm in doc['aliases']:
            print("[WARNING] Loc already in alias")
            return None

        doc['aliases'] += [loc_str_norm] 
        
        return doc

    print("\nQuerying place:\t%s" % (loc_str_norm))

    # QUERY FIRST
    view = db_geocodes.view('locnames/names', key=loc_str_norm,
                            limit=1, sorted='false')
    view_query = [i for i in view]

    # if the location name/alias has already been 'cached' in DB
    if len(view_query) > 0:
        print("Already added geocode...")
        return view_query[0].id

    # ... if not, we have to find via ArcGIS (a geocoder service)
    
    # TODO: Crap code, but it kinda ensures we get position in Australia
    if 'Australia' not in loc_str:
        loc_str += " Australia"

    # RETRY LIMIT?
    while True:
        try:
            approx_loc = arcgis.geocode(loc_str, out_fields=["RegionAbbr"])
        except geopy.exc.GeocoderTimedOut:
            continue
        break

    doc = retry_save(db_geocodes, approx_loc.address, f_init(approx_loc),
                     f_edit, None)

    return doc


def update_query_state(query_doc, last_tweet_ids, db_query, db_geocodes):
    new_time = time.time()

    def f_edit(doc):
        if float(doc['last_ran']) > new_time:
            return None

        num_new = 0
        if 'since_ids' not in doc:
            doc['since_ids'] = {}

        for term, since_id in last_tweet_ids.items():
            if term in doc['since_ids']:
                old_since_id = int(doc['since_ids'][term])
                if since_id > old_since_id:
                    doc['since_ids'][term] = since_id
                    num_new += 1
            else:
                doc['since_ids'][term] = since_id

        if num_new == 0:
            return None
            
        return doc

    retry_save(db_query, query_doc['_id'], None, f_edit, None)


def is_retweet(tweet):
    return 'retweeted_status' in tweet._json

def execute_api_search(query_doc, db_tweets, db_query, db_geocodes):
    # NOTES:
    #
    # 1. We're guaranteed to at least have a user location, since
    #    we're filtering through Twitter SEARCH API (geocode)
    #

    def f_init(tweet):
        # TODO: Should we import all of the data
        doc = tweet._json

        # add meta data
        doc['createdat_norm'] = normalise_createdat(doc['created_at'])

        # TODO: Use original tweeter's location as retweet
        if is_retweet(tweet):
            loc_str = doc['retweeted_status']['user']['location']
        else:
            loc_str = doc['user']['location']
            
        
        location_doc = find_user_location(loc_str, db_geocodes)
        if location_doc is None:
            return None

        doc['loc_norm'] = find_user_location(loc_str, db_geocodes)
        return doc

    def f_edit(tweet):
        return None
    
    def f_state(added, doc_id):
        if not added:
            print("Tweet already added:\t", doc_id)
        else:
            print("Tweet accepted:\t", doc_id)

    queries = query_doc["abbrev"] + [query_doc['_id']]
    print("Queries (including abbrevs):\t", queries)
    new_since_ids = defaultdict(int)

    for word in queries:
        print("Querying word:\t", word)
        
        if 'since_ids' in query_doc and word in query_doc['since_ids']:
            since_id = int(query_doc['since_ids']['word'])
        else:
            since_id = 0
        
        cur = tweepy.Cursor(api.search, q=word, lang=TWEET_LANGUAGE,
                            geocode=GEO_RADIAL, tweet_mode='extended',
                            since_id=since_id).items(SEARCH_TWEET_AMOUNT)

        #if tweet.place is not None or tweet.geo is not None or tweet.coordinates is not None:
        for tweet in limit_handled(cur):
            init_doc = f_init(tweet)

            if init_doc is not None:
                retry_save(db_tweets, tweet.id, f_init(tweet), f_edit, f_state)
            new_since_ids[word] = max(new_since_ids[word], tweet._json['id_str'])

    # at the end update query details
    update_query_state(query_doc, new_since_ids, db_query, db_geocodes)

    print("Finished query ID: %s" % query_doc['_id'])


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