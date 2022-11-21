from django.contrib.gis.geos.geometry import GEOSGeometry, hex_regex, wkt_regex


def fromfile(file_h):
    """
    Given a string file name, returns a GEOSGeometry. The file may contain WKB,
    WKT, or HEX.
    """
    # If given a file name, get a real handle.
    if isinstance(file_h, str):
        with open(file_h, "rb") as file_h:
            buf = file_h.read()
    else:
        buf = file_h.read()

    if not isinstance(buf, bytes):
        return GEOSGeometry(buf)

    try:
        decoded = buf.decode()
    except UnicodeDecodeError:
        pass
    else:
        if wkt_regex.match(decoded) or hex_regex.match(decoded):
            return GEOSGeometry(decoded)
    return GEOSGeometry(memoryview(buf))


def fromstr(string, **kwargs):
    "Given a string value, return a GEOSGeometry object."
    return GEOSGeometry(string, **kwargs)
