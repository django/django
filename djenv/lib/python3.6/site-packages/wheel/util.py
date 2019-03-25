import base64
import io
import sys


if sys.version_info[0] < 3:
    text_type = unicode  # noqa: F821

    StringIO = io.BytesIO

    def native(s, encoding='utf-8'):
        if isinstance(s, unicode):
            return s.encode(encoding)
        return s
else:
    text_type = str

    StringIO = io.StringIO

    def native(s, encoding='utf-8'):
        if isinstance(s, bytes):
            return s.decode(encoding)
        return s


def urlsafe_b64encode(data):
    """urlsafe_b64encode without padding"""
    return base64.urlsafe_b64encode(data).rstrip(b'=')


def urlsafe_b64decode(data):
    """urlsafe_b64decode without padding"""
    pad = b'=' * (4 - (len(data) & 3))
    return base64.urlsafe_b64decode(data + pad)


def as_unicode(s):
    if isinstance(s, bytes):
        return s.decode('utf-8')
    return s


def as_bytes(s):
    if isinstance(s, text_type):
        return s.encode('utf-8')
    return s
