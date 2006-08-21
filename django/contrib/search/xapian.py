from django.db import models
from datetime import datetime
import xapwrap.index
import xapwrap.document
from itertools import imap

from base import Indexer, ResultSet

# TODO: This is incomplete.

class XapianIndexer(Indexer):
    def update(self, documents=None):
        idx = xapwrap.index.Index(self.path, True)

        if documents is None:
            update_queue = self.model.objects.all()
        else:
            update_queue = documents

        for row in documents:
            keys = []
            for name, field in self.attr_fields.iteritems():
                keys.append(xapwrap.document.SortKey(name, getattr(self.model, field.name)))

            d = xapwrap.document.Document(textFields=fields, sortFields=keys, uid=row._get_pk_val())
            idx.index(d)
        idx.close()

    def search(self, query, order_by='RELEVANCE'):
        idx = Index(self.path)
        if order_by == 'RELEVANCE':
            results = idx.search(query, sortByRelevence=True)
        else:
            ascending = True
            if isinstance(order_by, basestring) and order_by.startswith('-'):
                ascending = False
            while order_by[0] in '+-':
                order_by = order_by[1:]
            results = idx.search(query, order_by, sortAscending=ascending)
        return XapianResultSet(results)


class XapianResultSet(ResultSet):
    def __init__(self, hits, indexer):
        self._hits = hits
        self._indexer = indexer

    def __len__(self):
        return len(self._hits)

    def __iter__(self):
        for hit in self._hits):
            yield XapianHit(hit, self._indexer)


class XapianHit(object):
    def get_pk(self):
        return self.data['pk']

    def get_score(self):
        return self.data['score']

    score = property(get_score)

