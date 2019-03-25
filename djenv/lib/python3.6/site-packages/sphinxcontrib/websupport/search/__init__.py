# -*- coding: utf-8 -*-
"""
    sphinxcontrib.websupport.search
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Server side search support for the web support package.

    :copyright: Copyright 2007-2016 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from six import text_type


class BaseSearch(object):
    def __init__(self, path):
        pass

    def init_indexing(self, changed=[]):
        """Called by the builder to initialize the search indexer. `changed`
        is a list of pagenames that will be reindexed. You may want to remove
        these from the search index before indexing begins.

        :param changed: a list of pagenames that will be re-indexed
        """
        pass

    def finish_indexing(self):
        """Called by the builder when writing has been completed. Use this
        to perform any finalization or cleanup actions after indexing is
        complete.
        """
        pass

    def feed(self, pagename, filename, title, doctree):
        """Called by the builder to add a doctree to the index. Converts the
        `doctree` to text and passes it to :meth:`add_document`. You probably
        won't want to override this unless you need access to the `doctree`.
        Override :meth:`add_document` instead.

        :param pagename: the name of the page to be indexed
        :param filename: the name of the original source file
        :param title: the title of the page to be indexed
        :param doctree: is the docutils doctree representation of the page
        """
        self.add_document(pagename, filename, title, doctree.astext())

    def add_document(self, pagename, filename, title, text):
        """Called by :meth:`feed` to add a document to the search index.
        This method should should do everything necessary to add a single
        document to the search index.

        `pagename` is name of the page being indexed. It is the combination
        of the source files relative path and filename,
        minus the extension. For example, if the source file is
        "ext/builders.rst", the `pagename` would be "ext/builders". This
        will need to be returned with search results when processing a
        query.

        :param pagename: the name of the page being indexed
        :param filename: the name of the original source file
        :param title: the page's title
        :param text: the full text of the page
        """
        raise NotImplementedError()

    def query(self, q):
        """Called by the web support api to get search results. This method
        compiles the regular expression to be used when :meth:`extracting
        context <extract_context>`, then calls :meth:`handle_query`.  You
        won't want to override this unless you don't want to use the included
        :meth:`extract_context` method.  Override :meth:`handle_query` instead.

        :param q: the search query string.
        """
        self.context_re = re.compile('|'.join(q.split()), re.I)
        return self.handle_query(q)

    def handle_query(self, q):
        """Called by :meth:`query` to retrieve search results for a search
        query `q`. This should return an iterable containing tuples of the
        following format::

            (<path>, <title>, <context>)

        `path` and `title` are the same values that were passed to
        :meth:`add_document`, and `context` should be a short text snippet
        of the text surrounding the search query in the document.

        The :meth:`extract_context` method is provided as a simple way
        to create the `context`.

        :param q: the search query
        """
        raise NotImplementedError()

    def extract_context(self, text, length=240):
        """Extract the context for the search query from the document's
        full `text`.

        :param text: the full text of the document to create the context for
        :param length: the length of the context snippet to return.
        """
        res = self.context_re.search(text)
        if res is None:
            return ''
        context_start = max(res.start() - int(length / 2), 0)
        context_end = context_start + length
        context = ''.join([context_start > 0 and '...' or '',
                           text[context_start:context_end],
                           context_end < len(text) and '...' or ''])

        try:
            return text_type(context, errors='ignore')
        except TypeError:
            return context

    def context_for_searchtool(self):
        """Required by the HTML builder."""
        return {}

    def get_js_stemmer_rawcode(self):
        """Required by the HTML builder."""
        return None


# The built-in search adapters.
SEARCH_ADAPTERS = {
    'xapian': ('xapiansearch', 'XapianSearch'),
    'whoosh': ('whooshsearch', 'WhooshSearch'),
    'null':   ('nullsearch', 'NullSearch'),
}
