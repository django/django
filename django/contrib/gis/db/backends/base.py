"""
Base/mixin classes for the spatial backend database operations and the
`<Backend>SpatialRefSys` model.
"""
from functools import partial
import re

from django.contrib.gis import gdal
from django.utils import six
from django.utils.encoding import python_2_unicode_compatible


class BaseSpatialFeatures(object):
    gis_enabled = True

    # Does the database contain a SpatialRefSys model to store SRID information?
    has_spatialrefsys_table = True

    # Does the backend support the django.contrib.gis.utils.add_srs_entry() utility?
    supports_add_srs_entry = True
    # Does the backend introspect GeometryField to its subtypes?
    supports_geometry_field_introspection = True

    # Reference implementation of 3D functions is:
    # http://postgis.net/docs/PostGIS_Special_Functions_Index.html#PostGIS_3D_Functions
    supports_3d_functions = False
    # Does the database support SRID transform operations?
    supports_transform = True
    # Do geometric relationship operations operate on real shapes (or only on bounding boxes)?
    supports_real_shape_operations = True
    # Can geometry fields be null?
    supports_null_geometries = True
    # Can the `distance` GeoQuerySet method be applied on geodetic coordinate systems?
    supports_distance_geodetic = True
    # Is the database able to count vertices on polygons (with `num_points`)?
    supports_num_points_poly = True

    # The following properties indicate if the database backend support
    # certain lookups (dwithin, left and right, relate, ...)
    supports_distances_lookups = True
    supports_left_right_lookups = False

    @property
    def supports_bbcontains_lookup(self):
        return 'bbcontains' in self.connection.ops.gis_operators

    @property
    def supports_contained_lookup(self):
        return 'contained' in self.connection.ops.gis_operators

    @property
    def supports_dwithin_lookup(self):
        return 'dwithin' in self.connection.ops.gis_operators

    @property
    def supports_relate_lookup(self):
        return 'relate' in self.connection.ops.gis_operators

    # For each of those methods, the class will have a property named
    # `has_<name>_method` (defined in __init__) which accesses connection.ops
    # to determine GIS method availability.
    geoqueryset_methods = (
        'area', 'centroid', 'difference', 'distance', 'distance_spheroid',
        'envelope', 'force_rhr', 'geohash', 'gml', 'intersection', 'kml',
        'length', 'num_geom', 'perimeter', 'point_on_surface', 'reverse',
        'scale', 'snap_to_grid', 'svg', 'sym_difference', 'transform',
        'translate', 'union', 'unionagg',
    )

    # Specifies whether the Collect and Extent aggregates are supported by the database
    @property
    def supports_collect_aggr(self):
        return 'Collect' in self.connection.ops.valid_aggregates

    @property
    def supports_extent_aggr(self):
        return 'Extent' in self.connection.ops.valid_aggregates

    @property
    def supports_make_line_aggr(self):
        return 'MakeLine' in self.connection.ops.valid_aggregates

    def __init__(self, *args):
        super(BaseSpatialFeatures, self).__init__(*args)
        for method in self.geoqueryset_methods:
            # Add dynamically properties for each GQS method, e.g. has_force_rhr_method, etc.
            setattr(self.__class__, 'has_%s_method' % method,
                    property(partial(BaseSpatialFeatures.has_ops_method, method=method)))

    def has_ops_method(self, method):
        return getattr(self.connection.ops, method, False)


