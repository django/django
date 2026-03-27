"""A lil' TOML parser."""

__all__ = ("loads", "load", "TOMLDecodeError")
__version__ = "1.2.0"  # DO NOT EDIT THIS LINE MANUALLY. LET bump2version UTILITY DO IT

from ._parser import TOMLDecodeError, load, loads
