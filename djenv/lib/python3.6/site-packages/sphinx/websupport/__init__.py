# -*- coding: utf-8 -*-
"""
    sphinx.websupport
    ~~~~~~~~~~~~~~~~~

    Base Module for web support functions.

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import warnings

from sphinx.deprecation import RemovedInSphinx20Warning

try:
    from sphinxcontrib.websupport import WebSupport  # NOQA
    from sphinxcontrib.websupport import errors  # NOQA
    from sphinxcontrib.websupport.search import BaseSearch, SEARCH_ADAPTERS  # NOQA
    from sphinxcontrib.websupport.storage import StorageBackend  # NOQA

    warnings.warn('sphinx.websupport module is now provided as sphinxcontrib-websupport. '
                  'sphinx.websupport will be removed at Sphinx-2.0. '
                  'Please use the package instead.',
                  RemovedInSphinx20Warning)
except ImportError:
    warnings.warn('Since Sphinx-1.6, sphinx.websupport module is now separated to '
                  'sphinxcontrib-websupport package. Please add it into your dependency list.')
