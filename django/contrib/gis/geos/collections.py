"""
 This module houses the Geometry Collection objects:
 GeometryCollection, MultiPoint, MultiLineString, and MultiPolygon
"""
from ctypes import c_int, c_uint, byref
from types import TupleType, ListType
from django.contrib.gis.geos.base import GEOSGeometry
from django.contrib.gis.geos.error import GEOSException, GEOSIndexError
from django.contrib.gis.geos.geometries import Point, LineString, LinearRing, Polygon
from django.contrib.gis.geos.libgeos import get_pointer_arr, GEOM_PTR
from django.contrib.gis.geos.prototypes import create_collection, destroy_geom, geom_clone, geos_typeid, get_cs, get_geomn

class GeometryCollection(GEOSGeometry):
    _allowed = (Point, LineString, LinearRing, Polygon)
    _typeid = 7

    def __init__(self, *args, **kwargs):
        "Initializes a Geometry Collection from a sequence of Geometry objects."

        # Checking the arguments
        if not args:
            raise TypeError, 'Must provide at least one Geometry to initialize %s.' % self.__class__.__name__

        if len(args) == 1: 
            # If only one geometry provided or a list of geometries is provided
            #  in the first argument.
            if isinstance(args[0], (TupleType, ListType)):
                init_geoms = args[0]
            else:
                init_geoms = args
        else:
            init_geoms = args

        # Ensuring that only the permitted geometries are allowed in this collection
        if False in [isinstance(geom, self._allowed) for geom in init_geoms]:
            raise TypeError('Invalid Geometry type encountered in the arguments.')

        # Creating the geometry pointer array.
        ngeoms = len(init_geoms)
        geoms = get_pointer_arr(ngeoms)
        for i in xrange(ngeoms): geoms[i] = geom_clone(init_geoms[i].ptr)
        super(GeometryCollection, self).__init__(create_collection(c_int(self._typeid), byref(geoms), c_uint(ngeoms)), **kwargs)

    def __getitem__(self, index):
        "Returns the Geometry from this Collection at the given index (0-based)."
        # Checking the index and returning the corresponding GEOS geometry.
        self._checkindex(index)
        return GEOSGeometry(geom_clone(get_geomn(self.ptr, index)), srid=self.srid)

    def __setitem__(self, index, geom):
        "Sets the Geometry at the specified index."
        self._checkindex(index)
        if not isinstance(geom, self._allowed):
            raise TypeError('Incompatible Geometry for collection.')
        
        ngeoms = len(self)
        geoms = get_pointer_arr(ngeoms)
        for i in xrange(ngeoms):
            if i == index:
                geoms[i] = geom_clone(geom.ptr)
            else:
                geoms[i] = geom_clone(get_geomn(self.ptr, i))
        
        # Creating a new collection, and destroying the contents of the previous poiner.
        prev_ptr = self.ptr
        srid = self.srid
        self._ptr = create_collection(c_int(self._typeid), byref(geoms), c_uint(ngeoms))
        if srid: self.srid = srid
        destroy_geom(prev_ptr)

    def __iter__(self):
        "Iterates over each Geometry in the Collection."
        for i in xrange(len(self)):
            yield self.__getitem__(i)

    def __len__(self):
        "Returns the number of geometries in this Collection."
        return self.num_geom

    def _checkindex(self, index):
        "Checks the given geometry index."
        if index < 0 or index >= self.num_geom:
            raise GEOSIndexError('invalid GEOS Geometry index: %s' % str(index))

    @property
    def kml(self):
        "Returns the KML for this Geometry Collection."
        return '<MultiGeometry>%s</MultiGeometry>' % ''.join([g.kml for g in self])

    @property
    def tuple(self):
        "Returns a tuple of all the coordinates in this Geometry Collection"
        return tuple([g.tuple for g in self])
    coords = tuple

# MultiPoint, MultiLineString, and MultiPolygon class definitions.
class MultiPoint(GeometryCollection): 
    _allowed = Point
    _typeid = 4
class MultiLineString(GeometryCollection): 
    _allowed = (LineString, LinearRing)
    _typeid = 5
class MultiPolygon(GeometryCollection): 
    _allowed = Polygon
    _typeid = 6
