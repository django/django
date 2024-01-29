"""
Portable file locking utilities.

Based partially on an example by Jonathan Feignberg in the Python
Cookbook [1] (licensed under the Python Software License) and a ctypes port by
Anatoly Techtonik for Roundup [2] (license [3]).

[1] https://code.activestate.com/recipes/65203/
[2] https://sourceforge.net/p/roundup/code/ci/default/tree/roundup/backends/portalocker.py  # NOQA
[3] https://sourceforge.net/p/roundup/code/ci/default/tree/COPYING.txt

Example Usage::

    >>> from django.core.files import locks
    >>> with open('./file', 'wb') as f:
    ...     locks.lock(f, locks.LOCK_EX)
    ...     f.write('Django')
"""

import os

__all__ = ("LOCK_EX", "LOCK_SH", "LOCK_NB", "lock", "unlock")


def _fd(f):
    """Get a filedescriptor from something which could be a file or an fd."""
    return f.fileno() if hasattr(f, "fileno") else f


if os.name == "nt":
    import msvcrt
    from ctypes import (
        POINTER,
        Structure,
        Union,
        WinDLL,
        byref,
        c_int64,
        c_ulong,
        c_void_p,
        sizeof,
    )
    from ctypes.wintypes import BOOL, DWORD, HANDLE

    LOCK_SH = 0  # the default
    LOCK_NB = 0x1  # LOCKFILE_FAIL_IMMEDIATELY
    LOCK_EX = 0x2  # LOCKFILE_EXCLUSIVE_LOCK

    # --- Adapted from the pyserial project ---
    # detect size of ULONG_PTR
    if sizeof(c_ulong) != sizeof(c_void_p):
        ULONG_PTR = c_int64
    else:
        ULONG_PTR = c_ulong
    PVOID = c_void_p

    # --- Union inside Structure by stackoverflow:3480240 ---
    class _OFFSET(Structure):
        _fields_ = [("Offset", DWORD), ("OffsetHigh", DWORD)]

    class _OFFSET_UNION(Union):
        _anonymous_ = ["_offset"]
        _fields_ = [("_offset", _OFFSET), ("Pointer", PVOID)]

    class OVERLAPPED(Structure):
        _anonymous_ = ["_offset_union"]
        _fields_ = [
            ("Internal", ULONG_PTR),
            ("InternalHigh", ULONG_PTR),
            ("_offset_union", _OFFSET_UNION),
            ("hEvent", HANDLE),
        ]

    LPOVERLAPPED = POINTER(OVERLAPPED)

    # --- Define function prototypes for extra safety ---
    kernel32 = WinDLL("kernel32")
    LockFileEx = kernel32.LockFileEx
    LockFileEx.restype = BOOL
    LockFileEx.argtypes = [HANDLE, DWORD, DWORD, DWORD, DWORD, LPOVERLAPPED]
    UnlockFileEx = kernel32.UnlockFileEx
    UnlockFileEx.restype = BOOL
    UnlockFileEx.argtypes = [HANDLE, DWORD, DWORD, DWORD, LPOVERLAPPED]

    def lock(f, flags):
        hfile = msvcrt.get_osfhandle(_fd(f))
        overlapped = OVERLAPPED()
        ret = LockFileEx(hfile, flags, 0, 0, 0xFFFF0000, byref(overlapped))
        return bool(ret)

    def unlock(f):
        hfile = msvcrt.get_osfhandle(_fd(f))
        overlapped = OVERLAPPED()
        ret = UnlockFileEx(hfile, 0, 0, 0xFFFF0000, byref(overlapped))
        return bool(ret)

else:
    try:
        import fcntl

        LOCK_SH = fcntl.LOCK_SH  # shared lock
        LOCK_NB = fcntl.LOCK_NB  # non-blocking
        LOCK_EX = fcntl.LOCK_EX
    except (ImportError, AttributeError):
        # File locking is not supported.
        LOCK_EX = LOCK_SH = LOCK_NB = 0

        # Dummy functions that don't do anything.
        def lock(f, flags):
            # File is not locked
            return False

        def unlock(f):
            # File is unlocked
            return True

    else:

        def lock(f, flags):
            try:
                fcntl.flock(_fd(f), flags)
                return True
            except BlockingIOError:
                return False

        def unlock(f):
            fcntl.flock(_fd(f), fcntl.LOCK_UN)
            return True
