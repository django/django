"""
   This module houses the Geometry Collection objects:
     GeometryCollection, MultiPoint, MultiLineString, and MultiPolygon
"""
from ctypes import c_int
from django.contrib.gis.geos.libgeos import lgeos, GEOSPointer
from django.contrib.gis.geos.base import GEOSGeometry
from django.contrib.gis.geos.error import GEOSException

class GeometryCollection(GEOSGeometry):

    def __del__(self):
        "Override the GEOSGeometry delete routine to safely take care of any spawned geometries."
        # Nullifying the pointers to internal geometries, preventing any attempted future access
        for k in self._geoms: self._geoms[k].nullify()
        super(GeometryCollection, self).__del__() # Calling the parent __del__() method.

    def __getitem__(self, index):
        "For indexing on the multiple geometries."
        self._checkindex(index)

        # Setting an entry in the _geoms dictionary for the requested geometry.
        if not index in self._geoms:
            self._geoms[index] = GEOSPointer(lgeos.GEOSGetGeometryN(self._ptr(), c_int(index)))

        # Cloning the GEOS Geometry first, before returning it.
        return GEOSGeometry(self._geoms[index], child=True)

    def __iter__(self):
        "For iteration on the multiple geometries."
        for i in xrange(self.__len__()):
            yield self.__getitem__(i)

    def __len__(self):
        "Returns the number of geometries in this collection."
        return self.num_geom

    def _checkindex(self, index):
        "Checks the given geometry index."
        if index < 0 or index >= self.num_geom:
            raise GEOSGeometryIndexError, 'invalid GEOS Geometry index: %s' % str(index)

# MultiPoint, MultiLineString, and MultiPolygon class definitions.
class MultiPoint(GeometryCollection): pass
class MultiLineString(GeometryCollection): pass
class MultiPolygon(GeometryCollection): pass
