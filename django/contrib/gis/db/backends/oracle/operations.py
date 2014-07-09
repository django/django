"""
 This module contains the spatial lookup types, and the `get_geo_where_clause`
 routine for Oracle Spatial.

 Please note that WKT support is broken on the XE version, and thus
 this backend will not work on such platforms.  Specifically, XE lacks
 support for an internal JVM, and Java libraries are required to use
 the WKT constructors.
"""
import re
from decimal import Decimal

from django.db.backends.oracle.base import DatabaseOperations
from django.contrib.gis.db.backends.base import BaseSpatialOperations
from django.contrib.gis.db.backends.oracle.adapter import OracleSpatialAdapter
from django.contrib.gis.db.backends.utils import SpatialFunction
from django.contrib.gis.geometry.backend import Geometry
from django.contrib.gis.measure import Distance
from django.utils import six


class SDOOperation(SpatialFunction):
    "Base class for SDO* Oracle operations."
    sql_template = "%(function)s(%(geo_col)s, %(geometry)s) %(operator)s '%(result)s'"

    def __init__(self, func, **kwargs):
        kwargs.setdefault('operator', '=')
        kwargs.setdefault('result', 'TRUE')
        super(SDOOperation, self).__init__(func, **kwargs)


class SDODistance(SpatialFunction):
    "Class for Distance queries."
    sql_template = ('%(function)s(%(geo_col)s, %(geometry)s, %(tolerance)s) '
                    '%(operator)s %(result)s')
    dist_func = 'SDO_GEOM.SDO_DISTANCE'

    def __init__(self, op, tolerance=0.05):
        super(SDODistance, self).__init__(self.dist_func,
                                          tolerance=tolerance,
                                          operator=op, result='%s')


class SDODWithin(SpatialFunction):
    dwithin_func = 'SDO_WITHIN_DISTANCE'
    sql_template = "%(function)s(%(geo_col)s, %(geometry)s, %%s) = 'TRUE'"

    def __init__(self):
        super(SDODWithin, self).__init__(self.dwithin_func)


class SDOGeomRelate(SpatialFunction):
    "Class for using SDO_GEOM.RELATE."
    relate_func = 'SDO_GEOM.RELATE'
    sql_template = ("%(function)s(%(geo_col)s, '%(mask)s', %(geometry)s, "
                    "%(tolerance)s) %(operator)s '%(mask)s'")

    def __init__(self, mask, tolerance=0.05):
        # SDO_GEOM.RELATE(...) has a peculiar argument order: column, mask, geom, tolerance.
        # Moreover, the runction result is the mask (e.g., 'DISJOINT' instead of 'TRUE').
        super(SDOGeomRelate, self).__init__(self.relate_func, operator='=',
                                            mask=mask, tolerance=tolerance)


class SDORelate(SpatialFunction):
    "Class for using SDO_RELATE."
    masks = 'TOUCH|OVERLAPBDYDISJOINT|OVERLAPBDYINTERSECT|EQUAL|INSIDE|COVEREDBY|CONTAINS|COVERS|ANYINTERACT|ON'
    mask_regex = re.compile(r'^(%s)(\+(%s))*$' % (masks, masks), re.I)
    sql_template = "%(function)s(%(geo_col)s, %(geometry)s, 'mask=%(mask)s') = 'TRUE'"
    relate_func = 'SDO_RELATE'

    def __init__(self, mask):
        if not self.mask_regex.match(mask):
            raise ValueError('Invalid %s mask: "%s"' % (self.relate_func, mask))
        super(SDORelate, self).__init__(self.relate_func, mask=mask)

# Valid distance types and substitutions
dtypes = (Decimal, Distance, float) + six.integer_types


