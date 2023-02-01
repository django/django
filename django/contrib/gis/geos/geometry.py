"""
 This module contains the 'base' GEOSGeometry object -- all GEOS Geometries
 inherit from this object.
"""
import re
from ctypes import addressof, byref, c_double

from django.contrib.gis import gdal
from django.contrib.gis.geometry import hex_regex, json_regex, wkt_regex
from django.contrib.gis.geos import prototypes as capi
from django.contrib.gis.geos.base import GEOSBase
from django.contrib.gis.geos.coordseq import GEOSCoordSeq
from django.contrib.gis.geos.error import GEOSException
from django.contrib.gis.geos.libgeos import GEOM_PTR
from django.contrib.gis.geos.mutable_list import ListMixin
from django.contrib.gis.geos.prepared import PreparedGeometry
from django.contrib.gis.geos.prototypes.io import ewkb_w, wkb_r, wkb_w, wkt_r, wkt_w
from django.utils.deconstruct import deconstructible
from django.utils.encoding import force_bytes, force_str


class GEOSGeometryBase(GEOSBase):
    _GEOS_CLASSES = None

    ptr_type = GEOM_PTR
    destructor = capi.destroy_geom
    has_cs = False  # Only Point, LineString, LinearRing have coordinate sequences

    def __init__(self, ptr, cls):
        self._ptr = ptr

        # Setting the class type (e.g., Point, Polygon, etc.)
        if type(self) in (GEOSGeometryBase, GEOSGeometry):
            if cls is None:
                if GEOSGeometryBase._GEOS_CLASSES is None:
                    # Inner imports avoid import conflicts with GEOSGeometry.
                    from .collections import (
                        GeometryCollection,
                        MultiLineString,
                        MultiPoint,
                        MultiPolygon,
                    )
                    from .linestring import LinearRing, LineString
                    from .point import Point
                    from .polygon import Polygon

                    GEOSGeometryBase._GEOS_CLASSES = {
                        0: Point,
                        1: LineString,
                        2: LinearRing,
                        3: Polygon,
                        4: MultiPoint,
                        5: MultiLineString,
                        6: MultiPolygon,
                        7: GeometryCollection,
                    }
                cls = GEOSGeometryBase._GEOS_CLASSES[self.geom_typeid]
            self.__class__ = cls
        self._post_init()

    def _post_init(self):
        "Perform post-initialization setup."
        # Setting the coordinate sequence for the geometry (will be None on
        # geometries that do not have coordinate sequences)
        self._cs = (
            GEOSCoordSeq(capi.get_cs(self.ptr), self.hasz) if self.has_cs else None
        )

    def __copy__(self):
        """
        Return a clone because the copy of a GEOSGeometry may contain an
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
        "EWKT is used for the string representation."
        return self.ewkt

    def __repr__(self):
        "Short-hand representation because WKT may be very large."
        return "<%s object at %s>" % (self.geom_type, hex(addressof(self.ptr)))

    # Pickling support
    def _to_pickle_wkb(self):
        return bytes(self.wkb)

    def _from_pickle_wkb(self, wkb):
        return wkb_r().read(memoryview(wkb))

    def __getstate__(self):
        # The pickled state is simply a tuple of the WKB (in string form)
        # and the SRID.
        return self._to_pickle_wkb(), self.srid

    def __setstate__(self, state):
        # Instantiating from the tuple state that was pickled.
        wkb, srid = state
        ptr = self._from_pickle_wkb(wkb)
        if not ptr:
            raise GEOSException("Invalid Geometry loaded from pickled state.")
        self.ptr = ptr
        self._post_init()
        self.srid = srid

    @classmethod
    def _from_wkb(cls, wkb):
        return wkb_r().read(wkb)

    @staticmethod
    def from_ewkt(ewkt):
        ewkt = force_bytes(ewkt)
        srid = None
        parts = ewkt.split(b";", 1)
        if len(parts) == 2:
            srid_part, wkt = parts
            match = re.match(rb"SRID=(?P<srid>\-?\d+)", srid_part)
            if not match:
                raise ValueError("EWKT has invalid SRID part.")
            srid = int(match["srid"])
        else:
            wkt = ewkt
        if not wkt:
            raise ValueError("Expected WKT but got an empty string.")
        return GEOSGeometry(GEOSGeometry._from_wkt(wkt), srid=srid)

    @staticmethod
    def _from_wkt(wkt):
        return wkt_r().read(wkt)

    @classmethod
    def from_gml(cls, gml_string):
        return gdal.OGRGeometry.from_gml(gml_string).geos

    # Comparison operators
    def __eq__(self, other):
        """
        Equivalence testing, a Geometry may be compared with another Geometry
        or an EWKT representation.
        """
        if isinstance(other, str):
            try:
                other = GEOSGeometry.from_ewkt(other)
            except (ValueError, GEOSException):
                return False
        return (
            isinstance(other, GEOSGeometry)
            and self.srid == other.srid
            and self.equals_exact(other)
        )

    def __hash__(self):
        return hash((self.srid, self.wkt))

    # ### Geometry set-like operations ###
    # Thanks to Sean Gillies for inspiration:
    #  http://lists.gispython.org/pipermail/community/2007-July/001034.html
    # g = g1 | g2
    def __or__(self, other):
        "Return the union of this Geometry and the other."
        return self.union(other)

    # g = g1 & g2
    def __and__(self, other):
        "Return the intersection of this Geometry and the other."
        return self.intersection(other)

    # g = g1 - g2
    def __sub__(self, other):
        "Return the difference this Geometry and the other."
        return self.difference(other)

    # g = g1 ^ g2
    def __xor__(self, other):
        "Return the symmetric difference of this Geometry and the other."
        return self.sym_difference(other)

    # #### Coordinate Sequence Routines ####
    @property
    def coord_seq(self):
        "Return a clone of the coordinate sequence for this Geometry."
        if self.has_cs:
            return self._cs.clone()

    # #### Geometry Info ####
    @property
    def geom_type(self):
        "Return a string representing the Geometry type, e.g. 'Polygon'"
        return capi.geos_type(self.ptr).decode()

    @property
    def geom_typeid(self):
        "Return an integer representing the Geometry type."
        return capi.geos_typeid(self.ptr)

    @property
    def num_geom(self):
        "Return the number of geometries in the Geometry."
        return capi.get_num_geoms(self.ptr)

    @property
    def num_coords(self):
        "Return the number of coordinates in the Geometry."
        return capi.get_num_coords(self.ptr)

    @property
    def num_points(self):
        "Return the number points, or coordinates, in the Geometry."
        return self.num_coords

    @property
    def dims(self):
        "Return the dimension of this Geometry (0=point, 1=line, 2=surface)."
        return capi.get_dims(self.ptr)

    def normalize(self):
        "Convert this Geometry to normal form (or canonical form)."
        capi.geos_normalize(self.ptr)

    # #### Unary predicates ####
    @property
    def empty(self):
        """
        Return a boolean indicating whether the set of points in this Geometry
        are empty.
        """
        return capi.geos_isempty(self.ptr)

    @property
    def hasz(self):
        "Return whether the geometry has a 3D dimension."
        return capi.geos_hasz(self.ptr)

    @property
    def ring(self):
        "Return whether or not the geometry is a ring."
        return capi.geos_isring(self.ptr)

    @property
    def simple(self):
        "Return false if the Geometry isn't simple."
        return capi.geos_issimple(self.ptr)

    @property
    def valid(self):
        "Test the validity of this Geometry."
        return capi.geos_isvalid(self.ptr)

    @property
    def valid_reason(self):
        """
        Return a string containing the reason for any invalidity.
        """
        return capi.geos_isvalidreason(self.ptr).decode()

    # #### Binary predicates. ####
    def contains(self, other):
        "Return true if other.within(this) returns true."
        return capi.geos_contains(self.ptr, other.ptr)

    def covers(self, other):
        """
        Return True if the DE-9IM Intersection Matrix for the two geometries is
        T*****FF*, *T****FF*, ***T**FF*, or ****T*FF*. If either geometry is
        empty, return False.
        """
        return capi.geos_covers(self.ptr, other.ptr)

    def crosses(self, other):
        """
        Return true if the DE-9IM intersection matrix for the two Geometries
        is T*T****** (for a point and a curve,a point and an area or a line and
        an area) 0******** (for two curves).
        """
        return capi.geos_crosses(self.ptr, other.ptr)

    def disjoint(self, other):
        """
        Return true if the DE-9IM intersection matrix for the two Geometries
        is FF*FF****.
        """
        return capi.geos_disjoint(self.ptr, other.ptr)

    def equals(self, other):
        """
        Return true if the DE-9IM intersection matrix for the two Geometries
        is T*F**FFF*.
        """
        return capi.geos_equals(self.ptr, other.ptr)

    def equals_exact(self, other, tolerance=0):
        """
        Return true if the two Geometries are exactly equal, up to a
        specified tolerance.
        """
        return capi.geos_equalsexact(self.ptr, other.ptr, float(tolerance))

    def intersects(self, other):
        "Return true if disjoint return false."
        return capi.geos_intersects(self.ptr, other.ptr)

    def overlaps(self, other):
        """
        Return true if the DE-9IM intersection matrix for the two Geometries
        is T*T***T** (for two points or two surfaces) 1*T***T** (for two curves).
        """
        return capi.geos_overlaps(self.ptr, other.ptr)

    def relate_pattern(self, other, pattern):
        """
        Return true if the elements in the DE-9IM intersection matrix for the
        two Geometries match the elements in pattern.
        """
        if not isinstance(pattern, str) or len(pattern) > 9:
            raise GEOSException("invalid intersection matrix pattern")
        return capi.geos_relatepattern(self.ptr, other.ptr, force_bytes(pattern))

    def touches(self, other):
        """
        Return true if the DE-9IM intersection matrix for the two Geometries
        is FT*******, F**T***** or F***T****.
        """
        return capi.geos_touches(self.ptr, other.ptr)

    def within(self, other):
        """
        Return true if the DE-9IM intersection matrix for the two Geometries
        is T*F**F***.
        """
        return capi.geos_within(self.ptr, other.ptr)

    # #### SRID Routines ####
    @property
    def srid(self):
        "Get the SRID for the geometry. Return None if no SRID is set."
        s = capi.geos_get_srid(self.ptr)
        if s == 0:
            return None
        else:
            return s

    @srid.setter
    def srid(self, srid):
        "Set the SRID for the geometry."
        capi.geos_set_srid(self.ptr, 0 if srid is None else srid)

    # #### Output Routines ####
    @property
    def ewkt(self):
        """
        Return the EWKT (SRID + WKT) of the Geometry.
        """
        srid = self.srid
        return "SRID=%s;%s" % (srid, self.wkt) if srid else self.wkt

    @property
    def wkt(self):
        "Return the WKT (Well-Known Text) representation of this Geometry."
        return wkt_w(dim=3 if self.hasz else 2, trim=True).write(self).decode()

    @property
    def hex(self):
        """
        Return the WKB of this Geometry in hexadecimal form. Please note
        that the SRID is not included in this representation because it is not
        a part of the OGC specification (use the `hexewkb` property instead).
        """
        # A possible faster, all-python, implementation:
        #  str(self.wkb).encode('hex')
        return wkb_w(dim=3 if self.hasz else 2).write_hex(self)

    @property
    def hexewkb(self):
        """
        Return the EWKB of this Geometry in hexadecimal form. This is an
        extension of the WKB specification that includes SRID value that are
        a part of this geometry.
        """
        return ewkb_w(dim=3 if self.hasz else 2).write_hex(self)

    @property
    def json(self):
        """
        Return GeoJSON representation of this Geometry.
        """
        return self.ogr.json

    geojson = json

    @property
    def wkb(self):
        """
        Return the WKB (Well-Known Binary) representation of this Geometry
        as a Python buffer.  SRID and Z values are not included, use the
        `ewkb` property instead.
        """
        return wkb_w(3 if self.hasz else 2).write(self)

    @property
    def ewkb(self):
        """
        Return the EWKB representation of this Geometry as a Python buffer.
        This is an extension of the WKB specification that includes any SRID
        value that are a part of this geometry.
        """
        return ewkb_w(3 if self.hasz else 2).write(self)

    @property
    def kml(self):
        "Return the KML representation of this Geometry."
        gtype = self.geom_type
        return "<%s>%s</%s>" % (gtype, self.coord_seq.kml, gtype)

    @property
    def prepared(self):
        """
        Return a PreparedGeometry corresponding to this geometry -- it is
        optimized for the contains, intersects, and covers operations.
        """
        return PreparedGeometry(self)

    # #### GDAL-specific output routines ####
    def _ogr_ptr(self):
        return gdal.OGRGeometry._from_wkb(self.wkb)

    @property
    def ogr(self):
        "Return the OGR Geometry for this Geometry."
        return gdal.OGRGeometry(self._ogr_ptr(), self.srs)

    @property
    def srs(self):
        "Return the OSR SpatialReference for SRID of this Geometry."
        if self.srid:
            try:
                return gdal.SpatialReference(self.srid)
            except (gdal.GDALException, gdal.SRSException):
                pass
        return None

    @property
    def crs(self):
        "Alias for `srs` property."
        return self.srs

    def transform(self, ct, clone=False):
        """
        Requires GDAL. Transform the geometry according to the given
        transformation object, which may be an integer SRID, and WKT or
        PROJ string. By default, transform the geometry in-place and return
        nothing. However if the `clone` keyword is set, don't modify the
        geometry and return a transformed clone instead.
        """
        srid = self.srid

        if ct == srid:
            # short-circuit where source & dest SRIDs match
            if clone:
                return self.clone()
            else:
                return

        if isinstance(ct, gdal.CoordTransform):
            # We don't care about SRID because CoordTransform presupposes
            # source SRS.
            srid = None
        elif srid is None or srid < 0:
            raise GEOSException("Calling transform() with no SRID set is not supported")

        # Creating an OGR Geometry, which is then transformed.
        g = gdal.OGRGeometry(self._ogr_ptr(), srid)
        g.transform(ct)
        # Getting a new GEOS pointer
        ptr = g._geos_ptr()
        if clone:
            # User wants a cloned transformed geometry returned.
            return GEOSGeometry(ptr, srid=g.srid)
        if ptr:
            # Reassigning pointer, and performing post-initialization setup
            # again due to the reassignment.
            capi.destroy_geom(self.ptr)
            self.ptr = ptr
            self._post_init()
            self.srid = g.srid
        else:
            raise GEOSException("Transformed WKB was invalid.")

    # #### Topology Routines ####
    def _topology(self, gptr):
        "Return Geometry from the given pointer."
        return GEOSGeometry(gptr, srid=self.srid)

    @property
    def boundary(self):
        "Return the boundary as a newly allocated Geometry object."
        return self._topology(capi.geos_boundary(self.ptr))

    def buffer(self, width, quadsegs=8):
        """
        Return a geometry that represents all points whose distance from this
        Geometry is less than or equal to distance. Calculations are in the
        Spatial Reference System of this Geometry. The optional third parameter sets
        the number of segment used to approximate a quarter circle (defaults to 8).
        (Text from PostGIS documentation at ch. 6.1.3)
        """
        return self._topology(capi.geos_buffer(self.ptr, width, quadsegs))

    def buffer_with_style(
        self, width, quadsegs=8, end_cap_style=1, join_style=1, mitre_limit=5.0
    ):
        """
        Same as buffer() but allows customizing the style of the buffer.

        End cap style can be round (1), flat (2), or square (3).
        Join style can be round (1), mitre (2), or bevel (3).
        Mitre ratio limit only affects mitered join style.
        """
        return self._topology(
            capi.geos_bufferwithstyle(
                self.ptr, width, quadsegs, end_cap_style, join_style, mitre_limit
            ),
        )

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
        Return the smallest convex Polygon that contains all the points
        in the Geometry.
        """
        return self._topology(capi.geos_convexhull(self.ptr))

    def difference(self, other):
        """
        Return a Geometry representing the points making up this Geometry
        that do not make up other.
        """
        return self._topology(capi.geos_difference(self.ptr, other.ptr))

    @property
    def envelope(self):
        "Return the envelope for this geometry (a polygon)."
        return self._topology(capi.geos_envelope(self.ptr))

    def intersection(self, other):
        "Return a Geometry representing the points shared by this Geometry and other."
        return self._topology(capi.geos_intersection(self.ptr, other.ptr))

    @property
    def point_on_surface(self):
        "Compute an interior point of this Geometry."
        return self._topology(capi.geos_pointonsurface(self.ptr))

    def relate(self, other):
        "Return the DE-9IM intersection matrix for this Geometry and the other."
        return capi.geos_relate(self.ptr, other.ptr).decode()

    def simplify(self, tolerance=0.0, preserve_topology=False):
        """
        Return the Geometry, simplified using the Douglas-Peucker algorithm
        to the specified tolerance (higher tolerance => less points).  If no
        tolerance provided, defaults to 0.

        By default, don't preserve topology - e.g. polygons can be split,
        collapse to lines or disappear holes can be created or disappear, and
        lines can cross. By specifying preserve_topology=True, the result will
        have the same dimension and number of components as the input. This is
        significantly slower.
        """
        if preserve_topology:
            return self._topology(capi.geos_preservesimplify(self.ptr, tolerance))
        else:
            return self._topology(capi.geos_simplify(self.ptr, tolerance))

    def sym_difference(self, other):
        """
        Return a set combining the points in this Geometry not in other,
        and the points in other not in this Geometry.
        """
        return self._topology(capi.geos_symdifference(self.ptr, other.ptr))

    @property
    def unary_union(self):
        "Return the union of all the elements of this geometry."
        return self._topology(capi.geos_unary_union(self.ptr))

    def union(self, other):
        "Return a Geometry representing all the points in this Geometry and other."
        return self._topology(capi.geos_union(self.ptr, other.ptr))

    # #### Other Routines ####
    @property
    def area(self):
        "Return the area of the Geometry."
        return capi.geos_area(self.ptr, byref(c_double()))

    def distance(self, other):
        """
        Return the distance between the closest points on this Geometry
        and the other. Units will be in those of the coordinate system of
        the Geometry.
        """
        if not isinstance(other, GEOSGeometry):
            raise TypeError("distance() works only on other GEOS Geometries.")
        return capi.geos_distance(self.ptr, other.ptr, byref(c_double()))

    @property
    def extent(self):
        """
        Return the extent of this geometry as a 4-tuple, consisting of
        (xmin, ymin, xmax, ymax).
        """
        from .point import Point

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
        Return the length of this Geometry (e.g., 0 for point, or the
        circumference of a Polygon).
        """
        return capi.geos_length(self.ptr, byref(c_double()))

    def clone(self):
        "Clone this Geometry."
        return GEOSGeometry(capi.geom_clone(self.ptr))


class LinearGeometryMixin:
    """
    Used for LineString and MultiLineString.
    """

    def interpolate(self, distance):
        return self._topology(capi.geos_interpolate(self.ptr, distance))

    def interpolate_normalized(self, distance):
        return self._topology(capi.geos_interpolate_normalized(self.ptr, distance))

    def project(self, point):
        from .point import Point

        if not isinstance(point, Point):
            raise TypeError("locate_point argument must be a Point")
        return capi.geos_project(self.ptr, point.ptr)

    def project_normalized(self, point):
        from .point import Point

        if not isinstance(point, Point):
            raise TypeError("locate_point argument must be a Point")
        return capi.geos_project_normalized(self.ptr, point.ptr)

    @property
    def merged(self):
        """
        Return the line merge of this Geometry.
        """
        return self._topology(capi.geos_linemerge(self.ptr))

    @property
    def closed(self):
        """
        Return whether or not this Geometry is closed.
        """
        return capi.geos_isclosed(self.ptr)


@deconstructible
class GEOSGeometry(GEOSGeometryBase, ListMixin):
    "A class that, generally, encapsulates a GEOS geometry."

    def __init__(self, geo_input, srid=None):
        """
        The base constructor for GEOS geometry objects. It may take the
        following inputs:

         * strings:
            - WKT
            - HEXEWKB (a PostGIS-specific canonical form)
            - GeoJSON (requires GDAL)
         * buffer:
            - WKB

        The `srid` keyword specifies the Source Reference Identifier (SRID)
        number for this Geometry. If not provided, it defaults to None.
        """
        input_srid = None
        if isinstance(geo_input, bytes):
            geo_input = force_str(geo_input)
        if isinstance(geo_input, str):
            wkt_m = wkt_regex.match(geo_input)
            if wkt_m:
                # Handle WKT input.
                if wkt_m["srid"]:
                    input_srid = int(wkt_m["srid"])
                g = self._from_wkt(force_bytes(wkt_m["wkt"]))
            elif hex_regex.match(geo_input):
                # Handle HEXEWKB input.
                g = wkb_r().read(force_bytes(geo_input))
            elif json_regex.match(geo_input):
                # Handle GeoJSON input.
                ogr = gdal.OGRGeometry.from_json(geo_input)
                g = ogr._geos_ptr()
                input_srid = ogr.srid
            else:
                raise ValueError("String input unrecognized as WKT EWKT, and HEXEWKB.")
        elif isinstance(geo_input, GEOM_PTR):
            # When the input is a pointer to a geometry (GEOM_PTR).
            g = geo_input
        elif isinstance(geo_input, memoryview):
            # When the input is a buffer (WKB).
            g = wkb_r().read(geo_input)
        elif isinstance(geo_input, GEOSGeometry):
            g = capi.geom_clone(geo_input.ptr)
        else:
            raise TypeError("Improper geometry input type: %s" % type(geo_input))

        if not g:
            raise GEOSException("Could not initialize GEOS Geometry with given input.")

        input_srid = input_srid or capi.geos_get_srid(g) or None
        if input_srid and srid and input_srid != srid:
            raise ValueError("Input geometry already has SRID: %d." % input_srid)

        super().__init__(g, None)
        # Set the SRID, if given.
        srid = input_srid or srid
        if srid and isinstance(srid, int):
            self.srid = srid
