"""Provides the ``ifconfig`` directive.

The ``ifconfig`` directive enables writing documentation
that is included depending on configuration variables.

Usage::

    .. ifconfig:: releaselevel in ('alpha', 'beta', 'rc')

       This stuff is only included in the built docs for unstable versions.

The argument for ``ifconfig`` is a plain Python expression, evaluated in the
namespace of the project configuration (that is, all variables from
``conf.py`` are available.)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from docutils import nodes

import sphinx
from sphinx.util.docutils import SphinxDirective
from sphinx.util.nodes import nested_parse_with_titles

if TYPE_CHECKING:
    from docutils.nodes import Node

    from sphinx.application import Sphinx
    from sphinx.util.typing import OptionSpec


class ifconfig(nodes.Element):
    pass


class IfConfig(SphinxDirective):

    has_content = True
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = True
    option_spec: OptionSpec = {}

    def run(self) -> list[Node]:
        node = ifconfig()
        node.document = self.state.document
        self.set_source_info(node)
        node['expr'] = self.arguments[0]
        nested_parse_with_titles(self.state, self.content, node, self.content_offset)
        return [node]


def process_ifconfig_nodes(app: Sphinx, doctree: nodes.document, docname: str) -> None:
    ns = {confval.name: confval.value for confval in app.config}
    ns.update(app.config.__dict__.copy())
    ns['builder'] = app.builder.name
    for node in list(doctree.findall(ifconfig)):
        try:
            res = eval(node['expr'], ns)  # NoQA: PGH001
        except Exception as err:
            # handle exceptions in a clean fashion
            from traceback import format_exception_only
            msg = ''.join(format_exception_only(err.__class__, err))
            newnode = doctree.reporter.error('Exception occurred in '
                                             'ifconfig expression: \n%s' %
                                             msg, base_node=node)
            node.replace_self(newnode)
        else:
            if not res:
                node.replace_self([])
            else:
                node.replace_self(node.children)


def setup(app: Sphinx) -> dict[str, Any]:
    app.add_node(ifconfig)
    app.add_directive('ifconfig', IfConfig)
    app.connect('doctree-resolved', process_ifconfig_nodes)
    return {'version': sphinx.__display_version__, 'parallel_read_safe': True}
