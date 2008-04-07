class WKTAdaptor(object):
    """
    This provides an adaptor for Geometries sent to the
    MySQL and Oracle database backends.
    """
    def __init__(self, geom):
        self.wkt = geom.wkt

    def __eq__(self, other):
        return self.wkt == other.wkt

    def __str__(self):
        return self.wkt
