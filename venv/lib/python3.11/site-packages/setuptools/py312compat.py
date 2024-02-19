import sys
import shutil


def shutil_rmtree(path, ignore_errors=False, onexc=None):
    if sys.version_info >= (3, 12):
        return shutil.rmtree(path, ignore_errors, onexc=onexc)

    def _handler(fn, path, excinfo):
        return onexc(fn, path, excinfo[1])

    return shutil.rmtree(path, ignore_errors, onerror=_handler)
