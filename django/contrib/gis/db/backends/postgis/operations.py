import re
from decimal import Decimal

from django.conf import settings
from django.contrib.gis.db.backends.base import BaseSpatialOperations
from django.contrib.gis.db.backends.util import SpatialOperation, SpatialFunction
from django.contrib.gis.db.backends.postgis.adapter import PostGISAdapter
from django.contrib.gis.geometry.backend import Geometry
from django.contrib.gis.measure import Distance
from django.core.exceptions import ImproperlyConfigured
from django.db.backends.postgresql_psycopg2.base import DatabaseOperations
from django.db.utils import DatabaseError
from django.utils import six

#### Classes used in constructing PostGIS spatial SQL ####
class PostGISOperator(SpatialOperation):
    "For PostGIS operators (e.g. `&&`, `~`)."
    def __init__(self, operator):
        super(PostGISOperator, self).__init__(operator=operator)

class PostGISFunction(SpatialFunction):
    "For PostGIS function calls (e.g., `ST_Contains(table, geom)`)."
    def __init__(self, prefix, function, **kwargs):
        super(PostGISFunction, self).__init__(prefix + function, **kwargs)

class PostGISFunctionParam(PostGISFunction):
    "For PostGIS functions that take another parameter (e.g. DWithin, Relate)."
    sql_template = '%(function)s(%(geo_col)s, %(geometry)s, %%s)'

class PostGISDistance(PostGISFunction):
    "For PostGIS distance operations."
    dist_func = 'Distance'
    sql_template = '%(function)s(%(geo_col)s, %(geometry)s) %(operator)s %%s'

    def __init__(self, prefix, operator):
        super(PostGISDistance, self).__init__(prefix, self.dist_func,
                                              operator=operator)

class PostGISSpheroidDistance(PostGISFunction):
    "For PostGIS spherical distance operations (using the spheroid)."
    dist_func = 'distance_spheroid'
    sql_template = '%(function)s(%(geo_col)s, %(geometry)s, %%s) %(operator)s %%s'
    def __init__(self, prefix, operator):
        # An extra parameter in `end_subst` is needed for the spheroid string.
        super(PostGISSpheroidDistance, self).__init__(prefix, self.dist_func,
                                                      operator=operator)

class PostGISSphereDistance(PostGISDistance):
    "For PostGIS spherical distance operations."
    dist_func = 'distance_sphere'

class PostGISRelate(PostGISFunctionParam):
    "For PostGIS Relate(<geom>, <pattern>) calls."
    pattern_regex = re.compile(r'^[012TF\*]{9}$')
    def __init__(self, prefix, pattern):
        if not self.pattern_regex.match(pattern):
            raise ValueError('Invalid intersection matrix pattern "%s".' % pattern)
        super(PostGISRelate, self).__init__(prefix, 'Relate')


