# -*- coding: utf-8 -*-
"""
    sphinx.transforms.post_transforms.code
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    transforms for code-blocks.

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import sys
from typing import NamedTuple

from docutils import nodes
from pygments.lexers import PythonConsoleLexer, guess_lexer
from six import text_type

from sphinx import addnodes
from sphinx.ext import doctest
from sphinx.transforms import SphinxTransform

if False:
    # For type annotation
    from typing import Any, Dict, List  # NOQA
    from sphinx.application import Sphinx  # NOQA


HighlightSetting = NamedTuple('HighlightSetting', [('language', text_type),
                                                   ('lineno_threshold', int)])


class HighlightLanguageTransform(SphinxTransform):
    """
    Apply highlight_language to all literal_block nodes.

    This refers both :confval:`highlight_language` setting and
    :rst:dir:`highlightlang` directive.  After processing, this transform
    removes ``highlightlang`` node from doctree.
    """
    default_priority = 400

    def apply(self):
        visitor = HighlightLanguageVisitor(self.document,
                                           self.config.highlight_language)
        self.document.walkabout(visitor)

        for node in self.document.traverse(addnodes.highlightlang):
            node.parent.remove(node)


class HighlightLanguageVisitor(nodes.NodeVisitor):
    def __init__(self, document, default_language):
        # type: (nodes.document, unicode) -> None
        self.default_setting = HighlightSetting(default_language, sys.maxsize)
        self.settings = []  # type: List[HighlightSetting]
        nodes.NodeVisitor.__init__(self, document)

    def unknown_visit(self, node):
        # type: (nodes.Node) -> None
        pass

    def unknown_departure(self, node):
        # type: (nodes.Node) -> None
        pass

    def visit_document(self, node):
        # type: (nodes.Node) -> None
        self.settings.append(self.default_setting)

    def depart_document(self, node):
        # type: (nodes.Node) -> None
        self.settings.pop()

    def visit_start_of_file(self, node):
        # type: (nodes.Node) -> None
        self.settings.append(self.default_setting)

    def depart_start_of_file(self, node):
        # type: (nodes.Node) -> None
        self.settings.pop()

    def visit_highlightlang(self, node):
        # type: (addnodes.highlightlang) -> None
        self.settings[-1] = HighlightSetting(node['lang'], node['linenothreshold'])

    def visit_literal_block(self, node):
        # type: (nodes.literal_block) -> None
        setting = self.settings[-1]
        if 'language' not in node:
            node['language'] = setting.language
            node['force_highlighting'] = False
        else:
            node['force_highlighting'] = True
        if 'linenos' not in node:
            lines = node.astext().count('\n')
            node['linenos'] = (lines >= setting.lineno_threshold - 1)


class TrimDoctestFlagsTransform(SphinxTransform):
    """
    Trim doctest flags like ``# doctest: +FLAG`` from python code-blocks.

    see :confval:`trim_doctest_flags` for more information.
    """
    default_priority = HighlightLanguageTransform.default_priority + 1

    def apply(self):
        if not self.config.trim_doctest_flags:
            return

        for node in self.document.traverse(nodes.literal_block):
            if self.is_pyconsole(node):
                source = node.rawsource
                source = doctest.blankline_re.sub('', source)
                source = doctest.doctestopt_re.sub('', source)
                node.rawsource = source
                node[:] = [nodes.Text(source)]

    @staticmethod
    def is_pyconsole(node):
        # type: (nodes.literal_block) -> bool
        if node.rawsource != node.astext():
            return False  # skip parsed-literal node

        language = node.get('language')
        if language in ('pycon', 'pycon3'):
            return True
        elif language in ('py', 'py3', 'python', 'python3', 'default'):
            return node.rawsource.startswith('>>>')
        elif language == 'guess':
            try:
                lexer = guess_lexer(node.rawsource)
                return isinstance(lexer, PythonConsoleLexer)
            except Exception:
                pass

        return False


def setup(app):
    # type: (Sphinx) -> Dict[unicode, Any]
    app.add_post_transform(HighlightLanguageTransform)
    app.add_post_transform(TrimDoctestFlagsTransform)

    return {
        'version': 'builtin',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
