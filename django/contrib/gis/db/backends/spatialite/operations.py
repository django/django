import re
from decimal import Decimal

from django.contrib.gis.db.backends.base import BaseSpatialOperations
from django.contrib.gis.db.backends.util import SpatialOperation, SpatialFunction
from django.contrib.gis.db.backends.spatialite.adapter import SpatiaLiteAdapter
from django.contrib.gis.geometry.backend import Geometry
from django.contrib.gis.measure import Distance
from django.core.exceptions import ImproperlyConfigured
from django.db.backends.sqlite3.base import DatabaseOperations

class SpatiaLiteOperator(SpatialOperation):
    "For SpatiaLite operators (e.g. `&&`, `~`)."
    def __init__(self, operator):
        super(SpatiaLiteOperator, self).__init__(operator=operator)

class SpatiaLiteFunction(SpatialFunction):
    "For SpatiaLite function calls."
    def __init__(self, function, **kwargs):
        super(SpatiaLiteFunction, self).__init__(function, **kwargs)

class SpatiaLiteFunctionParam(SpatiaLiteFunction):
    "For SpatiaLite functions that take another parameter."
    sql_template = '%(function)s(%(geo_col)s, %(geometry)s, %%s)'

class SpatiaLiteDistance(SpatiaLiteFunction):
    "For SpatiaLite distance operations."
    dist_func = 'Distance'
    sql_template = '%(function)s(%(geo_col)s, %(geometry)s) %(operator)s %%s'

    def __init__(self, operator):
        super(SpatiaLiteDistance, self).__init__(self.dist_func,
                                                 operator=operator)

class SpatiaLiteRelate(SpatiaLiteFunctionParam):
    "For SpatiaLite Relate(<geom>, <pattern>) calls."
    pattern_regex = re.compile(r'^[012TF\*]{9}$')
    def __init__(self, pattern):
        if not self.pattern_regex.match(pattern):
            raise ValueError('Invalid intersection matrix pattern "%s".' % pattern)
        super(SpatiaLiteRelate, self).__init__('Relate')

# Valid distance types and substitutions
dtypes = (Decimal, Distance, float, int, long)
def get_dist_ops(operator):
    "Returns operations for regular distances; spherical distances are not currently supported."
    return (SpatiaLiteDistance(operator),)

