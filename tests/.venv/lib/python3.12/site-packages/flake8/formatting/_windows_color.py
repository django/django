"""ctypes hackery to enable color processing on windows.

See: https://github.com/pre-commit/pre-commit/blob/cb40e96/pre_commit/color.py
"""

from __future__ import annotations

import sys

if sys.platform == "win32":  # pragma: no cover (windows)

    def _enable() -> None:
        from ctypes import POINTER
        from ctypes import windll
        from ctypes import WinError
        from ctypes import WINFUNCTYPE
        from ctypes.wintypes import BOOL
        from ctypes.wintypes import DWORD
        from ctypes.wintypes import HANDLE

        STD_ERROR_HANDLE = -12
        ENABLE_VIRTUAL_TERMINAL_PROCESSING = 4

        def bool_errcheck(result, func, args):
            if not result:
                raise WinError()
            return args

        GetStdHandle = WINFUNCTYPE(HANDLE, DWORD)(
            ("GetStdHandle", windll.kernel32),
            ((1, "nStdHandle"),),
        )

        GetConsoleMode = WINFUNCTYPE(BOOL, HANDLE, POINTER(DWORD))(
            ("GetConsoleMode", windll.kernel32),
            ((1, "hConsoleHandle"), (2, "lpMode")),
        )
        GetConsoleMode.errcheck = bool_errcheck

        SetConsoleMode = WINFUNCTYPE(BOOL, HANDLE, DWORD)(
            ("SetConsoleMode", windll.kernel32),
            ((1, "hConsoleHandle"), (1, "dwMode")),
        )
        SetConsoleMode.errcheck = bool_errcheck

        # As of Windows 10, the Windows console supports (some) ANSI escape
        # sequences, but it needs to be enabled using `SetConsoleMode` first.
        #
        # More info on the escape sequences supported:
        # https://msdn.microsoft.com/en-us/library/windows/desktop/mt638032(v=vs.85).aspx
        stderr = GetStdHandle(STD_ERROR_HANDLE)
        flags = GetConsoleMode(stderr)
        SetConsoleMode(stderr, flags | ENABLE_VIRTUAL_TERMINAL_PROCESSING)

    try:
        _enable()
    except OSError:
        terminal_supports_color = False
    else:
        terminal_supports_color = True
else:  # pragma: win32 no cover
    terminal_supports_color = True
