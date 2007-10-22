"""
  This module contains the 'base' GEOSGeometry object -- all GEOS geometries
   inherit from this object.
"""
# ctypes and types dependencies.
from ctypes import \
     byref, string_at, create_string_buffer, pointer, \
     c_char_p, c_double, c_int, c_size_t
from types import StringType, UnicodeType, IntType, FloatType, BufferType

# Python and GEOS-related dependencies.
import re
from django.contrib.gis.geos.coordseq import GEOSCoordSeq, create_cs
from django.contrib.gis.geos.error import GEOSException, GEOSGeometryIndexError
from django.contrib.gis.geos.libgeos import lgeos, HAS_NUMPY
from django.contrib.gis.geos.pointer import GEOSPointer, NULL_GEOM

# Trying to import GDAL libraries, if available.  Have to place in
# try/except since this package may be used outside GeoDjango.
try:
    from django.contrib.gis.gdal import OGRGeometry, SpatialReference
    HAS_GDAL=True
except:
    HAS_GDAL=False

# Regular expression for recognizing HEXEWKB and WKT.  A prophylactic measure
#  to prevent potentially malicious input from reaching the underlying C
#  library.  Not a substitute for good web security programming practices.
hex_regex = re.compile(r'^[0-9A-F]+$', re.I)
wkt_regex = re.compile(r'^(POINT|LINESTRING|LINEARRING|POLYGON|MULTIPOINT|MULTILINESTRING|MULTIPOLYGON|GEOMETRYCOLLECTION)[ACEGIMLONPSRUTY\d,\.\-\(\) ]+$', re.I)

