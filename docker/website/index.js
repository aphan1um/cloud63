
var createPie = function(values, name)
{
    var canvasTemplate = '<canvas id="'+name+'" width="100"  height="100"></canvas>';
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
      data: charData,
      options: {
        pieceLabel: {
          render: 'value'
        },
        responsive: true
      }
    });
}

var createScatter = function(values, name)
{
    var canvasTemplate = '<canvas id="'+name+'" width="100"  height="100"></canvas>';
    var chartHolder = document.getElementById("chartHolder");
    chartHolder.innerHTML = canvasTemplate;
    var canvas = document.getElementById(name);

    Chart.defaults.global.defaultFontFamily = "Lato";
    Chart.defaults.global.defaultFontSize = 18;

    var scatterChart = new Chart(canvas, {
      type: 'scatter',
      data: {
        datasets: [{
          label: name,
          data: values,
          showLine: false,
          pointBackgroundColor: "#FF0000",
          pointRadius: 5,
          pointHoverRadius: 6.5
        }]
      },
      responsive: true
    });
}

var createBarChart = function(values, name)
{
  var canvasTemplate = '<canvas id="'+name+'" width="100"  height="100"></canvas>';
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
      data: charData,
      options: {
        pieceLabel: {
          render: 'value'
        },
        responsive: true
      }
    });
}
var createBarChartRestaurant = function(values,label, name)
{
  var canvasTemplate = '<canvas id="'+name+'" width="100"  height="100"></canvas>';
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
                  backgroundColor: "#736AFF"
            }]
    };

    var pieChart = new Chart(canvas, {
      type: 'bar',
      data: charData,
      options: {
        pieceLabel: {
          render: 'value'
        }
      },
      responsive: true
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
  resultView.innerHTML = "<div style='width:60%; height:60%' id='chartHolder'></div>";
  var temp=formatResponse(chartData)
  //First Time Initialization
    createBarChartRestaurant(temp.values,temp.labels, "restaurant");
}

var createBarChartHour = function(values, name)
{
  var canvasTemplate = '<canvas id="'+name+'" width="12"  height="10"></canvas>';
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
                  backgroundColor: "#4CC417"
            }]
    };

    var pieChart = new Chart(canvas, {
      type: 'bar',
      data: charData,
      options: {
        pieceLabel: {
          render: 'value'
        }
      }
    });
}

var initBarResultViewHour = function(chartData)
{
  var resultView = document.getElementById("resultView");
  resultView.innerHTML = getDropDownHtml("barchart", chartData)+"<div style='width:60%; height:60%' id='chartHolder'></div>";
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


var init = function()
{
    var divTemplate = '<div id="chartContainer"><div id="dropDownContainer"></div><div id="resultView"></div></div>';
    document.getElementsByTagName("body")[0].innerHTML +=divTemplate;
}

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
      if(value === "Count of all food tweets within Victoria, arranged by day")
      {
       $.getJSON("/test/cloud/api/v1.0/stats/food_day/2?group=food", fetchDetailsForBar);
      }
      else if(value === "Sentiment Analysis of all food tweets within VIC/NSW/QLD/ACT")
      {
        $.getJSON("/test/cloud/api/v1.0/stats/sentiment/", function(data) {
          new_data = {"Bad food": data['bad'], "Good food": data['good']};
          fetchDetailsForPie(new_data);
        });
      }
      else if(value == "'Food Tweets' in Victoria Posted grouped by 24-hour time")
      {
          $.getJSON("/test/cloud/api/v1.0/stats/food_hour/2?group=food", fetchDetailsForBarHour);
      }
      else if(value == "All tweets with restaurant names posted within New South Wales")
      {
          $.getJSON("/test/cloud/api/v1.0/stats/restaurant/1", fetchDetailsForBarRestaurant);
      } else if (value == "S1 - Estimated # of obese people vs proportion of bad tweets in VIC (per LGA)") {
        $.getJSON("/test/cloud/api/v1.0/scenario/1/2", (data) =>
            createScatterPlot(data,
              "Percentage of bad food tweets vs est. num of obese people per 100 population"));

      } else if (value == "S2 - Estimated # of people with adequate fruit intake vs proportion of good food tweets in VIC (per LGA)") {
        $.getJSON("/test/cloud/api/v1.0/scenario/2/2", (data) =>
            createScatterPlot(data,
              "Percentage of good food tweets vs est. num of people with adequate fruit intake"));
      }
  }
}

var createScatterPlot = function(data, name)
{
  points = [];
  Object.keys(data).forEach(function (lgac) {
      if (data[lgac].aurin_rate && data[lgac].tweet_percent) {
        points.push({x: data[lgac].aurin_rate, y: data[lgac].tweet_percent});
      }
  });
  console.log(points);

  var resultView = document.getElementById("resultView");
  resultView.innerHTML = "<div style='width:60%; height:60%' id='chartHolder'></div>";
  
  // input [{x,y}] values
  createScatter(points, name);
}


var initBarResultView = function(chartData)
{
  var resultView = document.getElementById("resultView");
  resultView.innerHTML = getDropDownHtml("barchart", chartData)+"<div style='width:60%; height:60%' id='chartHolder'></div>";
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
  resultView.innerHTML = getDropDownHtml("barchart", chartData)+"<div style='width:60%; height:60%' id='chartHolder'></div>";
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
  resultView.innerHTML = getDropDownHtml("piechart", chartData)+"<div style='width:40%; height:40%' id='chartHolder'></div>";
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
initDropDown({"Count of all food tweets within Victoria, arranged by day" : "1",
              "Sentiment Analysis of all food tweets within VIC/NSW/QLD/ACT": "2",
              "'Food Tweets' in Victoria Posted grouped by 24-hour time": "3",
              "All tweets with restaurant names posted within New South Wales": "4",
              "S1 - Estimated # of obese people vs proportion of bad tweets in VIC (per LGA)" : "5",
              "S2 - Estimated # of people with adequate fruit intake vs proportion of good food tweets in VIC (per LGA)" : "6"});