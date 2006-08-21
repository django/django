from base import Indexer
from query import ResultSet, Hit
from itertools import imap
import os, sys

import PyLucene

# WARNING!*
# PyLucene wants you to use PyLucene.PythonThread for threading.
# Look at samples/ThreadIndexFiles.py bundled with PyLucene.
# * I'm not sure how important this is.

# TODO: Make Lucene aware of field types.

# Here's how to use me:
#
# class Person(models.Model):
#     first_name = models.CharField(maxlength=30)
#     last_name = models.CharField(maxlength=30)
#     biography = models.TextField()
#
# indexer = LuceneIndexer('/tmp/lucene-index', Person, [biography],
#                         {'first': 'Person.first_name',
#                          'last': 'Person.last_name'})
# indexer.update() # Note, calling this multiple times without clearing old
#                  # entries will cause duplicates in the index.
# indexer.search("brian -last:beck")

class LuceneIndexer(Indexer):
    def __init__(self, *args, **kwargs):
        # FIXME: This uses the sys._getframe hack to get the caller's namespace.
        namespace = sys._getframe(1).f_globals
        kwargs['namespace'] = namespace
        super(LuceneIndexer, self).__init__(*args, **kwargs)
        self.writer_closed = True

    def _prepare_path(self, path):
        # Lucene wants an abstraction of the directory.
        # Should look into storage in a Model-compatible database in the future...
        self._store = PyLucene.FSDirectory.getDirectory(path, True)

    def update(self, documents=None):
        close = False
        if self.writer_closed:
            close = True
            self.open_writer()

        if documents is None:
            update_queue = self.model.objects.all()
        else:
            update_queue = documents

        for document in update_queue:
            self.delete(document)
            self.index(document)

        if close:
            self.close_writer()

    def clear(self):
        close = False
        if self.writer_closed:
            close = True
            self.open_writer()
        for i in xrange(self._writer.docCount()):
            self._writer.deleteDocument(i)
        if close:
            self.close_writer()

    def delete(self, row):
        reader = PyLucene.IndexReader.open(self.path)
        reader.deleteDocuments(PyLucene.Term('pk', str(row._get_pk_val())))
        reader.close()

    def open_writer(self):
        self.writer_closed = False
        self._writer = PyLucene.IndexWriter(self._store, PyLucene.StandardAnalyzer(), True)
        self._writer.setMaxFieldLength(1048576) # Max number of tokens stored per field?

    def close_writer(self):
        self._writer.optimize()
        self._writer.close()
        self.writer_closed = True

    def index(self, row):
        close = False
        if self.writer_closed:
            close = True
            self.open_writer()

        document = PyLucene.Document()

        for name, field in self.attr_fields.iteritems():
            # FIXME: Assumes no Foreign Keys! Lame!
            value = getattr(row, field.name)
            document.add(PyLucene.Field(name, str(value),
                                        PyLucene.Field.Store.YES,
                                        PyLucene.Field.Index.TOKENIZED))
        # Lucene only seems to support one 'default' field.
        # However, we might want multiple fields to be searched
        # by default. Hopefully just joining their contents with
        # newlines solves this.
        contents = '\n'.join([str(getattr(row, field.name)) for field in \
                              self.text_fields])
        # FIXME: Hardcoded 'contents' field.
        document.add(PyLucene.Field('contents', contents,
                                    PyLucene.Field.Store.YES,
                                    PyLucene.Field.Index.TOKENIZED))
        self._writer.addDocument(document)
        if close:
            self.close_writer()

    def search(self, query_string, default_field='contents', order_by='RELEVANCE'):
        searcher = PyLucene.IndexSearcher(self._store)
        analyzer = PyLucene.StandardAnalyzer()
        query = PyLucene.QueryParser(default_field, analyzer).parse(query_string)

        if order_by == 'SCORE':
            sort_field = PyLucene.SortField.FIELD_SCORE
            sort = PyLucene.Sort(sort_field)
        elif order_by == 'INDEX':
            sort = PyLucene.Sort.INDEXORDER
        elif order_by == 'RELEVANCE':
            sort = PyLucene.Sort.RELEVANCE
        else:
            reverse = order_by.startswith('-')
            while order_by[0] in '+-':
                order_by = order_by[1:]
            sort_field = PyLucene.SortField(order_by, reverse)
            sort = PyLucene.Sort(sort_field)
        hits = searcher.search(query, sort)
        return LuceneResultSet(hits, self)


class LuceneResultSet(ResultSet):
    def __init__(self, hits, indexer):
        self._hits = hits
        self._indexer = indexer

    def __len__(self):
        return self._hits.length()

    def __iter__(self):
        for hit in self._hits:
            yield LuceneHit(hit, self._indexer)

    def __getitem__(self, item):
        return LuceneHit(self._hits.__getitem__(item))


class LuceneHit(Hit):
    def get_pk(self):
        # FIXME: Hardcoded 'pk' field.
        return self.data.get('pk')

    def __getitem__(self, item):
        return self.data.__getitem__(item)

    def get_score(self):
        return self.data.getScore()

    score = property(get_score)