class SpatiaLiteOperations(DatabaseOperations, BaseSpatialOperations):
    compiler_module = 'django.contrib.gis.db.models.sql.compiler'
    name = 'spatialite'
    spatialite = True
    version_regex = re.compile(r'^(?P<major>\d)\.(?P<minor1>\d)\.(?P<minor2>\d+)')
    valid_aggregates = dict([(k, None) for k in ('Extent', 'Union')])

    Adapter = SpatiaLiteAdapter

    area = 'Area'
    centroid = 'Centroid'
    contained = 'MbrWithin'
    difference = 'Difference'
    distance = 'Distance'
    envelope = 'Envelope'
    intersection = 'Intersection'
    length = 'GLength' # OpenGis defines Length, but this conflicts with an SQLite reserved keyword
    num_geom = 'NumGeometries'
    num_points = 'NumPoints'
    point_on_surface = 'PointOnSurface'
    scale = 'ScaleCoords'
    svg = 'AsSVG'
    sym_difference = 'SymDifference'
    transform = 'Transform'
    translate = 'ShiftCoords'
    union = 'GUnion' # OpenGis defines Union, but this conflicts with an SQLite reserved keyword
    unionagg = 'GUnion'

    from_text = 'GeomFromText'
    from_wkb = 'GeomFromWKB'
    select = 'AsText(%s)'

    geometry_functions = {
        'equals' : SpatiaLiteFunction('Equals'),
        'disjoint' : SpatiaLiteFunction('Disjoint'),
        'touches' : SpatiaLiteFunction('Touches'),
        'crosses' : SpatiaLiteFunction('Crosses'),
        'within' : SpatiaLiteFunction('Within'),
        'overlaps' : SpatiaLiteFunction('Overlaps'),
        'contains' : SpatiaLiteFunction('Contains'),
        'intersects' : SpatiaLiteFunction('Intersects'),
        'relate' : (SpatiaLiteRelate, basestring),
        # Retruns true if B's bounding box completely contains A's bounding box.
        'contained' : SpatiaLiteFunction('MbrWithin'),
        # Returns true if A's bounding box completely contains B's bounding box.
        'bbcontains' : SpatiaLiteFunction('MbrContains'),
        # Returns true if A's bounding box overlaps B's bounding box.
        'bboverlaps' : SpatiaLiteFunction('MbrOverlaps'),
        # These are implemented here as synonyms for Equals
        'same_as' : SpatiaLiteFunction('Equals'),
        'exact' : SpatiaLiteFunction('Equals'),
        }

    distance_functions = {
        'distance_gt' : (get_dist_ops('>'), dtypes),
        'distance_gte' : (get_dist_ops('>='), dtypes),
        'distance_lt' : (get_dist_ops('<'), dtypes),
        'distance_lte' : (get_dist_ops('<='), dtypes),
        }
    geometry_functions.update(distance_functions)

    def __init__(self, connection):
        super(DatabaseOperations, self).__init__()
        self.connection = connection

        # Determine the version of the SpatiaLite library.
        try:
            vtup = self.spatialite_version_tuple()
            version = vtup[1:]
            if version < (2, 3, 1):
                raise ImproperlyConfigured('GeoDjango only supports SpatiaLite versions '
                                           '2.3.1 and above')
            self.spatial_version = version
        except ImproperlyConfigured:
            raise
        except Exception, msg:
            raise ImproperlyConfigured('Cannot determine the SpatiaLite version for the "%s" '
                                       'database (error was "%s").  Was the SpatiaLite initialization '
                                       'SQL loaded on this database?' %
                                       (self.connection.settings_dict['NAME'], msg))

        # Creating the GIS terms dictionary.
        gis_terms = ['isnull']
        gis_terms += self.geometry_functions.keys()
        self.gis_terms = dict([(term, None) for term in gis_terms])

    def check_aggregate_support(self, aggregate):
        """
        Checks if the given aggregate name is supported (that is, if it's
        in `self.valid_aggregates`).
        """
        agg_name = aggregate.__class__.__name__
        return agg_name in self.valid_aggregates

    def convert_geom(self, wkt, geo_field):
        """
        Converts geometry WKT returned from a SpatiaLite aggregate.
        """
        if wkt:
            return Geometry(wkt, geo_field.srid)
        else:
            return None

    def geo_db_type(self, f):
        """
        Returns None because geometry columnas are added via the
        `AddGeometryColumn` stored procedure on SpatiaLite.
        """
        return None

    def get_distance(self, f, value, lookup_type):
        """
        Returns the distance parameters for the given geometry field,
        lookup value, and lookup type.  SpatiaLite only supports regular
        cartesian-based queries (no spheroid/sphere calculations for point
        geometries like PostGIS).
        """
        if not value:
            return []
        value = value[0]
        if isinstance(value, Distance):
            if f.geodetic(self.connection):
                raise ValueError('SpatiaLite does not support distance queries on '
                                 'geometry fields with a geodetic coordinate system. '
                                 'Distance objects; use a numeric value of your '
                                 'distance in degrees instead.')
            else:
                dist_param = getattr(value, Distance.unit_attname(f.units_name(self.connection)))
        else:
            dist_param = value
        return [dist_param]

    def get_geom_placeholder(self, f, value):
        """
        Provides a proper substitution value for Geometries that are not in the
        SRID of the field.  Specifically, this routine will substitute in the
        Transform() and GeomFromText() function call(s).
        """
        def transform_value(value, srid):
            return not (value is None or value.srid == srid)
        if hasattr(value, 'expression'):
            if transform_value(value, f.srid):
                placeholder = '%s(%%s, %s)' % (self.transform, f.srid)
            else:
                placeholder = '%s'
            # No geometry value used for F expression, substitue in
            # the column name instead.
            return placeholder % '%s.%s' % tuple(map(self.quote_name, value.cols[value.expression]))
        else:
            if transform_value(value, f.srid):
                # Adding Transform() to the SQL placeholder.
                return '%s(%s(%%s,%s), %s)' % (self.transform, self.from_text, value.srid, f.srid)
            else:
                return '%s(%%s,%s)' % (self.from_text, f.srid)

    def _get_spatialite_func(self, func):
        """
        Helper routine for calling PostGIS functions and returning their result.
        """
        cursor = self.connection._cursor()
        try:
            try:
                cursor.execute('SELECT %s()' % func)
                row = cursor.fetchone()
            except:
                # Responsibility of caller to perform error handling.
                raise
        finally:
            cursor.close()
        return row[0]

    def geos_version(self):
        "Returns the version of GEOS used by SpatiaLite as a string."
        return self._get_spatialite_func('geos_version')

    def proj4_version(self):
        "Returns the version of the PROJ.4 library used by SpatiaLite."
        return self._get_spatialite_func('proj4_version')

    def spatialite_version(self):
        "Returns the SpatiaLite library version as a string."
        return self._get_spatialite_func('spatialite_version')

    def spatialite_version_tuple(self):
        """
        Returns the SpatiaLite version as a tuple (version string, major,
        minor, subminor).
        """
        # Getting the PostGIS version
        version = self.spatialite_version()
        m = self.version_regex.match(version)

        if m:
            major = int(m.group('major'))
            minor1 = int(m.group('minor1'))
            minor2 = int(m.group('minor2'))
        else:
            raise Exception('Could not parse SpatiaLite version string: %s' % version)

        return (version, major, minor1, minor2)

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
        sql_template = self.select % '%(function)s(%(field)s)'
        sql_function = getattr(self, agg_name)
        return sql_template, sql_function

    def spatial_lookup_sql(self, lvalue, lookup_type, value, field, qn):
        """
        Returns the SpatiaLite-specific SQL for the given lookup value
        [a tuple of (alias, column, db_type)], lookup type, lookup
        value, the model field, and the quoting function.
        """
        alias, col, db_type = lvalue

        # Getting the quoted field as `geo_col`.
        geo_col = '%s.%s' % (qn(alias), qn(col))

        if lookup_type in self.geometry_functions:
            # See if a SpatiaLite geometry function matches the lookup type.
            tmp = self.geometry_functions[lookup_type]

            # Lookup types that are tuples take tuple arguments, e.g., 'relate' and
            # distance lookups.
            if isinstance(tmp, tuple):
                # First element of tuple is the SpatiaLiteOperation instance, and the
                # second element is either the type or a tuple of acceptable types
                # that may passed in as further parameters for the lookup type.
                op, arg_type = tmp

                # Ensuring that a tuple _value_ was passed in from the user
                if not isinstance(value, (tuple, list)):
                    raise ValueError('Tuple required for `%s` lookup type.' % lookup_type)

                # Geometry is first element of lookup tuple.
                geom = value[0]

                # Number of valid tuple parameters depends on the lookup type.
                if len(value) != 2:
                    raise ValueError('Incorrect number of parameters given for `%s` lookup type.' % lookup_type)

                # Ensuring the argument type matches what we expect.
                if not isinstance(value[1], arg_type):
                    raise ValueError('Argument type should be %s, got %s instead.' % (arg_type, type(value[1])))

                # For lookup type `relate`, the op instance is not yet created (has
                # to be instantiated here to check the pattern parameter).
                if lookup_type == 'relate':
                    op = op(value[1])
                elif lookup_type in self.distance_functions:
                    op = op[0]
            else:
                op = tmp
                geom = value
            # Calling the `as_sql` function on the operation instance.
            return op.as_sql(geo_col, self.get_geom_placeholder(field, geom))
        elif lookup_type == 'isnull':
            # Handling 'isnull' lookup type
            return "%s IS %sNULL" % (geo_col, (not value and 'NOT ' or ''))

        raise TypeError("Got invalid lookup_type: %s" % repr(lookup_type))

    # Routines for getting the OGC-compliant models.
    def geometry_columns(self):
        from django.contrib.gis.db.backends.spatialite.models import GeometryColumns
        return GeometryColumns

    def spatial_ref_sys(self):
        from django.contrib.gis.db.backends.spatialite.models import SpatialRefSys
        return SpatialRefSys
