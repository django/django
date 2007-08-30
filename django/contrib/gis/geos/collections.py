"""
  This module houses the Geometry Collection objects:
   GeometryCollection, MultiPoint, MultiLineString, and MultiPolygon
"""
from ctypes import c_int, c_uint, byref, cast
from types import TupleType, ListType
from django.contrib.gis.geos.base import GEOSGeometry
from django.contrib.gis.geos.error import GEOSException, GEOSGeometryIndexError
from django.contrib.gis.geos.geometries import Point, LineString, LinearRing, Polygon
from django.contrib.gis.geos.libgeos import lgeos, get_pointer_arr, GEOM_PTR
from django.contrib.gis.geos.pointer import GEOSPointer

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
            raise TypeError, 'Invalid Geometry type encountered in the arguments.'

        # Creating the geometry pointer array, and populating each element in
        #  the array with the address of the Geometry returned by _nullify().
        ngeom = len(init_geoms)
        geoms = get_pointer_arr(ngeom)
        for i in xrange(ngeom):
            geoms[i] = cast(init_geoms[i]._nullify(), GEOM_PTR)
        
        # Calling the parent class, using the pointer returned from the 
        #  GEOS createCollection() factory.
        addr = lgeos.GEOSGeom_createCollection(c_int(self._typeid), 
                                               byref(geoms), c_uint(ngeom))
        super(GeometryCollection, self).__init__(addr, **kwargs)

    def __del__(self):
        "Overloaded deletion method for Geometry Collections."
        #print 'collection: Deleting %s (parent=%s, valid=%s)' % (self.__class__.__name__, self._ptr.parent, self._ptr.valid)
        # If this geometry is still valid, it hasn't been modified by others.
        if self._ptr.valid:
            # Nullifying pointers to internal Geometries, preventing any 
            #  attempted future access.
            for g in self._ptr: g.nullify()
        else:
            # Internal memory has become part of other Geometry objects; must 
            #  delete the internal objects which are still valid individually, 
            #  because calling the destructor on the entire geometry will result 
            #  in an attempted deletion of NULL pointers for the missing 
            #  components (which may crash Python).
            for g in self._ptr:
                if len(g) > 0:
                    # The collection geometry is a Polygon, destroy any leftover
                    #  LinearRings.
                    for r in g: r.destroy()
                g.destroy()
                    
        super(GeometryCollection, self).__del__()
            
    def __getitem__(self, index):
        "Returns the Geometry from this Collection at the given index (0-based)."
        # Checking the index and returning the corresponding GEOS geometry.
        self._checkindex(index)
        return GEOSGeometry(self._ptr[index], srid=self.srid)

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
        for g in self._ptr: g.nullify()
        return super(GeometryCollection, self)._nullify()

    def _populate(self):
        "Internal routine that populates the internal children geometries list."
        ptr_list = []
        for i in xrange(len(self)):
            # Getting the geometry pointer for the geometry at the index.
            geom_ptr = lgeos.GEOSGetGeometryN(self._ptr(), c_int(i))

            # Adding the coordinate sequence to the list, or using None if the
            #  collection Geometry doesn't support coordinate sequences.
            if lgeos.GEOSGeomTypeId(geom_ptr) in (0, 1, 2):
                ptr_list.append((geom_ptr, lgeos.GEOSGeom_getCoordSeq(geom_ptr)))
            else:
                ptr_list.append((geom_ptr, None))
        self._ptr.set_children(ptr_list)

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
