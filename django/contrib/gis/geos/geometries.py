"""
 This module houses the Point, LineString, LinearRing, and Polygon OGC
 geometry classes.  All geometry classes in this module inherit from 
 GEOSGeometry.
"""
from ctypes import c_uint, byref
from django.contrib.gis.geos.base import GEOSGeometry
from django.contrib.gis.geos.coordseq import GEOSCoordSeq
from django.contrib.gis.geos.error import GEOSException, GEOSIndexError
from django.contrib.gis.geos.libgeos import get_pointer_arr, GEOM_PTR, HAS_NUMPY
from django.contrib.gis.geos.prototypes import *
if HAS_NUMPY: from numpy import ndarray, array

class Point(GEOSGeometry):

    def __init__(self, x, y=None, z=None, srid=None):
        """
        The Point object may be initialized with either a tuple, or individual
        parameters.
        
        For Example:
        >>> p = Point((5, 23)) # 2D point, passed in as a tuple
        >>> p = Point(5, 23, 8) # 3D point, passed in with individual parameters
        """

        if isinstance(x, (tuple, list)):
            # Here a tuple or list was passed in under the `x` parameter.
            ndim = len(x)
            if ndim < 2 or ndim > 3:
                raise TypeError('Invalid sequence parameter: %s' % str(x))
            coords = x
        elif isinstance(x, (int, float, long)) and isinstance(y, (int, float, long)):
            # Here X, Y, and (optionally) Z were passed in individually, as parameters.
            if isinstance(z, (int, float, long)):
                ndim = 3
                coords = [x, y, z]
            else:
                ndim = 2
                coords = [x, y]
        else:
            raise TypeError('Invalid parameters given for Point initialization.')

        # Creating the coordinate sequence, and setting X, Y, [Z]
        cs = create_cs(c_uint(1), c_uint(ndim))
        cs_setx(cs, 0, coords[0])
        cs_sety(cs, 0, coords[1])
        if ndim == 3: cs_setz(cs, 0, coords[2])

        # Initializing using the address returned from the GEOS 
        #  createPoint factory.
        super(Point, self).__init__(create_point(cs), srid=srid)

    def __len__(self):
        "Returns the number of dimensions for this Point (either 0, 2 or 3)."
        if self.empty: return 0
        if self.hasz: return 3
        else: return 2
        
    def get_x(self):
        "Returns the X component of the Point."
        return self._cs.getOrdinate(0, 0)

    def set_x(self, value):
        "Sets the X component of the Point."
        self._cs.setOrdinate(0, 0, value)

    def get_y(self):
        "Returns the Y component of the Point."
        return self._cs.getOrdinate(1, 0)

    def set_y(self, value):
        "Sets the Y component of the Point."
        self._cs.setOrdinate(1, 0, value)

    def get_z(self):
        "Returns the Z component of the Point."
        if self.hasz:
            return self._cs.getOrdinate(2, 0)
        else:
            return None

    def set_z(self, value):
        "Sets the Z component of the Point."
        if self.hasz:
            self._cs.setOrdinate(2, 0, value)
        else:
            raise GEOSException('Cannot set Z on 2D Point.')

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
    coords = tuple

