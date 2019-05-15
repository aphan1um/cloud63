# REST API server
 A Python script (using Flask) to handle queries from website regarding Twitter data on obesity. RESTFul API acts as an intermediary between the website and the CouchDB database, so the website does not need to directly query for certain information from CouchDB database views, which may be complex to ask for all within the website.

## File overview:
1. *flaskserver.py*: Main Python script to act as a REST API server.
4. *requirements.txt*: List of Python packages the Python script needs.
5. *Dockerfile*: Pertains to creation of a Docker image for this Python script.
