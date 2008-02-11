"""
 This object provides the database adaptor for Oracle geometries.
"""
class OracleSpatialAdaptor(object):
    def __init__(self, geom):
        "Initializes only on the geometry object."
        self.wkt = geom.wkt

    def __str__(self):
        "WKT is used for the substitution value of the geometry."
        return self.wkt
