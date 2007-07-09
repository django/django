# Trying not to pollute the namespace.
from ctypes import \
     byref, string_at, create_string_buffer, pointer, \
     c_char_p, c_double, c_float, c_int, c_uint, c_size_t
from types import StringType, IntType, FloatType, TupleType, ListType

# Getting GEOS-related dependencies.
from django.contrib.gis.geos.libgeos import lgeos, GEOSPointer, HAS_NUMPY
from django.contrib.gis.geos.GEOSError import GEOSException
from django.contrib.gis.geos.GEOSCoordSeq import GEOSCoordSeq, create_cs

if HAS_NUMPY:
    from numpy import ndarray, array

class GEOSGeometry(object):
    "A class that, generally, encapsulates a GEOS geometry."
    
    #### Python 'magic' routines ####
    def __init__(self, geo_input, input_type='wkt', child=False):
        """The constructor for GEOS geometry objects.  May take the following
        strings as inputs, WKT ("wkt"), HEXEWKB ("hex", PostGIS-specific canonical form).

        When a hex string is to be used, the `input_type` keyword should be set with 'hex'.

        The `child` keyword is for internal use only, and indicates to the garbage collector
          not to delete this geometry if it was spawned from a parent (e.g., the exterior
          ring from a polygon).
        """

        # Initially, setting the pointer to NULL
        self._ptr = GEOSPointer(0)

        if isinstance(geo_input, StringType):
            if input_type == 'wkt':
                # If the geometry is in WKT form
                g = lgeos.GEOSGeomFromWKT(c_char_p(geo_input))
            elif input_type == 'hex':
                # If the geometry is in HEX form.
                sz = c_size_t(len(geo_input))
                buf = create_string_buffer(geo_input)
                g = lgeos.GEOSGeomFromHEX_buf(buf, sz)
            else:
                raise TypeError, 'GEOS input geometry type "%s" not supported.' % input_type
        elif isinstance(geo_input, (IntType, GEOSPointer)):
            # When the input is either a raw pointer value (an integer), or a GEOSPointer object.
            g = geo_input
        else:
            # Invalid geometry type.
            raise TypeError, 'Improper geometry input type: %s' % str(type(geo_input))

        if bool(g):
            # If we have a GEOSPointer object, just set the '_ptr' attribute with g
            if isinstance(g, GEOSPointer): self._ptr = g
            else: self._ptr.set(g) # Otherwise, set the address
        else:
            raise GEOSException, 'Could not initialize GEOS Geometry with given input.'

        # Setting the 'child' flag -- when the object is labeled with this flag
        #  it will not be destroyed by __del__().  This is used for child geometries from
        #  parent geometries (e.g., LinearRings from a Polygon, Points from a MultiPoint, etc.).
        self._child = child

        # Setting the class type (e.g., 'Point', 'Polygon', etc.)
        self.__class__ = GEOS_CLASSES[self.geom_type]

        # Extra setup needed for Geometries that may be parents.
        if isinstance(self, GeometryCollection): self._geoms = {}
        if isinstance(self, Polygon): self._rings = {}

    def __del__(self):
        "Destroys this geometry -- only if the pointer is valid and this is not a child geometry."
        #print 'Deleting %s (child=%s, valid=%s)' % (self.geom_type, self._child, self._ptr.valid)
        if self._ptr.valid and not self._child: lgeos.GEOSGeom_destroy(self._ptr())

    def __str__(self):
        "WKT is used for the string representation."
        return self.wkt

    def __eq__(self, other):
        "Equivalence testing."
        return self.equals(other)

    #### Coordinate Sequence Routines ####
    def _cache_cs(self):
        "Caches the coordinate sequence for this Geometry."
        if not hasattr(self, '_cs'):
            # Only these geometries are allowed to have coordinate sequences.
            if self.geom_type in ('LineString', 'LinearRing', 'Point'):
                self._cs = GEOSCoordSeq(GEOSPointer(lgeos.GEOSGeom_getCoordSeq(self._ptr())), self.hasz)
            else:
                self._cs = None

    @property
    def coord_seq(self):
        "Returns the coordinate sequence for the geometry."
        # Getting the coordinate sequence for the geometry
        self._cache_cs()

        # Returning a GEOSCoordSeq wrapped around the pointer.
        return self._cs

    #### Geometry Info ####
    @property
    def geom_type(self):
        "Returns a string representing the geometry type, e.g. 'Polygon'"
        return string_at(lgeos.GEOSGeomType(self._ptr()))

    @property
    def geom_typeid(self):
        "Returns an integer representing the geometry type."
        return lgeos.GEOSGeomTypeId(self._ptr())

    @property
    def num_geom(self):
        "Returns the number of geometries in the geometry."
        n = lgeos.GEOSGetNumGeometries(self._ptr())
        if n == -1: raise GEOSException, 'Error getting number of geometries.'
        else: return n

    @property
    def num_coords(self):
        "Returns the number of coordinates in the geometry."
        n = lgeos.GEOSGetNumCoordinates(self._ptr())
        if n == -1: raise GEOSException, 'Error getting number of coordinates.'
        else: return n

    @property
    def num_points(self):
        "Returns the number points, or coordinates, in the geometry."
        return self.num_coords

    @property
    def dims(self):
        "Returns the dimension of this Geometry (0=point, 1=line, 2=surface)."
        return lgeos.GEOSGeom_getDimensions(self._ptr())

    def normalize(self):
        "Converts this Geometry to normal form (or canonical form)."
        status = lgeos.GEOSNormalize(self._ptr())
        if status == -1: raise GEOSException, 'failed to normalize geometry'

    def _unary_predicate(self, func):
        "Returns the result, or raises an exception for the given unary predicate function."
        val = func(self._ptr())
        if val == 0: return False
        elif val == 1: return True
        else: raise GEOSException, '%s: exception occurred.' % func.__name__

    def _binary_predicate(self, func, other, *args):
        "Returns the result, or raises an exception for the given binary predicate function."
        if not isinstance(other, GEOSGeometry):
            raise TypeError, 'Binary predicate operation ("%s") requires another GEOSGeometry instance.' % func.__name__
        val = func(self._ptr(), other._ptr(), *args)
        if val == 0: return False
        elif val == 1: return True
        else: raise GEOSException, '%s: exception occurred.' % func.__name__

    #### Unary predicates ####
    @property
    def empty(self):
        "Returns a boolean indicating whether the set of points in this geometry are empty."
        return self._unary_predicate(lgeos.GEOSisEmpty)

    @property
    def valid(self):
        "This property tests the validity of this geometry."
        return self._unary_predicate(lgeos.GEOSisValid)

    @property
    def simple(self):
        "Returns false if the Geometry not simple."
        return self._unary_predicate(lgeos.GEOSisSimple)

    @property
    def ring(self):
        "Returns whether or not the geometry is a ring."
        return self._unary_predicate(lgeos.GEOSisRing)

    @property
    def hasz(self):
        "Returns whether the geometry has a 3D dimension."
        return self._unary_predicate(lgeos.GEOSHasZ)

    #### Binary predicates. ####
    def relate_pattern(self, other, pattern):
        """Returns true if the elements in the DE-9IM intersection matrix for
        the two Geometrys match the elements in pattern."""
        if len(pattern) > 9:
            raise GEOSException, 'invalid intersection matrix pattern'
        return self._binary_predicate(lgeos.GEOSRelatePattern, other, c_char_p(pattern))

    def disjoint(self, other):
        "Returns true if the DE-9IM intersection matrix for the two Geometrys is FF*FF****."
        return self._binary_predicate(lgeos.GEOSDisjoint, other)

    def touches(self, other):
        "Returns true if the DE-9IM intersection matrix for the two Geometrys is FT*******, F**T***** or F***T****."
        return self._binary_predicate(lgeos.GEOSTouches, other)

    def intersects(self, other):
        "Returns true if disjoint returns false."
        return self._binary_predicate(lgeos.GEOSIntersects, other)

    def crosses(self, other):
        """Returns true if the DE-9IM intersection matrix for the two Geometrys is T*T****** (for a point and a curve,
        a point and an area or a line and an area) 0******** (for two curves)."""
        return self._binary_predicate(lgeos.GEOSCrosses, other)

    def within(self, other):
        "Returns true if the DE-9IM intersection matrix for the two Geometrys is T*F**F***."
        return self._binary_predicate(lgeos.GEOSWithin, other)

    def contains(self, other):
        "Returns true if other.within(this) returns true."
        return self._binary_predicate(lgeos.GEOSContains, other)

    def overlaps(self, other):
        """Returns true if the DE-9IM intersection matrix for the two Geometrys is T*T***T** (for two points
        or two surfaces) 1*T***T** (for two curves)."""
        return self._binary_predicate(lgeos.GEOSOverlaps, other)

    def equals(self, other):
        "Returns true if the DE-9IM intersection matrix for the two Geometrys is T*F**FFF*."
        return self._binary_predicate(lgeos.GEOSEquals, other)

    def equals_exact(self, other, tolerance=0):
        "Returns true if the two Geometrys are exactly equal, up to a specified tolerance."
        tol = c_double(tolerance)
        return self._binary_predicate(lgeos.GEOSEqualsExact, other, tol)

    #### SRID Routines ####
    @property
    def srid(self):
        "Gets the SRID for the geometry, returns None if no SRID is set."
        s = lgeos.GEOSGetSRID(self._ptr())
        if s == 0:
            return None
        else:
            return s

    def set_srid(self, srid):
        "Sets the SRID for the geometry."
        lgeos.GEOSSetSRID(self._ptr(), c_int(srid))
    
    #### Output Routines ####
    @property
    def wkt(self):
        "Returns the WKT of the Geometry."
        return string_at(lgeos.GEOSGeomToWKT(self._ptr()))

    @property
    def hex(self):
        "Returns the WKBHEX of the Geometry."
        sz = c_size_t()
        h = lgeos.GEOSGeomToHEX_buf(self._ptr(), byref(sz))
        return string_at(h, sz.value)

    #### Topology Routines ####
    def _unary_topology(self, func, *args):
        "Returns a GEOSGeometry for the given unary (only takes one geomtry as a paramter) topological operation."
        return GEOSGeometry(func(self._ptr(), *args))

    def _binary_topology(self, func, other, *args):
        "Returns a GEOSGeometry for the given binary (takes two geometries as parameters) topological operation."
        return GEOSGeometry(func(self._ptr(), other._ptr(), *args))

    def buffer(self, width, quadsegs=8):
        """Returns a geometry that represents all points whose distance from this
        Geometry is less than or equal to distance. Calculations are in the
        Spatial Reference System of this Geometry. The optional third parameter sets
        the number of segment used to approximate a quarter circle (defaults to 8).
        (Text from PostGIS documentation at ch. 6.1.3)
        """
        if not isinstance(width, (FloatType, IntType)):
            raise TypeError, 'width parameter must be a float'
        if not isinstance(quadsegs, IntType):
            raise TypeError, 'quadsegs parameter must be an integer'
        return self._unary_topology(lgeos.GEOSBuffer, c_double(width), c_int(quadsegs))

    @property
    def envelope(self):
        "Return the envelope for this geometry (a polygon)."
        return self._unary_topology(lgeos.GEOSEnvelope)

    @property
    def centroid(self):
        """The centroid is equal to the centroid of the set of component Geometrys
        of highest dimension (since the lower-dimension geometries contribute zero
        "weight" to the centroid)."""
        return self._unary_topology(lgeos.GEOSGetCentroid)

    @property
    def boundary(self):
        "Returns the boundary as a newly allocated Geometry object."
        return self._unary_topology(lgeos.GEOSBoundary)

    @property
    def convex_hull(self):
        "Returns the smallest convex Polygon that contains all the points in the Geometry."
        return self._unary_topology(lgeos.GEOSConvexHull)

    @property
    def point_on_surface(self):
        "Computes an interior point of this Geometry."
        return self._unary_topology(lgeos.GEOSPointOnSurface)

    def relate(self, other):
        "Returns the DE-9IM intersection matrix for this geometry and the other."
        return string_at(lgeos.GEOSRelate(self._ptr(), other._ptr()))

    def difference(self, other):
        """Returns a Geometry representing the points making up this Geometry
        that do not make up other."""
        return self._binary_topology(lgeos.GEOSDifference, other)

    def sym_difference(self, other):
        """Returns a set combining the points in this Geometry not in other,
        and the points in other not in this Geometry."""
        return self._binary_topology(lgeos.GEOSSymDifference, other)

    def intersection(self, other):
        "Returns a Geometry representing the points shared by this Geometry and other."
        return self._binary_topology(lgeos.GEOSIntersection, other)

    def union(self, other):
        "Returns a Geometry representing all the points in this Geometry and other."
        return self._binary_topology(lgeos.GEOSUnion, other)

    #### Other Routines ####
    @property
    def area(self):
        "Returns the area of the Geometry."
        a = c_double()
        status = lgeos.GEOSArea(self._ptr(), byref(a))
        if not status: return None
        else: return a.value

    def clone(self):
        "Clones this Geometry."
        return GEOSGeometry(lgeos.GEOSGeom_clone(self._ptr()))
    
