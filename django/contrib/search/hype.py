from base import Indexer
from query import ResultSet, Hit

import hype

# TODO: This is very incomplete.

class HypeIndexer(Indexer):
    def __init__(self, *args, **kwargs):
        super(Indexer, self).__init__(*args, **kwargs)
        self.db = hype.Database(self.path, hype.ESTDBWRITER | hype.ESTDBCREAT)

    def index(self, row):
        document = hype.Document()
        document['@pk'] = row._get_pk_val()
        document.add_text()

    def search(self, query_string, sortBy=None):
        searcher = self.db.search(query_string)
        return HypeResultSet(searcher)

    def close(self):
        self.db.close()


class HypeResultSet(ResultSet):
    def __len__(self):
        return len(self._hits)

    def __iter__(self):
        for hit in self._hits:
            yield HypeHit(hit, self._indexer)

class HypeHit(Hit):
    pass