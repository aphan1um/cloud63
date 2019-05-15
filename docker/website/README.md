# Website front-end
 Has static web-pages to host our website via Nginx. With Nginx's configuration, it also allows to interact with our website to interact with our REST API server within a Docker stack.

## File overview:
1. *index.html*: Main web page.
2. *maps.html*: Map web-page with associated files: *gdropdown.js*, *gdropdown.css*, *rainbow.js* and *cloud_scenarios.js*. Uses Google Maps as a map service.
3. *graphs.html*: Web-page containing graphs of our Twitter data. Uses script *index.js* that contains the logic to display graphs.
4. *nginx.conf*: Nginx configuration file, to display our website and allow access to REST API server within Docker.
5. *json_maps/*: Contains .geojson files to load up LGA regions per concerned Australian states into Google Maps.
6. *Dockerfile*: Pertains to creation of front-end as a Docker image.

## Credits:
* [chart.js](https://www.chartjs.org/) for displaying charts on our graphs web-page.
* [RainbowVis-JS](https://github.com/anomal/RainbowVis-JS) for allowing to create a gradient of colours shown on the maps webpage.
* [Google Map web-page example](http://vislab-ccom.unh.edu/~briana/examples/gdropdown/) for showing example on how to display a custom combobox inside a Google Map.
* [Mapshaper](https://mapshaper.org/) for compressing the .geojson files converted from AURIN, so that they would load fast enough.

