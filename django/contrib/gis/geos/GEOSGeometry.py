# Copyright (c) 2007, Justin Bronn
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
#     1. Redistributions of source code must retain the above copyright notice, 
#        this list of conditions and the following disclaimer.
#    
#     2. Redistributions in binary form must reproduce the above copyright 
#        notice, this list of conditions and the following disclaimer in the
#        documentation and/or other materials provided with the distribution.
#
#     3. Neither the name of GEOSGeometry nor the names of its contributors may be used
#        to endorse or promote products derived from this software without
#        specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
# ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#

# Trying not to pollute the namespace.
from ctypes import \
     CDLL, CFUNCTYPE, byref, string_at, create_string_buffer, \
     c_char_p, c_double, c_float, c_int, c_uint, c_size_t, c_ubyte
import os, sys

"""
  The goal of this module is to be a ctypes wrapper around the GEOS library
  that will work on both *NIX and Windows systems.  Specifically, this uses
  the GEOS C api.

  I have several motivations for doing this:
    (1) The GEOS SWIG wrapper is no longer maintained, and requires the
        installation of SWIG.
    (2) The PCL implementation is over 2K+ lines of C and would make
        PCL a requisite package for the GeoDjango application stack.
    (3) Windows compatibility becomes substantially easier, and does not require the
        additional compilation of PCL or GEOS and SWIG -- all that is needed is
        a Win32 compiled GEOS C library (dll) in a location that Python can read
        (e.g. C:\Python25).

  In summary, I wanted to wrap GEOS in a more maintainable and portable way using
   only Python and the excellent ctypes library (now standard in Python 2.5).

  In the spirit of loose coupling, this library does not require Django or
   GeoDjango.  Only the GEOS C library and ctypes are needed for the platform
   of your choice.

  For more information about GEOS:
    http://geos.refractions.net
  
  For more info about PCL and the discontinuation of the Python GEOS
   library see Sean Gillies' writeup (and subsequent update) at:
     http://zcologia.com/news/150/geometries-for-python/
     http://zcologia.com/news/429/geometries-for-python-update/
"""

# Setting the appropriate name for the GEOS-C library, depending on which
# platform we're running.
if os.name == 'nt':
    # Windows NT library
    lib_name = 'libgeos_c-1.dll'
else:
    # Linux shared library
    lib_name = 'libgeos_c.so'

# Getting the GEOS C library.  The C interface (CDLL) is used for
#  both *NIX and Windows.
# See the GEOS C API source code for more details on the library function calls:
#  http://geos.refractions.net/ro/doxygen_docs/html/geos__c_8h-source.html
lgeos = CDLL(lib_name)

# The notice and error handlers
#  Supposed to mimic the GEOS message handler (C below):
#  "typedef void (*GEOSMessageHandler)(const char *fmt, ...);"
NOTICEFUNC = CFUNCTYPE(None, c_char_p, c_char_p)
def notice_h(fmt, list):
    sys.stdout.write((fmt + '\n') % list)
notice_h = NOTICEFUNC(notice_h)

ERRORFUNC = CFUNCTYPE(None, c_char_p, c_char_p)
def error_h(fmt, list):
    if not list:
        sys.stderr.write(fmt)
    else:
        sys.stderr.write('ERROR: %s' % str(list))
error_h = ERRORFUNC(error_h)

# The initGEOS routine should be called first, however, that routine takes
#  the notice and error functions as parameters.  Here is the C code that
#  we need to wrap:
#  "extern void GEOS_DLL initGEOS(GEOSMessageHandler notice_function, GEOSMessageHandler error_function);"
lgeos.initGEOS(notice_h, error_h)

class GEOSException:
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return repr(self.msg)

