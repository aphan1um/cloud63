# Credit to: https://blog.miguelgrinberg.com/post/designing-a-restful-api-with-python-and-flask

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

DB_URL = os.environ['API_COUCHDB_URL']
TWEETS_DB_NAME = os.environ['API_TWEETS_DBNAME']
AURIN_DB_NAME = os.environ['API_AURIN_DBNAME']

STATE_LGA_PREFIX = bidict(
                    { 3 : 'Queensland', 8 : 'Australian Capital Territory',
                      2 : 'Victoria',  1: 'New South Wales'})

STATE_LGA_ABBREV = bidict({ 3 : 'qld', 8 : 'act', 2 : 'vic',  1: 'nsw'})

JS_DAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

db_server = couchdb.Server(DB_URL)
db_tweets = db_server[TWEETS_DB_NAME]
db_aurin = db_server[AURIN_DB_NAME]

def utc_hour_diff():
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
    lga_aurin_data = db_aurin.get(str(lga_code))
    return lga_aurin_data is not None

@app.route('/cloud/api/v1.0/scenario/2/<int:lga_prefix>', methods = ['GET'])
def lga_good_foods(lga_prefix):
    return get_food_prop_byState(lga_prefix, False, 'obese_p_2_asr')

@app.route('/cloud/api/v1.0/scenario/1/<int:lga_prefix>', methods = ['GET'])
def lga_bad_foods(lga_prefix):
    return get_food_prop_byState(lga_prefix, True, 'frt_intk_2_asr')

@app.route('/cloud/api/v1.0/scenario/food/<int:lga_code>', methods = ['GET'])
def get_food_queries(lga_code):
    if not lga_code_exists(lga_code):
        abort(404)
    
    ret_json = []
    queries_view = db_tweets.view('scenarios/foodsByLGA', startkey=[lga_code], \
        endkey=[lga_code, {}], group=True)

    if 'bad_only' in request.args:
        if request.args.get('bad_only').lower() == 'true':
            queries_view = db_tweets.view('scenarios/foodsByLGA', \
                startkey=[lga_code, True], endkey=[lga_code, True, {}], group=True)
        elif request.args.get('bad_only').lower() == 'false':
            queries_view = db_tweets.view('scenarios/foodsByLGA', \
                startkey=[lga_code, False], endkey=[lga_code, False, {}], group=True)
        else:
            abort(400)
    else:
        queries_view = db_tweets.view('scenarios/foodsByLGA', startkey=[lga_code], \
            endkey=[lga_code, {}], group=True)

    
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
    if 'top' in request.args:
        ret_json = ret_json[:int(request.args.get('top'))]
    
    return jsonify( {'items': ret_json} )


def get_food_prop_byState(lga_prefix, consider_badFoods, aurin_stat):
    if lga_prefix not in STATE_LGA_PREFIX.keys():
        abort(404)

    json_ret = defaultdict(dict)

    aurin_state = db_aurin.view('_all_docs', startkey=str(lga_prefix*10000), \
         endkey=str((lga_prefix + 1) * 10000))

    for lga_area in aurin_state:
        lga_doc = db_aurin.get(lga_area.id)
        lga_code = int(lga_area.id)
        
        foodCountView = db_tweets.view('scenarios/tweetCounts', \
            startkey=[lga_code, "food"], endkey=[lga_code, "food", {}], \
            group=True)
        foodCountItems = [v for v in foodCountView]

        view_items = {v.key[2] : v.value for v in foodCountItems}

        if consider_badFoods in view_items:
            prop_group = view_items[consider_badFoods]/sum(view_items.values()) * 100
            json_ret[lga_code]["relevant_tweets"] = view_items[consider_badFoods]
        else:
            prop_group = 0
            json_ret[lga_code]["relevant_tweets"] = 0
        
        if aurin_stat in lga_doc:
            json_ret[lga_code]["aurin_rate"] = lga_doc[aurin_stat]
        
        json_ret[lga_code]["tweet_percent"] = prop_group
        json_ret[lga_code]["total_tweets"] = sum(view_items.values())

    return jsonify(json_ret)

@app.route('/cloud/api/v1.0/stats/food_hour/<int:lga_prefix>', methods = ['GET'])
def get_food_by_hour(lga_prefix):
    return get_food_by_time(lga_prefix, "stats/byHour", \
        lambda hour: (utc_hour_diff() + hour) % 24, \
        order=lambda x: x)

@app.route('/cloud/api/v1.0/stats/food_day/<int:lga_prefix>', methods = ['GET'])
def get_food_by_day(lga_prefix):
    return get_food_by_time(lga_prefix, "stats/byDay", \
        lambda day: JS_DAYS[day], order=JS_DAYS.index)

def get_food_by_time(lga_prefix, view_loc, f_time, order):
    if lga_prefix not in STATE_LGA_PREFIX.keys():
        abort(404)

    state_name = STATE_LGA_PREFIX[lga_prefix]
    
    view = db_tweets.view(view_loc, startkey=[state_name], \
            endkey=[state_name, {}], group=True)

    if 'group' in request.args:
        group = request.args.get('group') if request.args.get('group') != "none" else None

        view.options['startkey'] =  [state_name, group]
        view.options['endkey'] = [state_name, group, {}]
    
    reduced_result = [i for i in view]

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
    return get_restaurant_info(0, all_states=True)

@app.route('/cloud/api/v1.0/stats/restaurant/<int:lga_code>', methods = ['GET'])
def get_restaurant_info(lga_code, all_states=False):
    if all_states:
        view = db_tweets.view("stats/byRestaurant", group=True)
    elif lga_code in STATE_LGA_PREFIX.keys():
        view = db_tweets.view("stats/byRestaurant", startkey=[lga_code*10000], \
            endkey=[(lga_code + 1) * 10000], reduce=False)
    elif int(str(lga_code)[0]) in STATE_LGA_PREFIX.keys():
        lga_aurin_data = db_aurin.get(str(lga_code))
        if lga_aurin_data is None:
            abort(404)

        view = db_tweets.view("stats/byRestaurant", startkey=[lga_code], \
            endkey=[lga_code, {}], reduce=False)
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
    view_allFoodTweets = db_tweets.view('stats/bySentiment', startkey=["food"], \
        endkey=["food", {}], group_level=2)
    sentiment_foodGroups = {"bad" if v.key[1] else "good" : v.value \
        for v in view_allFoodTweets}
    
    return jsonify(sentiment_foodGroups)
    

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')