class BaseSpatialOperations(object):
    """
    This module holds the base `BaseSpatialBackend` object, which is
    instantiated by each spatial database backend with the features
    it has.
    """
    truncate_params = {}

    # Quick booleans for the type of this spatial backend, and
    # an attribute for the spatial database version tuple (if applicable)
    postgis = False
    spatialite = False
    mysql = False
    oracle = False
    spatial_version = None

    # How the geometry column should be selected.
    select = None

    # Does the spatial database have a geometry or geography type?
    geography = False
    geometry = False

    area = False
    centroid = False
    difference = False
    distance = False
    distance_sphere = False
    distance_spheroid = False
    envelope = False
    force_rhr = False
    mem_size = False
    bounding_circle = False
    num_geom = False
    num_points = False
    perimeter = False
    perimeter3d = False
    point_on_surface = False
    polygonize = False
    reverse = False
    scale = False
    snap_to_grid = False
    sym_difference = False
    transform = False
    translate = False
    union = False

    # Aggregates
    collect = False
    extent = False
    extent3d = False
    make_line = False
    unionagg = False

    # Serialization
    geohash = False
    geojson = False
    gml = False
    kml = False
    svg = False

    # Constructors
    from_text = False
    from_wkb = False

    # Default conversion functions for aggregates; will be overridden if implemented
    # for the spatial backend.
    def convert_extent(self, box):
        raise NotImplementedError('Aggregate extent not implemented for this spatial backend.')

    def convert_extent3d(self, box):
        raise NotImplementedError('Aggregate 3D extent not implemented for this spatial backend.')

    def convert_geom(self, geom_val, geom_field):
        raise NotImplementedError('Aggregate method not implemented for this spatial backend.')

    # For quoting column values, rather than columns.
    def geo_quote_name(self, name):
        return "'%s'" % name

    # GeometryField operations
    def geo_db_type(self, f):
        """
        Returns the database column type for the geometry field on
        the spatial backend.
        """
        raise NotImplementedError('subclasses of BaseSpatialOperations must provide a geo_db_type() method')

    def get_distance(self, f, value, lookup_type):
        """
        Returns the distance parameters for the given geometry field,
        lookup value, and lookup type.
        """
        raise NotImplementedError('Distance operations not available on this spatial backend.')

    def get_geom_placeholder(self, f, value):
        """
        Returns the placeholder for the given geometry field with the given
        value.  Depending on the spatial backend, the placeholder may contain a
        stored procedure call to the transformation function of the spatial
        backend.
        """
        raise NotImplementedError('subclasses of BaseSpatialOperations must provide a geo_db_placeholder() method')

    def get_expression_column(self, evaluator):
        """
        Helper method to return the quoted column string from the evaluator
        for its expression.
        """
        for expr, col_tup in evaluator.cols:
            if expr is evaluator.expression:
                return '%s.%s' % tuple(map(self.quote_name, col_tup))
        raise Exception("Could not find the column for the expression.")

    # Spatial SQL Construction
    def spatial_aggregate_sql(self, agg):
        raise NotImplementedError('Aggregate support not implemented for this spatial backend.')

    # Routines for getting the OGC-compliant models.
    def geometry_columns(self):
        raise NotImplementedError('subclasses of BaseSpatialOperations must a provide geometry_columns() method')

    def spatial_ref_sys(self):
        raise NotImplementedError('subclasses of BaseSpatialOperations must a provide spatial_ref_sys() method')


