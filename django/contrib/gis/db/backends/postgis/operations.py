import re

from django.conf import settings
from django.contrib.gis.db.backends.base.operations import \
    BaseSpatialOperations
from django.contrib.gis.db.backends.postgis.adapter import PostGISAdapter
from django.contrib.gis.db.backends.utils import SpatialOperator
from django.contrib.gis.geometry.backend import Geometry
from django.contrib.gis.measure import Distance
from django.core.exceptions import ImproperlyConfigured
from django.db.backends.postgresql_psycopg2.operations import \
    DatabaseOperations
from django.db.utils import ProgrammingError
from django.utils.functional import cached_property

from .models import PostGISGeometryColumns, PostGISSpatialRefSys


class PostGISOperator(SpatialOperator):
    def __init__(self, geography=False, **kwargs):
        # Only a subset of the operators and functions are available
        # for the geography type.
        self.geography = geography
        super(PostGISOperator, self).__init__(**kwargs)

    def as_sql(self, connection, lookup, *args):
        if lookup.lhs.output_field.geography and not self.geography:
            raise ValueError('PostGIS geography does not support the "%s" '
                             'function/operator.' % (self.func or self.op,))
        return super(PostGISOperator, self).as_sql(connection, lookup, *args)


class PostGISDistanceOperator(PostGISOperator):
    sql_template = '%(func)s(%(lhs)s, %(rhs)s) %(op)s %%s'

    def as_sql(self, connection, lookup, template_params, sql_params):
        if not lookup.lhs.output_field.geography and lookup.lhs.output_field.geodetic(connection):
            sql_template = self.sql_template
            if len(lookup.rhs) == 3 and lookup.rhs[-1] == 'spheroid':
                template_params.update({'op': self.op, 'func': 'ST_Distance_Spheroid'})
                sql_template = '%(func)s(%(lhs)s, %(rhs)s, %%s) %(op)s %%s'
            else:
                template_params.update({'op': self.op, 'func': 'ST_Distance_Sphere'})
            return sql_template % template_params, sql_params
        return super(PostGISDistanceOperator, self).as_sql(connection, lookup, template_params, sql_params)


