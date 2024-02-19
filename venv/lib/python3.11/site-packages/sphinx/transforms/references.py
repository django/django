"""Docutils transforms used by Sphinx."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from docutils.transforms.references import DanglingReferences

from sphinx.transforms import SphinxTransform

if TYPE_CHECKING:
    from sphinx.application import Sphinx


class SphinxDanglingReferences(DanglingReferences):
    """DanglingReferences transform which does not output info messages."""

    def apply(self, **kwargs: Any) -> None:
        try:
            reporter = self.document.reporter
            report_level = reporter.report_level

            # suppress INFO level messages for a while
            reporter.report_level = max(reporter.WARNING_LEVEL, reporter.report_level)
            super().apply()
        finally:
            reporter.report_level = report_level


class SphinxDomains(SphinxTransform):
    """Collect objects to Sphinx domains for cross references."""
    default_priority = 850

    def apply(self, **kwargs: Any) -> None:
        for domain in self.env.domains.values():
            domain.process_doc(self.env, self.env.docname, self.document)


def setup(app: Sphinx) -> dict[str, Any]:
    app.add_transform(SphinxDanglingReferences)
    app.add_transform(SphinxDomains)

    return {
        'version': 'builtin',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
