"""propcache: An accelerated property cache for Python classes."""

from typing import TYPE_CHECKING

_PUBLIC_API = ("cached_property", "under_cached_property")

__version__ = "0.4.1"
__all__ = ()

# Imports have moved to `propcache.api` in 0.2.0+.
# This module is now a facade for the API.
if TYPE_CHECKING:
    from .api import cached_property as cached_property  # noqa: F401
    from .api import under_cached_property as under_cached_property  # noqa: F401


def _import_facade(attr: str) -> object:
    """Import the public API from the `api` module."""
    if attr in _PUBLIC_API:
        from . import api  # pylint: disable=import-outside-toplevel

        return getattr(api, attr)
    raise AttributeError(f"module '{__package__}' has no attribute '{attr}'")


def _dir_facade() -> list[str]:
    """Include the public API in the module's dir() output."""
    return [*_PUBLIC_API, *globals().keys()]


__getattr__ = _import_facade
__dir__ = _dir_facade
