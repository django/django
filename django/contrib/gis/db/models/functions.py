from decimal import Decimal

from django.contrib.gis.db.models.fields import GeometryField
from django.contrib.gis.db.models.sql import AreaField
from django.contrib.gis.geos.geometry import GEOSGeometry
from django.contrib.gis.measure import (
    Area as AreaMeasure, Distance as DistanceMeasure,
)
from django.db.models import FloatField, IntegerField, TextField
from django.db.models.expressions import Func, Value
from django.utils import six
from django.utils.six.moves import range

NUMERIC_TYPES = six.integer_types + (float, Decimal)


class GeoFunc(Func):
    function = None
    output_field_class = None
    geom_param_pos = None

    def __init__(self, *expressions, **extra):
        if 'output_field' not in extra and self.output_field_class:
            extra['output_field'] = self.output_field_class()

        if self.geom_param_pos is None:
            # Assume that all expressions should be geometric.
            self.geom_param_pos = range(len(expressions))
        if isinstance(self.geom_param_pos, six.integer_types):
            self.geom_param_pos = [self.geom_param_pos]
        super(GeoFunc, self).__init__(*expressions, **extra)

    def _parse_expressions(self, *expressions):
        expressions = super(GeoFunc, self)._parse_expressions(*expressions)

        for pos in self.geom_param_pos:
            expr = expressions[pos]
            if not isinstance(expr, Value):
                continue

            value = expr.value
            if not isinstance(value, GEOSGeometry):
                raise TypeError("%s function requires a geometric parameter, got %s." % (self.name, value))
            if not value.srid:
                raise ValueError("SRID is required for all geometries.")
            expressions[pos] = GeomValue(value)

        return expressions

    @property
    def name(self):
        return self.__class__.__name__

    @property
    def srid(self):
        expr = self.source_expressions[self.geom_param_pos[0]]
        return expr.srid if hasattr(expr, 'srid') else expr.field.srid

    def as_sql(self, compiler, connection):
        if self.function is None:
            self.function = connection.ops.spatial_function_name(self.name)
        return super(GeoFunc, self).as_sql(compiler, connection)

    def resolve_expression(self, *args, **kwargs):
        res = super(GeoFunc, self).resolve_expression(*args, **kwargs)

        for pos in self.geom_param_pos:
            expr = res.source_expressions[pos]
            if not isinstance(expr, Value) and not isinstance(expr.output_field, GeometryField):
                raise ValueError(
                    "%s function requires a geometric field, got %s of type %s." % (
                        self.name,
                        type(expr.output_field).__name__,
                        expr.output_field,
                    )
                )

        base_srid = res.srid
        for pos in self.geom_param_pos:
            if pos == self.geom_param_pos[0]:
                continue
            expr = res.source_expressions[pos]
            if isinstance(expr, GeomValue):
                expr_srid = expr.srid
            else:
                expr_srid = expr.output_field.srid
            if expr_srid != base_srid:
                # Automatic SRID conversion so objects are comparable.
                res.source_expressions[pos] = Transform(expr, base_srid).resolve_expression(*args, **kwargs)
        return res

    def _handle_param(self, value, param_name='', check_types=None):
        if not hasattr(value, 'resolve_expression'):
            if check_types and not isinstance(value, check_types):
                raise TypeError(
                    "The %s parameter has the wrong type: should be %s." % (
                        param_name, str(check_types))
                )
        return value


class GeomOutputGeoFunc(GeoFunc):

    @property
    def output_field(self):
        return GeometryField(srid=self.srid)


class GeomValue(Value):
    geography = False

    @property
    def srid(self):
        return self.value.srid

    def as_sql(self, compiler, connection):
        self.value = connection.ops.Adapter(self.value, geography=self.geography)
        return super(GeomValue, self).as_sql(compiler, connection)

    def as_mysql(self, compiler, connection):
        return 'GeomFromText(%%s, %s)' % self.srid, [connection.ops.Adapter(self.value)]

    def as_sqlite(self, compiler, connection):
        return 'GeomFromText(%%s, %s)' % self.srid, [connection.ops.Adapter(self.value)]

    def as_oracle(self, compiler, connection):
        return 'SDO_GEOMETRY(%%s, %s)' % self.srid, [connection.ops.Adapter(self.value)]


