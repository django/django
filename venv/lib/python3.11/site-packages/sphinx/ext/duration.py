"""Measure document reading durations."""

from __future__ import annotations

import time
from itertools import islice
from operator import itemgetter
from typing import TYPE_CHECKING, cast

import sphinx
from sphinx.domains import Domain
from sphinx.locale import __
from sphinx.util import logging

if TYPE_CHECKING:
    from docutils import nodes

    from sphinx.application import Sphinx

logger = logging.getLogger(__name__)


class DurationDomain(Domain):
    """A domain for durations of Sphinx processing."""
    name = 'duration'

    @property
    def reading_durations(self) -> dict[str, float]:
        return self.data.setdefault('reading_durations', {})

    def note_reading_duration(self, duration: float) -> None:
        self.reading_durations[self.env.docname] = duration

    def clear(self) -> None:
        self.reading_durations.clear()

    def clear_doc(self, docname: str) -> None:
        self.reading_durations.pop(docname, None)

    def merge_domaindata(self, docnames: list[str], otherdata: dict[str, float]) -> None:
        for docname, duration in otherdata.items():
            if docname in docnames:
                self.reading_durations[docname] = duration


def on_builder_inited(app: Sphinx) -> None:
    """Initialize DurationDomain on bootstrap.

    This clears the results of the last build.
    """
    domain = cast(DurationDomain, app.env.get_domain('duration'))
    domain.clear()


def on_source_read(app: Sphinx, docname: str, content: list[str]) -> None:
    """Start to measure reading duration."""
    app.env.temp_data['started_at'] = time.monotonic()


def on_doctree_read(app: Sphinx, doctree: nodes.document) -> None:
    """Record a reading duration."""
    started_at = app.env.temp_data['started_at']
    duration = time.monotonic() - started_at
    domain = cast(DurationDomain, app.env.get_domain('duration'))
    domain.note_reading_duration(duration)


def on_build_finished(app: Sphinx, error: Exception) -> None:
    """Display duration ranking on the current build."""
    domain = cast(DurationDomain, app.env.get_domain('duration'))
    if not domain.reading_durations:
        return
    durations = sorted(domain.reading_durations.items(), key=itemgetter(1), reverse=True)

    logger.info('')
    logger.info(__('====================== slowest reading durations ======================='))
    for docname, d in islice(durations, 5):
        logger.info(f'{d:.3f} {docname}')  # NoQA: G004


def setup(app: Sphinx) -> dict[str, bool | str]:
    app.add_domain(DurationDomain)
    app.connect('builder-inited', on_builder_inited)
    app.connect('source-read', on_source_read)
    app.connect('doctree-read', on_doctree_read)
    app.connect('build-finished', on_build_finished)

    return {
        'version': sphinx.__display_version__,
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
