"""
 This module contains the spatial lookup types, and the `get_geo_where_clause`
 routine for Oracle Spatial.

 Please note that WKT support is broken on the XE version, and thus
 this backend will not work on such platforms.  Specifically, XE lacks
 support for an internal JVM, and Java libraries are required to use
 the WKT constructors.
"""
import re

from django.contrib.gis.db.backends.base.operations import \
    BaseSpatialOperations
from django.contrib.gis.db.backends.oracle.adapter import OracleSpatialAdapter
from django.contrib.gis.db.backends.utils import SpatialOperator
from django.contrib.gis.db.models import aggregates
from django.contrib.gis.geometry.backend import Geometry
from django.contrib.gis.measure import Distance
from django.db.backends.oracle.base import Database
from django.db.backends.oracle.operations import DatabaseOperations
from django.utils import six

DEFAULT_TOLERANCE = '0.05'


class SDOOperator(SpatialOperator):
    sql_template = "%(func)s(%(lhs)s, %(rhs)s) = 'TRUE'"


class SDODistance(SpatialOperator):
    sql_template = "SDO_GEOM.SDO_DISTANCE(%%(lhs)s, %%(rhs)s, %s) %%(op)s %%%%s" % DEFAULT_TOLERANCE


class SDODWithin(SpatialOperator):
    sql_template = "SDO_WITHIN_DISTANCE(%(lhs)s, %(rhs)s, %%s) = 'TRUE'"


class SDODisjoint(SpatialOperator):
    sql_template = "SDO_GEOM.RELATE(%%(lhs)s, 'DISJOINT', %%(rhs)s, %s) = 'DISJOINT'" % DEFAULT_TOLERANCE


class SDORelate(SpatialOperator):
    sql_template = "SDO_RELATE(%(lhs)s, %(rhs)s, 'mask=%(mask)s') = 'TRUE'"

    def check_relate_argument(self, arg):
        masks = 'TOUCH|OVERLAPBDYDISJOINT|OVERLAPBDYINTERSECT|EQUAL|INSIDE|COVEREDBY|CONTAINS|COVERS|ANYINTERACT|ON'
        mask_regex = re.compile(r'^(%s)(\+(%s))*$' % (masks, masks), re.I)
        if not isinstance(arg, six.string_types) or not mask_regex.match(arg):
            raise ValueError('Invalid SDO_RELATE mask: "%s"' % arg)

    def as_sql(self, connection, lookup, template_params, sql_params):
        template_params['mask'] = sql_params.pop()
        return super(SDORelate, self).as_sql(connection, lookup, template_params, sql_params)


class OracleOperations(BaseSpatialOperations, DatabaseOperations):

    name = 'oracle'
    oracle = True
    disallowed_aggregates = (aggregates.Collect, aggregates.Extent3D, aggregates.MakeLine)

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

    gis_operators = {
        'contains': SDOOperator(func='SDO_CONTAINS'),
        'coveredby': SDOOperator(func='SDO_COVEREDBY'),
        'covers': SDOOperator(func='SDO_COVERS'),
        'disjoint': SDODisjoint(),
        'intersects': SDOOperator(func='SDO_OVERLAPBDYINTERSECT'),  # TODO: Is this really the same as ST_Intersects()?
        'equals': SDOOperator(func='SDO_EQUAL'),
        'exact': SDOOperator(func='SDO_EQUAL'),
        'overlaps': SDOOperator(func='SDO_OVERLAPS'),
        'same_as': SDOOperator(func='SDO_EQUAL'),
        'relate': SDORelate(),  # Oracle uses a different syntax, e.g., 'mask=inside+touch'
        'touches': SDOOperator(func='SDO_TOUCH'),
        'within': SDOOperator(func='SDO_INSIDE'),
        'distance_gt': SDODistance(op='>'),
        'distance_gte': SDODistance(op='>='),
        'distance_lt': SDODistance(op='<'),
        'distance_lte': SDODistance(op='<='),
        'dwithin': SDODWithin(),
    }

    truncate_params = {'relate': None}

    def geo_quote_name(self, name):
        return super(OracleOperations, self).geo_quote_name(name).upper()

    def get_db_converters(self, expression):
        converters = super(OracleOperations, self).get_db_converters(expression)
        internal_type = expression.output_field.get_internal_type()
        geometry_fields = (
            'PointField', 'GeometryField', 'LineStringField',
            'PolygonField', 'MultiPointField', 'MultiLineStringField',
            'MultiPolygonField', 'GeometryCollectionField', 'GeomField',
            'GMLField',
        )
        if internal_type in geometry_fields:
            converters.append(self.convert_textfield_value)
        if hasattr(expression.output_field, 'geom_type'):
            converters.append(self.convert_geometry)
        return converters

    def convert_geometry(self, value, expression, connection, context):
        if value:
            value = Geometry(value)
            if 'transformed_srid' in context:
                value.srid = context['transformed_srid']
        return value

    def convert_extent(self, clob, srid):
        if clob:
            # Generally, Oracle returns a polygon for the extent -- however,
            # it can return a single point if there's only one Point in the
            # table.
            ext_geom = Geometry(clob.read(), srid)
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

    def convert_geom(self, value, geo_field):
        if value:
            if isinstance(value, Database.LOB):
                value = value.read()
            return Geometry(value, geo_field.srid)
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

    def get_geom_placeholder(self, f, value, compiler):
        """
        Provides a proper substitution value for Geometries that are not in the
        SRID of the field.  Specifically, this routine will substitute in the
        SDO_CS.TRANSFORM() function call.
        """
        if value is None:
            return 'NULL'

        def transform_value(val, srid):
            return val.srid != srid

        if hasattr(value, 'as_sql'):
            if transform_value(value, f.srid):
                placeholder = '%s(%%s, %s)' % (self.transform, f.srid)
            else:
                placeholder = '%s'
            # No geometry value used for F expression, substitute in
            # the column name instead.
            sql, _ = compiler.compile(value)
            return placeholder % sql
        else:
            if transform_value(value, f.srid):
                return '%s(SDO_GEOMETRY(%%s, %s), %s)' % (self.transform, value.srid, f.srid)
            else:
                return 'SDO_GEOMETRY(%%s, %s)' % f.srid

    def spatial_aggregate_name(self, agg_name):
        """
        Returns the spatial aggregate SQL name.
        """
        agg_name = 'unionagg' if agg_name.lower() == 'union' else agg_name.lower()
        return getattr(self, agg_name)

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
