"""Constants used in the API."""

from enum import IntEnum


class Mode(IntEnum):
    """Database open modes.

    These modes control how the MaxMind DB file is opened and read.
    """

    AUTO = 0
    """Try MODE_MMAP_EXT, MODE_MMAP, MODE_FILE in that order. Default mode."""

    MMAP_EXT = 1
    """Use the C extension with memory map."""

    MMAP = 2
    """Read from memory map. Pure Python."""

    FILE = 4
    """Read database as standard file. Pure Python."""

    MEMORY = 8
    """Load database into memory. Pure Python."""

    FD = 16
    """Database is a file descriptor, not a path. This mode implies MODE_MEMORY."""


# Backward compatibility: export both enum members and old-style constants
MODE_AUTO = Mode.AUTO
MODE_MMAP_EXT = Mode.MMAP_EXT
MODE_MMAP = Mode.MMAP
MODE_FILE = Mode.FILE
MODE_MEMORY = Mode.MEMORY
MODE_FD = Mode.FD

__all__ = [
    "MODE_AUTO",
    "MODE_FD",
    "MODE_FILE",
    "MODE_MEMORY",
    "MODE_MMAP",
    "MODE_MMAP_EXT",
    "Mode",
]
