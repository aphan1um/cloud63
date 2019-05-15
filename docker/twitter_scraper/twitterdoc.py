'''
'
' [COMP90024 Assignment 2]
' File: twitterdoc.py
' Description: Contains functions to create/modify Twitter document
'              when executed as arguments of save_document(...) function
'              in twitterutils.py 
'
' Team members:
'   Akshaya S. (1058281), Andy P. (696382), Chenbang H. (967186),
'   Prashanth S. (986472), Qian S. (1027266)
'
'''

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from twitterutils import find_user_location, normalise_createdat

# VADER sentiment analyser
vader_analyser = SentimentIntensityAnalyzer()

def is_retweet(tweet):
    return 'retweeted_status' in tweet._json


def prepare_twitter_doc(tweet, query_doc, db_geocodes, arcgis):
    ''' Prepare document (representing Tweet) to be added to database. '''

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
    # NOTE: 'place' attribute in Twitter object exists with 'coordinate',
    # so we can use this in place of 'coordinate'. However, coordinate
    # gives us exact location of tweet, where as place is approximate.
    # https://developer.twitter.com/en/docs/tweets/data-dictionary/overview/geo-objects.html
    loc_str = None

    if 'place' in orig_tweet and orig_tweet['place'] is not None:
        loc_str = orig_tweet['place']['full_name']
    else:
        # next best guess is to look at user's profile loc
        loc_str = orig_tweet['user']['location']

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
    '''
    Function to execute should the document representing a Tweet
    already exist.
    '''

    def wrapper_f(doc):
        # append query to tweet (this can happen if tweet gets searched
        # again under a different term/word/query)
        if 'queries' in doc:
            doc['queries'][query_doc['_id']] = query_doc['meta']
            return doc
        return None

    if query_doc is None:
        return lambda doc : None
    else:
        return wrapper_f