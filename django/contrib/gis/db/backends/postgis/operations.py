import re

from django.conf import settings
from django.contrib.gis.db.backends.base.operations import \
    BaseSpatialOperations
from django.contrib.gis.db.backends.utils import SpatialOperator
from django.contrib.gis.gdal import GDALRaster
from django.contrib.gis.measure import Distance
from django.core.exceptions import ImproperlyConfigured
from django.db.backends.postgresql.operations import DatabaseOperations
from django.db.utils import ProgrammingError
from django.utils.functional import cached_property

from .adapter import PostGISAdapter
from .models import PostGISGeometryColumns, PostGISSpatialRefSys
from .pgraster import from_pgraster, get_pgraster_srid, to_pgraster

# Identifier to mark raster lookups as bilateral.
BILATERAL = 'bilateral'


class PostGISOperator(SpatialOperator):
    def __init__(self, geography=False, raster=False, **kwargs):
        # Only a subset of the operators and functions are available for the
        # geography type.
        self.geography = geography
        # Only a subset of the operators and functions are available for the
        # raster type. Lookups that don't suport raster will be converted to
        # polygons. If the raster argument is set to BILATERAL, then the
        # operator cannot handle mixed geom-raster lookups.
        self.raster = raster
        super().__init__(**kwargs)

    def as_sql(self, connection, lookup, template_params, *args):
        if lookup.lhs.output_field.geography and not self.geography:
            raise ValueError('PostGIS geography does not support the "%s" '
                             'function/operator.' % (self.func or self.op,))

        template_params = self.check_raster(lookup, template_params)
        return super().as_sql(connection, lookup, template_params, *args)

    def check_raster(self, lookup, template_params):
        # Get rhs value.
        if isinstance(lookup.rhs, (tuple, list)):
            rhs_val = lookup.rhs[0]
            spheroid = lookup.rhs[-1] == 'spheroid'
        else:
            rhs_val = lookup.rhs
            spheroid = False

        # Check which input is a raster.
        lhs_is_raster = lookup.lhs.field.geom_type == 'RASTER'
        rhs_is_raster = isinstance(rhs_val, GDALRaster)

        # Look for band indices and inject them if provided.
        if lookup.band_lhs is not None and lhs_is_raster:
            if not self.func:
                raise ValueError('Band indices are not allowed for this operator, it works on bbox only.')
            template_params['lhs'] = '%s, %s' % (template_params['lhs'], lookup.band_lhs)

        if lookup.band_rhs is not None and rhs_is_raster:
            if not self.func:
                raise ValueError('Band indices are not allowed for this operator, it works on bbox only.')
            template_params['rhs'] = '%s, %s' % (template_params['rhs'], lookup.band_rhs)

        # Convert rasters to polygons if necessary.
        if not self.raster or spheroid:
            # Operators without raster support.
            if lhs_is_raster:
                template_params['lhs'] = 'ST_Polygon(%s)' % template_params['lhs']
            if rhs_is_raster:
                template_params['rhs'] = 'ST_Polygon(%s)' % template_params['rhs']
        elif self.raster == BILATERAL:
            # Operators with raster support but don't support mixed (rast-geom)
            # lookups.
            if lhs_is_raster and not rhs_is_raster:
                template_params['lhs'] = 'ST_Polygon(%s)' % template_params['lhs']
            elif rhs_is_raster and not lhs_is_raster:
                template_params['rhs'] = 'ST_Polygon(%s)' % template_params['rhs']

        return template_params


class PostGISDistanceOperator(PostGISOperator):
    sql_template = '%(func)s(%(lhs)s, %(rhs)s) %(op)s %(value)s'

    def as_sql(self, connection, lookup, template_params, sql_params):
        if not lookup.lhs.output_field.geography and lookup.lhs.output_field.geodetic(connection):
            template_params = self.check_raster(lookup, template_params)
            sql_template = self.sql_template
            if len(lookup.rhs) == 3 and lookup.rhs[-1] == 'spheroid':
                template_params.update({
                    'op': self.op,
                    'func': connection.ops.spatial_function_name('DistanceSpheroid'),
                })
                sql_template = '%(func)s(%(lhs)s, %(rhs)s, %%s) %(op)s %(value)s'
                # Using DistanceSpheroid requires the spheroid of the field as
                # a parameter.
                sql_params.insert(1, lookup.lhs.output_field._spheroid)
            else:
                template_params.update({'op': self.op, 'func': connection.ops.spatial_function_name('DistanceSphere')})
            return sql_template % template_params, sql_params
        return super().as_sql(connection, lookup, template_params, sql_params)


