from django.contrib.gis.geos.geometry import GEOSGeometry, hex_regex, wkt_regex
from django.utils import six


def fromfile(file_h):
    """
    Given a string file name, returns a GEOSGeometry. The file may contain WKB,
    WKT, or HEX.
    """
    # If given a file name, get a real handle.
    if isinstance(file_h, str):
        with open(file_h, 'rb') as file_h:
            buf = file_h.read()
    else:
        buf = file_h.read()

    # If we get WKB need to wrap in memoryview(), so run through regexes.
    if isinstance(buf, bytes):
        try:
            decoded = buf.decode()
            if wkt_regex.match(decoded) or hex_regex.match(decoded):
                return GEOSGeometry(decoded)
        except UnicodeDecodeError:
            pass
    else:
        return GEOSGeometry(buf)

    return GEOSGeometry(six.memoryview(buf))


def fromstr(string, **kwargs):
    "Given a string value, returns a GEOSGeometry object."
    return GEOSGeometry(string, **kwargs)
