from .private import private
from .public import public


__version__ = '4.0'


# mypy does not understand that __all__ gets populated at runtime via the
# public() call below, so be explicit.
__all__ = [
    'private',
    'public',
]


public(
    private=private,
    public=public,
)
