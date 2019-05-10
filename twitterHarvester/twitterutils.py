import tweepy, couchdb
import random
from datetime import datetime
import pytz, geopy
import http.client
from time import sleep
import pygeohash as pgh

RATE_LIMIT_WAIT = 3.2 * 60
GEOPY_TIMEOUT_RETRY = 0.75
RECONNECT_COUCHDB_MAX = 4

THRESHOLD = 60 * 23     # 23 minutes
MAX_QUERIES = 20
TIMEWAIT_NO_QUERIES_FOUND = 9
TIMEWAIT_QUERY_TAKEN = 5

# Credit to http://docs.tweepy.org/en/latest/code_snippet.html
# for the example code.
def limit_handled(cursor, api):
    while True:
        try:
            yield cursor.next()
        except (tweepy.RateLimitError, tweepy.error.TweepError) as e:
            while True:
                print("[WARNING] Rate limit hit! Will check again in %.1f mins"
                    % (RATE_LIMIT_WAIT/60.0))
                print("Reported except: %s" % e)

                sleep(RATE_LIMIT_WAIT)

                limit = api.rate_limit_status()['resources']['search'] \
                                               ['/search/tweets']['remaining']
                if limit > 0:
                    break

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
    attempts_made = 0

    print("Preparing to find a query...")

    # in the query database section, look for a phrase/term which hasn't
    # been searched for a while or not at all.
    while True:
        startTime = time.time() - THRESHOLD
        view = db_queries.view("queryDD/last_ran",
                    startkey=str(startTime), descending='true',
                    limit=MAX_QUERIES)
        all_queries = [q for q in view]

        if len(all_queries) == 0:
            print("[#%d] No idle queries available. Waiting %ds..." \
                    % (attempts_made, TIMEWAIT_NO_QUERIES_FOUND))
            
            attempts_made += 1
            sleep(TIMEWAIT_NO_QUERIES_FOUND)
            continue

        # select random query
        rand_idx = random.randint(0, len(all_queries)) - 1
        chosen_query = all_queries[rand_idx].id

        # now attempt to update value
        new_doc = db_queries[chosen_query]
        new_doc["last_ran"] = str(time.time())
        
        # inform DB that we're using this query. TODO: shitty code?
        try:
            db_queries.save(new_doc)
        except couchdb.http.ResourceConflict as e:
            print("Query already taken. Waiting...")
            sleep(TIMEWAIT_QUERY_TAKEN) # wait for a bit
        else:
            print("Query selected:\t%s" % new_doc['_id'])
            break
    
    return new_doc

def update_query_state(query_doc, db_query, db_geocodes,
                       last_tweet_ids=None, amount_added=None, amount_recv=None):
    def f_edit(doc):
        # update time (if the query received a lot of results, search it
        # again)        
        if amount_added is not None and amount_recv is not None:
            proportion_accepted = amount_added/(amount_recv + 1)

            if amount_recv == 0:
                if 'streak_nonerecv' in doc:
                    doc['streak_nonerecv'] = \
                        str(int(doc['streak_nonerecv']) + 1)
                else:
                    doc['streak_nonerecv'] = str(1)
            else:
                doc['streak_nonerecv'] = str(0)

            if amount_added == 0:
                if 'streak_noneadded' in doc:
                    doc['streak_noneadded'] = \
                        str(int(doc['streak_noneadded']) + 1)
                else:
                    doc['streak_noneadded'] = str(1)
            else:
                doc['streak_noneadded'] = str(0)

            new_time = time.time() - 0.9 * THRESHOLD * proportion_accepted \
                + 0.42 * THRESHOLD * (1 - (amount_recv/SEARCH_TWEET_AMOUNT)) \
                + max(11 * int(doc['streak_nonerecv']), 5.5 * int(doc['streak_noneadded']))
        else:
            new_time = time.time()

        doc['last_ran'] = str(new_time)

        if amount_added is not None and amount_added > 0:
            if 'amount_added' in doc:
                doc['amount_added'] = str(int(doc['amount_added']) + amount_added)
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

        return doc

    save_document(db_query, query_doc['_id'], None, f_edit)

def save_document(db, id, init_doc, f_edit):
    added = False
    doc = None
    reconnect_attempts = 0
    
    while not added:
        try:
            retrieved_doc = db.get(str(id))
            if retrieved_doc is None:
                doc = init_doc
                doc['_id'] = str(id)
            else:
                new_doc = f_edit(retrieved_doc)
                if new_doc is None:
                    break
                else:
                    doc = new_doc

            try:
                db.save(doc)
            except couchdb.http.ResourceConflict: # revision issue
                # TODO: not sure if this is needed
                sleep(0.100)  # sleep for 100 ms for server relief
            else:
                added = True

            reconnect_attempts = 0
        except http.client.BadStatusLine as e:
            # possible if we don't interact with couchdb for some time;
            # re-establish by responding again limited amt of times
            if reconnect_attempts >= RECONNECT_COUCHDB_MAX:
                raise e
            
            reconnect_attempts += 1
            pass
    
    return (doc if doc is not None else db.get(str(id)), added)


def is_retweet(tweet):
    return 'retweeted_status' in tweet._json

def norm_location(loc_str):
    return loc_str.lower().replace(',', '')


def find_user_location(loc_str, db_geocodes, arcgis):
    loc_str_norm = norm_location(loc_str)

    def f_init(geoc):
        return {'position': [geoc.latitude, geoc.longitude],
                'aliases':  list(set([loc_str_norm, norm_location(geoc.address)])),
                'state': geoc.raw['attributes']['Region'],
                'country': geoc.raw['attributes']['Country'],
                'geohash': pgh.encode(geoc.latitude, geoc.longitude)}

    def f_edit(doc):
        if loc_str_norm in doc['aliases']:
            print("[INFO] Loc already in alias")
            return None

        doc['aliases'] += [loc_str_norm] 
        return doc

    # QUERY FIRST
    view = db_geocodes.view('locnames/names', key=loc_str_norm,
                            limit=1, sorted='false')
    view_query = [i for i in view]

    # if location isn't DB stored, have to find via ArcGIS (geocoder service)
    if len(view_query) == 0:
        # TODO: Crap code, but it kinda ensures we get position in Australia
        if 'australia' not in loc_str.lower():
            loc_str += " Australia"

        # TODO: RETRY LIMIT?
        while True:
            try:
                approx_loc = arcgis.geocode(loc_str, out_fields=["Region", "Country"])
            except geopy.exc.GeocoderTimedOut:
                sleep(GEOPY_TIMEOUT_RETRY) # wait until we query ArcGIS again
                continue
            break

        loc_doc = save_document(db_geocodes, approx_loc.address, \
                                f_init(approx_loc), f_edit)[0]
    else:
        print("[INFO] Geocode \"%s\" already added." % loc_str)
        loc_doc = db_geocodes.get(view_query[0].id)
    
    return (loc_doc, loc_doc['country'] == 'AUS')