class PostGISOperations(BaseSpatialOperations, DatabaseOperations):
    name = 'postgis'
    postgis = True
    geography = True
    geom_func_prefix = 'ST_'
    version_regex = re.compile(r'^(?P<major>\d)\.(?P<minor1>\d)\.(?P<minor2>\d+)')

    Adapter = PostGISAdapter

    gis_operators = {
        'bbcontains': PostGISOperator(op='~', raster=True),
        'bboverlaps': PostGISOperator(op='&&', geography=True, raster=True),
        'contained': PostGISOperator(op='@', raster=True),
        'overlaps_left': PostGISOperator(op='&<', raster=BILATERAL),
        'overlaps_right': PostGISOperator(op='&>', raster=BILATERAL),
        'overlaps_below': PostGISOperator(op='&<|'),
        'overlaps_above': PostGISOperator(op='|&>'),
        'left': PostGISOperator(op='<<'),
        'right': PostGISOperator(op='>>'),
        'strictly_below': PostGISOperator(op='<<|'),
        'strictly_above': PostGISOperator(op='|>>'),
        'same_as': PostGISOperator(op='~=', raster=BILATERAL),
        'exact': PostGISOperator(op='~=', raster=BILATERAL),  # alias of same_as
        'contains': PostGISOperator(func='ST_Contains', raster=BILATERAL),
        'contains_properly': PostGISOperator(func='ST_ContainsProperly', raster=BILATERAL),
        'coveredby': PostGISOperator(func='ST_CoveredBy', geography=True, raster=BILATERAL),
        'covers': PostGISOperator(func='ST_Covers', geography=True, raster=BILATERAL),
        'crosses': PostGISOperator(func='ST_Crosses'),
        'disjoint': PostGISOperator(func='ST_Disjoint', raster=BILATERAL),
        'equals': PostGISOperator(func='ST_Equals'),
        'intersects': PostGISOperator(func='ST_Intersects', geography=True, raster=BILATERAL),
        'isvalid': PostGISOperator(func='ST_IsValid'),
        'overlaps': PostGISOperator(func='ST_Overlaps', raster=BILATERAL),
        'relate': PostGISOperator(func='ST_Relate'),
        'touches': PostGISOperator(func='ST_Touches', raster=BILATERAL),
        'within': PostGISOperator(func='ST_Within', raster=BILATERAL),
        'dwithin': PostGISOperator(func='ST_DWithin', geography=True, raster=BILATERAL),
        'distance_gt': PostGISDistanceOperator(func='ST_Distance', op='>', geography=True),
        'distance_gte': PostGISDistanceOperator(func='ST_Distance', op='>=', geography=True),
        'distance_lt': PostGISDistanceOperator(func='ST_Distance', op='<', geography=True),
        'distance_lte': PostGISDistanceOperator(func='ST_Distance', op='<=', geography=True),
    }

    unsupported_functions = set()

    def __init__(self, connection):
        super().__init__(connection)

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
        self.extent3d = prefix + '3DExtent'
        self.force_rhr = prefix + 'ForceRHR'
        self.geohash = prefix + 'GeoHash'
        self.geojson = prefix + 'AsGeoJson'
        self.gml = prefix + 'AsGML'
        self.intersection = prefix + 'Intersection'
        self.isvalid = prefix + 'IsValid'
        self.kml = prefix + 'AsKML'
        self.length = prefix + 'Length'
        self.length3d = prefix + '3DLength'
        self.length_spheroid = prefix + 'length_spheroid'
        self.makeline = prefix + 'MakeLine'
        self.makevalid = prefix + 'MakeValid'
        self.mem_size = prefix + 'mem_size'
        self.num_geom = prefix + 'NumGeometries'
        self.num_points = prefix + 'npoints'
        self.perimeter = prefix + 'Perimeter'
        self.perimeter3d = prefix + '3DPerimeter'
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

    @cached_property
    def function_names(self):
        function_names = {
            'BoundingCircle': 'ST_MinimumBoundingCircle',
            'NumPoints': 'ST_NPoints',
        }
        if self.spatial_version < (2, 2, 0):
            function_names.update({
                'DistanceSphere': 'ST_distance_sphere',
                'DistanceSpheroid': 'ST_distance_spheroid',
                'LengthSpheroid': 'ST_length_spheroid',
                'MemSize': 'ST_mem_size',
            })
        return function_names

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
            # Run a basic query to check the status of the connection so we're
            # sure we only raise the error below if the problem comes from
            # PostGIS and not from PostgreSQL itself (see #24862).
            self._get_postgis_func('version')

            try:
                vtup = self.postgis_version_tuple()
            except ProgrammingError:
                raise ImproperlyConfigured(
                    'Cannot determine PostGIS version for database "%s" '
                    'using command "SELECT postgis_lib_version()". '
                    'GeoDjango requires at least PostGIS version 2.1. '
                    'Was the database created from a spatial database '
                    'template?' % self.connection.settings_dict['NAME']
                )
            version = vtup[1:]
        return version

    def convert_extent(self, box, srid):
        """
        Return a 4-tuple extent for the `Extent` aggregate by converting
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
        Return a 6-tuple extent for the `Extent3D` aggregate by converting
        the 3d bounding-box text returned by PostGIS (`box3d` argument), for
        example: "BOX3D(-90.0 30.0 1, -85.0 40.0 2)".
        """
        if box3d is None:
            return None
        ll, ur = box3d[6:-1].split(',')
        xmin, ymin, zmin = map(float, ll.split())
        xmax, ymax, zmax = map(float, ur.split())
        return (xmin, ymin, zmin, xmax, ymax, zmax)

    def geo_db_type(self, f):
        """
        Return the database field type for the given spatial field.
        """
        if f.geom_type == 'RASTER':
            return 'raster'

        # Type-based geometries.
        # TODO: Support 'M' extension.
        if f.dim == 3:
            geom_type = f.geom_type + 'Z'
        else:
            geom_type = f.geom_type
        if f.geography:
            if f.srid != 4326:
                raise NotImplementedError('PostGIS only supports geography columns with an SRID of 4326.')

            return 'geography(%s,%d)' % (geom_type, f.srid)
        else:
            return 'geometry(%s,%d)' % (geom_type, f.srid)

    def get_distance(self, f, dist_val, lookup_type):
        """
        Retrieve the distance parameters for the given geometry field,
        distance lookup value, and the distance lookup type.

        This is the most complex implementation of the spatial backends due to
        what is supported on geodetic geometry columns vs. what's available on
        projected geometry columns.  In addition, it has to take into account
        the geography column type.
        """
        # Getting the distance parameter
        value = dist_val[0]

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

        return [dist_param]

    def get_geom_placeholder(self, f, value, compiler):
        """
        Provide a proper substitution value for Geometries or rasters that are
        not in the SRID of the field. Specifically, this routine will
        substitute in the ST_Transform() function call.
        """
        # Get the srid for this object
        if value is None:
            value_srid = None
        elif f.geom_type == 'RASTER' and isinstance(value, str):
            value_srid = get_pgraster_srid(value)
        else:
            value_srid = value.srid

        # Adding Transform() to the SQL placeholder if the value srid
        # is not equal to the field srid.
        if value_srid is None or value_srid == f.srid:
            placeholder = '%s'
        elif f.geom_type == 'RASTER' and isinstance(value, str):
            placeholder = '%s((%%s)::raster, %s)' % (self.transform, f.srid)
        else:
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
        "Return the version of the GEOS library used with PostGIS."
        return self._get_postgis_func('postgis_geos_version')

    def postgis_lib_version(self):
        "Return the version number of the PostGIS library used with PostgreSQL."
        return self._get_postgis_func('postgis_lib_version')

    def postgis_proj_version(self):
        "Return the version of the PROJ.4 library used with PostGIS."
        return self._get_postgis_func('postgis_proj_version')

    def postgis_version(self):
        "Return PostGIS version number and compile-time options."
        return self._get_postgis_func('postgis_version')

    def postgis_full_version(self):
        "Return PostGIS version number and compile-time options."
        return self._get_postgis_func('postgis_full_version')

    def postgis_version_tuple(self):
        """
        Return the PostGIS version as a tuple (version string, major,
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

    # Methods to convert between PostGIS rasters and dicts that are
    # readable by GDALRaster.
    def parse_raster(self, value):
        return from_pgraster(value)

    def deconstruct_raster(self, value):
        return to_pgraster(value)
