# types & ctypes
from types import IntType, StringType
from ctypes import byref, string_at, c_char_p, c_double, c_int, c_void_p

# Getting the GDAL C library and error checking facilities
from django.contrib.gis.gdal.libgdal import lgdal
from django.contrib.gis.gdal.OGRError import check_err, OGRException
from django.contrib.gis.gdal.SpatialReference import SpatialReference, CoordTransform

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

# For more information, see the OGR C API source code:
#  http://www.gdal.org/ogr/ogr__api_8h.html
#
# The OGR_G_* routines are relevant here.

#### ctypes prototypes ####
def pnt_func(f):
    "For accessing point information."
    f.restype = c_double
    f.argtypes = [c_void_p, c_int]
    return f
getx = pnt_func(lgdal.OGR_G_GetX)
gety = pnt_func(lgdal.OGR_G_GetY)
getz = pnt_func(lgdal.OGR_G_GetZ)

#### OGRGeomType ####
class OGRGeomType(object):
    "Encapulates OGR Geometry Types."

    # Ordered array of acceptable strings and their corresponding OGRwkbGeometryType
    __ogr_str = ['Point', 'LineString', 'Polygon', 'MultiPoint',
                 'MultiLineString', 'MultiPolygon', 'GeometryCollection',
                 'LinearRing']
    __ogr_int = [1, 2, 3, 4, 5, 6, 7, 101]

    def __init__(self, input):
        "Figures out the correct OGR Type based upon the input."
        if isinstance(input, OGRGeomType):
            self._index = input._index
        elif isinstance(input, StringType):
            idx = self._has_str(self.__ogr_str, input)
            if idx == None:
                raise OGRException, 'Invalid OGR String Type "%s"' % input
            self._index = idx
        elif isinstance(input, int):
            if not input in self.__ogr_int:
                raise OGRException, 'Invalid OGR Integer Type: %d' % input
            self._index =  self.__ogr_int.index(input)
        else:
            raise TypeError, 'Invalid OGR Input type given!'

    def __str__(self):
        "Returns a short-hand string form of the OGR Geometry type."
        return self.__ogr_str[self._index]

    def __eq__(self, other):
        """Does an equivalence test on the OGR type with the given
        other OGRGeomType, the short-hand string, or the integer."""
        if isinstance(other, OGRGeomType):
            return self._index == other._index
        elif isinstance(other, StringType):
            idx = self._has_str(self.__ogr_str, other)
            if not (idx == None): return self._index == idx
            return False
        elif isinstance(other, int):
            if not other in self.__ogr_int: return False
            return self.__ogr_int.index(other) == self._index
        else:
            raise TypeError, 'Cannot compare with type: %s' % str(type(other))

    def _has_str(self, arr, s):
        "Case-insensitive search of the string array for the given pattern."
        s_low = s.lower()
        for i in xrange(len(arr)):
            if s_low == arr[i].lower(): return i
        return None

    @property
    def django(self):
        "Returns the Django GeometryField for this OGR Type."
        s = self.__ogr_str[self._index]
        if s in ('Unknown', 'LinearRing'):
            return None
        else:
            return s + 'Field'

    @property
    def num(self):
        "Returns the OGRwkbGeometryType number for the OGR Type."
        return self.__ogr_int[self._index]