class SQLiteDecimalToFloatMixin(object):
    """
    By default, Decimal values are converted to str by the SQLite backend, which
    is not acceptable by the GIS functions expecting numeric values.
    """
    def as_sqlite(self, compiler, connection):
        for expr in self.get_source_expressions():
            if hasattr(expr, 'value') and isinstance(expr.value, Decimal):
                expr.value = float(expr.value)
        return super(SQLiteDecimalToFloatMixin, self).as_sql(compiler, connection)


class OracleToleranceMixin(object):
    tolerance = 0.05

    def as_oracle(self, compiler, connection):
        tol = self.extra.get('tolerance', self.tolerance)
        self.template = "%%(function)s(%%(expressions)s, %s)" % tol
        return super(OracleToleranceMixin, self).as_sql(compiler, connection)


class Area(OracleToleranceMixin, GeoFunc):
    arity = 1

    def as_sql(self, compiler, connection):
        if connection.ops.geography:
            # Geography fields support area calculation, returns square meters.
            self.output_field = AreaField('sq_m')
        elif not self.output_field.geodetic(connection):
            # Getting the area units of the geographic field.
            units = self.output_field.units_name(connection)
            if units:
                self.output_field = AreaField(
                    AreaMeasure.unit_attname(self.output_field.units_name(connection))
                )
            else:
                self.output_field = FloatField()
        else:
            # TODO: Do we want to support raw number areas for geodetic fields?
            raise NotImplementedError('Area on geodetic coordinate systems not supported.')
        return super(Area, self).as_sql(compiler, connection)

    def as_oracle(self, compiler, connection):
        self.output_field = AreaField('sq_m')  # Oracle returns area in units of meters.
        return super(Area, self).as_oracle(compiler, connection)


class AsGeoJSON(GeoFunc):
    geom_param_pos = 0
    output_field_class = TextField

    def __init__(self, expression, bbox=False, crs=False, precision=8, **extra):
        expressions = [expression]
        if precision is not None:
            expressions.append(self._handle_param(precision, 'precision', six.integer_types))
        options = 0
        if crs and bbox:
            options = 3
        elif bbox:
            options = 1
        elif crs:
            options = 2
        if options:
            expressions.append(options)
        super(AsGeoJSON, self).__init__(*expressions, **extra)


class AsGML(GeoFunc):
    geom_param_pos = 1
    output_field_class = TextField

    def __init__(self, expression, version=2, precision=8, **extra):
        expressions = [version, expression]
        if precision is not None:
            expressions.append(self._handle_param(precision, 'precision', six.integer_types))
        super(AsGML, self).__init__(*expressions, **extra)


class AsKML(AsGML):
    def as_sqlite(self, compiler, connection):
        # No version parameter
        self.source_expressions.pop(0)
        return super(AsKML, self).as_sql(compiler, connection)


class AsSVG(GeoFunc):
    geom_param_pos = 0
    output_field_class = TextField

    def __init__(self, expression, relative=False, precision=8, **extra):
        relative = relative if hasattr(relative, 'resolve_expression') else int(relative)
        expressions = [
            expression,
            relative,
            self._handle_param(precision, 'precision', six.integer_types),
        ]
        super(AsSVG, self).__init__(*expressions, **extra)


class BoundingCircle(GeoFunc):
    geom_param_pos = 0

    def __init__(self, expression, num_seg=48, **extra):
        super(BoundingCircle, self).__init__(expression, num_seg, **extra)


class Centroid(OracleToleranceMixin, GeomOutputGeoFunc):
    arity = 1


class Difference(OracleToleranceMixin, GeomOutputGeoFunc):
    arity = 2


