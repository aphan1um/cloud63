class QueryDoc(object):
    def __init__(self, query, abbrev, item_type):
        self.abbrev = abbrev
        self.item_type = item_type
        self.query = query

    def to_dict(self):
        return {'_id': self.query, 'abbrev': self.abbrev,
                'meta': {'type': self.item_type}}

def batch_add_db(queries, db):
    all_docs = [q.to_dict() for q in queries]
    return db.update(all_docs)
