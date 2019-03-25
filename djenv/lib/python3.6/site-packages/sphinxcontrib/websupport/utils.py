# -*- coding: utf-8 -*-
"""
    sphinxcontrib.websupport.utils
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    :copyright: Copyright 2007-2016 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

if False:
    # For type annotation
    from docutils import nodes  # NOQA


def is_commentable(node):
    # type: (nodes.Node) -> bool
    # return node.__class__.__name__ in ('paragraph', 'literal_block')
    return node.__class__.__name__ == 'paragraph'
