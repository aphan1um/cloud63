'''
'
' [COMP90024 Assignment 2]
' File: flask_server.py
' Description: REST API server for querying information from database.
'
' For Cloud Team 63:
'  * Akshaya Shankar - 1058281
'  * Andy Phan - 696382
'  * Chenbang Huang - 967186
'  * Prashanth Shrinivasan - 986472
'  * Qian Sun – 1027266
'
'''

# Credit to: https://blog.miguelgrinberg.com/post/designing-a-restful-api-with-python-and-flask
# for info on how to write rest api with Flask 

from flask import Flask, make_response, jsonify, abort, request
from flask_cors import CORS, cross_origin

import os
import couchdb
from collections import Counter, defaultdict, OrderedDict
from bidict import bidict
import pytz
import json

app = Flask(__name__)
CORS(app)

########################   CONSTANTS HERE:   ######################

DB_URL = os.environ['API_COUCHDB_URL']
# database name for tweets
TWEETS_DB_NAME = os.environ['API_TWEETS_DBNAME']
# database name containing AURIN statistics
AURIN_DB_NAME = os.environ['API_AURIN_DBNAME']

# LGA prefix and full name of state (e.g. all LGAs within Victoria
# have LGA codes in the range 20000-29999)
STATE_LGA_PREFIX = bidict(
                    { 3 : 'Queensland', 8 : 'Australian Capital Territory',
                      2 : 'Victoria',  1: 'New South Wales'})

# LGA prefix and state abbreviations
STATE_LGA_ABBREV = bidict({ 3 : 'qld', 8 : 'act', 2 : 'vic',  1: 'nsw'})

# Order of days (so Sunday would be ordered first of all 7 days)
JS_DAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]


db_server = couchdb.Server(DB_URL)
db_tweets = db_server[TWEETS_DB_NAME]
db_aurin = db_server[AURIN_DB_NAME]


########################   FUNCTIONS:   ######################

def utc_hour_diff():
    ''' Set UTC time to AEST hours. '''
    return 10

@app.route('/')
def index():
    return "Page is running!"

@app.route('/hello/world')
def index2():
    return "Hello world!"

@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify( {'error': 'Not found.'} ), 404)


@app.errorhandler(400)
def bad_request(error):
    return make_response(jsonify( {'error': 'Bad request.'} ), 400)

#@app.route('/cloud/api/v1.0/obesity/<int:lga_code>', methods = ['GET'])
#def get_lga_info(lga_code):
#    if lga_code in STATE_LGA_PREFIX.keys():
#        view = db_server.view("demo/foodsByLGA")
#    else:
#        abort(404)

def lga_code_exists(lga_code):
    ''' Check if LGA code exists in AURIN data. '''
    lga_aurin_data = db_aurin.get(str(lga_code))
    return lga_aurin_data is not None


@app.route('/cloud/api/v1.0/scenario/2/<int:lga_prefix>', methods = ['GET'])
def lga_good_foods(lga_prefix):
    '''
    Get proportion of good tweet foods for a state, appending with
    AURIN statistic regarding estimated number of obese people per LGA in
    state.
    '''
    return get_food_prop_byState(lga_prefix, False, 'obese_p_2_asr')


@app.route('/cloud/api/v1.0/scenario/1/<int:lga_prefix>', methods = ['GET'])
def lga_bad_foods(lga_prefix):
    '''
    Get proportion of 'bad' tweet foods for a state, appending with
    AURIN statistic regarding proportion of people with sufficient fruit
    intake per LGA in state.
    '''
    return get_food_prop_byState(lga_prefix, True, 'frt_intk_2_asr')


