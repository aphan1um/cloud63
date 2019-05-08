class MetadataBase(object):
    def __init__(self, query, version):
        self.query = query
        self.version = 0.0

    def get_meta_general(self):
        return {'version' : self.version}

    def get_data(self):
        return {}

    def to_dict(self):
        ret = self.get_data()
        ret.update({'meta_general': self.get_meta_general(),
                    '_id': self.query})
        return ret

class Metadata_V1(MetadataBase):
    def __init__(self, query, abbrev, item_type):
        MetadataBase.__init__(self, query, 1.0)
        self.abbrev = abbrev
        self.item_type = item_type

    def get_data(self):
        return { 'abbrev': self.abbrev }

    def get_meta_general(self):
        return dict({'type': self.item_type},
                    **super(Metadata_V1, self).get_meta_general())


def batch_add_db(queries, db):
    all_docs = [q.to_dict() for q in queries]
    return db.update(all_docs)
