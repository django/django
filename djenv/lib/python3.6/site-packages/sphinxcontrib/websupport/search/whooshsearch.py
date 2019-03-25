# -*- coding: utf-8 -*-
"""
    sphinxcontrib.websupport.search.whooshsearch
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Whoosh search adapter.

    :copyright: Copyright 2007-2016 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from whoosh import index
from whoosh.fields import Schema, ID, TEXT
from whoosh.qparser import QueryParser
from whoosh.analysis import StemmingAnalyzer

from six import text_type

from sphinx.util.osutil import ensuredir
from sphinxcontrib.websupport.search import BaseSearch


class WhooshSearch(BaseSearch):
    """The whoosh search adapter for sphinx web support."""

    # Define the Whoosh Schema for the search index.
    schema = Schema(path=ID(stored=True, unique=True),
                    title=TEXT(field_boost=2.0, stored=True),
                    text=TEXT(analyzer=StemmingAnalyzer(), stored=True))

    def __init__(self, db_path):
        ensuredir(db_path)
        if index.exists_in(db_path):
            self.index = index.open_dir(db_path)
        else:
            self.index = index.create_in(db_path, schema=self.schema)
        self.qparser = QueryParser('text', self.schema)

    def init_indexing(self, changed=[]):
        for changed_path in changed:
            self.index.delete_by_term('path', changed_path)
        self.index_writer = self.index.writer()

    def finish_indexing(self):
        self.index_writer.commit()

    def add_document(self, pagename, filename, title, text):
        self.index_writer.add_document(path=text_type(pagename),
                                       title=title,
                                       text=text)

    def handle_query(self, q):
        searcher = self.index.searcher()
        whoosh_results = searcher.search(self.qparser.parse(q))
        results = []
        for result in whoosh_results:
            context = self.extract_context(result['text'])
            results.append((result['path'],
                            result.get('title', ''),
                            context))
        return results
