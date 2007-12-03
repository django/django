"""
 This module contains the 'base' GEOSGeometry object -- all GEOS Geometries
 inherit from this object.
"""
# Python, ctypes and types dependencies.
import re
from ctypes import addressof, byref, c_double, c_size_t
from types import StringType, UnicodeType, IntType, FloatType, BufferType

# GEOS-related dependencies.
from django.contrib.gis.geos.coordseq import GEOSCoordSeq
from django.contrib.gis.geos.error import GEOSException
from django.contrib.gis.geos.libgeos import GEOM_PTR

# All other functions in this module come from the ctypes 
# prototypes module -- which handles all interaction with
# the underlying GEOS library.
from django.contrib.gis.geos.prototypes import * 

# Trying to import GDAL libraries, if available.  Have to place in
# try/except since this package may be used outside GeoDjango.
try:
    from django.contrib.gis.gdal import OGRGeometry, SpatialReference
    HAS_GDAL=True
except:
    HAS_GDAL=False

# Regular expression for recognizing HEXEWKB and WKT.  A prophylactic measure
# to prevent potentially malicious input from reaching the underlying C
# library.  Not a substitute for good web security programming practices.
hex_regex = re.compile(r'^[0-9A-F]+$', re.I)
wkt_regex = re.compile(r'^(POINT|LINESTRING|LINEARRING|POLYGON|MULTIPOINT|MULTILINESTRING|MULTIPOLYGON|GEOMETRYCOLLECTION)[ACEGIMLONPSRUTY\d,\.\-\(\) ]+$', re.I)

