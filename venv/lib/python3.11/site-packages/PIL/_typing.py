from __future__ import annotations

import sys

if sys.version_info >= (3, 10):
    from typing import TypeGuard
else:
    try:
        from typing_extensions import TypeGuard
    except ImportError:
        from typing import Any

        class TypeGuard:  # type: ignore[no-redef]
            def __class_getitem__(cls, item: Any) -> type[bool]:
                return bool


__all__ = ["TypeGuard"]
