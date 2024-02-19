"""The metadata collector components for sphinx.environment."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from docutils import nodes

from sphinx.environment.collectors import EnvironmentCollector

if TYPE_CHECKING:
    from sphinx.application import Sphinx
    from sphinx.environment import BuildEnvironment


class MetadataCollector(EnvironmentCollector):
    """metadata collector for sphinx.environment."""

    def clear_doc(self, app: Sphinx, env: BuildEnvironment, docname: str) -> None:
        env.metadata.pop(docname, None)

    def merge_other(self, app: Sphinx, env: BuildEnvironment,
                    docnames: set[str], other: BuildEnvironment) -> None:
        for docname in docnames:
            env.metadata[docname] = other.metadata[docname]

    def process_doc(self, app: Sphinx, doctree: nodes.document) -> None:
        """Process the docinfo part of the doctree as metadata.

        Keep processing minimal -- just return what docutils says.
        """
        index = doctree.first_child_not_matching_class(nodes.PreBibliographic)
        if index is None:
            return
        elif isinstance(doctree[index], nodes.docinfo):
            md = app.env.metadata[app.env.docname]
            for node in doctree[index]:  # type: ignore[attr-defined]
                # nodes are multiply inherited...
                if isinstance(node, nodes.authors):
                    authors = cast(list[nodes.author], node)
                    md['authors'] = [author.astext() for author in authors]
                elif isinstance(node, nodes.field):
                    assert len(node) == 2
                    field_name = cast(nodes.field_name, node[0])
                    field_body = cast(nodes.field_body, node[1])
                    md[field_name.astext()] = field_body.astext()
                elif isinstance(node, nodes.TextElement):
                    # other children must be TextElement
                    # see: https://docutils.sourceforge.io/docs/ref/doctree.html#bibliographic-elements  # noqa: E501
                    md[node.__class__.__name__] = node.astext()

            for name, value in md.items():
                if name in ('tocdepth',):
                    try:
                        value = int(value)
                    except ValueError:
                        value = 0
                    md[name] = value

            doctree.pop(index)


def setup(app: Sphinx) -> dict[str, Any]:
    app.add_env_collector(MetadataCollector)

    return {
        'version': 'builtin',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
