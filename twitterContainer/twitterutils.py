import tweepy
import couchdb

RATE_LIMIT_WAIT = 15 * 60

# Credit to http://docs.tweepy.org/en/latest/code_snippet.html
# for the example code.
def limit_handled(cursor):
    while True:
        try:
            yield cursor.next()
        except tweepy.RateLimitError as e:
            print("[WARNING] Rate limit hit! Now waiting for %d mins..."
                  % RATE_LIMIT_WAIT)
            time.sleep(RATE_LIMIT_WAIT)

def retry_save(db, id, init_doc, f_edit, f_state):
    added = False
    doc = None

    while not added:
        if db.get(str(id)) is None:
            doc = init_doc
            doc['_id'] = str(id)
        else:
            new_doc = f_edit(db.get(str(id)))
            if new_doc is None:
                break
            else:
                doc = new_doc

        try:
            db.save(doc)
        except couchdb.http.ResourceConflict: # revision issue
            # TODO: not sure if this is needed
            sleep(0.100)  # sleep for 100 ms for server relief
        else:
            added = True

        if f_state is not None:
            f_state(added, doc['_id'])

    
    return doc if doc is not None else db.get(str(id))

