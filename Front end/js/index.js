
var createPie = function(values, name)
{
    var canvasTemplate = '<canvas id="'+name+'" width="600"  height="400"></canvas>';
    var chartHolder = document.getElementById("chartHolder");
    chartHolder.innerHTML =canvasTemplate;
    var canvas = document.getElementById(name);

    Chart.defaults.global.defaultFontFamily = "Lato";
    Chart.defaults.global.defaultFontSize = 18;

    var charData = {
                labels : ["Good","Neutral","Bad"],
                datasets: [{
                  label : name,
                  data: values,
                  backgroundColor: [
                      "#63FF84",
                      "#ffdd40",
                      "#FF6384"
                  ]
            }]
    };

    var pieChart = new Chart(canvas, {
      type: 'pie',
      data: charData
    });
}

var createBarChart = function(values, name)
{
  var canvasTemplate = '<canvas id="'+name+'" width="600"  height="400"></canvas>';
    var chartHolder = document.getElementById("chartHolder");
    chartHolder.innerHTML =canvasTemplate;
    var canvas = document.getElementById(name);

    Chart.defaults.global.defaultFontFamily = "Lato";
    Chart.defaults.global.defaultFontSize = 18;

    var charData = {
                labels : ["Sunday","Monday","Tuesday","Wednesday", "Thursday","Friday","Saturday"],
                datasets: [{
                  label : name,
                  data: values,
                  backgroundColor: [
                      "#63FF84",
                      "#ffdd40",
                      "#FF6384",
                      "#b9f",
                      "#76daff",
                      "#2d303a"
                  ]
            }]
    };

    var pieChart = new Chart(canvas, {
      type: 'bar',
      data: charData
    });
}
var createBarChartRestaurant = function(values,label, name)
{
  var canvasTemplate = '<canvas id="'+name+'" width="600"  height="400"></canvas>';
    var chartHolder = document.getElementById("chartHolder");
    chartHolder.innerHTML =canvasTemplate;
    var canvas = document.getElementById(name);

    Chart.defaults.global.defaultFontFamily = "Lato";
    Chart.defaults.global.defaultFontSize = 18;

    var charData = {
                labels : label,
                datasets: [{
                  label : name,
                  data: values,
                  backgroundColor: [
                      "#63FF84",
                      "#ffdd40",
                      "#FF6384",
                      "#b9f",
                      "#76daff",
                      "#2d303a",
                       "#63FF84",
                      "#ffdd40",
                      "#FF6384",
                      "#b9f",
                      "#76daff",
                      "#2d303a",
                       "#63FF84",
                      "#ffdd40",
                      "#FF6384",
                      "#b9f",
                      "#76daff",
                      "#2d303a",
                       "#63FF84",
                      "#ffdd40",
                      "#FF6384",
                      "#b9f",
                      "#76daff",
                      "#2d303a"
                  ]
            }]
    };

    var pieChart = new Chart(canvas, {
      type: 'bar',
      data: charData
    });
}

var initBarResultViewRestaurant = function(chartData)
{
    var formatResponse = function(response)
{
    var labels = [];
    var values = [];
    var length = response.length;
    for(var i=0;i<length;i++)
    {
        labels.push(response[i].key);
        values.push(response[i].value);
    }
    return {labels : labels, values : values}
}
  var resultView = document.getElementById("resultView");
  resultView.innerHTML = "<div id='chartHolder'></div>";
  var temp=formatResponse(chartData)
  //First Time Initialization
    createBarChartRestaurant(temp.values,temp.labels, "restaurant");
}

var createBarChartHour = function(values, name)
{
  var canvasTemplate = '<canvas id="'+name+'" width="600"  height="400"></canvas>';
    var chartHolder = document.getElementById("chartHolder");
    chartHolder.innerHTML =canvasTemplate;
    var canvas = document.getElementById(name);

    Chart.defaults.global.defaultFontFamily = "Lato";
    Chart.defaults.global.defaultFontSize = 18;

    var charData = {
                labels : ["0","1","2","3","4","5","6","7","8","9","10","11","12","13","14","15","16","17","18","19","20","21","22","23"],
                datasets: [{
                  label : name,
                  data: values,
                  backgroundColor: [
                      "#63FF84",
                      "#ffdd40",
                      "#FF6384",
                      "#b9f",
                      "#76daff",
                      "#2d303a",
                      "#63FF84",
                      "#ffdd40",
                      "#FF6384",
                      "#b9f",
                      "#76daff",
                      "#2d303a",
                      "#63FF84",
                      "#ffdd40",
                      "#FF6384",
                      "#b9f",
                      "#76daff",
                      "#2d303a",
                      "#63FF84",
                      "#ffdd40",
                      "#FF6384",
                      "#b9f",
                      "#76daff",
                      "#2d303a"
                  ]
            }]
    };

    var pieChart = new Chart(canvas, {
      type: 'bar',
      data: charData
    });
}

