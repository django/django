# -*- coding: utf-8 -*-
"""
    sphinx.environment.collectors.indexentries
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Index entries collector for sphinx.environment.

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from six import text_type

from sphinx import addnodes
from sphinx.environment.collectors import EnvironmentCollector
from sphinx.util import split_index_msg, logging

if False:
    # For type annotation
    from typing import Dict, Set  # NOQA
    from docutils import nodes  # NOQA
    from sphinx.applicatin import Sphinx  # NOQA
    from sphinx.environment import BuildEnvironment  # NOQA

logger = logging.getLogger(__name__)


class IndexEntriesCollector(EnvironmentCollector):
    name = 'indices'

    def clear_doc(self, app, env, docname):
        # type: (Sphinx, BuildEnvironment, unicode) -> None
        env.indexentries.pop(docname, None)

    def merge_other(self, app, env, docnames, other):
        # type: (Sphinx, BuildEnvironment, Set[unicode], BuildEnvironment) -> None
        for docname in docnames:
            env.indexentries[docname] = other.indexentries[docname]

    def process_doc(self, app, doctree):
        # type: (Sphinx, nodes.Node) -> None
        docname = app.env.docname
        entries = app.env.indexentries[docname] = []
        for node in doctree.traverse(addnodes.index):
            try:
                for entry in node['entries']:
                    split_index_msg(entry[0], entry[1])
            except ValueError as exc:
                logger.warning(text_type(exc), location=node)
                node.parent.remove(node)
            else:
                for entry in node['entries']:
                    if len(entry) == 5:
                        # Since 1.4: new index structure including index_key (5th column)
                        entries.append(entry)
                    else:
                        entries.append(entry + (None,))


def setup(app):
    # type: (Sphinx) -> Dict
    app.add_env_collector(IndexEntriesCollector)

    return {
        'version': 'builtin',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