class GEOSGeometry:
    "A class that, generally, encapsulates a GEOS geometry."

    #### Python 'magic' routines ####
    def __init__(self, input, geom_type='wkt'):
        "Takes an input and the type of the input for initialization."
        if geom_type == 'wkt':
            # If the geometry is in WKT form
            self._g = lgeos.GEOSGeomFromWKT(c_char_p(input))
        elif geom_type == 'hex':
            # If the geometry is in EWHEX form.
            sz = c_size_t(len(input))
            buf = create_string_buffer(input)
            self._g = lgeos.GEOSGeomFromHEX_buf(buf, sz)
        elif geom_type == 'geos':
            # When the input is a C pointer (Python integer)
            self._g = input
        else:
            # Invalid geometry type.
            raise GEOSException, 'Improper geometry input type!'

        # Setting the class type (e.g. 'Point', 'Polygon', etc.)
        self.__class__ = GEO_CLASSES[self.geom_type]

        # If the geometry pointer is NULL (0), then raise an exception.
        if not self._g:
            raise GEOSException, 'Could not initialize on input!'

    def __del__(self):
        "This cleans up the memory allocated for the geometry."
        lgeos.GEOSGeom_destroy(self._g)

    def __str__(self):
        "WKT is used for the string representation."
        return self.wkt

    def __eq__(self, other):
        "Equivalence testing."
        return self.equals(other)

    #### Geometry Info ####
    @property
    def geom_type(self):
        "Returns a string representing the geometry type, e.g. 'Polygon'"
        return string_at(lgeos.GEOSGeomType(self._g))

    @property
    def geom_typeid(self):
        "Returns an integer representing the geometry type."
        return lgeos.GEOSGeomTypeId(self._g)

    @property
    def num_geom(self):
        "Returns the number of geometries in the geometry."
        n = lgeos.GEOSGetNumGeometries(self._g)
        if n == -1: raise GEOSException, 'Error getting number of geometries!'
        else: return n

    @property
    def num_coords(self):
        "Returns the number of coordinates in the geometry."
        n = lgeos.GEOSGetNumCoordinates(self._g)
        if n == -1: raise GEOSException, 'Error getting number of coordinates!'
        else: return n

    @property
    def dims(self):
        "Returns the dimension of this Geometry (0=point, 1=line, 2=surface)."
        return lgeos.GEOSGeom_getDimensions(self._g)

    @property
    def coord_seq(self):
        "Returns the coordinate sequence for the geometry."

        # Only these geometries can return coordinate sequences
        if self.geom_type not in ['LineString', 'LinearRing', 'Point']:
            return None

        # Getting the coordinate sequence for the geometry
        cs = lgeos.GEOSGeom_getCoordSeq(self._g)

        # Cloning the coordinate sequence (if the original is returned,
        #  and it is garbage-collected we will get a segmentation fault!)
        clone = lgeos.GEOSCoordSeq_clone(cs)
        return GEOSCoordSeq(clone, z=self.hasz)

    def normalize(self):
        "Converts this Geometry to normal form (or canonical form).Converts this Geometry to normal form (or canonical form)."
        status = lgeos.GEOSNormalize(self._g)
        if status == -1: raise GEOSException, 'failed to normalize geometry'

    def _predicate(self, val):
        "Checks the result, 2 for exception, 1 on true, 0 on false."
        if val == 0:
            return False
        elif val == 1:
            return True
        else:
            raise GEOSException, 'Predicate exception occurred!'

    ### Unary predicates ###
    @property
    def empty(self):
        "Returns a boolean indicating whether the set of points in this geometry are empty."
        return self._predicate(lgeos.GEOSisEmpty(self._g))

    @property
    def valid(self):
        "This property tests the validity of this geometry."
        return self._predicate(lgeos.GEOSisValid(self._g))

    @property
    def simple(self):
        "Returns false if the Geometry not simple."
        return self._predicate(lgeos.GEOSisSimple(self._g))

    @property
    def ring(self):
        "Returns whether or not the geometry is a ring."
        return self._predicate(lgeos.GEOSisRing(self._g))

    @property
    def hasz(self):
        "Returns whether the geometry has a 3D dimension."
        return self._predicate(lgeos.GEOSHasZ(self._g))

    #### Binary predicates. ####
    def relate_pattern(self, other, pattern):
        """Returns true if the elements in the DE-9IM intersection matrix for
        the two Geometrys match the elements in pattern."""
        if len(pattern) > 9:
            raise GEOSException, 'invalid intersection matrix pattern'
        pat = create_string_buffer(pattern)
        return self._predicate(lgeos.GEOSRelatePattern(self._g, other._g, pat))

    def disjoint(self, other):
        "Returns true if the DE-9IM intersection matrix for the two Geometrys is FF*FF****."
        return self._predicate(lgeos.GEOSDisjoint(self._g, other._g))

    def touches(self, other):
        "Returns true if the DE-9IM intersection matrix for the two Geometrys is FT*******, F**T***** or F***T****."
        return self._predicate(lgeos.GEOSTouches(self._g, other._g))

    def intersects(self, other):
        "Returns true if disjoint returns false."
        return self._predicate(lgeos.GEOSIntersects(self._g, other._g))

    def crosses(self, other):
        """Returns true if the DE-9IM intersection matrix for the two Geometrys is T*T****** (for a point and a curve,
        a point and an area or a line and an area) 0******** (for two curves)."""
        return self._predicate(lgeos.GEOSCrosses(self._g, other._g))

    def within(self, other):
        "Returns true if the DE-9IM intersection matrix for the two Geometrys is T*F**F***."
        return self._predicate(lgeos.GEOSWithin(self._g, other._g))

    def contains(self, other):
        "Returns true if other.within(this) returns true."
        return self._predicate(lgeos.GEOSContains(self._g, other._g))

    def overlaps(self, other):
        """Returns true if the DE-9IM intersection matrix for the two Geometrys is T*T***T** (for two points
        or two surfaces) 1*T***T** (for two curves)."""
        return self._predicate(lgeos.GEOSOverlaps(self._g, other._g))

    def equals(self, other):
        "Returns true if the DE-9IM intersection matrix for the two Geometrys is T*F**FFF*."
        return self._predicate(lgeos.GEOSEquals(self._g, other._g))

    def equals_exact(self, other, tolerance=0):
        "Returns true if the two Geometrys are exactly equal, up to a specified tolerance."
        tol = c_double(tolerance)
        return self._predicate(lgeos.GEOSEqualsExact(self._g, other._g, tol))

    #### SRID Routines ####
    @property
    def srid(self):
        "Gets the SRID for the geometry, returns None if no SRID is set."
        s = lgeos.GEOSGetSRID(self._g)
        if s == 0:
            return None
        else:
            return lgeos.GEOSGetSRID(self._g)

    def set_srid(self, srid):
        "Sets the SRID for the geometry."
        lgeos.GEOSSetSRID(self._g, c_int(srid))
    
    #### Output Routines ####
    @property
    def wkt(self):
        "Returns the WKT of the Geometry."
        return string_at(lgeos.GEOSGeomToWKT(self._g))

    @property
    def hex(self):
        "Returns the WKBHEX of the Geometry."
        sz = c_size_t()
        h = lgeos.GEOSGeomToHEX_buf(self._g, byref(sz))
        return string_at(h, sz.value)

    #### Topology Routines ####
    def buffer(self, width, quadsegs=8):
        """Returns a geometry that represents all points whose distance from this
        Geometry is less than or equal to distance. Calculations are in the
        Spatial Reference System of this Geometry. The optional third parameter sets
        the number of segment used to approximate a quarter circle (defaults to 8).
        [Text from PostGIS documentation at ch. 6.2.2 <-- verify]
        """
        if type(width) != type(0.0):
            raise TypeError, 'width parameter must be a float'
        if type(quadsegs) != type(0):
            raise TypeError, 'quadsegs parameter must be an integer'
        b = lgeos.GEOSBuffer(self._g, c_float(width), c_int(quadsegs))
        return GEOSGeometry(b, 'geos')

    @property
    def envelope(self):
        "Return the geometries bounding box."
        e = lgeos.GEOSEnvelope(self._g)
        return GEOSGeometry(e, 'geos')

    @property
    def centroid(self):
        """The centroid is equal to the centroid of the set of component Geometrys
        of highest dimension (since the lower-dimension geometries contribute zero
        "weight" to the centroid)."""
        g = lgeos.GEOSGetCentroid(self._g)
        return GEOSGeometry(g, 'geos')

    @property
    def boundary(self):
        "Returns the boundary as a newly allocated Geometry object."
        g = lgeos.GEOSBoundary(self._g)
        return GEOSGeometry(g, 'geos')

    @property
    def convex_hull(self):
        "Returns the smallest convex Polygon that contains all the points in the Geometry."
        g = lgeos.GEOSConvexHull(self._g)
        return GEOSGeometry(g, 'geos')

    @property
    def point_on_surface(self):
        "Computes an interior point of this Geometry."
        g = lgeos.GEOSPointOnSurface(self._g)
        return GEOSGeometry(g, 'geos')

    def relate(self, other):
        "Returns the DE-9IM intersection matrix for this geometry and the other."
        return string_at(lgeos.GEOSRelate(self._g, other._g))

    def difference(self, other):
        """Returns a Geometry representing the points making up this Geometry
        that do not make up other."""
        d = lgeos.GEOSDifference(self._g, other._g)
        return GEOSGeometry(d, 'geos')

    def sym_difference(self, other):
        """Returns a set combining the points in this Geometry not in other,
        and the points in other not in this Geometry."""
        d = lgeos.GEOSSymDifference(self._g, other._g)
        return GEOSGeometry(d, 'geos')

    def intersection(self, other):
        "Returns a Geometry representing the points shared by this Geometry and other."
        i = lgeos.GEOSIntersection(self._g, other._g)
        return GEOSGeometry(i, 'geos')

    def union(self, other):
        "Returns a Geometry representing all the points in this Geometry and other."
        u = lgeos.GEOSUnion(self._g, other._g)
        return GEOSGeometry(u, 'geos')

    #### Other Routines ####
    @property
    def area(self):
        "Returns the area of the Geometry."
        a = c_double()
        status = lgeos.GEOSArea(self._g, byref(a))
        if not status:
            return None
        else:
            return a.value

