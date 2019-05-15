'''
'
' [COMP90024 Assignment 2]
' File: twitterutils.py
' Description: Utility functions for the main twitterscript.py
'
' Team members:
'   Akshaya S. (1058281), Andy P. (696382), Chenbang H. (967186),
'   Prashanth S. (986472), Qian S. (1027266)
'
'''

import tweepy, couchdb
import random
from datetime import datetime
import pytz, geopy
import http.client
from time import sleep
import pygeohash as pgh
import time

import fiona
from shapely.geometry import shape, mapping, Point, Polygon, MultiPolygon

########################   CONSTANTS HERE:   ######################

# If arcgis fails to respond, how many seconds to wait until retry
GEOPY_TIMEOUT_RETRY = 0.8

# Amount of times to reconnect to CouchDB if we fail
RECONNECT_COUCHDB_MAX = 4

# Amount of time until we retry the query again
THRESHOLD = 60 * 23

# Maximum of queries to get from CouchDB, as candidates to select for search.
MAX_QUERIES = 20

# If no (available) queries were found, amount of seconds until retry
TIMEWAIT_NO_QUERIES_FOUND = 9

# Seconds to wait if query was selected but was later found to be taken
TIMEWAIT_QUERY_TAKEN = 5

# Amount of times to retry accessing arcgis until we cancel location search
MAX_ARCGIS_ATTEMPTS = 4

# Tweets to collect if its within Australian states (fullname : abbreviation)
HARVEST_STATES = {'victoria': 'vic', 'new south wales': 'nsw', \
                  'queensland': 'qld', 'australian capital territory': 'act'}


########################   FUNCTIONS HERE:   ######################

# Credit to http://docs.tweepy.org/en/latest/code_snippet.html
# for the example code.
def limit_handled(cursor, api, family, method, wait_time):
    '''
    Execute a Twitter API method, considering its rate limits.

    Parameters:
        - cursor:       Tweepy's cursor object, to allow iteration of Twitter
                        objects.
        - api:          Tweepy API instance.
        - family:       String representing the family of used Twitter method.
        - method:       Specific name of method.
        - wait_time:    Amount of time to wait if method's limit has exceeded.
    '''
    while True:
        try:
            yield cursor.next()
        except (tweepy.error.RateLimitError, tweepy.error.TweepError) as e:
            while True:
                print("Rate limit for resource %s/%s! Checking in %.1f mins"
                    % (family, method, wait_time/60.0))
                print("Reported exception: %s" % e)

                # wait and then recheck to see if it's free
                sleep(wait_time)
                limit = api.rate_limit_status()['resources'][family] \
                                    ['/%s/%s' % (family, method)]['remaining']
                if limit > 0:
                    break


def normalise_createdat(str_date):
    ''' Turn Twitter date into a list. '''
    # Credit to: https://stackoverflow.com/a/18736802 for the snippet.
    ret_date = datetime.strptime(str_date, 
                        '%a %b %d %H:%M:%S +0000 %Y').replace(tzinfo=pytz.UTC)
    
    # turn it into a list to make it easy to search through
    # CouchDB's view queries
    return [ret_date.year, ret_date.month, ret_date.day,
            ret_date.hour, ret_date.minute, ret_date.second]


def find_query(db_queries):
    '''
    Return a query to use within CouchDB for search.

    Parameters:
        - db_queries:   Database within CouchDB pertaining to queries. 
    '''
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


def create_user(id, db_users):
    ''' Create Twitter user into database. '''
    _, added = save_document(db_users, id, {}, lambda doc : None)
    return added


def finish_user_search(id, db_users, friend_lst, queries=None,  \
    twit_data=None, user_loc=None, searched_friends=True, node_depth=None):
    '''
    Finalize the state of the twitter user, such as if his/her friends
    have been searched, user location etc.

    Parameters:
        - id:               Twitter user ID.
        - db_users:         Database containing Twitter users.
        - friend_lst:       List of user's friends IDs.
        - queries:          List of queries (within DB) found by searching user.
        - twit_data:        Twitter's User object (in raw JSON).
        - user_loc:         String location of user.
        - searched_friends: If user has its friends IDs searched.
        - node_depth:       How 'deep' is the user in the user_timeline search
    '''

    def f_edit(user_doc):
        if user_loc is not None:
            user_doc['location'] = user_loc
        if twit_data is not None:
            user_doc['twit_data'] = twit_data

        if 'friend_lst' not in user_doc:
            user_doc['friend_ids'] = []
        if 'query' not in user_doc:
            user_doc['query'] = {}

        if len(friend_lst) > 0:
            user_doc['friend_ids'] = list(set(user_doc['friend_ids'] + friend_lst))
        
        if queries is not None and len(queries) > 0:
            user_doc['query'] = dict(user_doc['query'], **queries)

        if node_depth is not None:
            user_doc['node_depth'] = node_depth

        user_doc['searched_friends'] = searched_friends
        
        return user_doc
    
    save_document(db_users, id, None, f_edit)


