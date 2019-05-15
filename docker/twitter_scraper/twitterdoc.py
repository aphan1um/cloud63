from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from twitterutils import find_user_location, normalise_createdat

vader_analyser = SentimentIntensityAnalyzer()

def is_retweet(tweet):
    return 'retweeted_status' in tweet._json

def prepare_twitter_doc(tweet, query_doc, db_geocodes, arcgis):
    doc = tweet._json

    # Turn created at date into list
    doc['createdat_list'] = normalise_createdat(doc['created_at'])

    ####### Add meta data
    # Use original tweet if it has been retweeted (location is null
    # for retweeter)
    if is_retweet(tweet):
        orig_tweet = doc['retweeted_status']
    else:
        orig_tweet = doc

    ## [META] Vader sentiment analysis tool
    doc['vader_score'] = vader_analyser.polarity_scores(doc['full_text'])

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
    #if 'coordinates' in orig_tweet and orig_tweet['coordinates'] is not None:
    #    if 'coordinates' in orig_tweet['coordinates'] and orig_tweet['coordinates']['type'] == 'Point':
    #        doc['coordinates'] = doc['coordinates']['coordinates'][::-1]
    
    # 'normalise' location string
    loc_doc, within_states = find_user_location(loc_str, db_geocodes, \
                                               arcgis, is_aus=True)
 
    doc['location_data'] = loc_doc

    ## [META] Copy query metadata
    if query_doc is not None:
        doc['queries'] = {query_doc['_id']: query_doc['meta']}
    else:
        doc['queries'] = {}

    return doc, within_states

def modify_twitter_doc(query_doc):
    def wrapper_f(doc):
        if 'queries' in doc:
            doc['queries'][query_doc['_id']] = query_doc['meta']
            return doc
        return None

    if query_doc is None:
        return lambda doc : None
    else:
        return wrapper_f