class GEOSCoordSeq:
    "The internal representation of a list of coordinates inside a Geometry."

    def __init__(self, ptr, z=False):
        "Initializes from a GEOS pointer."
        self._cs = ptr
        self._z = z

    def __del__(self):
        lgeos.GEOSCoordSeq_destroy(self._cs)

    def __iter__(self):
        for i in xrange(self.size):
            yield self.__getitem__(i)

    def __len__(self):
        return self.size

    def __str__(self):
        "The string representation of the coordinate sequence."
        rep = []
        for i in xrange(self.size):
            rep.append(self.__getitem__(i))
        return str(tuple(rep))

    def _checkindex(self, index):
        "Checks the index."
        sz = self.size
        if (sz < 1) or (index < 0) or (index >= sz):
            raise IndexError, 'index out of range'

    def _checkdim(self, dim):
        "Checks the given dimension."
        if dim < 0 or dim > 2:
            raise GEOSException, 'invalid ordinate dimension "%d"' % dim
        
    def __getitem__(self, index):
        "Can use the index [] operator to get coordinate sequence at an index."
        coords = [self.getX(index), self.getY(index)]
        if self.dims == 3 and self._z:
            coords.append(self.getZ(index))
        return tuple(coords)

    def __setitem__(self, index, value):
        "Can use the index [] operator to set coordinate sequence at an index."
        if self.dims == 3 and self._z:
            n_args = 3
            set_3d = True
        else:
            n_args = 2
            set_3d = False
        if len(value) != n_args:
            raise GEOSException, 'Improper value given!'
        self.setX(index, value)
        self.setY(index, value)
        if set_3d: self.setZ(index, value)
        
    # Getting and setting the X coordinate for the given index.
    def getX(self, index):
        return self.getOrdinate(0, index)

    def setX(self, index, value):
        self.setOrdinate(0, index, value)

    # Getting and setting the Y coordinate for the given index.
    def getY(self, index):
        return self.getOrdinate(1, index)

    def setY(self, index):
        self.setOrdinate(1, index)

    # Getting and setting the Z coordinate for the given index
    def getZ(self, index):
        return self.getOrdinate(2, index)

    def setZ(self, index):
        self.setOrdinate(2, index)

    def getOrdinate(self, dimension, index):
        "Gets the value for the given dimension and index."
        self._checkindex(index)
        self._checkdim(dimension)

        # Wrapping the dimension, index
        dim = c_uint(dimension)
        idx = c_uint(index)

        # 'd' is the value of the point
        d = c_double()
        status = lgeos.GEOSCoordSeq_getOrdinate(self._cs, idx, dim, byref(d))
        if status == 0:
            raise GEOSException, 'Could not get the ordinate for (dim, index): (%d, %d)' % (dimension, index)
        return d.value

    def setOrdinate(self, dimension, index, value):
        "Sets the value for the given dimension and index."
        self._checkindex(idnex)
        self._checkdim(dimension)

        # Wrapping the dimension, index
        dim = c_uint(dimension)
        idx = c_uint(index)

        # 'd' is the value of the point
        d = c_double(value)
        status = lgeos.GEOSCoordSeq_getOrdinate(self._cs, idx, dim, byref(d))
        if status == 0:
            raise GEOSException, 'Could not set the ordinate for (dim, index): (%d, %d)' % (dimension, index)

    ### Dimensions ###
    @property
    def size(self):
        "Returns the size of this coordinate sequence."
        n = c_uint(0)
        status = lgeos.GEOSCoordSeq_getSize(self._cs, byref(n))
        if status == 0:
            raise GEOSException, 'Could not get CoordSeq size!'
        return n.value

    @property
    def dims(self):
        "Returns the dimensions of this coordinate sequence."
        n = c_uint(0)
        status = lgeos.GEOSCoordSeq_getDimensions(self._cs, byref(n))
        if status == 0:
            raise GEOSException, 'Could not get CoordSeq dimensoins!'
        return n.value

    @property
    def hasz(self):
        "Inherits this from the parent geometry."
        return self._z

    ### Other Methods ###
    @property
    def tuple(self):
        n = self.size
        if n == 1:
            return self.__getitem__(0)
        else:
            return tuple(self.__getitem__(i) for i in xrange(n))
            
