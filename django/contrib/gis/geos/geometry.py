"""
 This module contains the 'base' GEOSGeometry object -- all GEOS Geometries
 inherit from this object.
"""
# Python, ctypes and types dependencies.
import re
import warnings
from ctypes import addressof, byref, c_double, c_size_t

# super-class for mutable list behavior
from django.contrib.gis.geos.mutable_list import ListMixin

# GEOS-related dependencies.
from django.contrib.gis.geos.base import GEOSBase, gdal
from django.contrib.gis.geos.coordseq import GEOSCoordSeq
from django.contrib.gis.geos.error import GEOSException, GEOSIndexError
from django.contrib.gis.geos.libgeos import GEOM_PTR, GEOS_PREPARE
from django.contrib.gis.geos.mutable_list import ListMixin

# All other functions in this module come from the ctypes
# prototypes module -- which handles all interaction with
# the underlying GEOS library.
from django.contrib.gis.geos import prototypes as capi

# These functions provide access to a thread-local instance
# of their corresponding GEOS I/O class.
from django.contrib.gis.geos.prototypes.io import wkt_r, wkt_w, wkb_r, wkb_w, ewkb_w, ewkb_w3d

# For recognizing geometry input.
from django.contrib.gis.geometry.regex import hex_regex, wkt_regex, json_regex

