"""Functions for constructing the requested report plugin."""

from __future__ import annotations

import argparse
import logging

from flake8.formatting.base import BaseFormatter
from flake8.plugins.finder import LoadedPlugin

LOG = logging.getLogger(__name__)


def make(
    reporters: dict[str, LoadedPlugin],
    options: argparse.Namespace,
) -> BaseFormatter:
    """Make the formatter from the requested user options.

    - if :option:`flake8 --quiet` is specified, return the ``quiet-filename``
      formatter.
    - if :option:`flake8 --quiet` is specified at least twice, return the
      ``quiet-nothing`` formatter.
    - otherwise attempt to return the formatter by name.
    - failing that, assume it is a format string and return the ``default``
      formatter.
    """
    format_name = options.format
    if options.quiet == 1:
        format_name = "quiet-filename"
    elif options.quiet >= 2:
        format_name = "quiet-nothing"

    try:
        format_plugin = reporters[format_name]
    except KeyError:
        LOG.warning(
            "%r is an unknown formatter.  Falling back to default.",
            format_name,
        )
        format_plugin = reporters["default"]

    return format_plugin.obj(options)