#### OGRGeometry Class ####
class OGRGeometry(object):
    "Generally encapsulates an OGR geometry."

    _g = 0 # Initially NULL

    def __init__(self, input, srs=False):
        "Initializes Geometry on either WKT or an OGR pointer as input."

        if isinstance(input, StringType):
            # Getting the spatial reference
            self._init_srs(srs)

            # First, trying the input as WKT
            buf = c_char_p(input)
            g = c_void_p()

            try:
                check_err(lgdal.OGR_G_CreateFromWkt(byref(buf), self._s._srs, byref(g)))
            except OGRException, msg:
                try:
                    ogr_t = OGRGeomType(input) # Seeing if the input is a valid short-hand string
                    g = lgdal.OGR_G_CreateGeometry(ogr_t.num)
                except:
                    raise OGRException, 'Could not initialize on WKT "%s"' % input
        elif isinstance(input, OGRGeomType):
            self._init_srs(srs)
            g = lgdal.OGR_G_CreateGeometry(input.num)
            lgdal.OGR_G_AssignSpatialReference(g, self._s._srs)
        elif isinstance(input, IntType):
            # OGR Pointer (integer) was the input
            g = input
        else:
            raise OGRException, 'Type of input cannot be determined!'

        # Now checking the Geometry pointer before finishing initialization
        if not g:
            raise OGRException, 'Cannot create OGR Geometry from input: %s' % str(input)
        self._g = g

        # Setting the class depending upon the OGR Geometry Type
        self.__class__ = GEO_CLASSES[self.geom_type.num]

    def _init_srs(self, srs):
        # Getting the spatial
        if not isinstance(srs, SpatialReference):
            self._s = SpatialReference() # creating an empty spatial reference
        else:
            self._s = srs.clone() # cloning the given spatial reference

    def __add__(self, other):
        "Returns the union of the two geometries."
        return self.union(other)

    def __del__(self):
        "Deletes this Geometry."
        if self._g: lgdal.OGR_G_DestroyGeometry(self._g)

    def __eq__(self, other):
        "Is this Geometry equal to the other?"
        return self.equals(other)

    def __str__(self):
        "WKT is used for the string representation."
        return self.wkt

    #### Geometry Properties ####
    @property
    def dimension(self):
        "Returns 0 for points, 1 for lines, and 2 for surfaces."
        return lgdal.OGR_G_GetDimension(self._g)

    @property
    def coord_dim(self):
        "Returns the coordinate dimension of the Geometry."
        return lgdal.OGR_G_GetCoordinateDimension(self._g)

    @property
    def geom_count(self):
        "The number of elements in this Geometry."
        return lgdal.OGR_G_GetGeometryCount(self._g)

    @property
    def point_count(self):
        "Returns the number of Points in this Geometry."
        return lgdal.OGR_G_GetPointCount(self._g)

    @property
    def num_coords(self):
        "Returns the number of Points in this Geometry."
        return self.point_count

    @property
    def srs(self):
        "Returns the Spatial Reference for this Geometry."
        return SpatialReference(lgdal.OSRClone(lgdal.OGR_G_GetSpatialReference(self._g)), 'ogr')

    @property
    def geom_type(self):
        "Returns the Type for this Geometry."
        return OGRGeomType(lgdal.OGR_G_GetGeometryType(self._g))

    @property
    def geom_name(self):
        "Returns the Name of this Geometry."
        return string_at(lgdal.OGR_G_GetGeometryName(self._g))

    @property
    def wkt(self):
        "Returns the WKT form of the Geometry."
        buf = c_char_p()
        check_err(lgdal.OGR_G_ExportToWkt(self._g, byref(buf)))
        return string_at(buf)

    @property
    def area(self):
        "Returns the area for a LinearRing, Polygon, or MultiPolygon; 0 otherwise."
        a = lgdal.OGR_G_GetArea(self._g)
        return a.value
    
    #### Geometry Methods ####
    def clone(self):
        "Clones this OGR Geometry."
        return OGRGeometry(lgdal.OGR_G_Clone(self._g))

    def close_rings(self):
        """If there are any rings within this geometry that have not been
        closed, this routine will do so by adding the starting point at the
        end."""
        # Closing the open rings.
        lgdal.OGR_G_CloseRings(self._g)
        # This "fixes" a GDAL bug. See http://trac.osgeo.org/gdal/ticket/1673
        foo = self.wkt

    def transform(self, coord_trans):
        "Transforms this Geometry with the given CoordTransform object."
        if not isinstance(coord_trans, CoordTransform):
            raise OGRException, 'CoordTransform object required for transform.'
        check_err(lgdal.OGR_G_Transform(self._g, coord_trans._ct))

    def transform_to(self, srs):
        "Transforms this Geometry with the given SpatialReference."
        if not isinstance(srs, SpatialReference):
            raise OGRException, 'SpatialReference object required for transform_to.'
        check_err(lgdal.OGR_G_TransformTo(self._g, srs._srs))

    #### Topology Methods ####
    def _topology(self, topo_func, other):
        """A generalized function for topology operations, takes a GDAL function and
        the other geometry to perform the operation on."""
        if not isinstance(other, OGRGeometry):
            raise OGRException, 'Must use another OGRGeometry object for topology operations!'

        # Calling the passed-in topology function with the other geometry
        status = topo_func(self._g, other._g)

        # Returning based on the status code (an integer)
        if status: return True
        else: return False

    def intersects(self, other):
        "Returns True if this geometry intersects with the other."
        return self._topology(lgdal.OGR_G_Intersects, other)
    
    def equals(self, other):
        "Returns True if this geometry is equivalent to the other."
        return self._topology(lgdal.OGR_G_Equals, other)

    def disjoint(self, other):
        "Returns True if this geometry and the other are spatially disjoint."
        return self._topology(lgdal.OGR_G_Disjoint, other)

    def touches(self, other):
        "Returns True if this geometry touches the other."
        return self._topology(lgdal.OGR_G_Touches, other)

    def crosses(self, other):
        "Returns True if this geometry crosses the other."
        return self._topology(lgdal.OGR_G_Crosses, other)

    def within(self, other):
        "Returns True if this geometry is within the other."
        return self._topology(lgdal.OGR_G_Within, other)

    def contains(self, other):
        "Returns True if this geometry contains the other."
        return self._topology(lgdal.OGR_G_Contains, other)

    def overlaps(self, other):
        "Returns True if this geometry overlaps the other."
        return self._topology(lgdal.OGR_G_Overlaps, other)

    #### Geometry-generation Methods ####
    def _geomgen(self, gen_func, other):
        if not isinstance(other, OGRGeometry):
            raise OGRException, 'Must use another OGRGeometry object for geometry-generating operations!'
        return OGRGeometry(gen_func(self._g, other._g))

    def union(self, other):
        """Returns a new geometry consisting of the region which is the union of
        this geometry and the other."""
        return self._geomgen(lgdal.OGR_G_Union, other)
        
    def difference(self, other):
        """Returns a new geometry consisting of the region which is the difference
        of this geometry and the other."""
        return self._geomgen(lgdal.OGR_G_Difference, other)

    def sym_difference(self, other):
        """Returns a new geometry which is the symmetric difference of this
        geometry and the other."""
        return self._geomgen(lgdal.OGR_G_SymmetricDifference, other)

    def intersection(self, other):
        """Returns a new geometry consisting of the region of intersection of this
        geometry and the other."""
        return self._geomgen(lgdal.OGR_G_Intersection, other)

