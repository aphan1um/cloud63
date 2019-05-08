from query_class import *
import csv
import sys
import couchdb

COUCHDB_URL = "http://user:pass@127.0.0.1:5700"
server = couchdb.Server(COUCHDB_URL)
db_query = server['tweet_queries']

csv_file = sys.argv[1]

with open(csv_file) as csv_file:
    csv_reader = csv.reader(csv_file, delimiter='\t')
    headers = next(csv_reader, None)

    idx_col_name = headers.index('product_name')
    
    queries = []
    for line in csv_reader:
        queries += [QueryDoc(line[idx_col_name], [], 'soft_drink') for line in csv_reader]

    batch_add_db(queries, db_query)

    