"""The data collector components for sphinx.environment."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from docutils import nodes

    from sphinx.application import Sphinx
    from sphinx.environment import BuildEnvironment


class EnvironmentCollector:
    """An EnvironmentCollector is a specific data collector from each document.

    It gathers data and stores :py:class:`BuildEnvironment
    <sphinx.environment.BuildEnvironment>` as a database.  Examples of specific
    data would be images, download files, section titles, metadatas, index
    entries and toctrees, etc.
    """

    listener_ids: dict[str, int] | None = None

    def enable(self, app: Sphinx) -> None:
        assert self.listener_ids is None
        self.listener_ids = {
            'doctree-read':     app.connect('doctree-read', self.process_doc),
            'env-merge-info':   app.connect('env-merge-info', self.merge_other),
            'env-purge-doc':    app.connect('env-purge-doc', self.clear_doc),
            'env-get-updated':  app.connect('env-get-updated', self.get_updated_docs),
            'env-get-outdated': app.connect('env-get-outdated', self.get_outdated_docs),
        }

    def disable(self, app: Sphinx) -> None:
        assert self.listener_ids is not None
        for listener_id in self.listener_ids.values():
            app.disconnect(listener_id)
        self.listener_ids = None

    def clear_doc(self, app: Sphinx, env: BuildEnvironment, docname: str) -> None:
        """Remove specified data of a document.

        This method is called on the removal of the document."""
        raise NotImplementedError

    def merge_other(self, app: Sphinx, env: BuildEnvironment,
                    docnames: set[str], other: BuildEnvironment) -> None:
        """Merge in specified data regarding docnames from a different `BuildEnvironment`
        object which coming from a subprocess in parallel builds."""
        raise NotImplementedError

    def process_doc(self, app: Sphinx, doctree: nodes.document) -> None:
        """Process a document and gather specific data from it.

        This method is called after the document is read."""
        raise NotImplementedError

    def get_updated_docs(self, app: Sphinx, env: BuildEnvironment) -> list[str]:
        """Return a list of docnames to re-read.

        This methods is called after reading the whole of documents (experimental).
        """
        return []

    def get_outdated_docs(self, app: Sphinx, env: BuildEnvironment,
                          added: set[str], changed: set[str], removed: set[str]) -> list[str]:
        """Return a list of docnames to re-read.

        This methods is called before reading the documents.
        """
        return []
