"""The dependencies collector components for sphinx.environment."""

from __future__ import annotations

import os
from os import path
from typing import TYPE_CHECKING, Any

from docutils.utils import relative_path

from sphinx.environment.collectors import EnvironmentCollector
from sphinx.util.osutil import fs_encoding

if TYPE_CHECKING:
    from docutils import nodes

    from sphinx.application import Sphinx
    from sphinx.environment import BuildEnvironment


class DependenciesCollector(EnvironmentCollector):
    """dependencies collector for sphinx.environment."""

    def clear_doc(self, app: Sphinx, env: BuildEnvironment, docname: str) -> None:
        env.dependencies.pop(docname, None)

    def merge_other(self, app: Sphinx, env: BuildEnvironment,
                    docnames: set[str], other: BuildEnvironment) -> None:
        for docname in docnames:
            if docname in other.dependencies:
                env.dependencies[docname] = other.dependencies[docname]

    def process_doc(self, app: Sphinx, doctree: nodes.document) -> None:
        """Process docutils-generated dependency info."""
        cwd = os.getcwd()
        frompath = path.join(path.normpath(app.srcdir), 'dummy')
        deps = doctree.settings.record_dependencies
        if not deps:
            return
        for dep in deps.list:
            # the dependency path is relative to the working dir, so get
            # one relative to the srcdir
            if isinstance(dep, bytes):
                dep = dep.decode(fs_encoding)
            relpath = relative_path(frompath,
                                    path.normpath(path.join(cwd, dep)))
            app.env.dependencies[app.env.docname].add(relpath)


def setup(app: Sphinx) -> dict[str, Any]:
    app.add_env_collector(DependenciesCollector)

    return {
        'version': 'builtin',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
