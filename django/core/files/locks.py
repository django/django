"""
Portable file locking utilities.

Based partially on example by Jonathan Feignberg <jdf@pobox.com> in the Python
Cookbook, licensed under the Python Software License.

    http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/65203

Example Usage::

    >>> from django.core.files import locks
    >>> f = open('./file', 'wb')
    >>> locks.lock(f, locks.LOCK_EX)
    >>> f.write('Django')
    >>> f.close()
"""

__all__ = ('LOCK_EX','LOCK_SH','LOCK_NB','lock','unlock')

system_type = None

try:
    import win32con
    import win32file
    import pywintypes
    LOCK_EX = win32con.LOCKFILE_EXCLUSIVE_LOCK
    LOCK_SH = 0
    LOCK_NB = win32con.LOCKFILE_FAIL_IMMEDIATELY
    __overlapped = pywintypes.OVERLAPPED()
    system_type = 'nt'
except (ImportError, AttributeError):
    pass

try:
    import fcntl
    LOCK_EX = fcntl.LOCK_EX
    LOCK_SH = fcntl.LOCK_SH
    LOCK_NB = fcntl.LOCK_NB
    system_type = 'posix'
except (ImportError, AttributeError):
    pass

if system_type == 'nt':
    def lock(file, flags):
        hfile = win32file._get_osfhandle(file.fileno())
        win32file.LockFileEx(hfile, flags, 0, -0x10000, __overlapped)

    def unlock(file):
        hfile = win32file._get_osfhandle(file.fileno())
        win32file.UnlockFileEx(hfile, 0, -0x10000, __overlapped)
elif system_type == 'posix':
    def lock(file, flags):
        fcntl.flock(file.fileno(), flags)

    def unlock(file):
        fcntl.flock(file.fileno(), fcntl.LOCK_UN)
else:
    # File locking is not supported.
    LOCK_EX = LOCK_SH = LOCK_NB = None

    # Dummy functions that don't do anything.
    def lock(file, flags):
        pass

    def unlock(file):
        pass
