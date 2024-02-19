"""The title collector components for sphinx.environment."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from docutils import nodes

from sphinx.environment.collectors import EnvironmentCollector
from sphinx.transforms import SphinxContentsFilter

if TYPE_CHECKING:
    from sphinx.application import Sphinx
    from sphinx.environment import BuildEnvironment


class TitleCollector(EnvironmentCollector):
    """title collector for sphinx.environment."""

    def clear_doc(self, app: Sphinx, env: BuildEnvironment, docname: str) -> None:
        env.titles.pop(docname, None)
        env.longtitles.pop(docname, None)

    def merge_other(self, app: Sphinx, env: BuildEnvironment,
                    docnames: set[str], other: BuildEnvironment) -> None:
        for docname in docnames:
            env.titles[docname] = other.titles[docname]
            env.longtitles[docname] = other.longtitles[docname]

    def process_doc(self, app: Sphinx, doctree: nodes.document) -> None:
        """Add a title node to the document (just copy the first section title),
        and store that title in the environment.
        """
        titlenode = nodes.title()
        longtitlenode = titlenode
        # explicit title set with title directive; use this only for
        # the <title> tag in HTML output
        if 'title' in doctree:
            longtitlenode = nodes.title()
            longtitlenode += nodes.Text(doctree['title'])
        # look for first section title and use that as the title
        for node in doctree.findall(nodes.section):
            visitor = SphinxContentsFilter(doctree)
            node[0].walkabout(visitor)
            titlenode += visitor.get_entry_text()
            break
        else:
            # document has no title
            titlenode += nodes.Text(doctree.get('title', '<no title>'))
        app.env.titles[app.env.docname] = titlenode
        app.env.longtitles[app.env.docname] = longtitlenode


def setup(app: Sphinx) -> dict[str, Any]:
    app.add_env_collector(TitleCollector)

    return {
        'version': 'builtin',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
