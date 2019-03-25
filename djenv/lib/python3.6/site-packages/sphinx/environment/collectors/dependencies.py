# -*- coding: utf-8 -*-
"""
    sphinx.environment.collectors.dependencies
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    The dependencies collector components for sphinx.environment.

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from os import path

from docutils.utils import relative_path

from sphinx.environment.collectors import EnvironmentCollector
from sphinx.util.osutil import getcwd, fs_encoding

if False:
    # For type annotation
    from typing import Dict, Set  # NOQA
    from docutils import nodes  # NOQA
    from sphinx.sphinx import Sphinx  # NOQA
    from sphinx.environment import BuildEnvironment  # NOQA


class DependenciesCollector(EnvironmentCollector):
    """dependencies collector for sphinx.environment."""

    def clear_doc(self, app, env, docname):
        # type: (Sphinx, BuildEnvironment, unicode) -> None
        env.dependencies.pop(docname, None)

    def merge_other(self, app, env, docnames, other):
        # type: (Sphinx, BuildEnvironment, Set[unicode], BuildEnvironment) -> None
        for docname in docnames:
            if docname in other.dependencies:
                env.dependencies[docname] = other.dependencies[docname]

    def process_doc(self, app, doctree):
        # type: (Sphinx, nodes.Node) -> None
        """Process docutils-generated dependency info."""
        cwd = getcwd()
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


def setup(app):
    # type: (Sphinx) -> Dict
    app.add_env_collector(DependenciesCollector)

    return {
        'version': 'builtin',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
