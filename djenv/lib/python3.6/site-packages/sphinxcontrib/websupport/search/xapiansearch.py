# -*- coding: utf-8 -*-
"""
    sphinxcontrib.websupport.search.xapiansearch
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Xapian search adapter.

    :copyright: Copyright 2007-2016 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import xapian

from six import string_types

from sphinx.util.osutil import ensuredir
from sphinxcontrib.websupport.search import BaseSearch


class XapianSearch(BaseSearch):
    # Adapted from the GSOC 2009 webapp project.

    # Xapian metadata constants
    DOC_PATH = 0
    DOC_TITLE = 1

    def __init__(self, db_path):
        self.db_path = db_path

    def init_indexing(self, changed=[]):
        ensuredir(self.db_path)
        self.database = xapian.WritableDatabase(self.db_path,
                                                xapian.DB_CREATE_OR_OPEN)
        self.indexer = xapian.TermGenerator()
        stemmer = xapian.Stem("english")
        self.indexer.set_stemmer(stemmer)

    def finish_indexing(self):
        # Ensure the db lock is removed.
        del self.database

    def add_document(self, pagename, filename, title, text):
        self.database.begin_transaction()
        # sphinx_page_path is used to easily retrieve documents by path.
        sphinx_page_path = '"sphinxpagepath%s"' % pagename.replace('/', '_')
        # Delete the old document if it exists.
        self.database.delete_document(sphinx_page_path)

        doc = xapian.Document()
        doc.set_data(text)
        doc.add_value(self.DOC_PATH, pagename)
        doc.add_value(self.DOC_TITLE, title)
        self.indexer.set_document(doc)
        self.indexer.index_text(text)
        doc.add_term(sphinx_page_path)
        for word in text.split():
            doc.add_posting(word, 1)
        self.database.add_document(doc)
        self.database.commit_transaction()

    def handle_query(self, q):
        database = xapian.Database(self.db_path)
        enquire = xapian.Enquire(database)
        qp = xapian.QueryParser()
        stemmer = xapian.Stem("english")
        qp.set_stemmer(stemmer)
        qp.set_database(database)
        qp.set_stemming_strategy(xapian.QueryParser.STEM_SOME)
        query = qp.parse_query(q)

        # Find the top 100 results for the query.
        enquire.set_query(query)
        matches = enquire.get_mset(0, 100)

        results = []

        for m in matches:
            data = m.document.get_data()
            if not isinstance(data, string_types):
                data = data.decode("utf-8")
            context = self.extract_context(data)
            results.append((m.document.get_value(self.DOC_PATH),
                            m.document.get_value(self.DOC_TITLE),
                            ''.join(context)))

        return results
