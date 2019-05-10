from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from twitterutils import find_user_location

vader_analyser = SentimentIntensityAnalyzer()

def prepare_twitter_doc(tweet, query_doc, db_geocodes, arcgis):
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

    ## [META] Vader sentiment analysis tool
    new_doc['vader_score'] = vader_analyser.polarity_scores(doc['full_text'])

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
        if 'coordinates' in orig_tweet['coordinates'] and orig_tweet['coordinates']['type'] == 'Point':
            new_doc['coordinates'] = doc['coordinates']['coordinates'][::-1]
    
    # 'normalise' location string
    loc_doc, is_aus = find_user_location(loc_str, db_geocodes, arcgis)
    
    # don't add tweet to db if not in Australia
    if not is_aus:
        return None
    
    new_doc['loc_norm'] = loc_doc['_id']
    new_doc['loc_state'] = loc_doc['state']

    ## [META] Copy other related query metadata
    new_doc['meta'] = {query_doc['_id']: query_doc['meta']}

    return new_doc

def modify_twitter_doc(query_doc, db_geocodes, arcgis):
    def wrapper_f(doc):
        doc['meta'][query_doc['_id']] = query_doc['meta']

        if 'loc_norm' in doc:
            doc_loc = db_geocodes.get(doc['loc_norm'])

            if doc_loc is None or 'loc_state' not in doc or 'loc_geohash' not in doc:
                doc_loc, is_aus = find_user_location(doc['loc_norm'], \
                                    db_geocodes, arcgis)
                doc['loc_state'] = doc_loc['state']
                doc['loc_geohash'] = doc_loc['geohash']

        if 'vader_score' not in doc:
            doc['vader_score'] = vader_analyser.polarity_scores(doc['full_text'])

        return doc

    return wrapper_f