# Factory coordinate sequence Function
def createCoordSeq(size, dims):
        return GEOSCoordSeq(lgeos.GEOSCoordSeq_create(c_uint(size), c_uint(dims)))

class Point(GEOSGeometry):

    def _cache_cs(self):
        "Caches the coordinate sequence."
        if not hasattr(self, '_cs'): self._cs = self.coord_seq        

    def _getOrdinate(self, dim, idx):
        "The coordinate sequence getOrdinate() wrapper."
        self._cache_cs()
        return self._cs.getOrdinate(dim, idx)

    @property
    def x(self):
        "Returns the X component of the Point."
        return self._getOrdinate(0, 0)

    @property
    def y(self):
        "Returns the Y component of the Point."
        return self._getOrdinate(1, 0)

    @property
    def z(self):
        "Returns the Z component of the Point."
        if self.hasz:
            return self._getOrdinate(2, 0)
        else:
            return None

    @property
    def tuple(self):
        "Returns a tuple of the point."
        self._cache_cs()
        return self._cs.tuple

class LineString(GEOSGeometry):

    def _cache_cs(self):
        "Caches the coordinate sequence."
        if not hasattr(self, '_cs'): self._cs = self.coord_seq 

    @property
    def tuple(self):
        "Returns a tuple version of the geometry from the coordinate sequence."
        self._cache_cs()
        return self._cs.tuple

