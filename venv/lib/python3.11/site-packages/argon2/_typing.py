# SPDX-License-Identifier: MIT

from __future__ import annotations

import sys


# try/except ImportError does NOT work.
# c.f. https://github.com/python/mypy/issues/8520
if sys.version_info >= (3, 8):
    from typing import Literal
else:
    from typing_extensions import Literal

__all__ = ["Literal"]
