# -*- coding: utf-8 -*-
"""
    sphinx.util.websupport
    ~~~~~~~~~~~~~~~~~~~~~~

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

try:
    from sphinxcontrib.websupport.utils import is_commentable  # NOQA
except ImportError:
    from docutils import nodes  # NOQA

    def is_commentable(node):
        # type: (nodes.Node) -> bool
        raise RuntimeError