def update_query_state(query_doc, db_query, db_geocodes,
                       last_tweet_ids=None, amount_added=None,
                       amount_recv=None):
    '''
    Update the state of query, such as its last time searched.

    Parameters:
        - query_doc:        Document in CouchDB's query DB related to query.
        - db_query:         Query database in CouchDB.
        - db_geocodes:      Database in CouchDB that stores geocodes/locations.
        - last_tweet_ids:   Latest tweet ID found within search.
        - amount_added:     Amount of tweets added to DB because of query.
        - amount_recv:      Amount of tweets received by search API by query.
    '''
    
    def f_edit(doc):
        if amount_added is not None and amount_recv is not None:
            proportion_accepted = amount_added/(amount_recv + 1)

            # record amount of tweets received & added from this query
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

            # calculate new time to search query again
            # penalize if tweet found no new and added queries
            # reduce time if tweet had many tweets added
            new_time = time.time() - 0.9 * THRESHOLD * proportion_accepted \
                + max(12 * int(doc['streak_nonerecv']), 6 * int(doc['streak_noneadded']))
        else:
            new_time = time.time()

        doc['last_ran'] = str(new_time)

        if amount_added is not None and amount_added > 0:
            if 'amount_added' in doc:
                doc['amount_added'] = str(int(doc['amount_added']) + amount_added)
            else:
                doc['amount_added'] = str(amount_added)

        # update last tweet ID seen from query (and its abbreviations/aliases
        # of query)
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
    '''
    Save document to a certain CouchDB database.

    Parameters:
        - db:           A CouchDB database.
        - id:           An ID to save as within the database.
        - init_doc:     Document to add to DB, if it doesn't exist.
        - f_edit:       A function of 1-parameter (that accepts a document)
                        should document with 'id' to already exist within
                        database.
                        
                        It may return a modified document or None, in which
                        nothing is done to edit the existing document.

    Returns:
        A 2-tuple (document, added).
            - document: CouchDB document that was added or found/modified.
            - added: If the document was added. This would be false if
                     document already existed.
    '''

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
            except couchdb.http.ResourceConflict:
                # revision issue or document already exists
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


def norm_location(loc_str):
    ''' Normalise location string (lowercase and remove commas). '''
    return loc_str.lower().replace(',', '')


# Credit to: https://gis.stackexchange.com/a/208574 for how to use SHP files
# to find a point's LGA region
# Expect it in (latit)
def find_lga(state, latitude, longitude):
    '''
    Given a full-name of a state (refer to HARVEST_STATES) and (lat, long),
    get its LGA location using SHP files.
    '''
    
    if state.lower() in HARVEST_STATES.keys():
        pt = Point(longitude, latitude)
        state_abbrev = HARVEST_STATES[state.lower()]
        
        with fiona.open("shapes/%s/%s.shp" % (state_abbrev, state_abbrev)) as f:
            for region in f:
                if pt.within(shape(region['geometry'])):
                    return {'lga_name': region['properties']['lga_name'], \
                            'lga_code': region['properties']['lga_code']}

    return None


def find_user_location(loc_str, db_geocodes, arcgis, is_aus=False):
    '''
    Get the 'normalised' string name of a location based on a string
    representing a place.

    Parameters:
        - loc_str:      String representing a palce.
        - db_geocodes:  Database containing locations.
        - arcgis:       ArcGIS's geolocator service.
        - is_aus:       If place is from Australia. If so, we can ask
                        ArcGIS to help clarify loc_str is coming from
                        Australia.

    Returns:
        A 2-tuple (loc_doc, in_area).
        - loc_doc:      Document in db_geocodes about the normalised location.
        - in_area:      If location is within HARVEST_STATES and in Australia.

        loc_doc can be None, should loc_str be degenerate (i.e. empty string)
        or if ArcGIS fails to respond within certain limits.
    '''

    # normalise loc_str name (lower case, remove commas)
    loc_str_norm = norm_location(loc_str)

    # prepare document to represent location in geocodes
    def f_init(geoc):
        ret =  {'position': [geoc.latitude, geoc.longitude],
                'aliases':  list(set([loc_str_norm, norm_location(geoc.address)])),
                'state': geoc.raw['attributes']['Region'],
                'country': geoc.raw['attributes']['Country'],
                'geohash': pgh.encode(geoc.latitude, geoc.longitude),
                'lga': None}
        
        if ret['country'] == "AUS" and ret['state'].lower() in HARVEST_STATES:
            ret['lga'] = find_lga(ret['state'], geoc.latitude, geoc.longitude)
        return ret

    # case if the loc_str is already within DB (or if loc_str is an alias/
    # another way of saying some normalised location queried by ArcGIS)
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

    # if location isn't DB stored, have to use ArcGIS (geocoder service)
    if len(view_query) == 0:
        if is_aus and 'australia' not in loc_str.lower():
            loc_str += " Australia"
        
        attempts = 0
        while attempts <= MAX_ARCGIS_ATTEMPTS:
            try:
                attempts += 1
                approx_loc = arcgis.geocode(loc_str, out_fields=["Region", "Country"])

                # ArcGIS fails to give any coordinates (e.g with empty string)
                if approx_loc is None:
                    return None, False

            except geopy.exc.GeocoderTimedOut:
                print("[#%d] ArcGIS time out on string: '%s'. Waiting..." % (attempts, loc_str))
                sleep(GEOPY_TIMEOUT_RETRY) # wait until we query ArcGIS again
                continue
            break

        if attempts > MAX_ARCGIS_ATTEMPTS:
            print("[WARN] ArcGIS timed out too much on:\t%s" % loc_str)
            return None, False

        loc_doc = save_document(db_geocodes, approx_loc.address, \
                                f_init(approx_loc), f_edit)[0]
    else:
        # if location is already found withitn database
        print("[INFO] Geocode \"%s\" already added." % loc_str)
        loc_doc = db_geocodes.get(view_query[0].id)

    loc_doc.pop("aliases", None)
    loc_doc.pop("_rev", None)
    
    return (loc_doc, loc_doc['country'] == 'AUS' and \
             loc_doc['state'].lower() in HARVEST_STATES.keys())