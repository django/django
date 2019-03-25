# -*- coding: utf-8 -*-
"""
    sphinx.environment.collectors
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    The data collector components for sphinx.environment.

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from six import itervalues

if False:
    # For type annotation
    from typing import Dict, List, Set  # NOQA
    from docutils import nodes  # NOQA
    from sphinx.sphinx import Sphinx  # NOQA
    from sphinx.environment import BuildEnvironment  # NOQA


class EnvironmentCollector(object):
    """An EnvironmentCollector is a specific data collector from each document.

    It gathers data and stores :py:class:`BuildEnvironment
    <sphinx.environment.BuildEnvironment>` as a database.  Examples of specific
    data would be images, download files, section titles, metadatas, index
    entries and toctrees, etc.
    """

    listener_ids = None  # type: Dict[unicode, int]

    def enable(self, app):
        # type: (Sphinx) -> None
        assert self.listener_ids is None
        self.listener_ids = {
            'doctree-read':     app.connect('doctree-read', self.process_doc),
            'env-merge-info':   app.connect('env-merge-info', self.merge_other),
            'env-purge-doc':    app.connect('env-purge-doc', self.clear_doc),
            'env-get-updated':  app.connect('env-get-updated', self.get_updated_docs),
            'env-get-outdated': app.connect('env-get-outdated', self.get_outdated_docs),
        }

    def disable(self, app):
        # type: (Sphinx) -> None
        assert self.listener_ids is not None
        for listener_id in itervalues(self.listener_ids):
            app.disconnect(listener_id)
        self.listener_ids = None

    def clear_doc(self, app, env, docname):
        # type: (Sphinx, BuildEnvironment, unicode) -> None
        """Remove specified data of a document.

        This method is called on the removal of the document."""
        raise NotImplementedError

    def merge_other(self, app, env, docnames, other):
        # type: (Sphinx, BuildEnvironment, Set[unicode], BuildEnvironment) -> None
        """Merge in specified data regarding docnames from a different `BuildEnvironment`
        object which coming from a subprocess in parallel builds."""
        raise NotImplementedError

    def process_doc(self, app, doctree):
        # type: (Sphinx, nodes.Node) -> None
        """Process a document and gather specific data from it.

        This method is called after the document is read."""
        raise NotImplementedError

    def get_updated_docs(self, app, env):
        # type: (Sphinx, BuildEnvironment) -> List[unicode]
        """Return a list of docnames to re-read.

        This methods is called after reading the whole of documents (experimental).
        """
        return []

    def get_outdated_docs(self, app, env, added, changed, removed):
        # type: (Sphinx, BuildEnvironment, unicode, Set[unicode], Set[unicode], Set[unicode]) -> List[unicode]  # NOQA
        """Return a list of docnames to re-read.

        This methods is called before reading the documents.
        """
        return []
