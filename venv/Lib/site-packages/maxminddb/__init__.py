"""Module for reading MaxMind DB files."""

from __future__ import annotations

from importlib.metadata import version
from typing import IO, TYPE_CHECKING, AnyStr, cast

from .const import (
    MODE_AUTO,
    MODE_FD,
    MODE_FILE,
    MODE_MEMORY,
    MODE_MMAP,
    MODE_MMAP_EXT,
)
from .decoder import InvalidDatabaseError
from .reader import Reader

if TYPE_CHECKING:
    import os

try:
    from . import extension as _extension
except ImportError:
    _extension = None  # type: ignore[assignment]


__all__ = [
    "MODE_AUTO",
    "MODE_FD",
    "MODE_FILE",
    "MODE_MEMORY",
    "MODE_MMAP",
    "MODE_MMAP_EXT",
    "InvalidDatabaseError",
    "Reader",
    "open_database",
]


def open_database(
    database: AnyStr | int | os.PathLike | IO,
    mode: int = MODE_AUTO,
) -> Reader:
    """Open a MaxMind DB database.

    Arguments:
        database: A path to a valid MaxMind DB file such as a GeoIP2 database
                  file, or a file descriptor in the case of MODE_FD.
        mode: mode to open the database with. Valid mode are:
              * MODE_MMAP_EXT - use the C extension with memory map.
              * MODE_MMAP - read from memory map. Pure Python.
              * MODE_FILE - read database as standard file. Pure Python.
              * MODE_MEMORY - load database into memory. Pure Python.
              * MODE_FD - the param passed via database is a file descriptor, not
                          a path. This mode implies MODE_MEMORY.
              * MODE_AUTO - tries MODE_MMAP_EXT, MODE_MMAP, MODE_FILE in that
                          order. Default mode.

    """
    if mode not in (
        MODE_AUTO,
        MODE_FD,
        MODE_FILE,
        MODE_MEMORY,
        MODE_MMAP,
        MODE_MMAP_EXT,
    ):
        msg = f"Unsupported open mode: {mode}"
        raise ValueError(msg)

    has_extension = _extension and hasattr(_extension, "Reader")
    use_extension = has_extension if mode == MODE_AUTO else mode == MODE_MMAP_EXT

    if not use_extension:
        return Reader(database, mode)

    if not has_extension:
        msg = "MODE_MMAP_EXT requires the maxminddb.extension module to be available"
        raise ValueError(
            msg,
        )

    # The C type exposes the same API as the Python Reader, so for type
    # checking purposes, pretend it is one. (Ideally this would be a subclass
    # of, or share a common parent class with, the Python Reader
    # implementation.)
    return cast("Reader", _extension.Reader(database, mode))


__version__ = version("maxminddb")
