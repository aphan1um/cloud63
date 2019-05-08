import tweepy
import couchdb
from datetime import datetime
import pytz

RATE_LIMIT_WAIT = 15 * 60

# Credit to http://docs.tweepy.org/en/latest/code_snippet.html
# for the example code.
def limit_handled(cursor):
    while True:
        try:
            yield cursor.next()
        except tweepy.RateLimitError as e:
            print("[WARNING] Rate limit hit! Now waiting for %.1f mins..."
                  % (RATE_LIMIT_WAIT/60.0))
            time.sleep(RATE_LIMIT_WAIT)

def normalise_createdat(str_date):
    # Credit to: https://stackoverflow.com/a/18736802 for the snippet.
    ret_date = datetime.strptime(str_date, 
                        '%a %b %d %H:%M:%S +0000 %Y').replace(tzinfo=pytz.UTC)
    
    # turn it into a list to make it easy to search through
    # CouchDB's view queries
    return [ret_date.year, ret_date.month, ret_date.day,
            ret_date.hour, ret_date.minute, ret_date.second]

def retry_save(db, id, init_doc, f_edit, f_state):
    added = False
    doc = None

    while not added:
        if db.get(str(id)) is None:
            doc = init_doc
            doc['_id'] = str(id)
        else:
            new_doc = f_edit(db.get(str(id)))
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

        if f_state is not None:
            f_state(added, doc['_id'])

    
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
                'state': geoc.raw['attributes']['RegionAbbr']}

    def f_edit(doc):
        if loc_str_norm in doc['aliases']:
            print("[WARNING] Loc already in alias")
            return None

        doc['aliases'] += [loc_str_norm] 
        
        return doc

    print("Querying place:\t%s" % (loc_str_norm))

    # QUERY FIRST
    view = db_geocodes.view('locnames/names', key=loc_str_norm,
                            limit=1, sorted='false')
    view_query = [i for i in view]

    # if location isn't DB stored, have to find via ArcGIS (geocoder service)
    if len(view_query) == 0:
        # TODO: Crap code, but it kinda ensures we get position in Australia
        if 'Australia' not in loc_str:
            loc_str += " Australia"

        # RETRY LIMIT?
        while True:
            try:
                approx_loc = arcgis.geocode(loc_str, out_fields=["RegionAbbr"])
            except geopy.exc.GeocoderTimedOut:
                sleep(0.5) # wait until we query ArcGIS again
                continue
            break

        doc = retry_save(db_geocodes, approx_loc.address, f_init(approx_loc),
                        f_edit, None)[0]

        # TODO: Adhoc fix
        return (approx_loc.address, approx_loc.raw['attributes']['RegionAbbr'] == "VIC")
    else:
        print("[NOTE] Geocode already added.")     
        return (view_query[0].id, view_query[0].value)


def prepare_twitter_doc(tweet, query_doc, current_term, db_geocodes, arcgis):
    # TODO: Should we import all of the data?
    # TODO: Any preprocessing we need to do?
    doc = tweet._json

    new_doc = {}

    ####### Step 0: Get subset of tweet object fields
    new_doc['full_text'] = doc['full_text']
    new_doc['trunc_hashtags'] = [e['text'] for e in doc['entities']['hashtags']]
    new_doc['is_retweet'] = is_retweet(tweet)
    new_doc['created_at_list'] = normalise_createdat(doc['created_at'])

    ####### Step 1: Add meta data
    # Use original tweet if it has been retweeted
    if is_retweet(tweet):
        orig_tweet = doc['retweeted_status']
    else:
        orig_tweet = doc

    ## [META] 'Normalise' or standardise the location string
    # TODO: https://developer.twitter.com/en/docs/tweets/data-dictionary/overview/geo-objects.html
    loc_str = None
    if 'place' in orig_tweet and orig_tweet['place'] is not None:
        loc_str = orig_tweet['place']['full_name']
    else:
        # next best guess is to look at user's profile loc
        loc_str = orig_tweet['user']['location']

    # 'geo' JSON field is deprecated; use 'coordinates' instead
    # 'coordinates' is in (long, lat) format; want it the other way
    if 'coordinates' in orig_tweet and orig_tweet['coordinates'] is not None:
        new_doc['coordinates'] = loc_str['coordinates'][::-1]
    
    # 'normalise' location string
    loc_nor_name, is_vic = find_user_location(loc_str, db_geocodes, arcgis)
    new_doc['loc_norm'] = loc_nor_name

    # don't add tweet to db if not in Victoria
    if not is_vic:
        return None

    ## [META] Copy other related query metadata
    new_doc['meta_general'] = query_doc['meta_general']

    # specific metadata for searched query/term is optional
    if 'meta_query' in query_doc and  current_term in query_doc['meta_query']:
        new_doc['meta_query'] = dict(query_doc['meta_query'][current_term],
                                    **{'query': current_term})

    return new_doc

def modify_twitter_doc(tweet):
    # TODO: Fix this
    return None

def notify_twit_save_status(added, doc_id):
    if not added:
        print("Tweet already added:\t", doc_id)
    else:
        print("Tweet accepted:\t", doc_id)