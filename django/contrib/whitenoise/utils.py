import errno
import os
import stat
import sys


if sys.version_info[0] >= 3:
    BINARY_TYPE = bytes
else:
    BINARY_TYPE = str


class NotARegularFileError(Exception):
    pass


class MissingFileError(NotARegularFileError):
    pass


class IsDirectoryError(MissingFileError):
    pass


def decode_if_byte_string(s):
    if isinstance(s, BINARY_TYPE):
        s = s.decode('utf-8')
    return s


# Follow Django in treating URLs as UTF-8 encoded (which requires undoing the
# implicit ISO-8859-1 decoding applied in Python 3). Strictly speaking, URLs
# should only be ASCII anyway, but UTF-8 can be found in the wild.
if sys.version_info[0] >= 3:
    def decode_path_info(path_info):
        return path_info.encode('iso-8859-1', 'replace').decode('utf-8', 'replace')
else:
    def decode_path_info(path_info):
        return path_info.decode('utf-8', 'replace')


def stat_regular_file(path):
    """
    Wrap os.stat to raise appropriate errors if `path` is not a regular file
    """
    try:
        file_stat = os.stat(path)
    except OSError as e:
        if e.errno in (errno.ENOENT, errno.ENAMETOOLONG):
            raise MissingFileError(path)
        else:
            raise
    if not stat.S_ISREG(file_stat.st_mode):
        if stat.S_ISDIR(file_stat.st_mode):
            raise IsDirectoryError(u'Path is a directory: {0}'.format(path))
        else:
            raise NotARegularFileError(u'Not a regular file: {0}'.format(path))
    return file_stat


def ensure_leading_trailing_slash(path):
    path = (path or u'').strip(u'/')
    return u'/{0}/'.format(path) if path else u'/'
