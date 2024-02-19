"""transforms for code-blocks."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Any, NamedTuple

from docutils import nodes
from pygments.lexers import PythonConsoleLexer, guess_lexer

from sphinx import addnodes
from sphinx.ext import doctest
from sphinx.transforms import SphinxTransform

if TYPE_CHECKING:
    from docutils.nodes import Node, TextElement

    from sphinx.application import Sphinx


class HighlightSetting(NamedTuple):
    language: str
    force: bool
    lineno_threshold: int


class HighlightLanguageTransform(SphinxTransform):
    """
    Apply highlight_language to all literal_block nodes.

    This refers both :confval:`highlight_language` setting and
    :rst:dir:`highlight` directive.  After processing, this transform
    removes ``highlightlang`` node from doctree.
    """
    default_priority = 400

    def apply(self, **kwargs: Any) -> None:
        visitor = HighlightLanguageVisitor(self.document,
                                           self.config.highlight_language)
        self.document.walkabout(visitor)

        for node in list(self.document.findall(addnodes.highlightlang)):
            node.parent.remove(node)


class HighlightLanguageVisitor(nodes.NodeVisitor):
    def __init__(self, document: nodes.document, default_language: str) -> None:
        self.default_setting = HighlightSetting(default_language, False, sys.maxsize)
        self.settings: list[HighlightSetting] = []
        super().__init__(document)

    def unknown_visit(self, node: Node) -> None:
        pass

    def unknown_departure(self, node: Node) -> None:
        pass

    def visit_document(self, node: Node) -> None:
        self.settings.append(self.default_setting)

    def depart_document(self, node: Node) -> None:
        self.settings.pop()

    def visit_start_of_file(self, node: Node) -> None:
        self.settings.append(self.default_setting)

    def depart_start_of_file(self, node: Node) -> None:
        self.settings.pop()

    def visit_highlightlang(self, node: addnodes.highlightlang) -> None:
        self.settings[-1] = HighlightSetting(node['lang'],
                                             node['force'],
                                             node['linenothreshold'])

    def visit_literal_block(self, node: nodes.literal_block) -> None:
        setting = self.settings[-1]
        if 'language' not in node:
            node['language'] = setting.language
            node['force'] = setting.force
        if 'linenos' not in node:
            lines = node.astext().count('\n')
            node['linenos'] = (lines >= setting.lineno_threshold - 1)


class TrimDoctestFlagsTransform(SphinxTransform):
    """
    Trim doctest flags like ``# doctest: +FLAG`` from python code-blocks.

    see :confval:`trim_doctest_flags` for more information.
    """
    default_priority = HighlightLanguageTransform.default_priority + 1

    def apply(self, **kwargs: Any) -> None:
        for lbnode in self.document.findall(nodes.literal_block):
            if self.is_pyconsole(lbnode):
                self.strip_doctest_flags(lbnode)

        for dbnode in self.document.findall(nodes.doctest_block):
            self.strip_doctest_flags(dbnode)

    def strip_doctest_flags(self, node: TextElement) -> None:
        if not node.get('trim_flags', self.config.trim_doctest_flags):
            return

        source = node.rawsource
        source = doctest.blankline_re.sub('', source)
        source = doctest.doctestopt_re.sub('', source)
        node.rawsource = source
        node[:] = [nodes.Text(source)]

    @staticmethod
    def is_pyconsole(node: nodes.literal_block) -> bool:
        if node.rawsource != node.astext():
            return False  # skip parsed-literal node

        language = node.get('language')
        if language in {'pycon', 'pycon3'}:
            return True
        elif language in {'py', 'python', 'py3', 'python3', 'default'}:
            return node.rawsource.startswith('>>>')
        elif language == 'guess':
            try:
                lexer = guess_lexer(node.rawsource)
                return isinstance(lexer, PythonConsoleLexer)
            except Exception:
                pass

        return False


def setup(app: Sphinx) -> dict[str, Any]:
    app.add_post_transform(HighlightLanguageTransform)
    app.add_post_transform(TrimDoctestFlagsTransform)

    return {
        'version': 'builtin',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
