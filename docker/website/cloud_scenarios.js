var scenario_data = {};
var current_scenario = null;

const ALL_STATES = {'Victoria': 2, 'New South Wales': 1, 'Queensland': 3,
                    'Australian Capital Territory': 8};
var enabled_states = {1: false, 2: false, 3: false, 8: false};

function toggle_state_visbility(name, map) {
  var lga_prefix = ALL_STATES[name];
  enabled_states[lga_prefix] = !(enabled_states[lga_prefix]);
  
  if (enabled_states[lga_prefix]) {
    all_gmap_datas[lga_prefix].setMap(map);
  } else {
    all_gmap_datas[lga_prefix].setMap(null);
  }
}

function load_scenario_data_LGA(evt, lga_prefix) {
    var lga_code = evt.feature.getProperty('lga_code').toString();
    var lga_name = evt.feature.getProperty('lga_name');

    var text = "<h3>" + lga_name + ' ' + lga_code + "</h3>";

    if (current_scenario == null || enabled_states[lga_prefix] == false) {
      return text;
    }

    switch (current_scenario) {
      case 1:
        text += "<p>Estimated # obese people (BMI 30+):\t"; 
        break;
      case 2:
        text += "<p>Est. # people with adequate fruit intake:\t"; 
        break;
    }

    if (typeof scenario_data[lga_code].aurin_rate === "undefined")
      text += "N/A (statistic not recorded for LGA)."
    else
      text += scenario_data[lga_code].aurin_rate + " per 100 people (age-standardised).</p>";

    switch (current_scenario) {
      case 1:
        text += "<p>Percentage of tweets with 'bad' food:\t";
        break;
      case 2:
        text += "<p>Percentage of tweets with 'good' food:\t";
        break;
    }

    if (typeof scenario_data[lga_code].tweet_percent === "undefined")
      var tweet_percent = "N/A"
    else
      var tweet_percent = scenario_data[lga_code].tweet_percent.toFixed(2);

    text += tweet_percent + "%</p>";
    
    if (tweet_percent > 0) {
      text += "Top 5 food queries (of all " 
                + (current_scenario == 1 ? "bad" : "good") + " food queries):"
      // retrieve top 5 food queries
      text += "<table><tr><th>Query</th><th>Food type</th><th>Percentage</th><th>Unhealthy?</th></tr>"
      
      var data;
      $.ajax({ 
        // TODO: Make it work for scenario 2
        url: '/test/cloud/api/v1.0/scenario/food/' + lga_code
          + "?top=5&bad_only=" + (current_scenario == 1 ? "true" : "false"), 
        dataType: 'json', 
        data: data, 
        async: false, 
        success: function (data) {
          data.items.forEach(function (food_query) {
            text += "<tr><td>" + food_query.query;

            if (food_query.brand != null)
              text += "  (" + food_query.brand + ")  "
            
            text += "</td><td>" + food_query.type;
            text += "</td><td>" + food_query.percent.toFixed(2) + "%"
            text += "</td><td>" + (food_query.unhealthy ? "Yes" : "No") + "</td></tr>"
        });
        }
      });
    }

    return text;
}

function load_scenario(map, new_scenario_num) {
    var rainbow = new Rainbow();
    var color_use = null;
    var color_groups = 4;

    window.scenario_data = {}
    window.current_scenario = null;

    switch (new_scenario_num) {
      case 1:
        color_use = 'red';
        break;
      case 2:
        color_use = 'blueviolet';
        break;
    }

    rainbow.setNumberRange(1, color_groups);
    rainbow.setSpectrum('white', color_use);

    Object.keys(enabled_states).forEach(function (st) {
        if (enabled_states[st] == false) return;

        $.getJSON('/test/cloud/api/v1.0/scenario/' + new_scenario_num + '/' + st,
          function (data) {
            
            window.scenario_data = Object.assign({}, window.scenario_data, data);
            aurin_stats = Object.values(data).map(function (v) { return parseFloat(v.aurin_rate); });
            stat_max = Math.max.apply(null, aurin_stats.filter(n => !isNaN(n)));
            stat_min = Math.min.apply(null, aurin_stats.filter(n => !isNaN(n)));

            keys = Object.keys(data);
            
            for (var i = 0; i < keys.length; i++) {
              if (isNaN(aurin_stats[i])) continue;

              var group = (keys.length <= 1) ? color_groups :
                Math.ceil((aurin_stats[i] - stat_min)/(stat_max - stat_min) * color_groups);
              all_gmap_datas[st].overrideStyle(all_gmap_datas[st].getFeatureById(keys[i]), 
                  {fillColor: '#' + rainbow.colorAt(group) });
            }
        });

        window.current_scenario = new_scenario_num;
    });
  }