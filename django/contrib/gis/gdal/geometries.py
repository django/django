"""
 The OGRGeometry is a wrapper for using the OGR Geometry class
 (see http://www.gdal.org/ogr/classOGRGeometry.html).  OGRGeometry
 may be instantiated when reading geometries from OGR Data Sources
 (e.g. SHP files), or when given OGC WKT (a string).

 While the 'full' API is not present yet, the API is "pythonic" unlike
 the traditional and "next-generation" OGR Python bindings.  One major
 advantage OGR Geometries have over their GEOS counterparts is support
 for spatial reference systems and their transformation.

 Example:
  >>> from django.contrib.gis.gdal import OGRGeometry, OGRGeomType, SpatialReference
  >>> wkt1, wkt2 = 'POINT(-90 30)', 'POLYGON((0 0, 5 0, 5 5, 0 5)'
  >>> pnt = OGRGeometry(wkt1)
  >>> print pnt
  POINT (-90 30)
  >>> mpnt = OGRGeometry(OGRGeomType('MultiPoint'), SpatialReference('WGS84'))
  >>> mpnt.add(wkt1)
  >>> mpnt.add(wkt1)
  >>> print mpnt
  MULTIPOINT (-90 30,-90 30)
  >>> print mpnt.srs.name
  WGS 84
  >>> print mpnt.srs.proj
  +proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs
  >>> mpnt.transform_to(SpatialReference('NAD27'))
  >>> print mpnt.proj
  +proj=longlat +ellps=clrk66 +datum=NAD27 +no_defs
  >>> print mpnt
  MULTIPOINT (-89.999930378602485 29.999797886557641,-89.999930378602485 29.999797886557641)
  
  The OGRGeomType class is to make it easy to specify an OGR geometry type:
  >>> from django.contrib.gis.gdal import OGRGeomType
  >>> gt1 = OGRGeomType(3) # Using an integer for the type
  >>> gt2 = OGRGeomType('Polygon') # Using a string
  >>> gt3 = OGRGeomType('POLYGON') # It's case-insensitive
  >>> print gt1 == 3, gt1 == 'Polygon' # Equivalence works w/non-OGRGeomType objects
  True
"""
# Python library requisites.
import re, sys
from binascii import a2b_hex
from ctypes import byref, string_at, c_char_p, c_double, c_ubyte, c_void_p
from types import UnicodeType

# Getting GDAL prerequisites
from django.contrib.gis.gdal.envelope import Envelope, OGREnvelope
from django.contrib.gis.gdal.error import OGRException, OGRIndexError, SRSException
from django.contrib.gis.gdal.geomtype import OGRGeomType
from django.contrib.gis.gdal.srs import SpatialReference, CoordTransform

# Getting the ctypes prototype functions that interface w/the GDAL C library.
from django.contrib.gis.gdal.prototypes.geom import *
from django.contrib.gis.gdal.prototypes.srs import clone_srs

# For more information, see the OGR C API source code:
#  http://www.gdal.org/ogr/ogr__api_8h.html
#
# The OGR_G_* routines are relevant here.

# Regular expressions for recognizing HEXEWKB and WKT.
hex_regex = re.compile(r'^[0-9A-F]+$', re.I)
wkt_regex = re.compile(r'^(?P<type>POINT|LINESTRING|LINEARRING|POLYGON|MULTIPOINT|MULTILINESTRING|MULTIPOLYGON|GEOMETRYCOLLECTION)[ACEGIMLONPSRUTY\d,\.\-\(\) ]+$', re.I)
json_regex = re.compile(r'^\{[\s\w,\-\.\"\'\:\[\]]+\}$')