class GEOSGeometry(GEOSBase, ListMixin):
    "A class that, generally, encapsulates a GEOS geometry."

    # Raise GEOSIndexError instead of plain IndexError
    # (see ticket #4740 and GEOSIndexError docstring)
    _IndexError = GEOSIndexError

    ptr_type = GEOM_PTR

    #### Python 'magic' routines ####
    def __init__(self, geo_input, srid=None):
        """
        The base constructor for GEOS geometry objects, and may take the
        following inputs:

         * strings:
            - WKT
            - HEXEWKB (a PostGIS-specific canonical form)
            - GeoJSON (requires GDAL)
         * buffer:
            - WKB

        The `srid` keyword is used to specify the Source Reference Identifier
        (SRID) number for this Geometry.  If not set, the SRID will be None.
        """
        if isinstance(geo_input, basestring):
            if isinstance(geo_input, unicode):
                # Encoding to ASCII, WKT or HEXEWKB doesn't need any more.
                geo_input = geo_input.encode('ascii')

            wkt_m = wkt_regex.match(geo_input)
            if wkt_m:
                # Handling WKT input.
                if wkt_m.group('srid'): srid = int(wkt_m.group('srid'))
                g = wkt_r().read(wkt_m.group('wkt'))
            elif hex_regex.match(geo_input):
                # Handling HEXEWKB input.
                g = wkb_r().read(geo_input)
            elif gdal.GEOJSON and json_regex.match(geo_input):
                # Handling GeoJSON input.
                g = wkb_r().read(gdal.OGRGeometry(geo_input).wkb)
            else:
                raise ValueError('String or unicode input unrecognized as WKT EWKT, and HEXEWKB.')
        elif isinstance(geo_input, GEOM_PTR):
            # When the input is a pointer to a geomtry (GEOM_PTR).
            g = geo_input
        elif isinstance(geo_input, buffer):
            # When the input is a buffer (WKB).
            g = wkb_r().read(geo_input)
        elif isinstance(geo_input, GEOSGeometry):
            g = capi.geom_clone(geo_input.ptr)
        else:
            # Invalid geometry type.
            raise TypeError('Improper geometry input type: %s' % str(type(geo_input)))

        if bool(g):
            # Setting the pointer object with a valid pointer.
            self.ptr = g
        else:
            raise GEOSException('Could not initialize GEOS Geometry with given input.')

        # Post-initialization setup.
        self._post_init(srid)

    def _post_init(self, srid):
        "Helper routine for performing post-initialization setup."
        # Setting the SRID, if given.
        if srid and isinstance(srid, int): self.srid = srid

        # Setting the class type (e.g., Point, Polygon, etc.)
        self.__class__ = GEOS_CLASSES[self.geom_typeid]

        # Setting the coordinate sequence for the geometry (will be None on
        # geometries that do not have coordinate sequences)
        self._set_cs()

    def __del__(self):
        """
        Destroys this Geometry; in other words, frees the memory used by the
        GEOS C++ object.
        """
        if self._ptr: capi.destroy_geom(self._ptr)

    def __copy__(self):
        """
        Returns a clone because the copy of a GEOSGeometry may contain an
        invalid pointer location if the original is garbage collected.
        """
        return self.clone()

    def __deepcopy__(self, memodict):
        """
        The `deepcopy` routine is used by the `Node` class of django.utils.tree;
        thus, the protocol routine needs to be implemented to return correct
        copies (clones) of these GEOS objects, which use C pointers.
        """
        return self.clone()

    def __str__(self):
        "WKT is used for the string representation."
        return self.wkt

    def __repr__(self):
        "Short-hand representation because WKT may be very large."
        return '<%s object at %s>' % (self.geom_type, hex(addressof(self.ptr)))

    # Pickling support
    def __getstate__(self):
        # The pickled state is simply a tuple of the WKB (in string form)
        # and the SRID.
        return str(self.wkb), self.srid

    def __setstate__(self, state):
        # Instantiating from the tuple state that was pickled.
        wkb, srid = state
        ptr = wkb_r().read(buffer(wkb))
        if not ptr: raise GEOSException('Invalid Geometry loaded from pickled state.')
        self.ptr = ptr
        self._post_init(srid)

    # Comparison operators
    def __eq__(self, other):
        """
        Equivalence testing, a Geometry may be compared with another Geometry
        or a WKT representation.
        """
        if isinstance(other, basestring):
            return self.wkt == other
        elif isinstance(other, GEOSGeometry):
            return self.equals_exact(other)
        else:
            return False

    def __ne__(self, other):
        "The not equals operator."
        return not (self == other)

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
            self._cs = GEOSCoordSeq(capi.get_cs(self.ptr), self.hasz)
        else:
            self._cs = None

    @property
    def coord_seq(self):
        "Returns a clone of the coordinate sequence for this Geometry."
        if self.has_cs:
            return self._cs.clone()

    #### Geometry Info ####
    @property
    def geom_type(self):
        "Returns a string representing the Geometry type, e.g. 'Polygon'"
        return capi.geos_type(self.ptr)

    @property
    def geom_typeid(self):
        "Returns an integer representing the Geometry type."
        return capi.geos_typeid(self.ptr)

    @property
    def num_geom(self):
        "Returns the number of geometries in the Geometry."
        return capi.get_num_geoms(self.ptr)

    @property
    def num_coords(self):
        "Returns the number of coordinates in the Geometry."
        return capi.get_num_coords(self.ptr)

    @property
    def num_points(self):
        "Returns the number points, or coordinates, in the Geometry."
        return self.num_coords

    @property
    def dims(self):
        "Returns the dimension of this Geometry (0=point, 1=line, 2=surface)."
        return capi.get_dims(self.ptr)

    def normalize(self):
        "Converts this Geometry to normal form (or canonical form)."
        return capi.geos_normalize(self.ptr)

    #### Unary predicates ####
    @property
    def empty(self):
        """
        Returns a boolean indicating whether the set of points in this Geometry
        are empty.
        """
        return capi.geos_isempty(self.ptr)

    @property
    def hasz(self):
        "Returns whether the geometry has a 3D dimension."
        return capi.geos_hasz(self.ptr)

    @property
    def ring(self):
        "Returns whether or not the geometry is a ring."
        return capi.geos_isring(self.ptr)

    @property
    def simple(self):
        "Returns false if the Geometry not simple."
        return capi.geos_issimple(self.ptr)

    @property
    def valid(self):
        "This property tests the validity of this Geometry."
        return capi.geos_isvalid(self.ptr)

    @property
    def valid_reason(self):
        """
        Returns a string containing the reason for any invalidity.
        """
        if not GEOS_PREPARE:
            raise GEOSException('Upgrade GEOS to 3.1 to get validity reason.')
        return capi.geos_isvalidreason(self.ptr)

    #### Binary predicates. ####
    def contains(self, other):
        "Returns true if other.within(this) returns true."
        return capi.geos_contains(self.ptr, other.ptr)

    def crosses(self, other):
        """
        Returns true if the DE-9IM intersection matrix for the two Geometries
        is T*T****** (for a point and a curve,a point and an area or a line and
        an area) 0******** (for two curves).
        """
        return capi.geos_crosses(self.ptr, other.ptr)

    def disjoint(self, other):
        """
        Returns true if the DE-9IM intersection matrix for the two Geometries
        is FF*FF****.
        """
        return capi.geos_disjoint(self.ptr, other.ptr)

    def equals(self, other):
        """
        Returns true if the DE-9IM intersection matrix for the two Geometries
        is T*F**FFF*.
        """
        return capi.geos_equals(self.ptr, other.ptr)

    def equals_exact(self, other, tolerance=0):
        """
        Returns true if the two Geometries are exactly equal, up to a
        specified tolerance.
        """
        return capi.geos_equalsexact(self.ptr, other.ptr, float(tolerance))

    def intersects(self, other):
        "Returns true if disjoint returns false."
        return capi.geos_intersects(self.ptr, other.ptr)

    def overlaps(self, other):
        """
        Returns true if the DE-9IM intersection matrix for the two Geometries
        is T*T***T** (for two points or two surfaces) 1*T***T** (for two curves).
        """
        return capi.geos_overlaps(self.ptr, other.ptr)

    def relate_pattern(self, other, pattern):
        """
        Returns true if the elements in the DE-9IM intersection matrix for the
        two Geometries match the elements in pattern.
        """
        if not isinstance(pattern, basestring) or len(pattern) > 9:
            raise GEOSException('invalid intersection matrix pattern')
        return capi.geos_relatepattern(self.ptr, other.ptr, pattern)

    def touches(self, other):
        """
        Returns true if the DE-9IM intersection matrix for the two Geometries
        is FT*******, F**T***** or F***T****.
        """
        return capi.geos_touches(self.ptr, other.ptr)

    def within(self, other):
        """
        Returns true if the DE-9IM intersection matrix for the two Geometries
        is T*F**F***.
        """
        return capi.geos_within(self.ptr, other.ptr)

    #### SRID Routines ####
    def get_srid(self):
        "Gets the SRID for the geometry, returns None if no SRID is set."
        s = capi.geos_get_srid(self.ptr)
        if s == 0: return None
        else: return s

    def set_srid(self, srid):
        "Sets the SRID for the geometry."
        capi.geos_set_srid(self.ptr, srid)
    srid = property(get_srid, set_srid)

    #### Output Routines ####
    @property
    def ewkt(self):
        """
        Returns the EWKT (WKT + SRID) of the Geometry.  Note that Z values
        are *not* included in this representation because GEOS does not yet
        support serializing them.
        """
        if self.get_srid(): return 'SRID=%s;%s' % (self.srid, self.wkt)
        else: return self.wkt

    @property
    def wkt(self):
        "Returns the WKT (Well-Known Text) representation of this Geometry."
        return wkt_w().write(self)

    @property
    def hex(self):
        """
        Returns the WKB of this Geometry in hexadecimal form.  Please note
        that the SRID and Z values are not included in this representation
        because it is not a part of the OGC specification (use the `hexewkb`
        property instead).
        """
        # A possible faster, all-python, implementation:
        #  str(self.wkb).encode('hex')
        return wkb_w().write_hex(self)

    @property
    def hexewkb(self):
        """
        Returns the EWKB of this Geometry in hexadecimal form.  This is an
        extension of the WKB specification that includes SRID and Z values
        that are a part of this geometry.
        """
        if self.hasz:
            if not GEOS_PREPARE:
                # See: http://trac.osgeo.org/geos/ticket/216
                raise GEOSException('Upgrade GEOS to 3.1 to get valid 3D HEXEWKB.')
            return ewkb_w3d().write_hex(self)
        else:
            return ewkb_w().write_hex(self)

    @property
    def json(self):
        """
        Returns GeoJSON representation of this Geometry if GDAL 1.5+
        is installed.
        """
        if gdal.GEOJSON:
            return self.ogr.json
        else:
            raise GEOSException('GeoJSON output only supported on GDAL 1.5+.')
    geojson = json

    @property
    def wkb(self):
        """
        Returns the WKB (Well-Known Binary) representation of this Geometry
        as a Python buffer.  SRID and Z values are not included, use the
        `ewkb` property instead.
        """
        return wkb_w().write(self)

    @property
    def ewkb(self):
        """
        Return the EWKB representation of this Geometry as a Python buffer.
        This is an extension of the WKB specification that includes any SRID
        and Z values that are a part of this geometry.
        """
        if self.hasz:
            if not GEOS_PREPARE:
                # See: http://trac.osgeo.org/geos/ticket/216
                raise GEOSException('Upgrade GEOS to 3.1 to get valid 3D EWKB.')
            return ewkb_w3d().write(self)
        else:
            return ewkb_w().write(self)

    @property
    def kml(self):
        "Returns the KML representation of this Geometry."
        gtype = self.geom_type
        return '<%s>%s</%s>' % (gtype, self.coord_seq.kml, gtype)

    @property
    def prepared(self):
        """
        Returns a PreparedGeometry corresponding to this geometry -- it is
        optimized for the contains, intersects, and covers operations.
        """
        if GEOS_PREPARE:
            return PreparedGeometry(self)
        else:
            raise GEOSException('GEOS 3.1+ required for prepared geometry support.')

    #### GDAL-specific output routines ####
    @property
    def ogr(self):
        "Returns the OGR Geometry for this Geometry."
        if gdal.HAS_GDAL:
            if self.srid:
                return gdal.OGRGeometry(self.wkb, self.srid)
            else:
                return gdal.OGRGeometry(self.wkb)
        else:
            raise GEOSException('GDAL required to convert to an OGRGeometry.')

    @property
    def srs(self):
        "Returns the OSR SpatialReference for SRID of this Geometry."
        if gdal.HAS_GDAL:
            if self.srid:
                return gdal.SpatialReference(self.srid)
            else:
                return None
        else:
            raise GEOSException('GDAL required to return a SpatialReference object.')

    @property
    def crs(self):
        "Alias for `srs` property."
        return self.srs

    def transform(self, ct, clone=False):
        """
        Requires GDAL. Transforms the geometry according to the given
        transformation object, which may be an integer SRID, and WKT or
        PROJ.4 string. By default, the geometry is transformed in-place and
        nothing is returned. However if the `clone` keyword is set, then this
        geometry will not be modified and a transformed clone will be returned
        instead.
        """
        srid = self.srid

        if ct == srid:
            # short-circuit where source & dest SRIDs match
            if clone:
                return self.clone()
            else:
                return

        if (srid is None) or (srid < 0):
            warnings.warn("Calling transform() with no SRID set does no transformation!",
                          stacklevel=2)
            warnings.warn("Calling transform() with no SRID will raise GEOSException in v1.5",
                          FutureWarning, stacklevel=2)
            return

        if not gdal.HAS_GDAL:
            raise GEOSException("GDAL library is not available to transform() geometry.")

        # Creating an OGR Geometry, which is then transformed.
        g = gdal.OGRGeometry(self.wkb, srid)
        g.transform(ct)
        # Getting a new GEOS pointer
        ptr = wkb_r().read(g.wkb)
        if clone:
            # User wants a cloned transformed geometry returned.
            return GEOSGeometry(ptr, srid=g.srid)
        if ptr:
            # Reassigning pointer, and performing post-initialization setup
            # again due to the reassignment.
            capi.destroy_geom(self.ptr)
            self.ptr = ptr
            self._post_init(g.srid)
        else:
            raise GEOSException('Transformed WKB was invalid.')

    #### Topology Routines ####
    def _topology(self, gptr):
        "Helper routine to return Geometry from the given pointer."
        return GEOSGeometry(gptr, srid=self.srid)

    @property
    def boundary(self):
        "Returns the boundary as a newly allocated Geometry object."
        return self._topology(capi.geos_boundary(self.ptr))

    def buffer(self, width, quadsegs=8):
        """
        Returns a geometry that represents all points whose distance from this
        Geometry is less than or equal to distance. Calculations are in the
        Spatial Reference System of this Geometry. The optional third parameter sets
        the number of segment used to approximate a quarter circle (defaults to 8).
        (Text from PostGIS documentation at ch. 6.1.3)
        """
        return self._topology(capi.geos_buffer(self.ptr, width, quadsegs))

    @property
    def centroid(self):
        """
        The centroid is equal to the centroid of the set of component Geometries
        of highest dimension (since the lower-dimension geometries contribute zero
        "weight" to the centroid).
        """
        return self._topology(capi.geos_centroid(self.ptr))

    @property
    def convex_hull(self):
        """
        Returns the smallest convex Polygon that contains all the points
        in the Geometry.
        """
        return self._topology(capi.geos_convexhull(self.ptr))

    def difference(self, other):
        """
        Returns a Geometry representing the points making up this Geometry
        that do not make up other.
        """
        return self._topology(capi.geos_difference(self.ptr, other.ptr))

    @property
    def envelope(self):
        "Return the envelope for this geometry (a polygon)."
        return self._topology(capi.geos_envelope(self.ptr))

    def intersection(self, other):
        "Returns a Geometry representing the points shared by this Geometry and other."
        return self._topology(capi.geos_intersection(self.ptr, other.ptr))

    @property
    def point_on_surface(self):
        "Computes an interior point of this Geometry."
        return self._topology(capi.geos_pointonsurface(self.ptr))

    def relate(self, other):
        "Returns the DE-9IM intersection matrix for this Geometry and the other."
        return capi.geos_relate(self.ptr, other.ptr)

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
            return self._topology(capi.geos_preservesimplify(self.ptr, tolerance))
        else:
            return self._topology(capi.geos_simplify(self.ptr, tolerance))

    def sym_difference(self, other):
        """
        Returns a set combining the points in this Geometry not in other,
        and the points in other not in this Geometry.
        """
        return self._topology(capi.geos_symdifference(self.ptr, other.ptr))

    def union(self, other):
        "Returns a Geometry representing all the points in this Geometry and other."
        return self._topology(capi.geos_union(self.ptr, other.ptr))

    #### Other Routines ####
    @property
    def area(self):
        "Returns the area of the Geometry."
        return capi.geos_area(self.ptr, byref(c_double()))

    def distance(self, other):
        """
        Returns the distance between the closest points on this Geometry
        and the other. Units will be in those of the coordinate system of
        the Geometry.
        """
        if not isinstance(other, GEOSGeometry):
            raise TypeError('distance() works only on other GEOS Geometries.')
        return capi.geos_distance(self.ptr, other.ptr, byref(c_double()))

    @property
    def extent(self):
        """
        Returns the extent of this geometry as a 4-tuple, consisting of
        (xmin, ymin, xmax, ymax).
        """
        env = self.envelope
        if isinstance(env, Point):
            xmin, ymin = env.tuple
            xmax, ymax = xmin, ymin
        else:
            xmin, ymin = env[0][0]
            xmax, ymax = env[0][2]
        return (xmin, ymin, xmax, ymax)

    @property
    def length(self):
        """
        Returns the length of this Geometry (e.g., 0 for point, or the
        circumfrence of a Polygon).
        """
        return capi.geos_length(self.ptr, byref(c_double()))

    def clone(self):
        "Clones this Geometry."
        return GEOSGeometry(capi.geom_clone(self.ptr), srid=self.srid)

# Class mapping dictionary.  Has to be at the end to avoid import
# conflicts with GEOSGeometry.
from django.contrib.gis.geos.linestring import LineString, LinearRing
from django.contrib.gis.geos.point import Point
from django.contrib.gis.geos.polygon import Polygon
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

# If supported, import the PreparedGeometry class.
if GEOS_PREPARE:
    from django.contrib.gis.geos.prepared import PreparedGeometry
