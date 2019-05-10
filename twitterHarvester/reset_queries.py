import couchdb

server = couchdb.Server("http://user:pass@127.0.0.1:5984")
db = server['tweet_queries']

view = db.view('queryDD/last_ran')

# Reset script-related fields
for v in view:
    doc = db.get(v.id)
    doc.pop('since_ids', None)
    doc.pop('last_ran', None)
    doc.pop('streak_nonerecv', None)
    doc.pop('amount_added', None)
    doc.pop('streak_noneadded', None)

    db.save(doc)