class PostGISOperations(DatabaseOperations, BaseSpatialOperations):
    compiler_module = 'django.contrib.gis.db.models.sql.compiler'
    name = 'postgis'
    postgis = True
    version_regex = re.compile(r'^(?P<major>\d)\.(?P<minor1>\d)\.(?P<minor2>\d+)')
    valid_aggregates = dict([(k, None) for k in
                             ('Collect', 'Extent', 'Extent3D', 'MakeLine', 'Union')])

    Adapter = PostGISAdapter
    Adaptor = Adapter # Backwards-compatibility alias.

    def __init__(self, connection):
        super(PostGISOperations, self).__init__(connection)

        # Trying to get the PostGIS version because the function
        # signatures will depend on the version used.  The cost
        # here is a database query to determine the version, which
        # can be mitigated by setting `POSTGIS_VERSION` with a 3-tuple
        # comprising user-supplied values for the major, minor, and
        # subminor revision of PostGIS.
        try:
            if hasattr(settings, 'POSTGIS_VERSION'):
                vtup = settings.POSTGIS_VERSION
                if len(vtup) == 3:
                    # The user-supplied PostGIS version.
                    version = vtup
                else:
                    # This was the old documented way, but it's stupid to
                    # include the string.
                    version = vtup[1:4]
            else:
                vtup = self.postgis_version_tuple()
                version = vtup[1:]

            # Getting the prefix -- even though we don't officially support
            # PostGIS 1.2 anymore, keeping it anyway in case a prefix change
            # for something else is necessary.
            if version >= (1, 2, 2):
                prefix = 'ST_'
            else:
                prefix = ''

            self.geom_func_prefix = prefix
            self.spatial_version = version
        except DatabaseError:
            raise ImproperlyConfigured(
                'Cannot determine PostGIS version for database "%s". '
                'GeoDjango requires at least PostGIS version 1.3. '
                'Was the database created from a spatial database '
                'template?' % self.connection.settings_dict['NAME']
                )
        # TODO: Raise helpful exceptions as they become known.

        # PostGIS-specific operators. The commented descriptions of these
        # operators come from Section 7.6 of the PostGIS 1.4 documentation.
        self.geometry_operators = {
            # The "&<" operator returns true if A's bounding box overlaps or
            # is to the left of B's bounding box.
            'overlaps_left' : PostGISOperator('&<'),
            # The "&>" operator returns true if A's bounding box overlaps or
            # is to the right of B's bounding box.
            'overlaps_right' : PostGISOperator('&>'),
            # The "<<" operator returns true if A's bounding box is strictly
            # to the left of B's bounding box.
            'left' : PostGISOperator('<<'),
            # The ">>" operator returns true if A's bounding box is strictly
            # to the right of B's bounding box.
            'right' : PostGISOperator('>>'),
            # The "&<|" operator returns true if A's bounding box overlaps or
            # is below B's bounding box.
            'overlaps_below' : PostGISOperator('&<|'),
            # The "|&>" operator returns true if A's bounding box overlaps or
            # is above B's bounding box.
            'overlaps_above' : PostGISOperator('|&>'),
            # The "<<|" operator returns true if A's bounding box is strictly
            # below B's bounding box.
            'strictly_below' : PostGISOperator('<<|'),
            # The "|>>" operator returns true if A's bounding box is strictly
            # above B's bounding box.
            'strictly_above' : PostGISOperator('|>>'),
            # The "~=" operator is the "same as" operator. It tests actual
            # geometric equality of two features. So if A and B are the same feature,
            # vertex-by-vertex, the operator returns true.
            'same_as' : PostGISOperator('~='),
            'exact' : PostGISOperator('~='),
            # The "@" operator returns true if A's bounding box is completely contained
            # by B's bounding box.
            'contained' : PostGISOperator('@'),
            # The "~" operator returns true if A's bounding box completely contains
            #  by B's bounding box.
            'bbcontains' : PostGISOperator('~'),
            # The "&&" operator returns true if A's bounding box overlaps
            # B's bounding box.
            'bboverlaps' : PostGISOperator('&&'),
            }

        self.geometry_functions = {
            'equals' : PostGISFunction(prefix, 'Equals'),
            'disjoint' : PostGISFunction(prefix, 'Disjoint'),
            'touches' : PostGISFunction(prefix, 'Touches'),
            'crosses' : PostGISFunction(prefix, 'Crosses'),
            'within' : PostGISFunction(prefix, 'Within'),
            'overlaps' : PostGISFunction(prefix, 'Overlaps'),
            'contains' : PostGISFunction(prefix, 'Contains'),
            'intersects' : PostGISFunction(prefix, 'Intersects'),
            'relate' : (PostGISRelate, six.string_types),
            'coveredby' : PostGISFunction(prefix, 'CoveredBy'),
            'covers' : PostGISFunction(prefix, 'Covers'),
        }

        # Valid distance types and substitutions
        dtypes = (Decimal, Distance, float) + six.integer_types
        def get_dist_ops(operator):
            "Returns operations for both regular and spherical distances."
            return {'cartesian' : PostGISDistance(prefix, operator),
                    'sphere' : PostGISSphereDistance(prefix, operator),
                    'spheroid' : PostGISSpheroidDistance(prefix, operator),
                    }
        self.distance_functions = {
            'distance_gt' : (get_dist_ops('>'), dtypes),
            'distance_gte' : (get_dist_ops('>='), dtypes),
            'distance_lt' : (get_dist_ops('<'), dtypes),
            'distance_lte' : (get_dist_ops('<='), dtypes),
            'dwithin' : (PostGISFunctionParam(prefix, 'DWithin'), dtypes)
        }

        # Adding the distance functions to the geometries lookup.
        self.geometry_functions.update(self.distance_functions)

        # Only PostGIS versions 1.3.4+ have GeoJSON serialization support.
        if version < (1, 3, 4):
            GEOJSON = False
        else:
            GEOJSON = prefix + 'AsGeoJson'

        # ST_ContainsProperly ST_MakeLine, and ST_GeoHash added in 1.4.
        if version >= (1, 4, 0):
            GEOHASH = 'ST_GeoHash'
            BOUNDINGCIRCLE = 'ST_MinimumBoundingCircle'
            self.geometry_functions['contains_properly'] = PostGISFunction(prefix, 'ContainsProperly')
        else:
            GEOHASH, BOUNDINGCIRCLE = False, False

        # Geography type support added in 1.5.
        if version >= (1, 5, 0):
            self.geography = True
            # Only a subset of the operators and functions are available
            # for the geography type.
            self.geography_functions = self.distance_functions.copy()
            self.geography_functions.update({
                    'coveredby' : self.geometry_functions['coveredby'],
                    'covers' : self.geometry_functions['covers'],
                    'intersects' : self.geometry_functions['intersects'],
                    })
            self.geography_operators = {
                'bboverlaps' : PostGISOperator('&&'),
                }

        # Native geometry type support added in PostGIS 2.0.
        if version >= (2, 0, 0):
            self.geometry = True

        # Creating a dictionary lookup of all GIS terms for PostGIS.
        gis_terms = ['isnull']
        gis_terms += list(self.geometry_operators)
        gis_terms += list(self.geometry_functions)
        self.gis_terms = dict([(term, None) for term in gis_terms])

        self.area = prefix + 'Area'
        self.bounding_circle = BOUNDINGCIRCLE
        self.centroid = prefix + 'Centroid'
        self.collect = prefix + 'Collect'
        self.difference = prefix + 'Difference'
        self.distance = prefix + 'Distance'
        self.distance_sphere = prefix + 'distance_sphere'
        self.distance_spheroid = prefix + 'distance_spheroid'
        self.envelope = prefix + 'Envelope'
        self.extent = prefix + 'Extent'
        self.force_rhr = prefix + 'ForceRHR'
        self.geohash = GEOHASH
        self.geojson = GEOJSON
        self.gml = prefix + 'AsGML'
        self.intersection = prefix + 'Intersection'
        self.kml = prefix + 'AsKML'
        self.length = prefix + 'Length'
        self.length_spheroid = prefix + 'length_spheroid'
        self.makeline = prefix + 'MakeLine'
        self.mem_size = prefix + 'mem_size'
        self.num_geom = prefix + 'NumGeometries'
        self.num_points =prefix + 'npoints'
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

        if version >= (2, 0, 0):
            self.extent3d = prefix + '3DExtent'
            self.length3d = prefix + '3DLength'
            self.perimeter3d = prefix + '3DPerimeter'
        else:
            self.extent3d = prefix + 'Extent3D'
            self.length3d = prefix + 'Length3D'
            self.perimeter3d = prefix + 'Perimeter3D'

    def check_aggregate_support(self, aggregate):
        """
        Checks if the given aggregate name is supported (that is, if it's
        in `self.valid_aggregates`).
        """
        agg_name = aggregate.__class__.__name__
        return agg_name in self.valid_aggregates

    def convert_extent(self, box):
        """
        Returns a 4-tuple extent for the `Extent` aggregate by converting
        the bounding box text returned by PostGIS (`box` argument), for
        example: "BOX(-90.0 30.0, -85.0 40.0)".
        """
        ll, ur = box[4:-1].split(',')
        xmin, ymin = map(float, ll.split())
        xmax, ymax = map(float, ur.split())
        return (xmin, ymin, xmax, ymax)

    def convert_extent3d(self, box3d):
        """
        Returns a 6-tuple extent for the `Extent3D` aggregate by converting
        the 3d bounding-box text returnded by PostGIS (`box3d` argument), for
        example: "BOX3D(-90.0 30.0 1, -85.0 40.0 2)".
        """
        ll, ur = box3d[6:-1].split(',')
        xmin, ymin, zmin = map(float, ll.split())
        xmax, ymax, zmax = map(float, ur.split())
        return (xmin, ymin, zmin, xmax, ymax, zmax)

    def convert_geom(self, hex, geo_field):
        """
        Converts the geometry returned from PostGIS aggretates.
        """
        if hex:
            return Geometry(hex)
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
            if not self.geography:
                raise NotImplementedError('PostGIS 1.5 required for geography column support.')

            if f.srid != 4326:
                raise NotImplementedError('PostGIS 1.5 supports geography columns '
                                          'only with an SRID of 4326.')

            return 'geography(%s,%d)'% (f.geom_type, f.srid)
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
        the newly introduced geography column type introudced in PostGIS 1.5.
        """
        # Getting the distance parameter and any options.
        if len(dist_val) == 1:
            value, option = dist_val[0], None
        else:
            value, option = dist_val

        # Shorthand boolean flags.
        geodetic = f.geodetic(self.connection)
        geography = f.geography and self.geography

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

    def get_geom_placeholder(self, f, value):
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

        if hasattr(value, 'expression'):
            # If this is an F expression, then we don't really want
            # a placeholder and instead substitute in the column
            # of the expression.
            placeholder = placeholder % self.get_expression_column(value)

        return placeholder

    def _get_postgis_func(self, func):
        """
        Helper routine for calling PostGIS functions and returning their result.
        """
        cursor = self.connection._cursor()
        try:
            try:
                cursor.execute('SELECT %s()' % func)
                row = cursor.fetchone()
            except:
                # Responsibility of callers to perform error handling.
                raise
        finally:
            # Close out the connection.  See #9437.
            self.connection.close()
        return row[0]

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

    def num_params(self, lookup_type, num_param):
        """
        Helper routine that returns a boolean indicating whether the number of
        parameters is correct for the lookup type.
        """
        def exactly_two(np): return np == 2
        def two_to_three(np): return np >= 2 and np <=3
        if (lookup_type in self.distance_functions and
            lookup_type != 'dwithin'):
            return two_to_three(num_param)
        else:
            return exactly_two(num_param)

    def spatial_lookup_sql(self, lvalue, lookup_type, value, field, qn):
        """
        Constructs spatial SQL from the given lookup value tuple a
        (alias, col, db_type), the lookup type string, lookup value, and
        the geometry field.
        """
        alias, col, db_type = lvalue

        # Getting the quoted geometry column.
        geo_col = '%s.%s' % (qn(alias), qn(col))

        if lookup_type in self.geometry_operators:
            if field.geography and not lookup_type in self.geography_operators:
                raise ValueError('PostGIS geography does not support the '
                                 '"%s" lookup.' % lookup_type)
            # Handling a PostGIS operator.
            op = self.geometry_operators[lookup_type]
            return op.as_sql(geo_col, self.get_geom_placeholder(field, value))
        elif lookup_type in self.geometry_functions:
            if field.geography and not lookup_type in self.geography_functions:
                raise ValueError('PostGIS geography type does not support the '
                                 '"%s" lookup.' % lookup_type)

            # See if a PostGIS geometry function matches the lookup type.
            tmp = self.geometry_functions[lookup_type]

            # Lookup types that are tuples take tuple arguments, e.g., 'relate' and
            # distance lookups.
            if isinstance(tmp, tuple):
                # First element of tuple is the PostGISOperation instance, and the
                # second element is either the type or a tuple of acceptable types
                # that may passed in as further parameters for the lookup type.
                op, arg_type = tmp

                # Ensuring that a tuple _value_ was passed in from the user
                if not isinstance(value, (tuple, list)):
                    raise ValueError('Tuple required for `%s` lookup type.' % lookup_type)

                # Geometry is first element of lookup tuple.
                geom = value[0]

                # Number of valid tuple parameters depends on the lookup type.
                nparams = len(value)
                if not self.num_params(lookup_type, nparams):
                    raise ValueError('Incorrect number of parameters given for `%s` lookup type.' % lookup_type)

                # Ensuring the argument type matches what we expect.
                if not isinstance(value[1], arg_type):
                    raise ValueError('Argument type should be %s, got %s instead.' % (arg_type, type(value[1])))

                # For lookup type `relate`, the op instance is not yet created (has
                # to be instantiated here to check the pattern parameter).
                if lookup_type == 'relate':
                    op = op(self.geom_func_prefix, value[1])
                elif lookup_type in self.distance_functions and lookup_type != 'dwithin':
                    if not field.geography and field.geodetic(self.connection):
                        # Geodetic distances are only available from Points to
                        # PointFields on PostGIS 1.4 and below.
                        if not self.connection.ops.geography:
                            if field.geom_type != 'POINT':
                                raise ValueError('PostGIS spherical operations are only valid on PointFields.')

                            if str(geom.geom_type) != 'Point':
                                raise ValueError('PostGIS geometry distance parameter is required to be of type Point.')

                        # Setting up the geodetic operation appropriately.
                        if nparams == 3 and value[2] == 'spheroid':
                            op = op['spheroid']
                        else:
                            op = op['sphere']
                    else:
                        op = op['cartesian']
            else:
                op = tmp
                geom = value

            # Calling the `as_sql` function on the operation instance.
            return op.as_sql(geo_col, self.get_geom_placeholder(field, geom))

        elif lookup_type == 'isnull':
            # Handling 'isnull' lookup type
            return "%s IS %sNULL" % (geo_col, (not value and 'NOT ' or ''))

        raise TypeError("Got invalid lookup_type: %s" % repr(lookup_type))

    def spatial_aggregate_sql(self, agg):
        """
        Returns the spatial aggregate SQL template and function for the
        given Aggregate instance.
        """
        agg_name = agg.__class__.__name__
        if not self.check_aggregate_support(agg):
            raise NotImplementedError('%s spatial aggregate is not implmented for this backend.' % agg_name)
        agg_name = agg_name.lower()
        if agg_name == 'union': agg_name += 'agg'
        sql_template = '%(function)s(%(field)s)'
        sql_function = getattr(self, agg_name)
        return sql_template, sql_function

    # Routines for getting the OGC-compliant models.
    def geometry_columns(self):
        from django.contrib.gis.db.backends.postgis.models import GeometryColumns
        return GeometryColumns

    def spatial_ref_sys(self):
        from django.contrib.gis.db.backends.postgis.models import SpatialRefSys
        return SpatialRefSys