@python_2_unicode_compatible
class SpatialRefSysMixin(object):
    """
    The SpatialRefSysMixin is a class used by the database-dependent
    SpatialRefSys objects to reduce redundant code.
    """
    # For pulling out the spheroid from the spatial reference string. This
    # regular expression is used only if the user does not have GDAL installed.
    # TODO: Flattening not used in all ellipsoids, could also be a minor axis,
    # or 'b' parameter.
    spheroid_regex = re.compile(r'.+SPHEROID\[\"(?P<name>.+)\",(?P<major>\d+(\.\d+)?),(?P<flattening>\d{3}\.\d+),')

    # For pulling out the units on platforms w/o GDAL installed.
    # TODO: Figure out how to pull out angular units of projected coordinate system and
    # fix for LOCAL_CS types.  GDAL should be highly recommended for performing
    # distance queries.
    units_regex = re.compile(
        r'.+UNIT ?\["(?P<unit_name>[\w \'\(\)]+)", ?(?P<unit>[\d\.]+)'
        r'(,AUTHORITY\["(?P<unit_auth_name>[\w \'\(\)]+)",'
        r'"(?P<unit_auth_val>\d+)"\])?\]([\w ]+)?(,'
        r'AUTHORITY\["(?P<auth_name>[\w \'\(\)]+)","(?P<auth_val>\d+)"\])?\]$'
    )

    @property
    def srs(self):
        """
        Returns a GDAL SpatialReference object, if GDAL is installed.
        """
        if gdal.HAS_GDAL:
            # TODO: Is caching really necessary here?  Is complexity worth it?
            if hasattr(self, '_srs'):
                # Returning a clone of the cached SpatialReference object.
                return self._srs.clone()
            else:
                # Attempting to cache a SpatialReference object.

                # Trying to get from WKT first.
                try:
                    self._srs = gdal.SpatialReference(self.wkt)
                    return self.srs
                except Exception as msg:
                    pass

                try:
                    self._srs = gdal.SpatialReference(self.proj4text)
                    return self.srs
                except Exception as msg:
                    pass

                raise Exception('Could not get OSR SpatialReference from WKT: %s\nError:\n%s' % (self.wkt, msg))
        else:
            raise Exception('GDAL is not installed.')

    @property
    def ellipsoid(self):
        """
        Returns a tuple of the ellipsoid parameters:
        (semimajor axis, semiminor axis, and inverse flattening).
        """
        if gdal.HAS_GDAL:
            return self.srs.ellipsoid
        else:
            m = self.spheroid_regex.match(self.wkt)
            if m:
                return (float(m.group('major')), float(m.group('flattening')))
            else:
                return None

    @property
    def name(self):
        "Returns the projection name."
        return self.srs.name

    @property
    def spheroid(self):
        "Returns the spheroid name for this spatial reference."
        return self.srs['spheroid']

    @property
    def datum(self):
        "Returns the datum for this spatial reference."
        return self.srs['datum']

    @property
    def projected(self):
        "Is this Spatial Reference projected?"
        if gdal.HAS_GDAL:
            return self.srs.projected
        else:
            return self.wkt.startswith('PROJCS')

    @property
    def local(self):
        "Is this Spatial Reference local?"
        if gdal.HAS_GDAL:
            return self.srs.local
        else:
            return self.wkt.startswith('LOCAL_CS')

    @property
    def geographic(self):
        "Is this Spatial Reference geographic?"
        if gdal.HAS_GDAL:
            return self.srs.geographic
        else:
            return self.wkt.startswith('GEOGCS')

    @property
    def linear_name(self):
        "Returns the linear units name."
        if gdal.HAS_GDAL:
            return self.srs.linear_name
        elif self.geographic:
            return None
        else:
            m = self.units_regex.match(self.wkt)
            return m.group('unit_name')

    @property
    def linear_units(self):
        "Returns the linear units."
        if gdal.HAS_GDAL:
            return self.srs.linear_units
        elif self.geographic:
            return None
        else:
            m = self.units_regex.match(self.wkt)
            return m.group('unit')

    @property
    def angular_name(self):
        "Returns the name of the angular units."
        if gdal.HAS_GDAL:
            return self.srs.angular_name
        elif self.projected:
            return None
        else:
            m = self.units_regex.match(self.wkt)
            return m.group('unit_name')

    @property
    def angular_units(self):
        "Returns the angular units."
        if gdal.HAS_GDAL:
            return self.srs.angular_units
        elif self.projected:
            return None
        else:
            m = self.units_regex.match(self.wkt)
            return m.group('unit')

    @property
    def units(self):
        "Returns a tuple of the units and the name."
        if self.projected or self.local:
            return (self.linear_units, self.linear_name)
        elif self.geographic:
            return (self.angular_units, self.angular_name)
        else:
            return (None, None)

    @classmethod
    def get_units(cls, wkt):
        """
        Class method used by GeometryField on initialization to
        retrieve the units on the given WKT, without having to use
        any of the database fields.
        """
        if gdal.HAS_GDAL:
            return gdal.SpatialReference(wkt).units
        else:
            m = cls.units_regex.match(wkt)
            return m.group('unit'), m.group('unit_name')

    @classmethod
    def get_spheroid(cls, wkt, string=True):
        """
        Class method used by GeometryField on initialization to
        retrieve the `SPHEROID[..]` parameters from the given WKT.
        """
        if gdal.HAS_GDAL:
            srs = gdal.SpatialReference(wkt)
            sphere_params = srs.ellipsoid
            sphere_name = srs['spheroid']
        else:
            m = cls.spheroid_regex.match(wkt)
            if m:
                sphere_params = (float(m.group('major')), float(m.group('flattening')))
                sphere_name = m.group('name')
            else:
                return None

        if not string:
            return sphere_name, sphere_params
        else:
            # `string` parameter used to place in format acceptable by PostGIS
            if len(sphere_params) == 3:
                radius, flattening = sphere_params[0], sphere_params[2]
            else:
                radius, flattening = sphere_params
            return 'SPHEROID["%s",%s,%s]' % (sphere_name, radius, flattening)

    def __str__(self):
        """
        Returns the string representation.  If GDAL is installed,
        it will be 'pretty' OGC WKT.
        """
        try:
            return six.text_type(self.srs)
        except Exception:
            return six.text_type(self.wkt)
