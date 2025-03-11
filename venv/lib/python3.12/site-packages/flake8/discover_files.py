"""Functions related to discovering paths."""
from __future__ import annotations

import logging
import os.path
from typing import Callable
from typing import Generator
from typing import Sequence

from flake8 import utils

LOG = logging.getLogger(__name__)


def _filenames_from(
    arg: str,
    *,
    predicate: Callable[[str], bool],
) -> Generator[str, None, None]:
    """Generate filenames from an argument.

    :param arg:
        Parameter from the command-line.
    :param predicate:
        Predicate to use to filter out filenames. If the predicate
        returns ``True`` we will exclude the filename, otherwise we
        will yield it. By default, we include every filename
        generated.
    :returns:
        Generator of paths
    """
    if predicate(arg):
        return

    if os.path.isdir(arg):
        for root, sub_directories, files in os.walk(arg):
            # NOTE(sigmavirus24): os.walk() will skip a directory if you
            # remove it from the list of sub-directories.
            for directory in tuple(sub_directories):
                joined = os.path.join(root, directory)
                if predicate(joined):
                    sub_directories.remove(directory)

            for filename in files:
                joined = os.path.join(root, filename)
                if not predicate(joined):
                    yield joined
    else:
        yield arg


def expand_paths(
    *,
    paths: Sequence[str],
    stdin_display_name: str,
    filename_patterns: Sequence[str],
    exclude: Sequence[str],
) -> Generator[str, None, None]:
    """Expand out ``paths`` from commandline to the lintable files."""
    if not paths:
        paths = ["."]

    def is_excluded(arg: str) -> bool:
        if arg == "-":
            # if the stdin_display_name is the default, always include it
            if stdin_display_name == "stdin":
                return False
            arg = stdin_display_name

        return utils.matches_filename(
            arg,
            patterns=exclude,
            log_message='"%(path)s" has %(whether)sbeen excluded',
            logger=LOG,
        )

    return (
        filename
        for path in paths
        for filename in _filenames_from(path, predicate=is_excluded)
        if (
            # always lint `-`
            filename == "-"
            # always lint explicitly passed (even if not matching filter)
            or path == filename
            # otherwise, check the file against filtered patterns
            or utils.fnmatch(filename, filename_patterns)
        )
    )
