"""
   This module houses the Geometry Collection objects:
     GeometryCollection, MultiPoint, MultiLineString, and MultiPolygon
"""
from ctypes import c_int, c_uint, byref, cast
from types import TupleType, ListType
from django.contrib.gis.geos.libgeos import lgeos, GEOSPointer, get_pointer_arr, GEOM_PTR
from django.contrib.gis.geos.base import GEOSGeometry
from django.contrib.gis.geos.error import GEOSException, GEOSGeometryIndexError
from django.contrib.gis.geos.geometries import Point, LineString, LinearRing, Polygon

class GeometryCollection(GEOSGeometry):
    _allowed = (Point, LineString, LinearRing, Polygon)
    _typeid = 7

    def __init__(self, *args, **kwargs):
        "Initializes a Geometry Collection from a sequence of Geometry objects."
        # Setting up the collection for creation
        self._ptr = GEOSPointer(0) # Initially NULL
        self._geoms = {}
        self._parent = None

        # Checking the arguments
        if not args:
            raise TypeError, 'Must provide at least one Geometry to initialize %s.' % self.__class__.__name__

        if len(args) == 1: # If only one geometry provided or a list of geometries is provided
            if isinstance(args[0], (TupleType, ListType)):
                init_geoms = args[0]
            else:
                init_geoms = args
        else:
            init_geoms = args

        # Ensuring that only the permitted geometries are allowed in this collection
        if False in [isinstance(geom, self._allowed) for geom in init_geoms]:
            raise TypeError, 'Invalid Geometry type encountered in the arguments.'

        # Creating the geometry pointer array
        ngeom = len(init_geoms)
        geoms = get_pointer_arr(ngeom)

        # Incrementing through each input geometry.
        for i in xrange(ngeom):
            geoms[i] = cast(init_geoms[i]._nullify(), GEOM_PTR)
        
        # Calling the parent class, using the pointer returned from GEOS createCollection()
        super(GeometryCollection, self).__init__(lgeos.GEOSGeom_createCollection(c_int(self._typeid), byref(geoms), c_uint(ngeom)), **kwargs)

    def __del__(self):
        "Overloaded deletion method for Geometry Collections."
        #print 'collection: Deleting %s (parent=%s, valid=%s)' % (self.__class__.__name__, self._parent, self._ptr.valid)
        # If this geometry is still valid, it hasn't been modified by others.
        if self._ptr.valid:
            # Nullifying pointers to internal geometries, preventing any attempted future access.
            for k in self._geoms: self._geoms[k].nullify()
        else:
            # Internal memory has become part of other Geometry objects, must delete the
            #  internal objects which are still valid individually, since calling destructor
            #  on entire geometry will result in an attempted deletion of NULL pointers for
            #  the missing components.
            for k in self._geoms:
                if self._geoms[k].valid:
                    lgeos.GEOSGeom_destroy(self._geoms[k].address)
                    self._geoms[k].nullify()
        super(GeometryCollection, self).__del__()
            
    def __getitem__(self, index):
        "Returns the Geometry from this Collection at the given index (0-based)."
        # Checking the index and returning the corresponding GEOS geometry.
        self._checkindex(index)
        return GEOSGeometry(self._geoms[index], parent=self._ptr, srid=self.srid)

    def __setitem__(self, index, geom):
        "Sets the Geometry at the specified index."
        self._checkindex(index)
        if not isinstance(geom, self._allowed):
            raise TypeError, 'Incompatible Geometry for collection.'

        # Constructing the list of geometries that will go in the collection.
        new_geoms = []
        for i in xrange(len(self)):
            if i == index: new_geoms.append(geom)
            else: new_geoms.append(self[i])

        # Creating a new geometry collection from the list, and
        #  re-assigning the pointers.
        new_collection = self.__class__(*new_geoms, **{'srid':self.srid})
        self._reassign(new_collection)
        
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
            raise GEOSGeometryIndexError, 'invalid GEOS Geometry index: %s' % str(index)

    def _nullify(self):
        "Overloaded from base method to nullify geometry references in this Collection."
        # Nullifying the references to the internal Geometry objects from this Collection.
        for k in self._geoms: self._geoms[k].nullify()
        return super(GeometryCollection, self)._nullify()

    def _populate(self):
        "Populates the internal child geometry dictionary."
        self._geoms = {}
        for i in xrange(self.num_geom):
            self._geoms[i] = GEOSPointer(lgeos.GEOSGetGeometryN(self._ptr(), c_int(i)))

    @property
    def kml(self):
        "Returns the KML for this Geometry Collection."
        kml = '<MultiGeometry>'
        for g in self: kml += g.kml
        return kml + '</MultiGeometry>'

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