@app.route('/cloud/api/v1.0/scenario/food/<int:lga_code>', methods = ['GET'])
def get_food_queries(lga_code):
    '''
    Get info on food tweets by specific LGA code.
    '''

    if not lga_code_exists(lga_code):
        abort(404)
    
    ret_json = []
    queries_view = db_tweets.view('scenarios/foodsByLGA', startkey=[lga_code], \
        endkey=[lga_code, {}], group=True, stale='update_after')

    # if query argument has bad_only=true, then only count tweets that
    # were considered 'bad food'; if bad_only=false, consider only good foods
    # if not specified, collect both
    if 'bad_only' in request.args:
        if request.args.get('bad_only').lower() == 'true':
            queries_view = db_tweets.view('scenarios/foodsByLGA', \
                startkey=[lga_code, True], endkey=[lga_code, True, {}], group=True, stale='update_after')
        elif request.args.get('bad_only').lower() == 'false':
            queries_view = db_tweets.view('scenarios/foodsByLGA', \
                startkey=[lga_code, False], endkey=[lga_code, False, {}], group=True, stale='update_after')
        else:
            abort(400)
    else:
        queries_view = db_tweets.view('scenarios/foodsByLGA', startkey=[lga_code], \
            endkey=[lga_code, {}], group=True, stale='update_after')

    # get all tweets in view (grouped & reduced by its keys from CouchDB)
    all_items = [v for v in queries_view]
    total_foodtweets = sum([v.value for v in all_items])

    for item in all_items:
        query = item.key[3]
        food_brand = item.key[4]
        food_type = item.key[2]
        food_unhealthy = item.key[1]

        ret_json.append({'query': query, 'type': food_type, \
            'unhealthy': food_unhealthy, 'brand': food_brand, \
            'percent': 0 if total_foodtweets == 0 else (item.value/total_foodtweets * 100)})

    ret_json = sorted(ret_json, key=lambda k: k['percent'], reverse=True)

    # if query argument has 'top', then only the top tweets by percentage
    if 'top' in request.args:
        ret_json = ret_json[:int(request.args.get('top'))]
    
    return jsonify( {'items': ret_json} )


def get_food_prop_byState(lga_prefix, consider_badFoods, aurin_stat):
    '''
    Collect info on proportion of good/bad food tweets based for a specific
    state (LGA prefix), alongside an AURIN statistic to attach for each LGA
    region.
    '''

    if lga_prefix not in STATE_LGA_PREFIX.keys():
        abort(404)

    json_ret = defaultdict(dict)

    aurin_state = db_aurin.view('_all_docs', startkey=str(lga_prefix*10000), \
         endkey=str((lga_prefix + 1) * 10000), stale='update_after')

    # go through each LGA in state
    for lga_area in aurin_state:
        lga_doc = db_aurin.get(lga_area.id)
        lga_code = int(lga_area.id)
        
        foodCountView = db_tweets.view('scenarios/tweetCounts', \
            startkey=[lga_code, "food"], endkey=[lga_code, "food", {}], \
            group=True, stale='update_after')
        foodCountItems = [v for v in foodCountView]

        view_items = {v.key[2] : v.value for v in foodCountItems}

        # if LGA contains number of tweets of bad/good food in LGA
        # (if consider_badFoods=true, get good food tweets info in LGA)
        if consider_badFoods in view_items:
            prop_group = view_items[consider_badFoods]/sum(view_items.values()) * 100
            json_ret[lga_code]["relevant_tweets"] = view_items[consider_badFoods]
        else:
            # if there's no tweets on good/bad food in LGA
            prop_group = 0
            json_ret[lga_code]["relevant_tweets"] = 0
        
        if aurin_stat in lga_doc:
            json_ret[lga_code]["aurin_rate"] = lga_doc[aurin_stat]
        
        json_ret[lga_code]["tweet_percent"] = prop_group
        json_ret[lga_code]["total_tweets"] = sum(view_items.values())

    return jsonify(json_ret)


@app.route('/cloud/api/v1.0/stats/food_hour/<int:lga_prefix>', methods = ['GET'])
def get_food_by_hour(lga_prefix):
    ''' Get food tweets by hour for a certain state. '''
    return get_food_by_time(lga_prefix, "stats/byHour", \
        lambda hour: (utc_hour_diff() + hour) % 24, \
        order=lambda x: x)


@app.route('/cloud/api/v1.0/stats/food_day/<int:lga_prefix>', methods = ['GET'])
def get_food_by_day(lga_prefix):
    ''' Get food tweets by day for certain Australian state. '''
    return get_food_by_time(lga_prefix, "stats/byDay", \
        lambda day: JS_DAYS[day], order=JS_DAYS.index)


