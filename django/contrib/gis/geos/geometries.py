from ctypes import c_double, c_int, c_uint
from types import FloatType, IntType, ListType, TupleType
from django.contrib.gis.geos.coordseq import GEOSCoordSeq, create_cs
from django.contrib.gis.geos.libgeos import lgeos, GEOSPointer, HAS_NUMPY
from django.contrib.gis.geos.base import GEOSGeometry
from django.contrib.gis.geos.error import GEOSException

if HAS_NUMPY:
    from numpy import ndarray, array

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

    ### Tuple setting and retrieval routines. ###
    def get_tuple(self):
        "Returns a tuple of the point."
        self._cache_cs()
        return self._cs.tuple

    def set_tuple(self):
        "Sets the tuple for this point object."
        pass

    # The tuple property
    tuple = property(get_tuple, set_tuple)

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