#### OGRGeometry Class ####
class OGRGeometry(object):
    "Generally encapsulates an OGR geometry."

    def __init__(self, geom_input, srs=None):
        "Initializes Geometry on either WKT or an OGR pointer as input."

        self._ptr = c_void_p(None) # Initially NULL
        str_instance = isinstance(geom_input, basestring)

        # If HEX, unpack input to to a binary buffer.
        if str_instance and hex_regex.match(geom_input):
            geom_input = buffer(a2b_hex(geom_input.upper()))
            str_instance = False

        # Constructing the geometry, 
        if str_instance:
            # Checking if unicode
            if isinstance(geom_input, UnicodeType):
                # Encoding to ASCII, WKT or HEX doesn't need any more.
                geo_input = geo_input.encode('ascii')

            wkt_m = wkt_regex.match(geom_input)
            json_m = json_regex.match(geom_input)
            if wkt_m:
                if wkt_m.group('type').upper() == 'LINEARRING':
                    # OGR_G_CreateFromWkt doesn't work with LINEARRING WKT.
                    #  See http://trac.osgeo.org/gdal/ticket/1992.
                    g = create_geom(OGRGeomType(wkt_m.group('type')).num)
                    import_wkt(g, byref(c_char_p(geom_input)))
                else:
                    g = from_wkt(byref(c_char_p(geom_input)), None, byref(c_void_p()))
            elif json_m:
                if GEOJSON:
                    g = from_json(geom_input)
                else:
                    raise NotImplementedError('GeoJSON input only supported on GDAL 1.5+.')
            else:
                # Seeing if the input is a valid short-hand string
                # (e.g., 'Point', 'POLYGON').
                ogr_t = OGRGeomType(geom_input)
                g = create_geom(OGRGeomType(geom_input).num)
        elif isinstance(geom_input, buffer):
            # WKB was passed in
            g = from_wkb(str(geom_input), None, byref(c_void_p()), len(geom_input))
        elif isinstance(geom_input, OGRGeomType):
            # OGRGeomType was passed in, an empty geometry will be created.
            g = create_geom(geom_input.num)
        elif isinstance(geom_input, c_void_p):
            # OGR pointer (c_void_p) was the input.
            g = geom_input
        else:
            raise OGRException('Invalid input type for OGR Geometry construction: %s' % type(geom_input))

        # Now checking the Geometry pointer before finishing initialization
        # by setting the pointer for the object.
        if not g:
            raise OGRException('Cannot create OGR Geometry from input: %s' % str(geom_input))
        self._ptr = g

        # Assigning the SpatialReference object to the geometry, if valid.
        if bool(srs): self.srs = srs

        # Setting the class depending upon the OGR Geometry Type
        self.__class__ = GEO_CLASSES[self.geom_type.num]

    def __del__(self):
        "Deletes this Geometry."
        if self._ptr: destroy_geom(self._ptr)

    ### Geometry set-like operations ###
    # g = g1 | g2
    def __or__(self, other):
        "Returns the union of the two geometries."
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

    def __eq__(self, other):
        "Is this Geometry equal to the other?"
        return self.equals(other)

    def __ne__(self, other):
        "Tests for inequality."
        return not self.equals(other)

    def __str__(self):
        "WKT is used for the string representation."
        return self.wkt

    #### Geometry Properties ####
    @property
    def dimension(self):
        "Returns 0 for points, 1 for lines, and 2 for surfaces."
        return get_dims(self._ptr)

    @property
    def coord_dim(self):
        "Returns the coordinate dimension of the Geometry."
        return get_coord_dims(self._ptr)

    @property
    def geom_count(self):
        "The number of elements in this Geometry."
        return get_geom_count(self._ptr)

    @property
    def point_count(self):
        "Returns the number of Points in this Geometry."
        return get_point_count(self._ptr)

    @property
    def num_points(self):
        "Alias for `point_count` (same name method in GEOS API.)"
        return self.point_count

    @property
    def num_coords(self):
        "Alais for `point_count`."
        return self.point_count

    @property
    def geom_type(self):
        "Returns the Type for this Geometry."
        try:
            return OGRGeomType(get_geom_type(self._ptr))
        except OGRException:
            # VRT datasources return an invalid geometry type
            # number, but a valid name -- we'll try that instead.
            # See: http://trac.osgeo.org/gdal/ticket/2491
            return OGRGeomType(get_geom_name(self._ptr))

    @property
    def geom_name(self):
        "Returns the Name of this Geometry."
        return get_geom_name(self._ptr)

    @property
    def area(self):
        "Returns the area for a LinearRing, Polygon, or MultiPolygon; 0 otherwise."
        return get_area(self._ptr)

    @property
    def envelope(self):
        "Returns the envelope for this Geometry."
        # TODO: Fix Envelope() for Point geometries.
        return Envelope(get_envelope(self._ptr, byref(OGREnvelope())))

    @property
    def extent(self):
        "Returns the envelope as a 4-tuple, instead of as an Envelope object."
        return self.envelope.tuple

    #### SpatialReference-related Properties ####
    
    # The SRS property
    def get_srs(self):
        "Returns the Spatial Reference for this Geometry."
        try:
            srs_ptr = get_geom_srs(self._ptr)
            return SpatialReference(clone_srs(srs_ptr))
        except SRSException:
            return None

    def set_srs(self, srs):
        "Sets the SpatialReference for this geometry."
        if isinstance(srs, SpatialReference):
            srs_ptr = clone_srs(srs._ptr)
        elif isinstance(srs, (int, long, basestring)):
            sr = SpatialReference(srs)
            srs_ptr = clone_srs(sr._ptr)
        else:
            raise TypeError('Cannot assign spatial reference with object of type: %s' % type(srs))
        assign_srs(self._ptr, srs_ptr)

    srs = property(get_srs, set_srs)

    # The SRID property
    def get_srid(self):
        if self.srs: return self.srs.srid
        else: return None

    def set_srid(self, srid):
        if isinstance(srid, (int, long)):
            self.srs = srid
        else:
            raise TypeError('SRID must be set with an integer.')

    srid = property(get_srid, set_srid)

    #### Output Methods ####
    @property
    def geos(self):
        "Returns a GEOSGeometry object from this OGRGeometry."
        from django.contrib.gis.geos import GEOSGeometry
        return GEOSGeometry(self.wkb, self.srid)

    @property
    def gml(self):
        "Returns the GML representation of the Geometry."
        return to_gml(self._ptr)

    @property
    def hex(self):
        "Returns the hexadecimal representation of the WKB (a string)."
        return str(self.wkb).encode('hex').upper()
        #return b2a_hex(self.wkb).upper()

    @property
    def json(self):
        if GEOJSON: 
            return to_json(self._ptr)
        else:
            raise NotImplementedError('GeoJSON output only supported on GDAL 1.5+.')
    geojson = json

    @property
    def wkb_size(self):
        "Returns the size of the WKB buffer."
        return get_wkbsize(self._ptr)

    @property
    def wkb(self):
        "Returns the WKB representation of the Geometry."
        if sys.byteorder == 'little':
            byteorder = 1 # wkbNDR (from ogr_core.h)
        else:
            byteorder = 0 # wkbXDR
        sz = self.wkb_size
        # Creating the unsigned character buffer, and passing it in by reference.
        buf = (c_ubyte * sz)()
        wkb = to_wkb(self._ptr, byteorder, byref(buf))
        # Returning a buffer of the string at the pointer.
        return buffer(string_at(buf, sz))

    @property
    def wkt(self):
        "Returns the WKT representation of the Geometry."
        return to_wkt(self._ptr, byref(c_char_p()))
    
    #### Geometry Methods ####
    def clone(self):
        "Clones this OGR Geometry."
        return OGRGeometry(clone_geom(self._ptr), self.srs)

    def close_rings(self):
        """
        If there are any rings within this geometry that have not been
        closed, this routine will do so by adding the starting point at the
        end.
        """
        # Closing the open rings.
        geom_close_rings(self._ptr)

    def transform(self, coord_trans, clone=False):
        """
        Transforms this geometry to a different spatial reference system.
        May take a CoordTransform object, a SpatialReference object, string
        WKT or PROJ.4, and/or an integer SRID.  By default nothing is returned
        and the geometry is transformed in-place.  However, if the `clone`
        keyword is set, then a transformed clone of this geometry will be
        returned.
        """
        if clone:
            klone = self.clone()
            klone.transform(coord_trans)
            return klone
        if isinstance(coord_trans, CoordTransform):
            geom_transform(self._ptr, coord_trans._ptr)
        elif isinstance(coord_trans, SpatialReference):
            geom_transform_to(self._ptr, coord_trans._ptr)
        elif isinstance(coord_trans, (int, long, basestring)):
            sr = SpatialReference(coord_trans)
            geom_transform_to(self._ptr, sr._ptr)
        else:
            raise TypeError('Transform only accepts CoordTransform, SpatialReference, string, and integer objects.')

    def transform_to(self, srs):
        "For backwards-compatibility."
        self.transform(srs)

    #### Topology Methods ####
    def _topology(self, func, other):
        """A generalized function for topology operations, takes a GDAL function and
        the other geometry to perform the operation on."""
        if not isinstance(other, OGRGeometry):
            raise TypeError('Must use another OGRGeometry object for topology operations!')

        # Returning the output of the given function with the other geometry's
        # pointer.
        return func(self._ptr, other._ptr)

    def intersects(self, other):
        "Returns True if this geometry intersects with the other."
        return self._topology(ogr_intersects, other)
    
    def equals(self, other):
        "Returns True if this geometry is equivalent to the other."
        return self._topology(ogr_equals, other)

    def disjoint(self, other):
        "Returns True if this geometry and the other are spatially disjoint."
        return self._topology(ogr_disjoint, other)

    def touches(self, other):
        "Returns True if this geometry touches the other."
        return self._topology(ogr_touches, other)

    def crosses(self, other):
        "Returns True if this geometry crosses the other."
        return self._topology(ogr_crosses, other)

    def within(self, other):
        "Returns True if this geometry is within the other."
        return self._topology(ogr_within, other)

    def contains(self, other):
        "Returns True if this geometry contains the other."
        return self._topology(ogr_contains, other)

    def overlaps(self, other):
        "Returns True if this geometry overlaps the other."
        return self._topology(ogr_overlaps, other)

    #### Geometry-generation Methods ####
    def _geomgen(self, gen_func, other=None):
        "A helper routine for the OGR routines that generate geometries."
        if isinstance(other, OGRGeometry):
            return OGRGeometry(gen_func(self._ptr, other._ptr), self.srs)
        else:
            return OGRGeometry(gen_func(self._ptr), self.srs)

    @property
    def boundary(self):
        "Returns the boundary of this geometry."
        return self._geomgen(get_boundary)

    @property
    def convex_hull(self):
        """
        Returns the smallest convex Polygon that contains all the points in 
        this Geometry.
        """
        return self._geomgen(geom_convex_hull)

    def difference(self, other):
        """
        Returns a new geometry consisting of the region which is the difference
        of this geometry and the other.
        """
        return self._geomgen(geom_diff, other)

    def intersection(self, other):
        """
        Returns a new geometry consisting of the region of intersection of this
        geometry and the other.
        """
        return self._geomgen(geom_intersection, other)

    def sym_difference(self, other):
        """                                                                                                                                                
        Returns a new geometry which is the symmetric difference of this
        geometry and the other.
        """
        return self._geomgen(geom_sym_diff, other)

    def union(self, other):
        """
        Returns a new geometry consisting of the region which is the union of
        this geometry and the other.
        """
        return self._geomgen(geom_union, other)

