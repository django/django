# pylint:disable=C0111
import os
from typing import IO, AnyStr, Union, cast

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

try:
    # pylint: disable=import-self
    from . import extension as _extension
except ImportError:
    _extension = None  # type: ignore[assignment]


__all__ = [
    "InvalidDatabaseError",
    "MODE_AUTO",
    "MODE_FD",
    "MODE_FILE",
    "MODE_MEMORY",
    "MODE_MMAP",
    "MODE_MMAP_EXT",
    "Reader",
    "open_database",
]


def open_database(
    database: Union[AnyStr, int, os.PathLike, IO],
    mode: int = MODE_AUTO,
) -> Reader:
    """Open a MaxMind DB database

    Arguments:
        database -- A path to a valid MaxMind DB file such as a GeoIP2 database
                    file, or a file descriptor in the case of MODE_FD.
        mode -- mode to open the database with. Valid mode are:
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
        raise ValueError(f"Unsupported open mode: {mode}")

    has_extension = _extension and hasattr(_extension, "Reader")
    use_extension = has_extension if mode == MODE_AUTO else mode == MODE_MMAP_EXT

    if not use_extension:
        return Reader(database, mode)

    if not has_extension:
        raise ValueError(
            "MODE_MMAP_EXT requires the maxminddb.extension module to be available"
        )

    # The C type exposes the same API as the Python Reader, so for type
    # checking purposes, pretend it is one. (Ideally this would be a subclass
    # of, or share a common parent class with, the Python Reader
    # implementation.)
    return cast(Reader, _extension.Reader(database, mode))


__title__ = "maxminddb"
__version__ = "2.6.1"
__author__ = "Gregory Oschwald"
__license__ = "Apache License, Version 2.0"
__copyright__ = "Copyright 2013-2024 MaxMind, Inc."
