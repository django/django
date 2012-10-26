"""
 This object provides quoting for GEOS geometries into PostgreSQL/PostGIS.
"""
from __future__ import unicode_literals

from psycopg2 import Binary
from psycopg2.extensions import ISQLQuote

class PostGISAdapter(object):
    def __init__(self, geom):
        "Initializes on the geometry."
        # Getting the WKB (in string form, to allow easy pickling of
        # the adaptor) and the SRID from the geometry.
        self.ewkb = bytes(geom.ewkb)
        self.srid = geom.srid
        self._adapter = Binary(self.ewkb)

    def __conform__(self, proto):
        # Does the given protocol conform to what Psycopg2 expects?
        if proto == ISQLQuote:
            return self
        else:
            raise Exception('Error implementing psycopg2 protocol. Is psycopg2 installed?')

    def __eq__(self, other):
        if not isinstance(other, PostGISAdapter):
            return False
        return (self.ewkb == other.ewkb) and (self.srid == other.srid)

    def __str__(self):
        return self.getquoted()

    def prepare(self, conn):
        """
        This method allows escaping the binary in the style required by the
        server's `standard_conforming_string` setting.
        """
        self._adapter.prepare(conn)

    def getquoted(self):
        "Returns a properly quoted string for use in PostgreSQL/PostGIS."
        # psycopg will figure out whether to use E'\\000' or '\000'
        return str('ST_GeomFromEWKB(%s)' % self._adapter.getquoted().decode())

    def prepare_database_save(self, unused):
        return self
