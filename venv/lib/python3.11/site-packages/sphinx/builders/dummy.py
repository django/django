"""Do syntax checks, but no writing."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sphinx.builders import Builder
from sphinx.locale import __

if TYPE_CHECKING:
    from docutils.nodes import Node

    from sphinx.application import Sphinx


class DummyBuilder(Builder):
    name = 'dummy'
    epilog = __('The dummy builder generates no files.')

    allow_parallel = True

    def init(self) -> None:
        pass

    def get_outdated_docs(self) -> set[str]:
        return self.env.found_docs

    def get_target_uri(self, docname: str, typ: str | None = None) -> str:
        return ''

    def prepare_writing(self, docnames: set[str]) -> None:
        pass

    def write_doc(self, docname: str, doctree: Node) -> None:
        pass

    def finish(self) -> None:
        pass


def setup(app: Sphinx) -> dict[str, Any]:
    app.add_builder(DummyBuilder)

    return {
        'version': 'builtin',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
