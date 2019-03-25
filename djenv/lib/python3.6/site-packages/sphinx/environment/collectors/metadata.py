# -*- coding: utf-8 -*-
"""
    sphinx.environment.collectors.metadata
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    The metadata collector components for sphinx.environment.

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from docutils import nodes

from sphinx.environment.collectors import EnvironmentCollector

if False:
    # For type annotation
    from typing import Dict, Set  # NOQA
    from docutils import nodes  # NOQA
    from sphinx.sphinx import Sphinx  # NOQA
    from sphinx.environment import BuildEnvironment  # NOQA


class MetadataCollector(EnvironmentCollector):
    """metadata collector for sphinx.environment."""

    def clear_doc(self, app, env, docname):
        # type: (Sphinx, BuildEnvironment, unicode) -> None
        env.metadata.pop(docname, None)

    def merge_other(self, app, env, docnames, other):
        # type: (Sphinx, BuildEnvironment, Set[unicode], BuildEnvironment) -> None
        for docname in docnames:
            env.metadata[docname] = other.metadata[docname]

    def process_doc(self, app, doctree):
        # type: (Sphinx, nodes.Node) -> None
        """Process the docinfo part of the doctree as metadata.

        Keep processing minimal -- just return what docutils says.
        """
        md = app.env.metadata[app.env.docname]
        try:
            docinfo = doctree[0]
        except IndexError:
            # probably an empty document
            return
        if docinfo.__class__ is not nodes.docinfo:
            # nothing to see here
            return
        for node in docinfo:
            # nodes are multiply inherited...
            if isinstance(node, nodes.authors):
                md['authors'] = [author.astext() for author in node]
            elif isinstance(node, nodes.TextElement):  # e.g. author
                md[node.__class__.__name__] = node.astext()
            else:
                name, body = node
                md[name.astext()] = body.astext()
        for name, value in md.items():
            if name in ('tocdepth',):
                try:
                    value = int(value)
                except ValueError:
                    value = 0
                md[name] = value

        del doctree[0]


def setup(app):
    # type: (Sphinx) -> Dict
    app.add_env_collector(MetadataCollector)

    return {
        'version': 'builtin',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
