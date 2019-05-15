# Twitter script
A Python script to harvest/scrape Tweets using a CouchDB prepared databases. To be run as a Docker image.

## File overview:
1. *twitterscript.py*: Main Python script to collect Tweets.
2. *twitterutils.py*: Utility functions for twitterscript.py.
3. *twitterdoc.py*: Contains functions regarding creation/modification of CouchDB documents relating to Tweets.
4. *requirements.txt*: List of Python packages the Python Tweet scrape needs.
5. *Dockerfile*: Pertains to creation of a Docker image for this Python script.
6. *state_shapes.7z*: Archived file for containing files (from AURIN) that has info on local government areas (LGA) and their bounding regions. Used with script to find which LGA some location (with latitude & longitude) belongs into.
