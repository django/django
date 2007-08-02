"""
  This module contains the 'base' GEOSGeometry object -- all GEOS geometries
  inherit from this object.
"""

# ctypes and types dependencies.
from ctypes import \
     byref, string_at, create_string_buffer, pointer, \
     c_char_p, c_double, c_int, c_size_t
from types import StringType, IntType, FloatType

# Python and GEOS-related dependencies.
import re
from warnings import warn
from django.contrib.gis.geos.libgeos import lgeos, GEOSPointer, HAS_NUMPY, ISQLQuote, GEOM_FUNC_PREFIX
from django.contrib.gis.geos.error import GEOSException, GEOSGeometryIndexError
from django.contrib.gis.geos.coordseq import GEOSCoordSeq, create_cs
if HAS_NUMPY: from numpy import ndarray, array

# Regular expression for recognizing HEXEWKB.
hex_regex = re.compile(r'^[0-9A-Fa-f]+$')

class GEOSGeometry(object):
    "A class that, generally, encapsulates a GEOS geometry."
    
    #### Python 'magic' routines ####
    def __init__(self, geo_input, input_type=False, parent=None, srid=None):
        """The constructor for GEOS geometry objects.  May take the following
        strings as inputs, WKT ("wkt"), HEXEWKB ("hex", PostGIS-specific canonical form).

        The `input_type` keyword has been deprecated -- geometry type is now auto-detected.

        The `parent` keyword is for internal use only, and indicates to the garbage collector
          not to delete this geometry because it was spawned from a parent (e.g., the exterior
          ring from a polygon).  Its value is the GEOSPointer of the parent geometry.
        """

        # Initially, setting the pointer to NULL
        self._ptr = GEOSPointer(0)

        if isinstance(geo_input, StringType):
            if input_type: warn('input_type keyword is deprecated')

            if hex_regex.match(geo_input):
                # If the regex matches, the geometry is in HEX form.
                sz = c_size_t(len(geo_input))
                buf = create_string_buffer(geo_input)
                g = lgeos.GEOSGeomFromHEX_buf(buf, sz)
            else:
                # Otherwise, the geometry is in WKT form.
                g = lgeos.GEOSGeomFromWKT(c_char_p(geo_input))

        elif isinstance(geo_input, (IntType, GEOSPointer)):
            # When the input is either a raw pointer value (an integer), or a GEOSPointer object.
            g = geo_input
        else:
            # Invalid geometry type.
            raise TypeError, 'Improper geometry input type: %s' % str(type(geo_input))

        if bool(g):
            # If we have a GEOSPointer object, just set the '_ptr' attribute with input
            if isinstance(g, GEOSPointer): self._ptr = g
            else: self._ptr.set(g) # Otherwise, set with the address
        else:
            raise GEOSException, 'Could not initialize GEOS Geometry with given input.'

        # Setting the 'parent' flag -- when the object is labeled with this flag
        #  it will not be destroyed by __del__().  This is used for child geometries spawned from
        #  parent geometries (e.g., LinearRings from a Polygon, Points from a MultiPoint, etc.).
        if isinstance(parent, GEOSPointer):
            self._parent = parent
        else:
            self._parent = GEOSPointer(0)
        
        # Setting the SRID, if given.
        if srid and isinstance(srid, int): self.srid = srid

        # Setting the class type (e.g., 'Point', 'Polygon', etc.)
        self.__class__ = GEOS_CLASSES[self.geom_type]

        # Getting the coordinate sequence for the geometry (will be None on geometries that
        #   do not have coordinate sequences)
        self._get_cs()

        # Extra setup needed for Geometries that may be parents.
        if isinstance(self, (Polygon, GeometryCollection)): self._populate()

    def __del__(self):
        "Destroys this geometry -- only if the pointer is valid and whether or not it belongs to a parent."
        #print 'base: Deleting %s (parent=%s, valid=%s)' % (self.__class__.__name__, self._parent, self._ptr.valid)
        # Only calling destroy on valid pointers not spawned from a parent
        if self._ptr.valid and not self._parent: lgeos.GEOSGeom_destroy(self._ptr())

    def __str__(self):
        "WKT is used for the string representation."
        return self.wkt

    def __repr__(self):
        return '<%s object>' % self.geom_type

    # Comparison operators
    def __eq__(self, other):
        "Equivalence testing."
        return self.equals_exact(other)

    def __ne__(self, other):
        "The not equals operator."
        return not self.equals_exact(other)

    ### Geometry set-like operations ###
    # Thanks to Sean Gillies for inspiration:
    #  http://lists.gispython.org/pipermail/community/2007-July/001034.html
    # g = g1 | g2
    def __or__(self, other):
        "Returns the union of this Geometry and the other."
        return self.union(other)

    # g1 |= g2
    def __ior__(self, other):
        "Reassigns this Geometry to the union of this Geometry and the other."
        return self.union(other)

    # g = g1 & g2
    def __and__(self, other):
        "Returns the intersection of this Geometry and the other."
        return self.intersection(other)

    # g1 &= g2
    def __iand__(self, other):
        "Reassigns this Geometry to the intersection of this Geometry and the other."
        return self.intersection(other)

    # g = g1 - g2
    def __sub__(self, other):
        "Return the difference this Geometry and the other."
        return self.difference(other)

    # g1 -= g2
    def __isub__(self, other):
        "Reassigns this Geometry to the difference of this Geometry and the other."
        return self.difference(other)

    # g = g1 ^ g2
    def __xor__(self, other):
        "Return the symmetric difference of this Geometry and the other."
        return self.sym_difference(other)

    # g1 ^= g2
    def __ixor__(self, other):
        "Reassigns this Geometry to the symmetric difference of this Geometry and the other."
        return self.sym_difference(other)

    def _nullify(self):
        """During initialization of geometries from other geometries, this routine is
        used to nullify any parent geometries (since they will now be missing memory
        components) and to nullify the geometry itself to prevent future access.
        Only the address (an integer) of the current geometry is returned for use in
        initializing the new geometry."""
        # First getting the memory address of the geometry.
        address = self._ptr()

        # If the geometry is a child geometry, then the parent geometry pointer is
        #  nullified.
        if self._parent: self._parent.nullify()

        # Nullifying the geometry pointer
        self._ptr.nullify()

        return address

    def _reassign(self, new_geom):
        "Internal routine for reassigning internal pointer to a new geometry."
        # Only can re-assign when given a pointer or a geometry.
        if not isinstance(new_geom, (GEOSPointer, GEOSGeometry)):
            raise TypeError, 'cannot reassign geometry on given type: %s' % type(new_geom)
        gtype = new_geom.geom_type 

        # Re-assigning the internal GEOSPointer to the new geometry, nullifying
        #  the new Geometry in the process.
        if isinstance(new_geom, GEOSGeometry): self._ptr.set(new_geom._nullify())
        else: self._ptr = new_geom
        
        # The new geometry class may be different from the original, so setting
        #  the __class__ and populating the internal geometry or ring dictionary.
        self.__class__ = GEOS_CLASSES[gtype]
        if isinstance(self, (Polygon, GeometryCollection)): self._populate()

    #### Psycopg2 database adaptor routines ####
    def __conform__(self, proto):
        # Does the given protocol conform to what Psycopg2 expects?
        if proto == ISQLQuote: 
            return self
        else:
            raise GEOSException, 'Error implementing psycopg2 protocol.  Is psycopg2 installed?'

    def getquoted(self):
        "Returns a properly quoted string for use in PostgresSQL/PostGIS."
        # GeometryFromText() is ST_GeometryFromText() in PostGIS >= 1.2.2
        return "%sGeometryFromText('%s', %s)" % (GEOM_FUNC_PREFIX, self.wkt, self.srid or -1)
    
    #### Coordinate Sequence Routines ####
    @property
    def has_cs(self):
        "Returns True if this Geometry has a coordinate sequence, False if not."
        # Only these geometries are allowed to have coordinate sequences.
        if isinstance(self, (Point, LineString, LinearRing)):
            return True
        else:
            return False

    def _get_cs(self):
        "Gets the coordinate sequence for this Geometry."
        if self.has_cs:
            self._ptr.set(lgeos.GEOSGeom_getCoordSeq(self._ptr()), coordseq=True)
            self._cs = GEOSCoordSeq(self._ptr, self.hasz)
        else:
            self._cs = None

    @property
    def coord_seq(self):
        "Returns the coordinate sequence for this Geometry."
        return self._cs

    #### Geometry Info ####
    @property
    def geom_type(self):
        "Returns a string representing the Geometry type, e.g. 'Polygon'"
        return string_at(lgeos.GEOSGeomType(self._ptr()))

    @property
    def geom_typeid(self):
        "Returns an integer representing the Geometry type."
        return lgeos.GEOSGeomTypeId(self._ptr())

    @property
    def num_geom(self):
        "Returns the number of geometries in the Geometry."
        n = lgeos.GEOSGetNumGeometries(self._ptr())
        if n == -1: raise GEOSException, 'Error getting number of geometries.'
        else: return n

    @property
    def num_coords(self):
        "Returns the number of coordinates in the Geometry."
        n = lgeos.GEOSGetNumCoordinates(self._ptr())
        if n == -1: raise GEOSException, 'Error getting number of coordinates.'
        else: return n

    @property
    def num_points(self):
        "Returns the number points, or coordinates, in the Geometry."
        return self.num_coords

    @property
    def dims(self):
        "Returns the dimension of this Geometry (0=point, 1=line, 2=surface)."
        return lgeos.GEOSGeom_getDimensions(self._ptr())

    def normalize(self):
        "Converts this Geometry to normal form (or canonical form)."
        status = lgeos.GEOSNormalize(self._ptr())
        if status == -1: raise GEOSException, 'failed to normalize geometry'

    ## Internal for GEOS unary & binary predicate functions ##
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
        "Returns a boolean indicating whether the set of points in this Geometry are empty."
        return self._unary_predicate(lgeos.GEOSisEmpty)

    @property
    def valid(self):
        "This property tests the validity of this Geometry."
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
        the two Geometries match the elements in pattern."""
        if len(pattern) > 9:
            raise GEOSException, 'invalid intersection matrix pattern'
        return self._binary_predicate(lgeos.GEOSRelatePattern, other, c_char_p(pattern))

    def disjoint(self, other):
        "Returns true if the DE-9IM intersection matrix for the two Geometries is FF*FF****."
        return self._binary_predicate(lgeos.GEOSDisjoint, other)

    def touches(self, other):
        "Returns true if the DE-9IM intersection matrix for the two Geometries is FT*******, F**T***** or F***T****."
        return self._binary_predicate(lgeos.GEOSTouches, other)

    def intersects(self, other):
        "Returns true if disjoint returns false."
        return self._binary_predicate(lgeos.GEOSIntersects, other)

    def crosses(self, other):
        """Returns true if the DE-9IM intersection matrix for the two Geometries is T*T****** (for a point and a curve,
        a point and an area or a line and an area) 0******** (for two curves)."""
        return self._binary_predicate(lgeos.GEOSCrosses, other)

    def within(self, other):
        "Returns true if the DE-9IM intersection matrix for the two Geometries is T*F**F***."
        return self._binary_predicate(lgeos.GEOSWithin, other)

    def contains(self, other):
        "Returns true if other.within(this) returns true."
        return self._binary_predicate(lgeos.GEOSContains, other)

    def overlaps(self, other):
        """Returns true if the DE-9IM intersection matrix for the two Geometries is T*T***T** (for two points
        or two surfaces) 1*T***T** (for two curves)."""
        return self._binary_predicate(lgeos.GEOSOverlaps, other)

    def equals(self, other):
        "Returns true if the DE-9IM intersection matrix for the two Geometries is T*F**FFF*."
        return self._binary_predicate(lgeos.GEOSEquals, other)

    def equals_exact(self, other, tolerance=0):
        "Returns true if the two Geometries are exactly equal, up to a specified tolerance."
        tol = c_double(tolerance)
        return self._binary_predicate(lgeos.GEOSEqualsExact, other, tol)

    #### SRID Routines ####
    def get_srid(self):
        "Gets the SRID for the geometry, returns None if no SRID is set."
        s = lgeos.GEOSGetSRID(self._ptr())
        if s == 0: return None
        else: return s

    def set_srid(self, srid):
        "Sets the SRID for the geometry."
        lgeos.GEOSSetSRID(self._ptr(), c_int(srid))
    srid = property(get_srid, set_srid)

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
        """The centroid is equal to the centroid of the set of component Geometries
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
        return GEOSGeometry(lgeos.GEOSGeom_clone(self._ptr()), srid=self.srid)

# Class mapping dictionary
from django.contrib.gis.geos.geometries import Point, Polygon, LineString, LinearRing
from django.contrib.gis.geos.collections import GeometryCollection, MultiPoint, MultiLineString, MultiPolygon
GEOS_CLASSES = {'Point' : Point,
                'Polygon' : Polygon,
                'LineString' : LineString,
                'LinearRing' : LinearRing,
                'MultiPoint' : MultiPoint,
                'MultiLineString' : MultiLineString,
                'MultiPolygon' : MultiPolygon,
                'GeometryCollection' : GeometryCollection,  
                }
