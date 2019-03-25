# -*- coding: utf-8 -*-
"""
    sphinxcontrib.websupport.search.nullsearch
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    The default search adapter, does nothing.

    :copyright: Copyright 2007-2016 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from sphinxcontrib.websupport.search import BaseSearch
from sphinxcontrib.websupport.errors import NullSearchException


class NullSearch(BaseSearch):
    """A search adapter that does nothing. Used when no search adapter
    is specified.
    """
    def feed(self, pagename, filename, title, doctree):
        pass

    def query(self, q):
        raise NullSearchException('No search adapter specified.')