class GEOSGeometry(object):
    "A class that, generally, encapsulates a GEOS geometry."
    
    # Initially, all geometries use a NULL pointer.
    _ptr = NULL_GEOM
    
    #### Python 'magic' routines ####
    def __init__(self, geo_input, srid=None):
        """
        The base constructor for GEOS geometry objects, and may take the 
         following inputs:
         
         * string: WKT
         * string: HEXEWKB (a PostGIS-specific canonical form)
         * buffer: WKB
        
        The `srid` keyword is used to specify the Source Reference Identifier
         (SRID) number for this Geometry.  If not set, the SRID will be None.
        """ 
        if isinstance(geo_input, UnicodeType):
            # Encoding to ASCII, WKT or HEXEWKB doesn't need any more.
            geo_input = geo_input.encode('ascii')
        if isinstance(geo_input, StringType):
            if hex_regex.match(geo_input):
                # If the regex matches, the geometry is in HEX form.
                sz = c_size_t(len(geo_input))
                buf = create_string_buffer(geo_input)
                g = lgeos.GEOSGeomFromHEX_buf(buf, sz)
            elif wkt_regex.match(geo_input):
                # Otherwise, the geometry is in WKT form.
                g = lgeos.GEOSGeomFromWKT(c_char_p(geo_input))
            else:
                raise GEOSException('String or unicode input unrecognized as WKT or HEXEWKB.')
        elif isinstance(geo_input, (IntType, GEOSPointer)):
            # When the input is either a memory address (an integer), or a 
            #  GEOSPointer object.
            g = geo_input
        elif isinstance(geo_input, BufferType):
            # When the input is a buffer (WKB).
            wkb_input = str(geo_input)
            sz = c_size_t(len(wkb_input))
            g = lgeos.GEOSGeomFromWKB_buf(c_char_p(wkb_input), sz)
        else:
            # Invalid geometry type.
            raise TypeError, 'Improper geometry input type: %s' % str(type(geo_input))

        if bool(g):
            # Setting the pointer object with a valid pointer.
            self._ptr = GEOSPointer(g)
        else:
            raise GEOSException, 'Could not initialize GEOS Geometry with given input.'

        # Setting the SRID, if given.
        if srid and isinstance(srid, int): self.srid = srid

        # Setting the class type (e.g., 'Point', 'Polygon', etc.)
        self.__class__ = GEOS_CLASSES[self.geom_type]

        # Setting the coordinate sequence for the geometry (will be None on 
        #  geometries that do not have coordinate sequences)
        self._set_cs()

        # _populate() needs to be called for parent Geometries.
        if isinstance(self, (Polygon, GeometryCollection)): self._populate()

    def __del__(self):
        """
        Destroys this Geometry; in other words, frees the memory used by the
         GEOS C++ object -- but only if the pointer is not a child Geometry
         (e.g., don't delete the LinearRings spawned from a Polygon).
        """
        #print 'base: Deleting %s (parent=%s, valid=%s)' % (self.__class__.__name__, self._ptr.parent, self._ptr.valid)
        if not self._ptr.child: self._ptr.destroy()

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
        """
        Reassigns this Geometry to the symmetric difference of this Geometry 
        and the other.
        """
        return self.sym_difference(other)

    #### Internal GEOSPointer-related routines. ####
    def _nullify(self):
        """
        Returns the address of this Geometry, and nullifies any related pointers.
         This function is called if this Geometry is used in the initialization
         of another Geometry.
        """
        # First getting the memory address of the geometry.
        address = self._ptr()

        # If the geometry is a child geometry, then the parent geometry pointer is
        #  nullified.
        if self._ptr.child: 
            p = self._ptr.parent
            # If we have a grandchild (a LinearRing from a MultiPolygon or
            #  GeometryCollection), then nullify the collection as well.
            if p.child: p.parent.nullify()
            p.nullify()
            
        # Nullifying the geometry pointer
        self._ptr.nullify()

        return address

    def _reassign(self, new_geom):
        "Reassigns the internal pointer to that of the new Geometry."
        # Only can re-assign when given a pointer or a geometry.
        if not isinstance(new_geom, (GEOSPointer, GEOSGeometry)):
            raise TypeError, 'cannot reassign geometry on given type: %s' % type(new_geom)
        gtype = new_geom.geom_type 

        # Re-assigning the internal GEOSPointer to the new geometry, nullifying
        #  the new Geometry in the process.
        if isinstance(new_geom, GEOSPointer): self._ptr = new_geom
        else: self._ptr = GEOSPointer(new_geom._nullify())
        
        # The new geometry class may be different from the original, so setting
        #  the __class__ and populating the internal geometry or ring dictionary.
        self.__class__ = GEOS_CLASSES[gtype]
        if isinstance(self, (Polygon, GeometryCollection)): self._populate()

    #### Coordinate Sequence Routines ####
    @property
    def has_cs(self):
        "Returns True if this Geometry has a coordinate sequence, False if not."
        # Only these geometries are allowed to have coordinate sequences.
        if isinstance(self, (Point, LineString, LinearRing)):
            return True
        else:
            return False

    def _set_cs(self):
        "Sets the coordinate sequence for this Geometry."
        if self.has_cs:
            if not self._ptr.coordseq_valid:
                self._ptr.set_coordseq(lgeos.GEOSGeom_getCoordSeq(self._ptr()))
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
        """
        Returns the result, or raises an exception for the given unary predicate 
         function.
        """
        val = func(self._ptr())
        if val == 0: return False
        elif val == 1: return True
        else: raise GEOSException, '%s: exception occurred.' % func.__name__

    def _binary_predicate(self, func, other, *args):
        """
        Returns the result, or raises an exception for the given binary 
         predicate function.
        """
        if not isinstance(other, GEOSGeometry):
            raise TypeError, 'Binary predicate operation ("%s") requires another GEOSGeometry instance.' % func.__name__
        val = func(self._ptr(), other._ptr(), *args)
        if val == 0: return False
        elif val == 1: return True
        else: raise GEOSException, '%s: exception occurred.' % func.__name__

    #### Unary predicates ####
    @property
    def empty(self):
        """
        Returns a boolean indicating whether the set of points in this Geometry 
         are empty.
        """
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
        """
        Returns true if the elements in the DE-9IM intersection matrix for the 
         two Geometries match the elements in pattern.
        """
        if len(pattern) > 9:
            raise GEOSException, 'invalid intersection matrix pattern'
        return self._binary_predicate(lgeos.GEOSRelatePattern, other, c_char_p(pattern))

    def disjoint(self, other):
        """
        Returns true if the DE-9IM intersection matrix for the two Geometries 
         is FF*FF****.
        """
        return self._binary_predicate(lgeos.GEOSDisjoint, other)

    def touches(self, other):
        """
        Returns true if the DE-9IM intersection matrix for the two Geometries
         is FT*******, F**T***** or F***T****.
        """
        return self._binary_predicate(lgeos.GEOSTouches, other)

    def intersects(self, other):
        "Returns true if disjoint returns false."
        return self._binary_predicate(lgeos.GEOSIntersects, other)

    def crosses(self, other):
        """
        Returns true if the DE-9IM intersection matrix for the two Geometries
         is T*T****** (for a point and a curve,a point and an area or a line and
         an area) 0******** (for two curves).
        """
        return self._binary_predicate(lgeos.GEOSCrosses, other)

    def within(self, other):
        """
        Returns true if the DE-9IM intersection matrix for the two Geometries 
         is T*F**F***.
        """
        return self._binary_predicate(lgeos.GEOSWithin, other)

    def contains(self, other):
        "Returns true if other.within(this) returns true."
        return self._binary_predicate(lgeos.GEOSContains, other)

    def overlaps(self, other):
        """
        Returns true if the DE-9IM intersection matrix for the two Geometries 
         is T*T***T** (for two points or two surfaces) 1*T***T** (for two curves).
        """
        return self._binary_predicate(lgeos.GEOSOverlaps, other)

    def equals(self, other):
        """
        Returns true if the DE-9IM intersection matrix for the two Geometries 
         is T*F**FFF*.
        """
        return self._binary_predicate(lgeos.GEOSEquals, other)

    def equals_exact(self, other, tolerance=0):
        """
        Returns true if the two Geometries are exactly equal, up to a
         specified tolerance.
        """
        return self._binary_predicate(lgeos.GEOSEqualsExact, other, 
                                      c_double(tolerance))

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
        "Returns the WKT (Well-Known Text) of the Geometry."
        return string_at(lgeos.GEOSGeomToWKT(self._ptr()))

    @property
    def hex(self):
        """
        Returns the HEX of the Geometry -- please note that the SRID is not
        included in this representation, because the GEOS C library uses
        -1 by default, even if the SRID is set.
        """
        # A possible faster, all-python, implementation: 
        #  str(self.wkb).encode('hex')
        sz = c_size_t()
        h = lgeos.GEOSGeomToHEX_buf(self._ptr(), byref(sz))
        return string_at(h, sz.value)

    @property
    def wkb(self):
        "Returns the WKB of the Geometry as a buffer."
        sz = c_size_t()
        h = lgeos.GEOSGeomToWKB_buf(self._ptr(), byref(sz))
        return buffer(string_at(h, sz.value))

    @property
    def kml(self):
        "Returns the KML representation of this Geometry."
        gtype = self.geom_type
        return '<%s>%s</%s>' % (gtype, self.coord_seq.kml, gtype)

    #### GDAL-specific output routines ####
    @property
    def ogr(self):
        "Returns the OGR Geometry for this Geometry."
        if HAS_GDAL:
            if self.srid:
                return OGRGeometry(self.wkb, self.srid)
            else:
                return OGRGeometry(self.wkb)
        else:
            return None

    @property
    def srs(self):
        "Returns the OSR SpatialReference for SRID of this Geometry."
        if HAS_GDAL and self.srid:
            return SpatialReference(self.srid)
        else:
            return None

    #### Topology Routines ####
    def _unary_topology(self, func, *args):
        """
        Returns a GEOSGeometry for the given unary (takes only one Geomtery 
         as a paramter) topological operation.
        """
        return GEOSGeometry(func(self._ptr(), *args), srid=self.srid)

    def _binary_topology(self, func, other, *args):
        """
        Returns a GEOSGeometry for the given binary (takes two Geometries 
         as parameters) topological operation.
        """
        return GEOSGeometry(func(self._ptr(), other._ptr(), *args), srid=self.srid)

    def buffer(self, width, quadsegs=8):
        """
        Returns a geometry that represents all points whose distance from this
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
        """
        The centroid is equal to the centroid of the set of component Geometries
         of highest dimension (since the lower-dimension geometries contribute zero
         "weight" to the centroid).
        """
        return self._unary_topology(lgeos.GEOSGetCentroid)

    @property
    def boundary(self):
        "Returns the boundary as a newly allocated Geometry object."
        return self._unary_topology(lgeos.GEOSBoundary)

    @property
    def convex_hull(self):
        """
        Returns the smallest convex Polygon that contains all the points 
         in the Geometry.
        """
        return self._unary_topology(lgeos.GEOSConvexHull)

    @property
    def point_on_surface(self):
        "Computes an interior point of this Geometry."
        return self._unary_topology(lgeos.GEOSPointOnSurface)

    def simplify(self, tolerance=0.0, preserve_topology=False):
        """
        Returns the Geometry, simplified using the Douglas-Peucker algorithm
         to the specified tolerance (higher tolerance => less points).  If no
         tolerance provided, defaults to 0.

        By default, this function does not preserve topology - e.g. polygons can 
         be split, collapse to lines or disappear holes can be created or 
         disappear, and lines can cross. By specifying preserve_topology=True, 
         the result will have the same dimension and number of components as the 
         input. This is significantly slower.         
        """
        if preserve_topology:
            return self._unary_topology(lgeos.GEOSTopologyPreserveSimplify, c_double(tolerance))
        else:
            return self._unary_topology(lgeos.GEOSSimplify, c_double(tolerance))        

    def relate(self, other):
        "Returns the DE-9IM intersection matrix for this Geometry and the other."
        return string_at(lgeos.GEOSRelate(self._ptr(), other._ptr()))

    def difference(self, other):
        """Returns a Geometry representing the points making up this Geometry
        that do not make up other."""
        return self._binary_topology(lgeos.GEOSDifference, other)

    def sym_difference(self, other):
        """
        Returns a set combining the points in this Geometry not in other,
         and the points in other not in this Geometry.
        """
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
        if status != 1: return None
        else: return a.value

    def distance(self, other):
        """
        Returns the distance between the closest points on this Geometry
         and the other. Units will be in those of the coordinate system of
         the Geometry.
        """
        if not isinstance(other, GEOSGeometry): 
            raise TypeError, 'distance() works only on other GEOS Geometries.'
        dist = c_double()
        status = lgeos.GEOSDistance(self._ptr(), other._ptr(), byref(dist))
        if status != 1: return None
        else: return dist.value

    @property
    def length(self):
        """
        Returns the length of this Geometry (e.g., 0 for point, or the
         circumfrence of a Polygon).
        """
        l = c_double()
        status = lgeos.GEOSLength(self._ptr(), byref(l))
        if status != 1: return None
        else: return l.value
    
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