class Point(GEOSGeometry):

    def __init__(self, x, y=None, z=None):
        """The Point object may be initialized with either a tuple, or individual
        parameters.  For example:
          >>> p = Point((5, 23)) # 2D point, passed in as a tuple
          >>> p = Point(5, 23, 8) # 3D point, passed in with individual parameters
        """
        
        if isinstance(x, (TupleType, ListType)):
            # Here a tuple or list was passed in under the ``x`` parameter.
            ndim = len(x)
            if ndim < 2 or ndim > 3:
                raise TypeError, 'Invalid sequence parameter: %s' % str(x)
            coords = x
        elif isinstance(x, (IntType, FloatType)) and isinstance(y, (IntType, FloatType)):
            # Here X, Y, and (optionally) Z were passed in individually as parameters.
            if isinstance(z, (IntType, FloatType)):
                ndim = 3
                coords = [x, y, z]
            else:
                ndim = 2
                coords = [x, y]
        else:
            raise TypeError, 'Invalid parameters given for Point initialization.'

        # Creating the coordinate sequence
        cs = create_cs(c_uint(1), c_uint(ndim))

        # Setting the X
        status = lgeos.GEOSCoordSeq_setX(cs, c_uint(0), c_double(coords[0]))
        if not status: raise GEOSException, 'Could not set X during Point initialization.'

        # Setting the Y
        status = lgeos.GEOSCoordSeq_setY(cs, c_uint(0), c_double(coords[1]))
        if not status: raise GEOSException, 'Could not set Y during Point initialization.'

        # Setting the Z
        if ndim == 3:
            status = lgeos.GEOSCoordSeq_setZ(cs, c_uint(0), c_double(coords[2]))

        # Initializing from the geometry, and getting a Python object
        super(Point, self).__init__(lgeos.GEOSGeom_createPoint(cs))

    def _getOrdinate(self, dim, idx):
        "The coordinate sequence getOrdinate() wrapper."
        self._cache_cs()
        return self._cs.getOrdinate(dim, idx)

    def _setOrdinate(self, dim, idx, value):
        "The coordinate sequence setOrdinate() wrapper."
        self._cache_cs()
        self._cs.setOrdinate(dim, idx, value)

    def get_x(self):
        "Returns the X component of the Point."
        return self._getOrdinate(0, 0)

    def set_x(self, value):
        "Sets the X component of the Point."
        self._setOrdinate(0, 0, value)

    def get_y(self):
        "Returns the Y component of the Point."
        return self._getOrdinate(1, 0)

    def set_y(self, value):
        "Sets the Y component of the Point."
        self._setOrdinate(1, 0, value)

    def get_z(self):
        "Returns the Z component of the Point."
        if self.hasz:
            return self._getOrdinate(2, 0)
        else:
            return None

    def set_z(self, value):
        "Sets the Z component of the Point."
        if self.hasz:
            self._setOrdinate(2, 0, value)
        else:
            raise GEOSException, 'Cannot set Z on 2D Point.'
    
    # X, Y, Z properties
    x = property(get_x, set_x)
    y = property(get_y, set_y)
    z = property(get_z, set_z)

    @property
    def tuple(self):
        "Returns a tuple of the point."
        self._cache_cs()
        return self._cs.tuple

