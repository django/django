"""
 This object provides quoting for GEOS geometries into MySQL.
"""
class MySQLAdaptor(object):
    def __init__(self, geom):
        self.wkt = geom.wkt

    def __str__(self):
        "WKT is used as for the substitution value for the geometry."
        return self.wkt
