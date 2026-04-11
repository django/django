"""Top-level package for outcome."""

from ._impl import (
    Error as Error,
    Maybe as Maybe,
    Outcome as Outcome,
    Value as Value,
    acapture as acapture,
    capture as capture,
)
from ._util import AlreadyUsedError as AlreadyUsedError, fixup_module_metadata
from ._version import __version__ as __version__

__all__ = (
    'Error', 'Outcome', 'Value', 'Maybe', 'acapture', 'capture',
    'AlreadyUsedError'
)

fixup_module_metadata(__name__, globals())
del fixup_module_metadata