class LineString(GEOSGeometry):

    #### Python 'magic' routines ####
    def __init__(self, coords, ring=False):
        """Initializes on the given sequence, may take lists, tuples, or NumPy arrays
        of X,Y pairs."""

        if isinstance(coords, (TupleType, ListType)):
            ncoords = len(coords)
            first = True
            for coord in coords:
                if not isinstance(coord, (TupleType, ListType)):
                    raise TypeError, 'each coordinate should be a sequence (list or tuple)'
                if first:
                    ndim = len(coord)
                    self._checkdim(ndim)
                    first = False
                else:
                    if len(coord) != ndim: raise TypeError, 'Dimension mismatch.'
            numpy_coords = False
        elif HAS_NUMPY and isinstance(coords, ndarray):
            shape = coords.shape
            if len(shape) != 2: raise TypeError, 'Too many dimensions.'
            self._checkdim(shape[1])
            ncoords = shape[0]
            ndim = shape[1]
            numpy_coords = True
        else:
            raise TypeError, 'Invalid initialization input for LineStrings.'

        # Creating the coordinate sequence
        cs = GEOSCoordSeq(GEOSPointer(create_cs(c_uint(ncoords), c_uint(ndim))))

        # Setting each point in the coordinate sequence
        for i in xrange(ncoords):
            if numpy_coords: cs[i] = coords[i,:]
            else: cs[i] = coords[i]        

        # Getting the initialization function
        if ring:
            func = lgeos.GEOSGeom_createLinearRing
        else:
            func = lgeos.GEOSGeom_createLineString
       
        # Calling the base geometry initialization with the returned pointer from the function.
        super(LineString, self).__init__(func(cs._ptr()))

    def __getitem__(self, index):
        "Gets the point at the specified index."
        self._cache_cs()
        return self._cs[index]

    def __setitem__(self, index, value):
        "Sets the point at the specified index, e.g., line_str[0] = (1, 2)."
        self._cache_cs()
        self._cs[index] = value

    def __iter__(self):
        "Allows iteration over this LineString."
        for i in xrange(self.__len__()):
            yield self.__getitem__(index)

    def __len__(self):
        "Returns the number of points in this LineString."
        self._cache_cs()
        return len(self._cs)

    def _checkdim(self, dim):
        if dim not in (2, 3): raise TypeError, 'Dimension mismatch.'

    #### Sequence Properties ####
    @property
    def tuple(self):
        "Returns a tuple version of the geometry from the coordinate sequence."
        self._cache_cs()
        return self._cs.tuple

    def _listarr(self, func):
        """Internal routine that returns a sequence (list) corresponding with
        the given function.  Will return a numpy array if possible."""
        lst = [func(i) for i in xrange(self.__len__())] # constructing the list, using the function
        if HAS_NUMPY: return array(lst) # ARRRR!
        else: return lst

    @property
    def array(self):
        "Returns a numpy array for the LineString."
        self._cache_cs()
        return self._listarr(self._cs.__getitem__)

    @property
    def x(self):
        "Returns a list or numpy array of the X variable."
        self._cache_cs()
        return self._listarr(self._cs.getX)
    
    @property
    def y(self):
        "Returns a list or numpy array of the Y variable."
        self._cache_cs()
        return self._listarr(self._cs.getY)

    @property
    def z(self):
        "Returns a list or numpy array of the Z variable."
        self._cache_cs()
        if not self.hasz: return None
        else: return self._listarr(self._cs.getZ)