# The subclasses for OGR Geometry.
class Point(OGRGeometry):

    @property
    def x(self):
        "Returns the X coordinate for this Point."
        return getx(self._ptr, 0)

    @property
    def y(self):
        "Returns the Y coordinate for this Point."
        return gety(self._ptr, 0)

    @property
    def z(self):
        "Returns the Z coordinate for this Point."
        if self.coord_dim == 3:
            return getz(self._ptr, 0)

    @property
    def tuple(self):
        "Returns the tuple of this point."
        if self.coord_dim == 2:
            return (self.x, self.y)
        elif self.coord_dim == 3:
            return (self.x, self.y, self.z)
    coords = tuple

class LineString(OGRGeometry):

    def __getitem__(self, index):
        "Returns the Point at the given index."
        if index >= 0 and index < self.point_count:
            x, y, z = c_double(), c_double(), c_double()
            get_point(self._ptr, index, byref(x), byref(y), byref(z))
            dim = self.coord_dim
            if dim == 1:
                return (x.value,)
            elif dim == 2:
                return (x.value, y.value)
            elif dim == 3:
                return (x.value, y.value, z.value)
        else:
            raise OGRIndexError('index out of range: %s' % str(index))

    def __iter__(self):
        "Iterates over each point in the LineString."
        for i in xrange(self.point_count):
            yield self[i]

    def __len__(self):
        "The length returns the number of points in the LineString."
        return self.point_count

    @property
    def tuple(self):
        "Returns the tuple representation of this LineString."
        return tuple([self[i] for i in xrange(len(self))])
    coords = tuple

    def _listarr(self, func):
        """
        Internal routine that returns a sequence (list) corresponding with
        the given function.
        """
        return [func(self._ptr, i) for i in xrange(len(self))]

    @property
    def x(self):
        "Returns the X coordinates in a list."
        return self._listarr(getx)

    @property
    def y(self):
        "Returns the Y coordinates in a list."
        return self._listarr(gety)
    
    @property
    def z(self):
        "Returns the Z coordinates in a list."
        if self.coord_dim == 3:
            return self._listarr(getz)

