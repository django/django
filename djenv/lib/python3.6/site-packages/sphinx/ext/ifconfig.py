# -*- coding: utf-8 -*-
"""
    sphinx.ext.ifconfig
    ~~~~~~~~~~~~~~~~~~~

    Provides the ``ifconfig`` directive that allows to write documentation
    that is included depending on configuration variables.

    Usage::

        .. ifconfig:: releaselevel in ('alpha', 'beta', 'rc')

           This stuff is only included in the built docs for unstable versions.

    The argument for ``ifconfig`` is a plain Python expression, evaluated in the
    namespace of the project configuration (that is, all variables from
    ``conf.py`` are available.)

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from docutils import nodes

import sphinx
from sphinx.util.docutils import SphinxDirective
from sphinx.util.nodes import set_source_info

if False:
    # For type annotation
    from typing import Any, Dict, List  # NOQA
    from sphinx.application import Sphinx  # NOQA


class ifconfig(nodes.Element):
    pass


class IfConfig(SphinxDirective):

    has_content = True
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = True
    option_spec = {}  # type: Dict

    def run(self):
        # type: () -> List[nodes.Node]
        node = ifconfig()
        node.document = self.state.document
        set_source_info(self, node)
        node['expr'] = self.arguments[0]
        self.state.nested_parse(self.content, self.content_offset,
                                node, match_titles=1)
        return [node]


def process_ifconfig_nodes(app, doctree, docname):
    # type: (Sphinx, nodes.Node, unicode) -> None
    ns = dict((confval.name, confval.value) for confval in app.config)
    ns.update(app.config.__dict__.copy())
    ns['builder'] = app.builder.name
    for node in doctree.traverse(ifconfig):
        try:
            res = eval(node['expr'], ns)
        except Exception as err:
            # handle exceptions in a clean fashion
            from traceback import format_exception_only
            msg = ''.join(format_exception_only(err.__class__, err))
            newnode = doctree.reporter.error('Exception occured in '
                                             'ifconfig expression: \n%s' %
                                             msg, base_node=node)
            node.replace_self(newnode)
        else:
            if not res:
                node.replace_self([])
            else:
                node.replace_self(node.children)


def setup(app):
    # type: (Sphinx) -> Dict[unicode, Any]
    app.add_node(ifconfig)
    app.add_directive('ifconfig', IfConfig)
    app.connect('doctree-resolved', process_ifconfig_nodes)
    return {'version': sphinx.__display_version__, 'parallel_read_safe': True}