class PostGISOperations(BaseSpatialOperations, DatabaseOperations):
    name = 'postgis'
    postgis = True
    geography = True
    geom_func_prefix = 'ST_'
    version_regex = re.compile(r'^(?P<major>\d)\.(?P<minor1>\d)\.(?P<minor2>\d+)')

    Adapter = PostGISAdapter
    Adaptor = Adapter  # Backwards-compatibility alias.

    gis_operators = {
        'bbcontains': PostGISOperator(op='~'),
        'bboverlaps': PostGISOperator(op='&&', geography=True),
        'contained': PostGISOperator(op='@'),
        'contains': PostGISOperator(func='ST_Contains'),
        'overlaps_left': PostGISOperator(op='&<'),
        'overlaps_right': PostGISOperator(op='&>'),
        'overlaps_below': PostGISOperator(op='&<|'),
        'overlaps_above': PostGISOperator(op='|&>'),
        'left': PostGISOperator(op='<<'),
        'right': PostGISOperator(op='>>'),
        'strictly_below': PostGISOperator(op='<<|'),
        'strictly_above': PostGISOperator(op='|>>'),
        'same_as': PostGISOperator(op='~='),
        'exact': PostGISOperator(op='~='),  # alias of same_as
        'contains_properly': PostGISOperator(func='ST_ContainsProperly'),
        'coveredby': PostGISOperator(func='ST_CoveredBy', geography=True),
        'covers': PostGISOperator(func='ST_Covers', geography=True),
        'crosses': PostGISOperator(func='ST_Crosses'),
        'disjoint': PostGISOperator(func='ST_Disjoint'),
        'equals': PostGISOperator(func='ST_Equals'),
        'intersects': PostGISOperator(func='ST_Intersects', geography=True),
        'overlaps': PostGISOperator(func='ST_Overlaps'),
        'relate': PostGISOperator(func='ST_Relate'),
        'touches': PostGISOperator(func='ST_Touches'),
        'within': PostGISOperator(func='ST_Within'),
        'dwithin': PostGISOperator(func='ST_DWithin', geography=True),
        'distance_gt': PostGISDistanceOperator(func='ST_Distance', op='>', geography=True),
        'distance_gte': PostGISDistanceOperator(func='ST_Distance', op='>=', geography=True),
        'distance_lt': PostGISDistanceOperator(func='ST_Distance', op='<', geography=True),
        'distance_lte': PostGISDistanceOperator(func='ST_Distance', op='<=', geography=True),
    }

    def __init__(self, connection):
        super(PostGISOperations, self).__init__(connection)

        prefix = self.geom_func_prefix

        self.area = prefix + 'Area'
        self.bounding_circle = prefix + 'MinimumBoundingCircle'
        self.centroid = prefix + 'Centroid'
        self.collect = prefix + 'Collect'
        self.difference = prefix + 'Difference'
        self.distance = prefix + 'Distance'
        self.distance_sphere = prefix + 'distance_sphere'
        self.distance_spheroid = prefix + 'distance_spheroid'
        self.envelope = prefix + 'Envelope'
        self.extent = prefix + 'Extent'
        self.force_rhr = prefix + 'ForceRHR'
        self.geohash = prefix + 'GeoHash'
        self.geojson = prefix + 'AsGeoJson'
        self.gml = prefix + 'AsGML'
        self.intersection = prefix + 'Intersection'
        self.kml = prefix + 'AsKML'
        self.length = prefix + 'Length'
        self.length_spheroid = prefix + 'length_spheroid'
        self.makeline = prefix + 'MakeLine'
        self.mem_size = prefix + 'mem_size'
        self.num_geom = prefix + 'NumGeometries'
        self.num_points = prefix + 'npoints'
        self.perimeter = prefix + 'Perimeter'
        self.point_on_surface = prefix + 'PointOnSurface'
        self.polygonize = prefix + 'Polygonize'
        self.reverse = prefix + 'Reverse'
        self.scale = prefix + 'Scale'
        self.snap_to_grid = prefix + 'SnapToGrid'
        self.svg = prefix + 'AsSVG'
        self.sym_difference = prefix + 'SymDifference'
        self.transform = prefix + 'Transform'
        self.translate = prefix + 'Translate'
        self.union = prefix + 'Union'
        self.unionagg = prefix + 'Union'

    # Following "attributes" are properties due to the spatial_version check and
    # to delay database access
    @property
    def extent3d(self):
        if self.spatial_version >= (2, 0, 0):
            return self.geom_func_prefix + '3DExtent'
        else:
            return self.geom_func_prefix + 'Extent3D'

    @property
    def length3d(self):
        if self.spatial_version >= (2, 0, 0):
            return self.geom_func_prefix + '3DLength'
        else:
            return self.geom_func_prefix + 'Length3D'

    @property
    def perimeter3d(self):
        if self.spatial_version >= (2, 0, 0):
            return self.geom_func_prefix + '3DPerimeter'
        else:
            return self.geom_func_prefix + 'Perimeter3D'

    @property
    def geometry(self):
        # Native geometry type support added in PostGIS 2.0.
        return self.spatial_version >= (2, 0, 0)

    @cached_property
    def spatial_version(self):
        """Determine the version of the PostGIS library."""
        # Trying to get the PostGIS version because the function
        # signatures will depend on the version used.  The cost
        # here is a database query to determine the version, which
        # can be mitigated by setting `POSTGIS_VERSION` with a 3-tuple
        # comprising user-supplied values for the major, minor, and
        # subminor revision of PostGIS.
        if hasattr(settings, 'POSTGIS_VERSION'):
            version = settings.POSTGIS_VERSION
        else:
            try:
                vtup = self.postgis_version_tuple()
            except ProgrammingError:
                raise ImproperlyConfigured(
                    'Cannot determine PostGIS version for database "%s". '
                    'GeoDjango requires at least PostGIS version 1.5. '
                    'Was the database created from a spatial database '
                    'template?' % self.connection.settings_dict['NAME']
                )
            version = vtup[1:]
        return version

    def convert_extent(self, box, srid):
        """
        Returns a 4-tuple extent for the `Extent` aggregate by converting
        the bounding box text returned by PostGIS (`box` argument), for
        example: "BOX(-90.0 30.0, -85.0 40.0)".
        """
        if box is None:
            return None
        ll, ur = box[4:-1].split(',')
        xmin, ymin = map(float, ll.split())
        xmax, ymax = map(float, ur.split())
        return (xmin, ymin, xmax, ymax)

    def convert_extent3d(self, box3d, srid):
        """
        Returns a 6-tuple extent for the `Extent3D` aggregate by converting
        the 3d bounding-box text returned by PostGIS (`box3d` argument), for
        example: "BOX3D(-90.0 30.0 1, -85.0 40.0 2)".
        """
        if box3d is None:
            return None
        ll, ur = box3d[6:-1].split(',')
        xmin, ymin, zmin = map(float, ll.split())
        xmax, ymax, zmax = map(float, ur.split())
        return (xmin, ymin, zmin, xmax, ymax, zmax)

    def convert_geom(self, hex, geo_field):
        """
        Converts the geometry returned from PostGIS aggregates.
        """
        if hex:
            return Geometry(hex, srid=geo_field.srid)
        else:
            return None

    def geo_db_type(self, f):
        """
        Return the database field type for the given geometry field.
        Typically this is `None` because geometry columns are added via
        the `AddGeometryColumn` stored procedure, unless the field
        has been specified to be of geography type instead.
        """
        if f.geography:
            if f.srid != 4326:
                raise NotImplementedError('PostGIS only supports geography columns with an SRID of 4326.')

            return 'geography(%s,%d)' % (f.geom_type, f.srid)
        elif self.geometry:
            # Postgis 2.0 supports type-based geometries.
            # TODO: Support 'M' extension.
            if f.dim == 3:
                geom_type = f.geom_type + 'Z'
            else:
                geom_type = f.geom_type
            return 'geometry(%s,%d)' % (geom_type, f.srid)
        else:
            return None

    def get_distance(self, f, dist_val, lookup_type):
        """
        Retrieve the distance parameters for the given geometry field,
        distance lookup value, and the distance lookup type.

        This is the most complex implementation of the spatial backends due to
        what is supported on geodetic geometry columns vs. what's available on
        projected geometry columns.  In addition, it has to take into account
        the geography column type newly introduced in PostGIS 1.5.
        """
        # Getting the distance parameter and any options.
        if len(dist_val) == 1:
            value, option = dist_val[0], None
        else:
            value, option = dist_val

        # Shorthand boolean flags.
        geodetic = f.geodetic(self.connection)
        geography = f.geography

        if isinstance(value, Distance):
            if geography:
                dist_param = value.m
            elif geodetic:
                if lookup_type == 'dwithin':
                    raise ValueError('Only numeric values of degree units are '
                                     'allowed on geographic DWithin queries.')
                dist_param = value.m
            else:
                dist_param = getattr(value, Distance.unit_attname(f.units_name(self.connection)))
        else:
            # Assuming the distance is in the units of the field.
            dist_param = value

        if (not geography and geodetic and lookup_type != 'dwithin'
                and option == 'spheroid'):
            # using distance_spheroid requires the spheroid of the field as
            # a parameter.
            return [f._spheroid, dist_param]
        else:
            return [dist_param]

    def get_geom_placeholder(self, f, value, compiler):
        """
        Provides a proper substitution value for Geometries that are not in the
        SRID of the field.  Specifically, this routine will substitute in the
        ST_Transform() function call.
        """
        if value is None or value.srid == f.srid:
            placeholder = '%s'
        else:
            # Adding Transform() to the SQL placeholder.
            placeholder = '%s(%%s, %s)' % (self.transform, f.srid)

        if hasattr(value, 'as_sql'):
            # If this is an F expression, then we don't really want
            # a placeholder and instead substitute in the column
            # of the expression.
            sql, _ = compiler.compile(value)
            placeholder = placeholder % sql

        return placeholder

    def _get_postgis_func(self, func):
        """
        Helper routine for calling PostGIS functions and returning their result.
        """
        # Close out the connection.  See #9437.
        with self.connection.temporary_connection() as cursor:
            cursor.execute('SELECT %s()' % func)
            return cursor.fetchone()[0]

    def postgis_geos_version(self):
        "Returns the version of the GEOS library used with PostGIS."
        return self._get_postgis_func('postgis_geos_version')

    def postgis_lib_version(self):
        "Returns the version number of the PostGIS library used with PostgreSQL."
        return self._get_postgis_func('postgis_lib_version')

    def postgis_proj_version(self):
        "Returns the version of the PROJ.4 library used with PostGIS."
        return self._get_postgis_func('postgis_proj_version')

    def postgis_version(self):
        "Returns PostGIS version number and compile-time options."
        return self._get_postgis_func('postgis_version')

    def postgis_full_version(self):
        "Returns PostGIS version number and compile-time options."
        return self._get_postgis_func('postgis_full_version')

    def postgis_version_tuple(self):
        """
        Returns the PostGIS version as a tuple (version string, major,
        minor, subminor).
        """
        # Getting the PostGIS version
        version = self.postgis_lib_version()
        m = self.version_regex.match(version)

        if m:
            major = int(m.group('major'))
            minor1 = int(m.group('minor1'))
            minor2 = int(m.group('minor2'))
        else:
            raise Exception('Could not parse PostGIS version string: %s' % version)

        return (version, major, minor1, minor2)

    def proj_version_tuple(self):
        """
        Return the version of PROJ.4 used by PostGIS as a tuple of the
        major, minor, and subminor release numbers.
        """
        proj_regex = re.compile(r'(\d+)\.(\d+)\.(\d+)')
        proj_ver_str = self.postgis_proj_version()
        m = proj_regex.search(proj_ver_str)
        if m:
            return tuple(map(int, [m.group(1), m.group(2), m.group(3)]))
        else:
            raise Exception('Could not determine PROJ.4 version from PostGIS.')

    def spatial_aggregate_name(self, agg_name):
        if agg_name == 'Extent3D':
            return self.extent3d
        else:
            return self.geom_func_prefix + agg_name

    # Routines for getting the OGC-compliant models.
    def geometry_columns(self):
        return PostGISGeometryColumns

    def spatial_ref_sys(self):
        return PostGISSpatialRefSys
