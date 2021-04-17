"""Stuff that differs in different Python versions and platform
distributions."""
from __future__ import absolute_import, division

import codecs
import locale
import logging
import os
import shutil
import sys

from pip._vendor.six import text_type
from pip._vendor.urllib3.util import IS_PYOPENSSL

from pip._internal.utils.typing import MYPY_CHECK_RUNNING

if MYPY_CHECK_RUNNING:
    from typing import Optional, Text, Tuple, Union

try:
    import _ssl  # noqa
except ImportError:
    ssl = None
else:
    # This additional assignment was needed to prevent a mypy error.
    ssl = _ssl

try:
    import ipaddress
except ImportError:
    try:
        from pip._vendor import ipaddress  # type: ignore
    except ImportError:
        import ipaddr as ipaddress  # type: ignore
        ipaddress.ip_address = ipaddress.IPAddress  # type: ignore
        ipaddress.ip_network = ipaddress.IPNetwork  # type: ignore


__all__ = [
    "ipaddress", "uses_pycache", "console_to_str", "native_str",
    "get_path_uid", "stdlib_pkgs", "WINDOWS", "samefile", "get_terminal_size",
    "get_extension_suffixes",
]


logger = logging.getLogger(__name__)

HAS_TLS = (ssl is not None) or IS_PYOPENSSL

if sys.version_info >= (3, 4):
    uses_pycache = True
    from importlib.util import cache_from_source
else:
    import imp

    try:
        cache_from_source = imp.cache_from_source  # type: ignore
    except AttributeError:
        # does not use __pycache__
        cache_from_source = None

    uses_pycache = cache_from_source is not None


if sys.version_info >= (3, 5):
    backslashreplace_decode = "backslashreplace"
else:
    # In version 3.4 and older, backslashreplace exists
    # but does not support use for decoding.
    # We implement our own replace handler for this
    # situation, so that we can consistently use
    # backslash replacement for all versions.
    def backslashreplace_decode_fn(err):
        raw_bytes = (err.object[i] for i in range(err.start, err.end))
        if sys.version_info[0] == 2:
            # Python 2 gave us characters - convert to numeric bytes
            raw_bytes = (ord(b) for b in raw_bytes)
        return u"".join(u"\\x%x" % c for c in raw_bytes), err.end
    codecs.register_error(
        "backslashreplace_decode",
        backslashreplace_decode_fn,
    )
    backslashreplace_decode = "backslashreplace_decode"


def str_to_display(data, desc=None):
    # type: (Union[bytes, Text], Optional[str]) -> Text
    """
    For display or logging purposes, convert a bytes object (or text) to
    text (e.g. unicode in Python 2) safe for output.

    :param desc: An optional phrase describing the input data, for use in
        the log message if a warning is logged. Defaults to "Bytes object".

    This function should never error out and so can take a best effort
    approach. It is okay to be lossy if needed since the return value is
    just for display.

    We assume the data is in the locale preferred encoding. If it won't
    decode properly, we warn the user but decode as best we can.

    We also ensure that the output can be safely written to standard output
    without encoding errors.
    """
    if isinstance(data, text_type):
        return data

    # Otherwise, data is a bytes object (str in Python 2).
    # First, get the encoding we assume. This is the preferred
    # encoding for the locale, unless that is not found, or
    # it is ASCII, in which case assume UTF-8
    encoding = locale.getpreferredencoding()
    if (not encoding) or codecs.lookup(encoding).name == "ascii":
        encoding = "utf-8"

    # Now try to decode the data - if we fail, warn the user and
    # decode with replacement.
    try:
        decoded_data = data.decode(encoding)
    except UnicodeDecodeError:
        if desc is None:
            desc = 'Bytes object'
        msg_format = '{} does not appear to be encoded as %s'.format(desc)
        logger.warning(msg_format, encoding)
        decoded_data = data.decode(encoding, errors=backslashreplace_decode)

    # Make sure we can print the output, by encoding it to the output
    # encoding with replacement of unencodable characters, and then
    # decoding again.
    # We use stderr's encoding because it's less likely to be
    # redirected and if we don't find an encoding we skip this
    # step (on the assumption that output is wrapped by something
    # that won't fail).
    # The double getattr is to deal with the possibility that we're
    # being called in a situation where sys.__stderr__ doesn't exist,
    # or doesn't have an encoding attribute. Neither of these cases
    # should occur in normal pip use, but there's no harm in checking
    # in case people use pip in (unsupported) unusual situations.
    output_encoding = getattr(getattr(sys, "__stderr__", None),
                              "encoding", None)

    if output_encoding:
        output_encoded = decoded_data.encode(
            output_encoding,
            errors="backslashreplace"
        )
        decoded_data = output_encoded.decode(output_encoding)

    return decoded_data