class OracleOperations(DatabaseOperations, BaseSpatialOperations):
    compiler_module = "django.contrib.gis.db.backends.oracle.compiler"

    name = 'oracle'
    oracle = True
    valid_aggregates = {'Union', 'Extent'}

    Adapter = OracleSpatialAdapter
    Adaptor = Adapter  # Backwards-compatibility alias.

    area = 'SDO_GEOM.SDO_AREA'
    gml = 'SDO_UTIL.TO_GMLGEOMETRY'
    centroid = 'SDO_GEOM.SDO_CENTROID'
    difference = 'SDO_GEOM.SDO_DIFFERENCE'
    distance = 'SDO_GEOM.SDO_DISTANCE'
    extent = 'SDO_AGGR_MBR'
    intersection = 'SDO_GEOM.SDO_INTERSECTION'
    length = 'SDO_GEOM.SDO_LENGTH'
    num_geom = 'SDO_UTIL.GETNUMELEM'
    num_points = 'SDO_UTIL.GETNUMVERTICES'
    perimeter = length
    point_on_surface = 'SDO_GEOM.SDO_POINTONSURFACE'
    reverse = 'SDO_UTIL.REVERSE_LINESTRING'
    sym_difference = 'SDO_GEOM.SDO_XOR'
    transform = 'SDO_CS.TRANSFORM'
    union = 'SDO_GEOM.SDO_UNION'
    unionagg = 'SDO_AGGR_UNION'

    # We want to get SDO Geometries as WKT because it is much easier to
    # instantiate GEOS proxies from WKT than SDO_GEOMETRY(...) strings.
    # However, this adversely affects performance (i.e., Java is called
    # to convert to WKT on every query).  If someone wishes to write a
    # SDO_GEOMETRY(...) parser in Python, let me know =)
    select = 'SDO_UTIL.TO_WKTGEOMETRY(%s)'

    distance_functions = {
        'distance_gt': (SDODistance('>'), dtypes),
        'distance_gte': (SDODistance('>='), dtypes),
        'distance_lt': (SDODistance('<'), dtypes),
        'distance_lte': (SDODistance('<='), dtypes),
        'dwithin': (SDODWithin(), dtypes),
    }

    geometry_functions = {
        'contains': SDOOperation('SDO_CONTAINS'),
        'coveredby': SDOOperation('SDO_COVEREDBY'),
        'covers': SDOOperation('SDO_COVERS'),
        'disjoint': SDOGeomRelate('DISJOINT'),
        'intersects': SDOOperation('SDO_OVERLAPBDYINTERSECT'),  # TODO: Is this really the same as ST_Intersects()?
        'equals': SDOOperation('SDO_EQUAL'),
        'exact': SDOOperation('SDO_EQUAL'),
        'overlaps': SDOOperation('SDO_OVERLAPS'),
        'same_as': SDOOperation('SDO_EQUAL'),
        'relate': (SDORelate, six.string_types),  # Oracle uses a different syntax, e.g., 'mask=inside+touch'
        'touches': SDOOperation('SDO_TOUCH'),
        'within': SDOOperation('SDO_INSIDE'),
    }
    geometry_functions.update(distance_functions)

    gis_terms = set(['isnull'])
    gis_terms.update(geometry_functions)

    truncate_params = {'relate': None}

    def convert_extent(self, clob):
        if clob:
            # Generally, Oracle returns a polygon for the extent -- however,
            # it can return a single point if there's only one Point in the
            # table.
            ext_geom = Geometry(clob.read())
            gtype = str(ext_geom.geom_type)
            if gtype == 'Polygon':
                # Construct the 4-tuple from the coordinates in the polygon.
                shell = ext_geom.shell
                ll, ur = shell[0][:2], shell[2][:2]
            elif gtype == 'Point':
                ll = ext_geom.coords[:2]
                ur = ll
            else:
                raise Exception('Unexpected geometry type returned for extent: %s' % gtype)
            xmin, ymin = ll
            xmax, ymax = ur
            return (xmin, ymin, xmax, ymax)
        else:
            return None

    def convert_geom(self, clob, geo_field):
        if clob:
            return Geometry(clob.read(), geo_field.srid)
        else:
            return None

    def geo_db_type(self, f):
        """
        Returns the geometry database type for Oracle.  Unlike other spatial
        backends, no stored procedure is necessary and it's the same for all
        geometry types.
        """
        return 'MDSYS.SDO_GEOMETRY'

    def get_distance(self, f, value, lookup_type):
        """
        Returns the distance parameters given the value and the lookup type.
        On Oracle, geometry columns with a geodetic coordinate system behave
        implicitly like a geography column, and thus meters will be used as
        the distance parameter on them.
        """
        if not value:
            return []
        value = value[0]
        if isinstance(value, Distance):
            if f.geodetic(self.connection):
                dist_param = value.m
            else:
                dist_param = getattr(value, Distance.unit_attname(f.units_name(self.connection)))
        else:
            dist_param = value

        # dwithin lookups on Oracle require a special string parameter
        # that starts with "distance=".
        if lookup_type == 'dwithin':
            dist_param = 'distance=%s' % dist_param

        return [dist_param]

    def get_geom_placeholder(self, f, value):
        """
        Provides a proper substitution value for Geometries that are not in the
        SRID of the field.  Specifically, this routine will substitute in the
        SDO_CS.TRANSFORM() function call.
        """
        if value is None:
            return 'NULL'

        def transform_value(val, srid):
            return val.srid != srid

        if hasattr(value, 'expression'):
            if transform_value(value, f.srid):
                placeholder = '%s(%%s, %s)' % (self.transform, f.srid)
            else:
                placeholder = '%s'
            # No geometry value used for F expression, substitute in
            # the column name instead.
            return placeholder % self.get_expression_column(value)
        else:
            if transform_value(value, f.srid):
                return '%s(SDO_GEOMETRY(%%s, %s), %s)' % (self.transform, value.srid, f.srid)
            else:
                return 'SDO_GEOMETRY(%%s, %s)' % f.srid

    def spatial_lookup_sql(self, lvalue, lookup_type, value, field, qn):
        "Returns the SQL WHERE clause for use in Oracle spatial SQL construction."
        geo_col, db_type = lvalue

        # See if an Oracle Geometry function matches the lookup type next
        lookup_info = self.geometry_functions.get(lookup_type, False)
        if lookup_info:
            # Lookup types that are tuples take tuple arguments, e.g., 'relate' and
            # 'dwithin' lookup types.
            if isinstance(lookup_info, tuple):
                # First element of tuple is lookup type, second element is the type
                # of the expected argument (e.g., str, float)
                sdo_op, arg_type = lookup_info
                geom = value[0]

                # Ensuring that a tuple _value_ was passed in from the user
                if not isinstance(value, tuple):
                    raise ValueError('Tuple required for `%s` lookup type.' % lookup_type)
                if len(value) != 2:
                    raise ValueError('2-element tuple required for %s lookup type.' % lookup_type)

                # Ensuring the argument type matches what we expect.
                if not isinstance(value[1], arg_type):
                    raise ValueError('Argument type should be %s, got %s instead.' % (arg_type, type(value[1])))

                if lookup_type == 'relate':
                    # The SDORelate class handles construction for these queries,
                    # and verifies the mask argument.
                    return sdo_op(value[1]).as_sql(geo_col, self.get_geom_placeholder(field, geom))
                else:
                    # Otherwise, just call the `as_sql` method on the SDOOperation instance.
                    return sdo_op.as_sql(geo_col, self.get_geom_placeholder(field, geom))
            else:
                # Lookup info is a SDOOperation instance, whose `as_sql` method returns
                # the SQL necessary for the geometry function call. For example:
                #  SDO_CONTAINS("geoapp_country"."poly", SDO_GEOMTRY('POINT(5 23)', 4326)) = 'TRUE'
                return lookup_info.as_sql(geo_col, self.get_geom_placeholder(field, value))
        elif lookup_type == 'isnull':
            # Handling 'isnull' lookup type
            return "%s IS %sNULL" % (geo_col, ('' if value else 'NOT ')), []

        raise TypeError("Got invalid lookup_type: %s" % repr(lookup_type))

    def spatial_aggregate_sql(self, agg):
        """
        Returns the spatial aggregate SQL template and function for the
        given Aggregate instance.
        """
        agg_name = agg.__class__.__name__.lower()
        if agg_name == 'union':
            agg_name += 'agg'
        if agg.is_extent:
            sql_template = '%(function)s(%(field)s)'
        else:
            sql_template = '%(function)s(SDOAGGRTYPE(%(field)s,%(tolerance)s))'
        sql_function = getattr(self, agg_name)
        return self.select % sql_template, sql_function

    # Routines for getting the OGC-compliant models.
    def geometry_columns(self):
        from django.contrib.gis.db.backends.oracle.models import OracleGeometryColumns
        return OracleGeometryColumns

    def spatial_ref_sys(self):
        from django.contrib.gis.db.backends.oracle.models import OracleSpatialRefSys
        return OracleSpatialRefSys

    def modify_insert_params(self, placeholders, params):
        """Drop out insert parameters for NULL placeholder. Needed for Oracle Spatial
        backend due to #10888
        """
        # This code doesn't work for bulk insert cases.
        assert len(placeholders) == 1
        return [[param for pholder, param
                 in six.moves.zip(placeholders[0], params[0]) if pholder != 'NULL'], ]
