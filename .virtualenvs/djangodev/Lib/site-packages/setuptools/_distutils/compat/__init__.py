from __future__ import annotations

from .py38 import removeprefix


def consolidate_linker_args(args: list[str]) -> str:
    """
    Ensure the return value is a string for backward compatibility.

    Retain until at least 2024-04-31. See pypa/distutils#246
    """

    if not all(arg.startswith('-Wl,') for arg in args):
        return args
    return '-Wl,' + ','.join(removeprefix(arg, '-Wl,') for arg in args)
