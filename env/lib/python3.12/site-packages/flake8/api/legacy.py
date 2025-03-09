"""Module containing shims around Flake8 2.x behaviour.

Previously, users would import :func:`get_style_guide` from ``flake8.engine``.
In 3.0 we no longer have an "engine" module but we maintain the API from it.
"""

from __future__ import annotations

import argparse
import logging
import os.path
from typing import Any

from flake8.discover_files import expand_paths
from flake8.formatting import base as formatter
from flake8.main import application as app
from flake8.options.parse_args import parse_args

LOG = logging.getLogger(__name__)


__all__ = ("get_style_guide",)


class Report:
    """Public facing object that mimic's Flake8 2.0's API.

    .. note::

        There are important changes in how this object behaves compared to
        the object provided in Flake8 2.x.

    .. warning::

        This should not be instantiated by users.

    .. versionchanged:: 3.0.0
    """

    def __init__(self, application: app.Application) -> None:
        """Initialize the Report for the user.

        .. warning:: This should not be instantiated by users.
        """
        assert application.guide is not None
        self._application = application
        self._style_guide = application.guide
        self._stats = self._style_guide.stats

    @property
    def total_errors(self) -> int:
        """Return the total number of errors."""
        return self._application.result_count

    def get_statistics(self, violation: str) -> list[str]:
        """Get the list of occurrences of a violation.

        :returns:
            List of occurrences of a violation formatted as:
            {Count} {Error Code} {Message}, e.g.,
            ``8 E531 Some error message about the error``
        """
        return [
            f"{s.count} {s.error_code} {s.message}"
            for s in self._stats.statistics_for(violation)
        ]


class StyleGuide:
    """Public facing object that mimic's Flake8 2.0's StyleGuide.

    .. note::

        There are important changes in how this object behaves compared to
        the StyleGuide object provided in Flake8 2.x.

    .. warning::

        This object should not be instantiated directly by users.

    .. versionchanged:: 3.0.0
    """

    def __init__(self, application: app.Application) -> None:
        """Initialize our StyleGuide."""
        self._application = application
        self._file_checker_manager = application.file_checker_manager

    @property
    def options(self) -> argparse.Namespace:
        """Return application's options.

        An instance of :class:`argparse.Namespace` containing parsed options.
        """
        assert self._application.options is not None
        return self._application.options

    @property
    def paths(self) -> list[str]:
        """Return the extra arguments passed as paths."""
        assert self._application.options is not None
        return self._application.options.filenames

    def check_files(self, paths: list[str] | None = None) -> Report:
        """Run collected checks on the files provided.

        This will check the files passed in and return a :class:`Report`
        instance.

        :param paths:
            List of filenames (or paths) to check.
        :returns:
            Object that mimic's Flake8 2.0's Reporter class.
        """
        assert self._application.options is not None
        self._application.options.filenames = paths
        self._application.run_checks()
        self._application.report_errors()
        return Report(self._application)

    def excluded(self, filename: str, parent: str | None = None) -> bool:
        """Determine if a file is excluded.

        :param filename:
            Path to the file to check if it is excluded.
        :param parent:
            Name of the parent directory containing the file.
        :returns:
            True if the filename is excluded, False otherwise.
        """

        def excluded(path: str) -> bool:
            paths = tuple(
                expand_paths(
                    paths=[path],
                    stdin_display_name=self.options.stdin_display_name,
                    filename_patterns=self.options.filename,
                    exclude=self.options.exclude,
                )
            )
            return not paths

        return excluded(filename) or (
            parent is not None and excluded(os.path.join(parent, filename))
        )

    def init_report(
        self,
        reporter: type[formatter.BaseFormatter] | None = None,
    ) -> None:
        """Set up a formatter for this run of Flake8."""
        if reporter is None:
            return
        if not issubclass(reporter, formatter.BaseFormatter):
            raise ValueError(
                "Report should be subclass of " "flake8.formatter.BaseFormatter."
            )
        self._application.formatter = reporter(self.options)
        self._application.guide = None
        # NOTE(sigmavirus24): This isn't the intended use of
        # Application#make_guide but it works pretty well.
        # Stop cringing... I know it's gross.
        self._application.make_guide()
        self._application.file_checker_manager = None
        self._application.make_file_checker_manager([])

    def input_file(
        self,
        filename: str,
        lines: Any | None = None,
        expected: Any | None = None,
        line_offset: Any | None = 0,
    ) -> Report:
        """Run collected checks on a single file.

        This will check the file passed in and return a :class:`Report`
        instance.

        :param filename:
            The path to the file to check.
        :param lines:
            Ignored since Flake8 3.0.
        :param expected:
            Ignored since Flake8 3.0.
        :param line_offset:
            Ignored since Flake8 3.0.
        :returns:
            Object that mimic's Flake8 2.0's Reporter class.
        """
        return self.check_files([filename])


def get_style_guide(**kwargs: Any) -> StyleGuide:
    r"""Provision a StyleGuide for use.

    :param \*\*kwargs:
        Keyword arguments that provide some options for the StyleGuide.
    :returns:
        An initialized StyleGuide
    """
    application = app.Application()
    application.plugins, application.options = parse_args([])
    # We basically want application.initialize to be called but with these
    # options set instead before we make our formatter, notifier, internal
    # style guide and file checker manager.
    options = application.options
    for key, value in kwargs.items():
        try:
            getattr(options, key)
            setattr(options, key, value)
        except AttributeError:
            LOG.error('Could not update option "%s"', key)
    application.make_formatter()
    application.make_guide()
    application.make_file_checker_manager([])
    return StyleGuide(application)
