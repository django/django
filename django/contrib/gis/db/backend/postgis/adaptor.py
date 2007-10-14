"""
 This object provides quoting for GEOS geometries into PostgreSQL/PostGIS.
"""

from django.contrib.gis.db.backend.postgis.query import GEOM_FROM_WKB
from psycopg2 import Binary
from psycopg2.extensions import ISQLQuote

class PostGISAdaptor(object):
    def __init__(self, geom, srid):
        "Initializes on the geometry and the SRID."
        # Getting the WKB and the SRID
        self.wkb = geom.wkb
        self.srid = srid

    def __conform__(self, proto):
        # Does the given protocol conform to what Psycopg2 expects?
        if proto == ISQLQuote:
            return self
        else:
            raise Exception('Error implementing psycopg2 protocol. Is psycopg2 installed?')

    def __str__(self):
        return self.getquoted()

    def getquoted(self):
        "Returns a properly quoted string for use in PostgreSQL/PostGIS."
        # Want to use WKB, so wrap with psycopg2 Binary() to quote properly.
        return "%s(%s, %s)" % (GEOM_FROM_WKB, Binary(self.wkb), self.srid or -1)
