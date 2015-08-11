class WKTAdapter(object):
    """
    This provides an adaptor for Geometries sent to the
    MySQL and Oracle database backends.
    """
    def __init__(self, geom):
        self.wkt = geom.wkt
        self.srid = geom.srid

    def __eq__(self, other):
        if not isinstance(other, WKTAdapter):
            return False
        return self.wkt == other.wkt and self.srid == other.srid

    def __hash__(self):
        return hash((self.wkt, self.srid))

    def __str__(self):
        return self.wkt