# The subclasses for OGR Geometry.
class Point(OGRGeometry):

    @property
    def x(self):
        "Returns the X coordinate for this Point."
        return getx(self._g, c_int(0))

    @property
    def y(self):
        "Returns the Y coordinate for this Point."
        return gety(self._g, c_int(0))

    @property
    def z(self):
        "Returns the Z coordinate for this Point."
        return getz(self._g, c_int(0))

    @property
    def tuple(self):
        "Returns the tuple of this point."
        if self.coord_dim == 1:
            return (self.x,)
        elif self.coord_dim == 2:
            return (self.x, self.y)
        elif self.coord_dim == 3:
            return (self.x, self.y, self.z)

class LineString(OGRGeometry):

    def __getitem__(self, index):
        "Returns the Point at the given index."
        if index > 0 or index < self.point_count:
            x = c_double()
            y = c_double()
            z = c_double()
            lgdal.OGR_G_GetPoint(self._g, c_int(index),
                                 byref(x), byref(y), byref(z))
            if self.coord_dim == 1:
                return (x.value,)
            elif self.coord_dim == 2:
                return (x.value, y.value)
            elif self.coord_dim == 3:
                return (x.value, y.value, z.value)
        else:
            raise IndexError, 'index out of range'

    def __iter__(self):
        "Iterates over each point in the LineString."
        for i in xrange(self.point_count):
            yield self.__getitem__(i)

    def __len__(self, index):
        "The length returns the number of points in the LineString."
        return self.point_count

    @property
    def tuple(self):
        "Returns the tuple representation of this LineString."
        return tuple(self.__getitem__(i) for i in xrange(self.point_count))

# LinearRings are used in Polygons.
class LinearRing(LineString): pass

class Polygon(OGRGeometry):

    def __len__(self):
        "The number of interior rings in this Polygon."
        return self.geom_count

    def __iter__(self):
        "Iterates through each ring in the Polygon."
        for i in xrange(self.geom_count):
            yield self.__getitem__(i)

    def __getitem__(self, index):
        "Gets the ring at the specified index."
        if index < 0 or index >= self.geom_count:
            raise IndexError, 'index out of range'
        else:
            return OGRGeometry(lgdal.OGR_G_Clone(lgdal.OGR_G_GetGeometryRef(self._g, c_int(index))))

    # Polygon Properties
    @property
    def shell(self):
        "Returns the shell of this Polygon."
        return self.__getitem__(0) # First ring is the shell

    @property
    def tuple(self):
        "Returns a tuple of LinearRing coordinate tuples."
        return tuple(self.__getitem__(i).tuple for i in xrange(self.geom_count))

    @property
    def point_count(self):
        "The number of Points in this Polygon."
        # Summing up the number of points in each ring of the Polygon.
        return sum([self.__getitem__(i).point_count for i in xrange(self.geom_count)])

    @property
    def centroid(self):
        "Returns the centroid (a Point) of this Polygon."
        # The centroid is a Point, create a geometry for this.
        p = OGRGeometry(OGRGeomType('Point'))
        check_err(lgdal.OGR_G_Centroid(self._g, p._g))
        return p

# Geometry Collection base class.
class GeometryCollection(OGRGeometry):
    "The Geometry Collection class."

    def __getitem__(self, index):
        "Gets the Geometry at the specified index."
        if index < 0 or index >= self.geom_count:
            raise IndexError, 'index out of range'
        else:
            return OGRGeometry(lgdal.OGR_G_Clone(lgdal.OGR_G_GetGeometryRef(self._g, c_int(index))))
        
    def __iter__(self):
        "Iterates over each Geometry."
        for i in xrange(self.geom_count):
            yield self.__getitem__(i)

    def __len__(self):
        "The number of geometries in this Geometry Collection."
        return self.geom_count

    def add(self, geom):
        "Add the geometry to this Geometry Collection."
        if isinstance(geom, OGRGeometry):
            ptr = geom._g
        elif isinstance(geom, StringType):
            tmp = OGRGeometry(geom)
            ptr = tmp._g
        else:
            raise OGRException, 'Must add an OGRGeometry.'
        lgdal.OGR_G_AddGeometry(self._g, ptr)

    @property
    def point_count(self):
        "The number of Points in this Geometry Collection."
        # Summing up the number of points in each geometry in this collection
        return sum([self.__getitem__(i).point_count for i in xrange(self.geom_count)])

    @property
    def tuple(self):
        "Returns a tuple representation of this Geometry Collection."
        return tuple(self.__getitem__(i).tuple for i in xrange(self.geom_count)) 

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
               }
