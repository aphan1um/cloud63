# Docker
 This folder represents different components of our system, which were then turned into Docker images and deployed onto [Docker Hub](https://hub.docker.com/) publicly. Docker Swarm would then handle who would run these containers to different VM Nectar instances within the swarm.

More specifically, the images were pushed onto Docker Hub under user name ```aphan1um``` and tags:
|Folder name| Docker tag |
|--|--|
| *twitter_scraper* | ```twittest:final``` |
| *restful_api* | ```restapi:final``` |
| *website* | ```web:final``` |

## Folder contents
 * *website*: Our front-end website to be hosted on our Nectar instances.
 * *twitter_scraper*: Twitter harvester.
 * *restful_api*: Represents a REST API server which our website interacts with. Server then gets relevant data from CouchDB's views to send back to the web-pages.