class DistanceResultMixin(object):
    def convert_value(self, value, expression, connection, context):
        if value is None:
            return None
        geo_field = GeometryField(srid=self.srid)  # Fake field to get SRID info
        if geo_field.geodetic(connection):
            dist_att = 'm'
        else:
            units = geo_field.units_name(connection)
            if units:
                dist_att = DistanceMeasure.unit_attname(units)
            else:
                dist_att = None
        if dist_att:
            return DistanceMeasure(**{dist_att: value})
        return value


class Distance(DistanceResultMixin, OracleToleranceMixin, GeoFunc):
    geom_param_pos = (0, 1)
    output_field_class = FloatField
    spheroid = None

    def __init__(self, expr1, expr2, spheroid=None, **extra):
        expressions = [expr1, expr2]
        if spheroid is not None:
            self.spheroid = spheroid
            expressions += (self._handle_param(spheroid, 'spheroid', bool),)
        super(Distance, self).__init__(*expressions, **extra)

    def as_postgresql(self, compiler, connection):
        geo_field = GeometryField(srid=self.srid)  # Fake field to get SRID info
        src_fields = [self.get_source_fields()[i] for i in self.geom_param_pos]
        geography = self.srid == 4326 and any(f is not None and f.geography for f in src_fields)
        if geography:
            # Set parameters as geography if base field is geography
            for expr in [self.source_expressions[i] for i in self.geom_param_pos]:
                if isinstance(expr, GeomValue):
                    expr.geography = True
        elif geo_field.geodetic(connection):
            # Geometry fields with geodetic (lon/lat) coordinates need special distance functions
            if self.spheroid:
                self.function = 'ST_Distance_Spheroid'  # More accurate, resource intensive
                # Replace boolean param by the real spheroid of the base field
                self.source_expressions[2] = Value(geo_field._spheroid)
            else:
                self.function = 'ST_Distance_Sphere'
        return super(Distance, self).as_sql(compiler, connection)

    def as_oracle(self, compiler, connection):
        if self.spheroid:
            self.source_expressions.pop(2)
        return super(Distance, self).as_oracle(compiler, connection)


class Envelope(GeomOutputGeoFunc):
    arity = 1


class ForceRHR(GeomOutputGeoFunc):
    arity = 1


class GeoHash(GeoFunc):
    geom_param_pos = 0
    output_field_class = TextField

    def __init__(self, expression, precision=None, **extra):
        expressions = [expression]
        if precision is not None:
            expressions.append(self._handle_param(precision, 'precision', six.integer_types))
        super(GeoHash, self).__init__(*expressions, **extra)


class Intersection(OracleToleranceMixin, GeomOutputGeoFunc):
    arity = 2


class Length(DistanceResultMixin, OracleToleranceMixin, GeoFunc):
    output_field_class = FloatField

    def __init__(self, expression, spheroid=True, **extra):
        self.spheroid = spheroid
        super(Length, self).__init__(expression, **extra)

    def as_sql(self, compiler, connection):
        geo_field = GeometryField(srid=self.srid)  # Fake field to get SRID info
        if geo_field.geodetic(connection) and not connection.features.supports_length_geodetic:
            raise NotImplementedError("This backend doesn't support Length on geodetic fields")
        return super(Length, self).as_sql(compiler, connection)

    def as_postgresql(self, compiler, connection):
        geo_field = GeometryField(srid=self.srid)  # Fake field to get SRID info
        src_fields = [self.get_source_fields()[i] for i in self.geom_param_pos]
        geography = self.srid == 4326 and any(f is not None and f.geography for f in src_fields)
        if geography:
            self.source_expressions.append(Value(self.spheroid))
        elif geo_field.geodetic(connection):
            # Geometry fields with geodetic (lon/lat) coordinates need length_spheroid
            self.function = 'ST_Length_Spheroid'
            self.source_expressions.append(Value(geo_field._spheroid))
        else:
            dim = min(f.dim for f in self.get_source_fields() if f)
            if dim > 2:
                self.function = connection.ops.length3d
        return super(Length, self).as_sql(compiler, connection)

    def as_sqlite(self, compiler, connection):
        geo_field = GeometryField(srid=self.srid)
        if geo_field.geodetic(connection):
            if self.spheroid:
                self.function = 'GeodesicLength'
            else:
                self.function = 'GreatCircleLength'
        return super(Length, self).as_sql(compiler, connection)