class LinearRing(LineString):
    pass

class Polygon(GEOSGeometry):

    #### Polygon Routines ####
    @property
    def num_interior_rings(self):
        "Returns the number of interior rings."

        # Getting the number of rings
        n = lgeos.GEOSGetNumInteriorRings(self._g)

        # -1 indicates an exception occurred
        if n == -1: raise GEOSException, 'Error getting the number of interior rings!'
        else: return n

    def get_interior_ring(self, ring_i):
        "Gets the interior ring at the specified index."

        # Making sure the ring index is within range
        if ring_i >= self.num_interior_rings:
            raise GEOSException, 'Invalid ring index.'

        # Getting a clone of the ring geometry at the given ring index.
        r = lgeos.GEOSGeom_clone(lgeos.GEOSGetInteriorRingN(self._g, c_int(ring_i)))
        return GEOSGeometry(r, 'geos')

    @property
    def exterior_ring(self):
        "Gets the exterior ring of the Polygon."

        # Getting a clone of the ring geometry
        r = lgeos.GEOSGeom_clone(lgeos.GEOSGetExteriorRing(self._g))
        return GEOSGeometry(r, 'geos')
    
class GeometryCollection(GEOSGeometry):

    def _checkindex(self, index):
        "Checks the given geometry index."
        if index < 0 or index >= self.num_geom:
            raise IndexError, 'index out of range'

    def __iter__(self):
        "For iteration on the multiple geometries."
        for i in xrange(self.num_geom):
            yield self.__getitem__(i)

    def __getitem__(self, index):
        "For indexing on the multiple geometries."
        self._checkindex(index)
        item = lgeos.GEOSGeom_clone(lgeos.GEOSGetGeometryN(self._g, c_int(index)))
        return GEOSGeometry(item, 'geos')

    def __len__(self):
        return self.num_geom

class MultiPoint(GeometryCollection):
    pass

class MultiLineString(GeometryCollection):
    pass

class MultiPolygon(GeometryCollection):
    pass

# Class mapping dictionary
GEO_CLASSES = {'Point' : Point,
               'Polygon' : Polygon,
               'LineString' : LineString,
               'LinearRing' : LinearRing,
               'GeometryCollection' : GeometryCollection,
               'MultiPoint' : MultiPoint,
               'MultiLineString' : MultiLineString,
               'MultiPolygon' : MultiPolygon,
               }
