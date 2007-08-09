"""
  This module houses the Point, LineString, LinearRing, and Polygon OGC
   geometry classes.  All geometry classes in this module inherit from 
   GEOSGeometry.
"""

from ctypes import c_double, c_int, c_uint, byref, cast
from types import FloatType, IntType, ListType, TupleType
from django.contrib.gis.geos.coordseq import GEOSCoordSeq, create_cs
from django.contrib.gis.geos.libgeos import lgeos, GEOSPointer, get_pointer_arr, GEOM_PTR, HAS_NUMPY
from django.contrib.gis.geos.base import GEOSGeometry
from django.contrib.gis.geos.error import GEOSException, GEOSGeometryIndexError
if HAS_NUMPY: from numpy import ndarray, array

class Point(GEOSGeometry):

    def __init__(self, x, y=None, z=None, srid=None):
        """The Point object may be initialized with either a tuple, or individual
        parameters.  For example:
          >>> p = Point((5, 23)) # 2D point, passed in as a tuple
          >>> p = Point(5, 23, 8) # 3D point, passed in with individual parameters
        """

        # Setting-up for Point Creation
        self._ptr = GEOSPointer(0) # Initially NULL
        self._parent = None

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
        super(Point, self).__init__(lgeos.GEOSGeom_createPoint(cs), srid=srid)

    def __len__(self):
        "Returns the number of dimensions for this Point (either 2 or 3)."
        if self.hasz: return 3
        else: return 2
        
    def _getOrdinate(self, dim, idx):
        "The coordinate sequence getOrdinate() wrapper."
        return self._cs.getOrdinate(dim, idx)

    def _setOrdinate(self, dim, idx, value):
        "The coordinate sequence setOrdinate() wrapper."
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

    ### Tuple setting and retrieval routines. ###
    def get_coords(self):
        "Returns a tuple of the point."
        return self._cs.tuple

    def set_coords(self, tup):
        "Sets the coordinates of the point with the given tuple."
        self._cs[0] = tup
    
    # The tuple and coords properties
    tuple = property(get_coords, set_coords)
    coords = property(get_coords, set_coords)

class LineString(GEOSGeometry):

    #### Python 'magic' routines ####
    def __init__(self, *args, **kwargs):
        """Initializes on the given sequence -- may take lists, tuples, NumPy arrays
        of X,Y pairs, or Point objects.  If Point objects are used, ownership is
        _not_ transferred to the LineString object.

        Examples:
          ls = LineString((1, 1), (2, 2))
          ls = LineString([(1, 1), (2, 2)])
          ls = LineString(array([(1, 1), (2, 2)]))
          ls = LineString(Point(1, 1), Point(2, 2))
        """
        # Setting up for LineString creation
        self._ptr = GEOSPointer(0) # Initially NULL
        self._parent = None

        # If only one argument was provided, then set the coords array appropriately
        if len(args) == 1: coords = args[0]
        else: coords = args

        if isinstance(coords, (TupleType, ListType)):
            # Getting the number of coords and the number of dimensions -- which
            #  must stay the same, e.g., no LineString((1, 2), (1, 2, 3)).
            ncoords = len(coords)
            if coords: ndim = len(coords[0])
            else: raise TypeError, 'Cannot initialize on empty sequence.'
            self._checkdim(ndim)
            # Incrementing through each of the coordinates and verifying
            for i in xrange(1, ncoords):
                if not isinstance(coords[i], (TupleType, ListType, Point)):
                    raise TypeError, 'each coordinate should be a sequence (list or tuple)'
                if len(coords[i]) != ndim: raise TypeError, 'Dimension mismatch.'
            numpy_coords = False
        elif HAS_NUMPY and isinstance(coords, ndarray):
            shape = coords.shape # Using numpy's shape.
            if len(shape) != 2: raise TypeError, 'Too many dimensions.'
            self._checkdim(shape[1])
            ncoords = shape[0]
            ndim = shape[1]
            numpy_coords = True
        else:
            raise TypeError, 'Invalid initialization input for LineStrings.'

        # Creating the coordinate sequence
        cs = GEOSCoordSeq(GEOSPointer(0, create_cs(c_uint(ncoords), c_uint(ndim))), z=bool(ndim==3))

        # Setting each point in the coordinate sequence
        for i in xrange(ncoords):
            if numpy_coords: cs[i] = coords[i,:]
            elif isinstance(coords[i], Point): cs[i] = coords[i].tuple
            else: cs[i] = coords[i]        

        # Getting the initialization function
        if kwargs.get('ring', False):
            func = lgeos.GEOSGeom_createLinearRing
        else:
            func = lgeos.GEOSGeom_createLineString

        # If SRID was passed in with the keyword arguments
        srid = kwargs.get('srid', None)
       
        # Calling the base geometry initialization with the returned pointer from the function.
        super(LineString, self).__init__(func(cs._ptr.coordseq()), srid=srid)

    def __getitem__(self, index):
        "Gets the point at the specified index."
        return self._cs[index]

    def __setitem__(self, index, value):
        "Sets the point at the specified index, e.g., line_str[0] = (1, 2)."
        self._cs[index] = value

    def __iter__(self):
        "Allows iteration over this LineString."
        for i in xrange(self.__len__()):
            yield self.__getitem__(i)

    def __len__(self):
        "Returns the number of points in this LineString."
        return len(self._cs)

    def _checkdim(self, dim):
        if dim not in (2, 3): raise TypeError, 'Dimension mismatch.'

    #### Sequence Properties ####
    @property
    def tuple(self):
        "Returns a tuple version of the geometry from the coordinate sequence."
        return self._cs.tuple

    def _listarr(self, func):
        """Internal routine that returns a sequence (list) corresponding with
        the given function.  Will return a numpy array if possible."""
        lst = [func(i) for i in xrange(len(self))] # constructing the list, using the function
        if HAS_NUMPY: return array(lst) # ARRRR!
        else: return lst

    @property
    def array(self):
        "Returns a numpy array for the LineString."
        return self._listarr(self._cs.__getitem__)

    @property
    def x(self):
        "Returns a list or numpy array of the X variable."
        return self._listarr(self._cs.getX)
    
    @property
    def y(self):
        "Returns a list or numpy array of the Y variable."
        return self._listarr(self._cs.getY)

    @property
    def z(self):
        "Returns a list or numpy array of the Z variable."
        if not self.hasz: return None
        else: return self._listarr(self._cs.getZ)