# LinearRings are LineStrings used within Polygons.
class LinearRing(LineString):
    def __init__(self, coords):
        "Overriding the initialization function to set the ring keyword."
        super(LinearRing, self).__init__(coords, ring=True)

class Polygon(GEOSGeometry):

    def __del__(self):
        "Override the GEOSGeometry delete routine to safely take care of any spawned rings."
        # Nullifying the pointers to internal rings, preventing any attempted future access
        for k in self._rings: self._rings[k].nullify()
        super(Polygon, self).__del__() # Calling the parent __del__() method.
    
    def __getitem__(self, index):
        """Returns the ring at the specified index.  The first index, 0, will always
        return the exterior ring.  Indices > 0 will return the interior ring."""
        if index < 0 or index > self.num_interior_rings:
            raise GEOSGeometryIndexError, 'invalid GEOS Geometry index: %s' % str(index)
        else:
            if index == 0:
                return self.exterior_ring
            else:
                # Getting the interior ring, have to subtract 1 from the index.
                return self.get_interior_ring(index-1) 

    def __iter__(self):
        "Iterates over each ring in the polygon."
        for i in xrange(self.__len__()):
            yield self.__getitem__(i)

    def __len__(self):
        "Returns the number of rings in this Polygon."
        return self.num_interior_rings + 1

    def get_interior_ring(self, ring_i):
        """Gets the interior ring at the specified index,
        0 is for the first interior ring, not the exterior ring."""

        # Making sure the ring index is within range
        if ring_i < 0 or ring_i >= self.num_interior_rings:
            raise IndexError, 'ring index out of range'

        # Placing the ring in internal rings dictionary.
        idx = ring_i+1 # the index for the polygon is +1 because of the exterior ring
        if not idx in self._rings:
            self._rings[idx] = GEOSPointer(lgeos.GEOSGetInteriorRingN(self._ptr(), c_int(ring_i)))

        # Returning the ring at the given index.
        return GEOSGeometry(self._rings[idx], child=True)
                                                        
    #### Polygon Properties ####
    @property
    def num_interior_rings(self):
        "Returns the number of interior rings."

        # Getting the number of rings
        n = lgeos.GEOSGetNumInteriorRings(self._ptr())

        # -1 indicates an exception occurred
        if n == -1: raise GEOSException, 'Error getting the number of interior rings.'
        else: return n

    @property
    def exterior_ring(self):
        "Gets the exterior ring of the Polygon."
        # Returns exterior ring 
        self._rings[0] = GEOSPointer(lgeos.GEOSGetExteriorRing((self._ptr())))
        return GEOSGeometry(self._rings[0], child=True)

    @property
    def shell(self):
        "Gets the shell (exterior ring) of the Polygon."
        return self.exterior_ring
    
    @property
    def tuple(self):
        "Gets the tuple for each ring in this Polygon."
        return tuple(self.__getitem__(i).tuple for i in xrange(self.__len__()))

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

# Class mapping dictionary
GEOS_CLASSES = {'Point' : Point,
                'Polygon' : Polygon,
                'LineString' : LineString,
                'LinearRing' : LinearRing,
                'GeometryCollection' : GeometryCollection,
                'MultiPoint' : MultiPoint,
                'MultiLineString' : MultiLineString,
                'MultiPolygon' : MultiPolygon,
                }