# LinearRings are used in Polygons.
class LinearRing(LineString): pass

class Polygon(OGRGeometry):

    def __len__(self):
        "The number of interior rings in this Polygon."
        return self.geom_count

    def __iter__(self):
        "Iterates through each ring in the Polygon."
        for i in xrange(self.geom_count):
            yield self[i]

    def __getitem__(self, index):
        "Gets the ring at the specified index."
        if index < 0 or index >= self.geom_count:
            raise OGRIndexError('index out of range: %s' % index)
        else:
            return OGRGeometry(clone_geom(get_geom_ref(self._ptr, index)), self.srs)

    # Polygon Properties
    @property
    def shell(self):
        "Returns the shell of this Polygon."
        return self[0] # First ring is the shell
    exterior_ring = shell

    @property
    def tuple(self):
        "Returns a tuple of LinearRing coordinate tuples."
        return tuple([self[i].tuple for i in xrange(self.geom_count)])
    coords = tuple

    @property
    def point_count(self):
        "The number of Points in this Polygon."
        # Summing up the number of points in each ring of the Polygon.
        return sum([self[i].point_count for i in xrange(self.geom_count)])

    @property
    def centroid(self):
        "Returns the centroid (a Point) of this Polygon."
        # The centroid is a Point, create a geometry for this.
        p = OGRGeometry(OGRGeomType('Point'))
        get_centroid(self._ptr, p._ptr)
        return p