# LinearRings are LineStrings used within Polygons.
class LinearRing(LineString):
    def __init__(self, *args, **kwargs):
        "Overriding the initialization function to set the ring keyword."
        kwargs['ring'] = True # Setting the ring keyword argument to True
        super(LinearRing, self).__init__(*args, **kwargs)

class Polygon(GEOSGeometry):

    def __init__(self, *args, **kwargs):
        """Initializes on an exterior ring and a sequence of holes (both instances of LinearRings.
        All LinearRing instances used for creation will become owned by this Polygon.
        
        Examples, where shell, hole1, and hole2 are valid LinearRing geometries:
          poly = Polygon(shell, hole1, hole2)
          poly = Polygon(shell, (hole1, hole2))
        """
        self._ptr = GEOSPointer(0) # Initially NULL
        self._parent = None
        self._rings = {} 
        if not args:
            raise TypeError, 'Must provide at list one LinearRing instance to initialize Polygon.'

        # Getting the ext_ring and init_holes parameters from the argument list
        ext_ring = args[0]
        init_holes = args[1:]
        if len(init_holes) == 1 and isinstance(init_holes[0], (TupleType, ListType)): 
            init_holes = init_holes[0]

        # Ensuring the exterior ring parameter is a LinearRing object
        if not isinstance(ext_ring, LinearRing):
            raise TypeError, 'First argument for Polygon initialization must be a LinearRing.'

        # Making sure all of the holes are LinearRing objects
        if False in [isinstance(hole, LinearRing) for hole in init_holes]:
            raise TypeError, 'Holes parameter must be a sequence of LinearRings.'

        # Getting the holes
        nholes = len(init_holes)
        holes = get_pointer_arr(nholes)
        for i in xrange(nholes):
            # Casting to the Geometry Pointer type
            holes[i] = cast(init_holes[i]._nullify(), GEOM_PTR)
                      
        # Getting the shell pointer address, 
        shell = ext_ring._nullify()

        # Calling with the GEOS createPolygon factory.
        super(Polygon, self).__init__(lgeos.GEOSGeom_createPolygon(shell, byref(holes), c_uint(nholes)), **kwargs)

    def __del__(self):
        "Overloaded deletion method for Polygons."
        #print 'polygon: Deleting %s (parent=%s, valid=%s)' % (self.__class__.__name__, self._parent, self._ptr.valid)
        # If this geometry is still valid, it hasn't been modified by others.
        if self._ptr.valid:
            # Nulling the pointers to internal rings, preventing any attempted future access
            for k in self._rings: self._rings[k].nullify()
        elif not self._parent: 
            # Internal memory has become part of other objects; must delete the 
            #  internal objects which are still valid individually, since calling
            #  destructor on entire geometry will result in an attempted deletion 
            #  of NULL pointers for the missing components.  Not performed on
            #  children Polygons from MultiPolygon or GeometryCollection objects.
            for k in self._rings:
                if self._rings[k].valid:
                    lgeos.GEOSGeom_destroy(self._rings[k].address)
                    self._rings[k].nullify()
        super(Polygon, self).__del__()

    def __getitem__(self, index):
        """Returns the ring at the specified index.  The first index, 0, will always
        return the exterior ring.  Indices > 0 will return the interior ring."""
        if index == 0:
            return self.exterior_ring
        else:
            # Getting the interior ring, have to subtract 1 from the index.
            return self.get_interior_ring(index-1) 

    def __setitem__(self, index, ring):
        "Sets the ring at the specified index with the given ring."
        # Checking the index and ring parameters.
        self._checkindex(index)
        if not isinstance(ring, LinearRing):
            raise TypeError, 'must set Polygon index with a LinearRing object'

        # Constructing the ring parameters
        new_rings = []
        for i in xrange(len(self)):
            if index == i: new_rings.append(ring)
            else: new_rings.append(self[i])

        # Constructing the new Polygon with the ring parameters, and reassigning the internals.
        new_poly = Polygon(*new_rings, **{'srid':self.srid})
        self._reassign(new_poly)

    def __iter__(self):
        "Iterates over each ring in the polygon."
        for i in xrange(len(self)):
            yield self.__getitem__(i)

    def __len__(self):
        "Returns the number of rings in this Polygon."
        return self.num_interior_rings + 1

    def _checkindex(self, index):
        "Internal routine for checking the given ring index."
        if index < 0 or index >= len(self):
            raise GEOSGeometryIndexError, 'invalid Polygon ring index: %s' % index

    def _nullify(self):
        "Overloaded from base method to nullify ring references as well."
        # Nullifying the references to the internal rings of this Polygon.
        for k in self._rings: self._rings[k].nullify()
        return super(Polygon, self)._nullify()

    def _populate(self):
        "Populates the internal rings dictionary."
        # Getting the exterior ring first for the 0th index.
        self._rings = {0 : GEOSPointer(lgeos.GEOSGetExteriorRing(self._ptr()))}

        # Getting the interior rings.
        for i in xrange(self.num_interior_rings):
            self._rings[i+1] = GEOSPointer(lgeos.GEOSGetInteriorRingN(self._ptr(), c_int(i)))

    def get_interior_ring(self, ring_i):
        """Gets the interior ring at the specified index,
        0 is for the first interior ring, not the exterior ring."""
        # Returning the ring from the internal ring dictionary (have to add one
        #   to index since all internal rings come after the exterior ring)
        self._checkindex(ring_i+1)
        return GEOSGeometry(self._rings[ring_i+1], parent=self._ptr, srid=self.srid)
                                                        
    #### Polygon Properties ####
    @property
    def num_interior_rings(self):
        "Returns the number of interior rings."

        # Getting the number of rings
        n = lgeos.GEOSGetNumInteriorRings(self._ptr())

        # -1 indicates an exception occurred
        if n == -1: raise GEOSException, 'Error getting the number of interior rings.'
        else: return n

    def get_ext_ring(self):
        "Gets the exterior ring of the Polygon."
        return GEOSGeometry(self._rings[0], parent=self._ptr, srid=self.srid)

    def set_ext_ring(self, ring):
        "Sets the exterior ring of the Polygon."
        self[0] = ring

    # properties for the exterior ring/shell
    exterior_ring = property(get_ext_ring, set_ext_ring)
    shell = property(get_ext_ring, set_ext_ring)
    
    @property
    def tuple(self):
        "Gets the tuple for each ring in this Polygon."
        return tuple(self.__getitem__(i).tuple for i in xrange(self.__len__()))

    @property
    def kml(self):
        "Returns the KML representation of this Polygon."
        inner_kml = ''
        if self.num_interior_rings > 0: 
            for i in xrange(self.num_interior_rings):
                inner_kml += "<innerBoundaryIs>%s</innerBoundaryIs>" % self[i+1].kml
        return "<Polygon><outerBoundaryIs>%s</outerBoundaryIs>%s</Polygon>" % (self[0].kml, inner_kml)
