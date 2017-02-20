"""
 This object provides quoting for GEOS geometries into PostgreSQL/PostGIS.
"""
from psycopg2 import Binary
from psycopg2.extensions import ISQLQuote

from django.contrib.gis.db.backends.postgis.pgraster import to_pgraster
from django.contrib.gis.geometry.backend import Geometry


class PostGISAdapter:
    def __init__(self, obj, geography=False):
        """
        Initialize on the spatial object.
        """
        self.is_geometry = isinstance(obj, (Geometry, PostGISAdapter))

        # Getting the WKB (in string form, to allow easy pickling of
        # the adaptor) and the SRID from the geometry or raster.
        if self.is_geometry:
            self.ewkb = bytes(obj.ewkb)
            self._adapter = Binary(self.ewkb)
        else:
            self.ewkb = to_pgraster(obj)

        self.srid = obj.srid
        self.geography = geography

    def __conform__(self, proto):
        """Does the given protocol conform to what Psycopg2 expects?"""
        if proto == ISQLQuote:
            return self
        else:
            raise Exception('Error implementing psycopg2 protocol. Is psycopg2 installed?')

    def __eq__(self, other):
        if not isinstance(other, PostGISAdapter):
            return False
        return (self.ewkb == other.ewkb) and (self.srid == other.srid)

    def __hash__(self):
        return hash((self.ewkb, self.srid))

    def __str__(self):
        return self.getquoted()

    def prepare(self, conn):
        """
        This method allows escaping the binary in the style required by the
        server's `standard_conforming_string` setting.
        """
        if self.is_geometry:
            self._adapter.prepare(conn)

    def getquoted(self):
        """
        Return a properly quoted string for use in PostgreSQL/PostGIS.
        """
        if self.is_geometry:
            # Psycopg will figure out whether to use E'\\000' or '\000'.
            return '%s(%s)' % (
                'ST_GeogFromWKB' if self.geography else 'ST_GeomFromEWKB',
                self._adapter.getquoted().decode()
            )
        else:
            # For rasters, add explicit type cast to WKB string.
            return "'%s'::raster" % self.ewkb