# Geometry Collection base class.
class GeometryCollection(OGRGeometry):
    "The Geometry Collection class."

    def __getitem__(self, index):
        "Gets the Geometry at the specified index."
        if index < 0 or index >= self.geom_count:
            raise OGRIndexError('index out of range: %s' % index)
        else:
            return OGRGeometry(clone_geom(get_geom_ref(self._ptr, index)), self.srs)
        
    def __iter__(self):
        "Iterates over each Geometry."
        for i in xrange(self.geom_count):
            yield self[i]

    def __len__(self):
        "The number of geometries in this Geometry Collection."
        return self.geom_count

    def add(self, geom):
        "Add the geometry to this Geometry Collection."
        if isinstance(geom, OGRGeometry):
            if isinstance(geom, self.__class__):
                for g in geom: add_geom(self._ptr, g._ptr)
            else:
                add_geom(self._ptr, geom._ptr)
        elif isinstance(geom, basestring):
            tmp = OGRGeometry(geom)
            add_geom(self._ptr, tmp._ptr)
        else:
            raise OGRException('Must add an OGRGeometry.')

    @property
    def point_count(self):
        "The number of Points in this Geometry Collection."
        # Summing up the number of points in each geometry in this collection
        return sum([self[i].point_count for i in xrange(self.geom_count)])

    @property
    def tuple(self):
        "Returns a tuple representation of this Geometry Collection."
        return tuple([self[i].tuple for i in xrange(self.geom_count)])
    coords = tuple

# Multiple Geometry types.
class MultiPoint(GeometryCollection): pass
class MultiLineString(GeometryCollection): pass
class MultiPolygon(GeometryCollection): pass

# Class mapping dictionary (using the OGRwkbGeometryType as the key)
GEO_CLASSES = {1 : Point,
               2 : LineString,
               3 : Polygon,
               4 : MultiPoint,
               5 : MultiLineString,
               6 : MultiPolygon,
               7 : GeometryCollection,
               101: LinearRing, 
               }