var initBarResultViewHour = function(chartData)
{
  var resultView = document.getElementById("resultView");
  resultView.innerHTML = getDropDownHtml("barchart", chartData)+"<div id='chartHolder'></div>";
  document.getElementById("barchart").addEventListener("change", function(event){
        var value = event.srcElement.value;
        createBarChartHour(chartData[value], value);
  });
  //First Time Initialization
  for(var key in chartData)
  {
    createBarChartHour(chartData[key], key);
    break;
  }
}

var pieSampleData = {
  "Bad Food" : [24400, 16402, 11164],
  "Good Food" : [12000,  10000,16402]
}

var init = function()
{
    var divTemplate = '<div id="chartContainer"><div id="dropDownContainer"></div><div id="resultView"></div></div>';
    document.getElementsByTagName("body")[0].innerHTML +=divTemplate;
}

var barChartData= {
  "items": {
    "food": {
      "bad": [
        3482, 
        2348, 
        2230, 
        2323, 
        2883, 
        4260, 
        3645
      ], 
      "both": [
        5882, 
        4237, 
        3949, 
        3976, 
        5404, 
        6652, 
        6192
      ], 
      "good": [
        2400, 
        1889, 
        1719, 
        1653, 
        2521, 
        2392, 
        2547
      ]
    }
  }, 
  "state": "Victoria"
};
var fetchDetailsForBar = function(barChartData)
{
        var temp = barChartData.items.food;
            initBarResultView(temp);
}
var fetchDetailsForBarHour = function(barChartData)
{
        var temp = barChartData.items.food;
            initBarResultViewHour(temp);
}
var fetchDetailsForBarRestaurant = function(barChartData)
{
        var temp = barChartData.rows;
            initBarResultViewRestaurant(temp);
}
var fetchDetailsForPie = function(result)
{
          initPieResultView(result)
}


var dropDownCallBack = {
  fetchFromServer : function(value)
  {
      if(value === "Day")
      {
      //    fetchDetailsForBar(barChartData)
       $.getJSON("http://172.26.37.217/cloud/api/v1.0/stats/food_day/2?group=food", fetchDetailsForBar);
      }
      else if(value === "Sentiment Analysis")
      {
fetchDetailsForPie(pieSampleData)
//       $.getJSON("http://172.26.37.217/cloud/api/v1.0/stats/food_day/2?group=food", fetchDetailsForPie);
      }
      else if(value == "Tweets in Victoria Posted within 24hours")
      {
          $.getJSON("http://172.26.37.217/cloud/api/v1.0/stats/food_hour/2?group=food", fetchDetailsForBarHour);
      }
      else if(value == "All tweets with restaurant names posted within New South Wales")
      {
          $.getJSON("http://172.26.37.217/cloud/api/v1.0/stats/restaurant/1", fetchDetailsForBarRestaurant);
      }
  }
}

var initBarResultView = function(chartData)
{
  var resultView = document.getElementById("resultView");
  resultView.innerHTML = getDropDownHtml("barchart", chartData)+"<div id='chartHolder'></div>";
  document.getElementById("barchart").addEventListener("change", function(event){
        var value = event.srcElement.value;
        createBarChart(chartData[value], value);
  });
  //First Time Initialization
  for(var key in chartData)
  {
    createBarChart(chartData[key], key);
    break;
  }
}
var initBarResultViewHour = function(chartData)
{
  var resultView = document.getElementById("resultView");
  resultView.innerHTML = getDropDownHtml("barchart", chartData)+"<div id='chartHolder'></div>";
  document.getElementById("barchart").addEventListener("change", function(event){
        var value = event.srcElement.value;
        createBarChartHour(chartData[value], value);
  });
  //First Time Initialization
  for(var key in chartData)
  {
    createBarChartHour(chartData[key], key);
    break;
  }
}
var initPieResultView = function(chartData)
{
  var resultView = document.getElementById("resultView");
  resultView.innerHTML = getDropDownHtml("piechart", chartData)+"<div id='chartHolder'></div>";
  document.getElementById("piechart").addEventListener("change", function(event){
        var value = event.srcElement.value;
        createPie(chartData[value], value);
  });
  //First Time Initialization
  for(var key in chartData)
  {
    createPie(chartData[key], key);
    break;
  }
}
var getDropDownHtml = function(id, data)
{
  var dropDownTemplate = "<select id='"+id+"'>" ;
  var option = '<option value="{value}">{value}</option>';
  for(var key in data)
  {
        dropDownTemplate += option.replace(/{value}/g,key);
  }
  dropDownTemplate += "</select>"; 
  return dropDownTemplate;
}
var initDropDown = function(data)
{
  
  document.getElementById("dropDownContainer").innerHTML = getDropDownHtml("defaultDrop", data);
  document.getElementById("defaultDrop").addEventListener("change", function(event){
    var value = event.srcElement.value;
    dropDownCallBack.fetchFromServer(value);
    
  });
}
init();
initDropDown({"Day" : "1", "Sentiment Analysis":"2", "Tweets in Victoria Posted within 24hours":"3", "All tweets with restaurant names posted within New South Wales":"4"});