def get_food_by_time(lga_prefix, view_loc, f_time, order):
    '''
    Get food tweet tweets based on a view related to time (hour/second/day).

    Other parameters:
        - f_time: Function to modify the time outputted.
        - order: Function to reorder the time units into proper order.
    '''
    if lga_prefix not in STATE_LGA_PREFIX.keys():
        abort(404)

    state_name = STATE_LGA_PREFIX[lga_prefix]
    
    view = db_tweets.view(view_loc, startkey=[state_name], \
            endkey=[state_name, {}], group=True, stale='update_after')

    # if 'group' parameter specified in REST query, get foods within
    # certain group (e.g. junk food tweets as 'junk_food' or tweets
    # containing any food text as 'food')
    if 'group' in request.args:
        group = request.args.get('group') if request.args.get('group') != "none" else None

        view.options['startkey'] =  [state_name, group]
        view.options['endkey'] = [state_name, group, {}]
    
    reduced_result = [i for i in view]

    # for each food group, get number bad/good/(bad+good) tweets in that
    # food group
    ret_json = defaultdict(lambda : defaultdict(Counter))
    for view_item in reduced_result:
        time_unit_adjust = f_time(view_item.key[2])
        
        if view_item.key[1] is not None:
            is_bad = "bad" if view_item.key[3] else "good"
            ret_json[view_item.key[1]][is_bad][time_unit_adjust] = view_item.value
            ret_json[view_item.key[1]]["both"][time_unit_adjust] += view_item.value
        else:
            ret_json["none"]["none"][time_unit_adjust] = view_item.value

    if order is not None:
        for food_group, value in ret_json.items():
            for is_bad, time_dict in value.items():
                ret_json[food_group][is_bad] = [i[1] for i in sorted(time_dict.items(), key= lambda k : order(k[0]))]
    
    return jsonify( {'items' : ret_json, 'state': state_name} )


@app.route('/cloud/api/v1.0/stats/restaurant', methods = ['GET'])
def get_restaurant_info_allStates():
    ''' Get # tweets for restaurants within all states. '''
    return get_restaurant_info(0, all_states=True)


@app.route('/cloud/api/v1.0/stats/restaurant/<int:lga_code>', methods = ['GET'])
def get_restaurant_info(lga_code, all_states=False):
    '''
    Get amount of tweets with restaurant names for a certain Aussie state.
    '''

    if all_states:
        view = db_tweets.view("stats/byRestaurant", group=True, stale='update_after')
    elif lga_code in STATE_LGA_PREFIX.keys():
        view = db_tweets.view("stats/byRestaurant", startkey=[lga_code*10000], \
            endkey=[(lga_code + 1) * 10000], reduce=False, stale='update_after')
    elif int(str(lga_code)[0]) in STATE_LGA_PREFIX.keys():
        lga_aurin_data = db_aurin.get(str(lga_code))
        if lga_aurin_data is None:
            abort(404)

        view = db_tweets.view("stats/byRestaurant", startkey=[lga_code], \
            endkey=[lga_code, {}], reduce=False, stale='update_after')
    else:
        abort(400)

    all_items = [v for v in view]
    # aggregate all LGA areas into a state
    agg_state = Counter()
    for item in all_items:
        agg_state[item.key[1]] += item.value

    res_counts = {k : abs(v) for k, v in agg_state.items()}

    if 'top' in request.args:
        # Credit to: https://stackoverflow.com/a/22916447 for the snippet
        res_counts = dict(Counter(res_counts).most_common(int(request.args.get('top'))))
    
    res_counts = [{"key": k, "value": v} for k, v in res_counts.items()]

    return jsonify( {"rows": res_counts } )


@app.route('/cloud/api/v1.0/stats/sentiment/', methods = ['GET'])
def get_sentiment_tweets():
    ''' Get VADER sentiment on all food tweets for all concerned states. '''
    view_allFoodTweets = db_tweets.view('stats/bySentiment', startkey=["food"], \
        endkey=["food", {}], group_level=2, stale='update_after')
    sentiment_foodGroups = {"bad" if v.key[1] else "good" : v.value \
        for v in view_allFoodTweets}
    
    return jsonify(sentiment_foodGroups)
    

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')