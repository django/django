"""Top-level module for Flake8.

This module

- initializes logging for the command-line tool
- tracks the version of the package
- provides a way to configure logging for the command-line tool

.. autofunction:: flake8.configure_logging

"""
from __future__ import annotations

import logging
import sys

LOG = logging.getLogger(__name__)
LOG.addHandler(logging.NullHandler())

__version__ = "7.3.0"
__version_info__ = tuple(int(i) for i in __version__.split(".") if i.isdigit())

_VERBOSITY_TO_LOG_LEVEL = {
    # output more than warnings but not debugging info
    1: logging.INFO,  # INFO is a numerical level of 20
    # output debugging information
    2: logging.DEBUG,  # DEBUG is a numerical level of 10
}

LOG_FORMAT = (
    "%(name)-25s %(processName)-11s %(relativeCreated)6d "
    "%(levelname)-8s %(message)s"
)


def configure_logging(
    verbosity: int,
    filename: str | None = None,
    logformat: str = LOG_FORMAT,
) -> None:
    """Configure logging for flake8.

    :param verbosity:
        How verbose to be in logging information.
    :param filename:
        Name of the file to append log information to.
        If ``None`` this will log to ``sys.stderr``.
        If the name is "stdout" or "stderr" this will log to the appropriate
        stream.
    """
    if verbosity <= 0:
        return

    verbosity = min(verbosity, max(_VERBOSITY_TO_LOG_LEVEL))
    log_level = _VERBOSITY_TO_LOG_LEVEL[verbosity]

    if not filename or filename in ("stderr", "stdout"):
        fileobj = getattr(sys, filename or "stderr")
        handler_cls: type[logging.Handler] = logging.StreamHandler
    else:
        fileobj = filename
        handler_cls = logging.FileHandler

    handler = handler_cls(fileobj)
    handler.setFormatter(logging.Formatter(logformat))
    LOG.addHandler(handler)
    LOG.setLevel(log_level)
    LOG.debug(
        "Added a %s logging handler to logger root at %s", filename, __name__
    )