class GEOSGeometry(object):
    "A class that, generally, encapsulates a GEOS geometry."

    # Initially, the geometry pointer is NULL
    _ptr = None

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
                g = from_hex(geo_input, len(geo_input))
            elif wkt_regex.match(geo_input):
                # Otherwise, the geometry is in WKT form.
                g = from_wkt(geo_input)
            else:
                raise ValueError('String or unicode input unrecognized as WKT or HEXEWKB.')
        elif isinstance(geo_input, GEOM_PTR):
            # When the input is a pointer to a geomtry (GEOM_PTR).
            g = geo_input
        elif isinstance(geo_input, BufferType):
            # When the input is a buffer (WKB).
            wkb_input = str(geo_input)
            g = from_wkb(wkb_input, len(wkb_input))
        else:
            # Invalid geometry type.
            raise TypeError('Improper geometry input type: %s' % str(type(geo_input)))

        if bool(g):
            # Setting the pointer object with a valid pointer.
            self._ptr = g
        else:
            raise GEOSException('Could not initialize GEOS Geometry with given input.')

        # Setting the SRID, if given.
        if srid and isinstance(srid, int): self.srid = srid

        # Setting the class type (e.g., Point, Polygon, etc.)
        self.__class__ = GEOS_CLASSES[self.geom_typeid]

        # Setting the coordinate sequence for the geometry (will be None on 
        #  geometries that do not have coordinate sequences)
        self._set_cs()

    def __del__(self):
        """
        Destroys this Geometry; in other words, frees the memory used by the
        GEOS C++ object.
        """
        if self._ptr: destroy_geom(self._ptr)

    def __str__(self):
        "WKT is used for the string representation."
        return self.wkt

    def __repr__(self):
        "Short-hand representation because WKT may be very large."
        return '<%s object at %s>' % (self.geom_type, hex(addressof(self._ptr)))

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

    # g = g1 & g2
    def __and__(self, other):
        "Returns the intersection of this Geometry and the other."
        return self.intersection(other)

    # g = g1 - g2
    def __sub__(self, other):
        "Return the difference this Geometry and the other."
        return self.difference(other)

    # g = g1 ^ g2
    def __xor__(self, other):
        "Return the symmetric difference of this Geometry and the other."
        return self.sym_difference(other)

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
            self._cs = GEOSCoordSeq(get_cs(self._ptr), self.hasz)
        else:
            self._cs = None

    @property
    def coord_seq(self):
        "Returns a clone of the coordinate sequence for this Geometry."
        return self._cs.clone()

    #### Geometry Info ####
    @property
    def geom_type(self):
        "Returns a string representing the Geometry type, e.g. 'Polygon'"
        return geos_type(self._ptr)

    @property
    def geom_typeid(self):
        "Returns an integer representing the Geometry type."
        return geos_typeid(self._ptr)

    @property
    def num_geom(self):
        "Returns the number of geometries in the Geometry."
        return get_num_geoms(self._ptr)

    @property
    def num_coords(self):
        "Returns the number of coordinates in the Geometry."
        return get_num_coords(self._ptr)

    @property
    def num_points(self):
        "Returns the number points, or coordinates, in the Geometry."
        return self.num_coords

    @property
    def dims(self):
        "Returns the dimension of this Geometry (0=point, 1=line, 2=surface)."
        return get_dims(self._ptr)

    def normalize(self):
        "Converts this Geometry to normal form (or canonical form)."
        return geos_normalize(self._ptr)

    #### Unary predicates ####
    @property
    def empty(self):
        """
        Returns a boolean indicating whether the set of points in this Geometry 
        are empty.
        """
        return geos_isempty(self._ptr)

    @property
    def hasz(self):
        "Returns whether the geometry has a 3D dimension."
        return geos_hasz(self._ptr)

    @property
    def ring(self):
        "Returns whether or not the geometry is a ring."
        return geos_isring(self._ptr)

    @property
    def simple(self):
        "Returns false if the Geometry not simple."
        return geos_issimple(self._ptr)

    @property
    def valid(self):
        "This property tests the validity of this Geometry."
        return geos_isvalid(self._ptr)

    #### Binary predicates. ####
    def contains(self, other):
        "Returns true if other.within(this) returns true."
        return geos_contains(self._ptr, other._ptr)

    def crosses(self, other):
        """
        Returns true if the DE-9IM intersection matrix for the two Geometries
        is T*T****** (for a point and a curve,a point and an area or a line and
        an area) 0******** (for two curves).
        """
        return geos_crosses(self._ptr, other._ptr)

    def disjoint(self, other):
        """
        Returns true if the DE-9IM intersection matrix for the two Geometries
        is FF*FF****.
        """
        return geos_disjoint(self._ptr, other._ptr)

    def equals(self, other):
        """
        Returns true if the DE-9IM intersection matrix for the two Geometries 
        is T*F**FFF*.
        """
        return geos_equals(self._ptr, other._ptr)

    def equals_exact(self, other, tolerance=0):
        """
        Returns true if the two Geometries are exactly equal, up to a
        specified tolerance.
        """
        return geos_equalsexact(self._ptr, other._ptr, float(tolerance))

    def intersects(self, other):
        "Returns true if disjoint returns false."
        return geos_intersects(self._ptr, other._ptr)

    def overlaps(self, other):
        """
        Returns true if the DE-9IM intersection matrix for the two Geometries
        is T*T***T** (for two points or two surfaces) 1*T***T** (for two curves).
        """
        return geos_overlaps(self._ptr, other._ptr)

    def relate_pattern(self, other, pattern):
        """
        Returns true if the elements in the DE-9IM intersection matrix for the
        two Geometries match the elements in pattern.
        """
        if not isinstance(pattern, StringType) or len(pattern) > 9:
            raise GEOSException('invalid intersection matrix pattern')
        return geos_relatepattern(self._ptr, other._ptr, pattern)

    def touches(self, other):
        """
        Returns true if the DE-9IM intersection matrix for the two Geometries
        is FT*******, F**T***** or F***T****.
        """
        return geos_touches(self._ptr, other._ptr)

    def within(self, other):
        """
        Returns true if the DE-9IM intersection matrix for the two Geometries
        is T*F**F***.
        """
        return geos_within(self._ptr, other._ptr)

    #### SRID Routines ####
    def get_srid(self):
        "Gets the SRID for the geometry, returns None if no SRID is set."
        s = geos_get_srid(self._ptr)
        if s == 0: return None
        else: return s

    def set_srid(self, srid):
        "Sets the SRID for the geometry."
        geos_set_srid(self._ptr, srid)
    srid = property(get_srid, set_srid)

    #### Output Routines ####
    @property
    def wkt(self):
        "Returns the WKT (Well-Known Text) of the Geometry."
        return to_wkt(self._ptr)

    @property
    def hex(self):
        """
        Returns the HEX of the Geometry -- please note that the SRID is not
        included in this representation, because the GEOS C library uses
        -1 by default, even if the SRID is set.
        """
        # A possible faster, all-python, implementation: 
        #  str(self.wkb).encode('hex')
        return to_hex(self._ptr, byref(c_size_t()))

    @property
    def wkb(self):
        "Returns the WKB of the Geometry as a buffer."
        bin = to_wkb(self._ptr, byref(c_size_t()))
        return buffer(bin)

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

    @property
    def crs(self):
        "Alias for `srs` property."
        return self.srs

    #### Topology Routines ####
    def _topology(self, gptr):
        "Helper routine to return Geometry from the given pointer."
        return GEOSGeometry(gptr, srid=self.srid)

    @property
    def boundary(self):
        "Returns the boundary as a newly allocated Geometry object."
        return self._topology(geos_boundary(self._ptr))

    def buffer(self, width, quadsegs=8):
        """
        Returns a geometry that represents all points whose distance from this
        Geometry is less than or equal to distance. Calculations are in the
        Spatial Reference System of this Geometry. The optional third parameter sets
        the number of segment used to approximate a quarter circle (defaults to 8).
        (Text from PostGIS documentation at ch. 6.1.3)
        """
        return self._topology(geos_buffer(self._ptr, width, quadsegs))

    @property
    def centroid(self):
        """
        The centroid is equal to the centroid of the set of component Geometries
        of highest dimension (since the lower-dimension geometries contribute zero
        "weight" to the centroid).
        """
        return self._topology(geos_centroid(self._ptr))

    @property
    def convex_hull(self):
        """
        Returns the smallest convex Polygon that contains all the points 
        in the Geometry.
        """
        return self._topology(geos_convexhull(self._ptr))

    def difference(self, other):
        """
        Returns a Geometry representing the points making up this Geometry
        that do not make up other.
        """
        return self._topology(geos_difference(self._ptr, other._ptr))

    @property
    def envelope(self):
        "Return the envelope for this geometry (a polygon)."
        return self._topology(geos_envelope(self._ptr))

    def intersection(self, other):
        "Returns a Geometry representing the points shared by this Geometry and other."
        return self._topology(geos_intersection(self._ptr, other._ptr))

    @property
    def point_on_surface(self):
        "Computes an interior point of this Geometry."
        return self._topology(geos_pointonsurface(self._ptr))

    def relate(self, other):
        "Returns the DE-9IM intersection matrix for this Geometry and the other."
        return geos_relate(self._ptr, other._ptr)

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
            return self._topology(geos_preservesimplify(self._ptr, tolerance))
        else:
            return self._topology(geos_simplify(self._ptr, tolerance))

    def sym_difference(self, other):
        """
        Returns a set combining the points in this Geometry not in other,
        and the points in other not in this Geometry.
        """
        return self._topology(geos_symdifference(self._ptr, other._ptr))

    def union(self, other):
        "Returns a Geometry representing all the points in this Geometry and other."
        return self._topology(geos_union(self._ptr, other._ptr))

    #### Other Routines ####
    @property
    def area(self):
        "Returns the area of the Geometry."
        return geos_area(self._ptr, byref(c_double()))

    def distance(self, other):
        """
        Returns the distance between the closest points on this Geometry
        and the other. Units will be in those of the coordinate system of
        the Geometry.
        """
        if not isinstance(other, GEOSGeometry): 
            raise TypeError('distance() works only on other GEOS Geometries.')
        return geos_distance(self._ptr, other._ptr, byref(c_double()))

    @property
    def length(self):
        """
        Returns the length of this Geometry (e.g., 0 for point, or the
        circumfrence of a Polygon).
        """
        return geos_length(self._ptr, byref(c_double()))
    
    def clone(self):
        "Clones this Geometry."
        return GEOSGeometry(geom_clone(self._ptr), srid=self.srid)

# Class mapping dictionary
from django.contrib.gis.geos.geometries import Point, Polygon, LineString, LinearRing
from django.contrib.gis.geos.collections import GeometryCollection, MultiPoint, MultiLineString, MultiPolygon
GEOS_CLASSES = {0 : Point,
                1 : LineString,
                2 : LinearRing,
                3 : Polygon,
                4 : MultiPoint,
                5 : MultiLineString,
                6 : MultiPolygon,
                7 : GeometryCollection,
                }