class LineString(GEOSGeometry):

    #### Python 'magic' routines ####
    def __init__(self, *args, **kwargs):
        """
        Initializes on the given sequence -- may take lists, tuples, NumPy arrays
        of X,Y pairs, or Point objects.  If Point objects are used, ownership is
        _not_ transferred to the LineString object.

        Examples:
         ls = LineString((1, 1), (2, 2))
         ls = LineString([(1, 1), (2, 2)])
         ls = LineString(array([(1, 1), (2, 2)]))
         ls = LineString(Point(1, 1), Point(2, 2))
        """
        # If only one argument provided, set the coords array appropriately
        if len(args) == 1: coords = args[0]
        else: coords = args

        if isinstance(coords, (tuple, list)):
            # Getting the number of coords and the number of dimensions -- which
            #  must stay the same, e.g., no LineString((1, 2), (1, 2, 3)).
            ncoords = len(coords)
            if coords: ndim = len(coords[0])
            else: raise TypeError('Cannot initialize on empty sequence.')
            self._checkdim(ndim)
            # Incrementing through each of the coordinates and verifying
            for i in xrange(1, ncoords):
                if not isinstance(coords[i], (tuple, list, Point)):
                    raise TypeError('each coordinate should be a sequence (list or tuple)')
                if len(coords[i]) != ndim: raise TypeError('Dimension mismatch.')
            numpy_coords = False
        elif HAS_NUMPY and isinstance(coords, ndarray):
            shape = coords.shape # Using numpy's shape.
            if len(shape) != 2: raise TypeError('Too many dimensions.')
            self._checkdim(shape[1])
            ncoords = shape[0]
            ndim = shape[1]
            numpy_coords = True
        else:
            raise TypeError('Invalid initialization input for LineStrings.')

        # Creating a coordinate sequence object because it is easier to 
        #  set the points using GEOSCoordSeq.__setitem__().
        cs = GEOSCoordSeq(create_cs(ncoords, ndim), z=bool(ndim==3))
        for i in xrange(ncoords):
            if numpy_coords: cs[i] = coords[i,:]
            elif isinstance(coords[i], Point): cs[i] = coords[i].tuple
            else: cs[i] = coords[i]        

        # Getting the correct initialization function
        if kwargs.get('ring', False):
            func = create_linearring
        else:
            func = create_linestring

        # If SRID was passed in with the keyword arguments
        srid = kwargs.get('srid', None)
       
        # Calling the base geometry initialization with the returned pointer 
        #  from the function.
        super(LineString, self).__init__(func(cs.ptr), srid=srid)

    def __getitem__(self, index):
        "Gets the point at the specified index."
        return self._cs[index]

    def __setitem__(self, index, value):
        "Sets the point at the specified index, e.g., line_str[0] = (1, 2)."
        self._cs[index] = value

    def __iter__(self):
        "Allows iteration over this LineString."
        for i in xrange(len(self)):
            yield self[i]

    def __len__(self):
        "Returns the number of points in this LineString."
        return len(self._cs)

    def _checkdim(self, dim):
        if dim not in (2, 3): raise TypeError('Dimension mismatch.')

    #### Sequence Properties ####
    @property
    def tuple(self):
        "Returns a tuple version of the geometry from the coordinate sequence."
        return self._cs.tuple
    coords = tuple

    def _listarr(self, func):
        """
        Internal routine that returns a sequence (list) corresponding with
        the given function.  Will return a numpy array if possible.
        """
        lst = [func(i) for i in xrange(len(self))]
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
        """
        Initializes on an exterior ring and a sequence of holes (both
        instances may be either LinearRing instances, or a tuple/list
        that may be constructed into a LinearRing).
        
        Examples of initialization, where shell, hole1, and hole2 are 
        valid LinearRing geometries:
        >>> poly = Polygon(shell, hole1, hole2)
        >>> poly = Polygon(shell, (hole1, hole2))

        Example where a tuple parameters are used:
        >>> poly = Polygon(((0, 0), (0, 10), (10, 10), (0, 10), (0, 0)), 
                           ((4, 4), (4, 6), (6, 6), (6, 4), (4, 4)))
        """
        if not args:
            raise TypeError('Must provide at list one LinearRing instance to initialize Polygon.')

        # Getting the ext_ring and init_holes parameters from the argument list
        ext_ring = args[0]
        init_holes = args[1:]
        n_holes = len(init_holes)

        # If initialized as Polygon(shell, (LinearRing, LinearRing)) [for backward-compatibility]
        if n_holes == 1 and isinstance(init_holes[0], (tuple, list)) and \
                (len(init_holes[0]) == 0 or isinstance(init_holes[0][0], LinearRing)): 
            init_holes = init_holes[0]
            n_holes = len(init_holes)

        # Ensuring the exterior ring and holes parameters are LinearRing objects
        # or may be instantiated into LinearRings.
        ext_ring = self._construct_ring(ext_ring, 'Exterior parameter must be a LinearRing or an object that can initialize a LinearRing.')
        holes_list = [] # Create new list, cause init_holes is a tuple.
        for i in xrange(n_holes):
            holes_list.append(self._construct_ring(init_holes[i], 'Holes parameter must be a sequence of LinearRings or objects that can initialize to LinearRings'))

        # Why another loop?  Because if a TypeError is raised, cloned pointers will
        # be around that can't be cleaned up.
        holes = get_pointer_arr(n_holes)
        for i in xrange(n_holes): holes[i] = geom_clone(holes_list[i].ptr)
                      
        # Getting the shell pointer address.
        shell = geom_clone(ext_ring.ptr)

        # Calling with the GEOS createPolygon factory.
        super(Polygon, self).__init__(create_polygon(shell, byref(holes), c_uint(n_holes)), **kwargs)

    def __getitem__(self, index):
        """
        Returns the ring at the specified index.  The first index, 0, will 
        always return the exterior ring.  Indices > 0 will return the 
        interior ring at the given index (e.g., poly[1] and poly[2] would
        return the first and second interior ring, respectively).
        """
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
            raise TypeError('must set Polygon index with a LinearRing object')

        # Getting the shell
        if index == 0:
            shell = geom_clone(ring.ptr)
        else:
            shell = geom_clone(get_extring(self.ptr))

        # Getting the interior rings (holes)
        nholes = len(self)-1
        if nholes > 0:
            holes = get_pointer_arr(nholes)
            for i in xrange(nholes):
                if i == (index-1):
                    holes[i] = geom_clone(ring.ptr)
                else:
                    holes[i] = geom_clone(get_intring(self.ptr, i))
            holes_param = byref(holes)
        else:
            holes_param = None
         
        # Getting the current pointer, replacing with the newly constructed
        # geometry, and destroying the old geometry.
        prev_ptr = self.ptr
        srid = self.srid
        self._ptr = create_polygon(shell, holes_param, c_uint(nholes))
        if srid: self.srid = srid
        destroy_geom(prev_ptr)

    def __iter__(self):
        "Iterates over each ring in the polygon."
        for i in xrange(len(self)):
            yield self[i]

    def __len__(self):
        "Returns the number of rings in this Polygon."
        return self.num_interior_rings + 1

    def _checkindex(self, index):
        "Internal routine for checking the given ring index."
        if index < 0 or index >= len(self):
            raise GEOSIndexError('invalid Polygon ring index: %s' % index)

    def _construct_ring(self, param, msg=''):
        "Helper routine for trying to construct a ring from the given parameter."
        if isinstance(param, LinearRing): return param
        try:
            ring = LinearRing(param)
            return ring
        except TypeError:
            raise TypeError(msg)

    def get_interior_ring(self, ring_i):
        """
        Gets the interior ring at the specified index, 0 is for the first 
        interior ring, not the exterior ring.
        """
        self._checkindex(ring_i+1)
        return GEOSGeometry(geom_clone(get_intring(self.ptr, ring_i)), srid=self.srid)
                                                        
    #### Polygon Properties ####
    @property
    def num_interior_rings(self):
        "Returns the number of interior rings."
        # Getting the number of rings
        return get_nrings(self.ptr)

    def get_ext_ring(self):
        "Gets the exterior ring of the Polygon."
        return GEOSGeometry(geom_clone(get_extring(self.ptr)), srid=self.srid)

    def set_ext_ring(self, ring):
        "Sets the exterior ring of the Polygon."
        self[0] = ring

    # properties for the exterior ring/shell
    exterior_ring = property(get_ext_ring, set_ext_ring)
    shell = exterior_ring
    
    @property
    def tuple(self):
        "Gets the tuple for each ring in this Polygon."
        return tuple([self[i].tuple for i in xrange(len(self))])
    coords = tuple

    @property
    def kml(self):
        "Returns the KML representation of this Polygon."
        inner_kml = ''.join(["<innerBoundaryIs>%s</innerBoundaryIs>" % self[i+1].kml 
                             for i in xrange(self.num_interior_rings)])
        return "<Polygon><outerBoundaryIs>%s</outerBoundaryIs>%s</Polygon>" % (self[0].kml, inner_kml)