def console_to_str(data):
    # type: (bytes) -> Text
    """Return a string, safe for output, of subprocess output.
    """
    return str_to_display(data, desc='Subprocess output')


if sys.version_info >= (3,):
    def native_str(s, replace=False):
        # type: (str, bool) -> str
        if isinstance(s, bytes):
            return s.decode('utf-8', 'replace' if replace else 'strict')
        return s

else:
    def native_str(s, replace=False):
        # type: (str, bool) -> str
        # Replace is ignored -- unicode to UTF-8 can't fail
        if isinstance(s, text_type):
            return s.encode('utf-8')
        return s


def get_path_uid(path):
    # type: (str) -> int
    """
    Return path's uid.

    Does not follow symlinks:
        https://github.com/pypa/pip/pull/935#discussion_r5307003

    Placed this function in compat due to differences on AIX and
    Jython, that should eventually go away.

    :raises OSError: When path is a symlink or can't be read.
    """
    if hasattr(os, 'O_NOFOLLOW'):
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        file_uid = os.fstat(fd).st_uid
        os.close(fd)
    else:  # AIX and Jython
        # WARNING: time of check vulnerability, but best we can do w/o NOFOLLOW
        if not os.path.islink(path):
            # older versions of Jython don't have `os.fstat`
            file_uid = os.stat(path).st_uid
        else:
            # raise OSError for parity with os.O_NOFOLLOW above
            raise OSError(
                "%s is a symlink; Will not return uid for symlinks" % path
            )
    return file_uid


if sys.version_info >= (3, 4):
    from importlib.machinery import EXTENSION_SUFFIXES

    def get_extension_suffixes():
        return EXTENSION_SUFFIXES
else:
    from imp import get_suffixes

    def get_extension_suffixes():
        return [suffix[0] for suffix in get_suffixes()]


def expanduser(path):
    # type: (str) -> str
    """
    Expand ~ and ~user constructions.

    Includes a workaround for https://bugs.python.org/issue14768
    """
    expanded = os.path.expanduser(path)
    if path.startswith('~/') and expanded.startswith('//'):
        expanded = expanded[1:]
    return expanded


# packages in the stdlib that may have installation metadata, but should not be
# considered 'installed'.  this theoretically could be determined based on
# dist.location (py27:`sysconfig.get_paths()['stdlib']`,
# py26:sysconfig.get_config_vars('LIBDEST')), but fear platform variation may
# make this ineffective, so hard-coding
stdlib_pkgs = {"python", "wsgiref", "argparse"}


# windows detection, covers cpython and ironpython
WINDOWS = (sys.platform.startswith("win") or
           (sys.platform == 'cli' and os.name == 'nt'))


def samefile(file1, file2):
    # type: (str, str) -> bool
    """Provide an alternative for os.path.samefile on Windows/Python2"""
    if hasattr(os.path, 'samefile'):
        return os.path.samefile(file1, file2)
    else:
        path1 = os.path.normcase(os.path.abspath(file1))
        path2 = os.path.normcase(os.path.abspath(file2))
        return path1 == path2


if hasattr(shutil, 'get_terminal_size'):
    def get_terminal_size():
        # type: () -> Tuple[int, int]
        """
        Returns a tuple (x, y) representing the width(x) and the height(y)
        in characters of the terminal window.
        """
        return tuple(shutil.get_terminal_size())  # type: ignore
else:
    def get_terminal_size():
        # type: () -> Tuple[int, int]
        """
        Returns a tuple (x, y) representing the width(x) and the height(y)
        in characters of the terminal window.
        """
        def ioctl_GWINSZ(fd):
            try:
                import fcntl
                import termios
                import struct
                cr = struct.unpack_from(
                    'hh',
                    fcntl.ioctl(fd, termios.TIOCGWINSZ, '12345678')
                )
            except Exception:
                return None
            if cr == (0, 0):
                return None
            return cr
        cr = ioctl_GWINSZ(0) or ioctl_GWINSZ(1) or ioctl_GWINSZ(2)
        if not cr:
            try:
                fd = os.open(os.ctermid(), os.O_RDONLY)
                cr = ioctl_GWINSZ(fd)
                os.close(fd)
            except Exception:
                pass
        if not cr:
            cr = (os.environ.get('LINES', 25), os.environ.get('COLUMNS', 80))
        return int(cr[1]), int(cr[0])
