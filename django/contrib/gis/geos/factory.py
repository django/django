from django.contrib.gis.geos.geometry import GEOSGeometry, wkt_regex, hex_regex

def fromfile(file_h):
    """
    Given a string file name, returns a GEOSGeometry. The file may contain WKB,
    WKT, or HEX.
    """
    # If given a file name, get a real handle.
    if isinstance(file_h, basestring): 
        file_h = open(file_h, 'rb')

    # Reading in the file's contents,
    buf = file_h.read()

    # If we get WKB need to wrap in buffer(), so run through regexes.
    if wkt_regex.match(buf) or hex_regex.match(buf):
        return GEOSGeometry(buf)
    else:
        return GEOSGeometry(buffer(buf))

def fromstr(string, **kwargs):
    "Given a string value, returns a GEOSGeometry object."
    return GEOSGeometry(string, **kwargs)
