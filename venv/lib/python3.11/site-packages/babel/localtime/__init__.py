"""
    babel.localtime
    ~~~~~~~~~~~~~~~

    Babel specific fork of tzlocal to determine the local timezone
    of the system.

    :copyright: (c) 2013-2023 by the Babel Team.
    :license: BSD, see LICENSE for more details.
"""

import datetime
import sys

if sys.platform == 'win32':
    from babel.localtime._win32 import _get_localzone
else:
    from babel.localtime._unix import _get_localzone


# TODO(3.0): the offset constants are not part of the public API
#            and should be removed
from babel.localtime._fallback import (
    DSTDIFF,  # noqa: F401
    DSTOFFSET,  # noqa: F401
    STDOFFSET,  # noqa: F401
    ZERO,  # noqa: F401
    _FallbackLocalTimezone,
)


def get_localzone() -> datetime.tzinfo:
    """Returns the current underlying local timezone object.
    Generally this function does not need to be used, it's a
    better idea to use the :data:`LOCALTZ` singleton instead.
    """
    return _get_localzone()


try:
    LOCALTZ = get_localzone()
except LookupError:
    LOCALTZ = _FallbackLocalTimezone()