class MemSize(GeoFunc):
    output_field_class = IntegerField
    arity = 1


class NumGeometries(GeoFunc):
    output_field_class = IntegerField
    arity = 1


class NumPoints(GeoFunc):
    output_field_class = IntegerField
    arity = 1

    def as_sqlite(self, compiler, connection):
        if self.source_expressions[0].output_field.geom_type != 'LINESTRING':
            raise TypeError("Spatialite NumPoints can only operate on LineString content")
        return super(NumPoints, self).as_sql(compiler, connection)


class Perimeter(DistanceResultMixin, OracleToleranceMixin, GeoFunc):
    output_field_class = FloatField
    arity = 1

    def as_postgresql(self, compiler, connection):
        dim = min(f.dim for f in self.get_source_fields())
        if dim > 2:
            self.function = connection.ops.perimeter3d
        return super(Perimeter, self).as_sql(compiler, connection)


class PointOnSurface(OracleToleranceMixin, GeomOutputGeoFunc):
    arity = 1


class Reverse(GeomOutputGeoFunc):
    arity = 1


class Scale(SQLiteDecimalToFloatMixin, GeomOutputGeoFunc):
    geom_param_pos = 0

    def __init__(self, expression, x, y, z=0.0, **extra):
        expressions = [
            expression,
            self._handle_param(x, 'x', NUMERIC_TYPES),
            self._handle_param(y, 'y', NUMERIC_TYPES),
        ]
        if z != 0.0:
            expressions.append(self._handle_param(z, 'z', NUMERIC_TYPES))
        super(Scale, self).__init__(*expressions, **extra)


class SnapToGrid(SQLiteDecimalToFloatMixin, GeomOutputGeoFunc):
    geom_param_pos = 0

    def __init__(self, expression, *args, **extra):
        nargs = len(args)
        expressions = [expression]
        if nargs in (1, 2):
            expressions.extend(
                [self._handle_param(arg, '', NUMERIC_TYPES) for arg in args]
            )
        elif nargs == 4:
            # Reverse origin and size param ordering
            expressions.extend(
                [self._handle_param(arg, '', NUMERIC_TYPES) for arg in args[2:]]
            )
            expressions.extend(
                [self._handle_param(arg, '', NUMERIC_TYPES) for arg in args[0:2]]
            )
        else:
            raise ValueError('Must provide 1, 2, or 4 arguments to `SnapToGrid`.')
        super(SnapToGrid, self).__init__(*expressions, **extra)


class SymDifference(OracleToleranceMixin, GeomOutputGeoFunc):
    arity = 2


class Transform(GeomOutputGeoFunc):
    geom_param_pos = 0

    def __init__(self, expression, srid, **extra):
        expressions = [
            expression,
            self._handle_param(srid, 'srid', six.integer_types),
        ]
        super(Transform, self).__init__(*expressions, **extra)

    @property
    def srid(self):
        # Make srid the resulting srid of the transformation
        return self.source_expressions[1].value


class Translate(Scale):
    def as_sqlite(self, compiler, connection):
        func_name = connection.ops.spatial_function_name(self.name)
        if func_name == 'ST_Translate' and len(self.source_expressions) < 4:
            # Always provide the z parameter for ST_Translate (Spatialite >= 3.1)
            self.source_expressions.append(Value(0))
        elif func_name == 'ShiftCoords' and len(self.source_expressions) > 3:
            raise ValueError("This version of Spatialite doesn't support 3D")
        return super(Translate, self).as_sqlite(compiler, connection)


class Union(OracleToleranceMixin, GeomOutputGeoFunc):
    arity = 2
