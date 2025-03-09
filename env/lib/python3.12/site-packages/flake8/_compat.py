from __future__ import annotations

import sys
import tokenize

if sys.version_info >= (3, 12):  # pragma: >=3.12 cover
    FSTRING_START = tokenize.FSTRING_START
    FSTRING_MIDDLE = tokenize.FSTRING_MIDDLE
    FSTRING_END = tokenize.FSTRING_END
else:  # pragma: <3.12 cover
    FSTRING_START = FSTRING_MIDDLE = FSTRING_END = -1
