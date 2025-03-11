"""
runtest: Numerically tolerant end-to-end test library for research software.
"""

from .filter_constructor import get_filter
from .run import run
from .version import version_info, __version__
from .cli import cli

__author__ = "Radovan Bast <radovan.bast@uit.no>"

__all__ = [
    "get_filter",
    "version_info",
    "run",
    "cli",
]
