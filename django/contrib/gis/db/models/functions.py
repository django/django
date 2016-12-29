from decimal import Decimal

from django.contrib.gis.db.models.fields import GeometryField, RasterField
from django.contrib.gis.db.models.sql import AreaField
from django.contrib.gis.geometry.backend import Geometry
from django.contrib.gis.measure import (
    Area as AreaMeasure, Distance as DistanceMeasure,
)
from django.core.exceptions import FieldError
from django.db.models import BooleanField, FloatField, IntegerField, TextField
from django.db.models.expressions import Func, Value

NUMERIC_TYPES = (int, float, Decimal)


class GeoFunc(Func):
    function = None
    output_field_class = None
    geom_param_pos = 0

    def __init__(self, *expressions, **extra):
        if 'output_field' not in extra and self.output_field_class:
            extra['output_field'] = self.output_field_class()
        super(GeoFunc, self).__init__(*expressions, **extra)

    @property
    def name(self):
        return self.__class__.__name__

    @property
    def srid(self):
        expr = self.source_expressions[self.geom_param_pos]
        if hasattr(expr, 'srid'):
            return expr.srid
        try:
            return expr.field.srid
        except (AttributeError, FieldError):
            return None

    @property
    def geo_field(self):
        return GeometryField(srid=self.srid) if self.srid else None

    def as_sql(self, compiler, connection, **extra_context):
        if self.function is None:
            self.function = connection.ops.spatial_function_name(self.name)
        if any(isinstance(field, RasterField) for field in self.get_source_fields()):
            raise TypeError("Geometry functions not supported for raster fields.")
        return super(GeoFunc, self).as_sql(compiler, connection, **extra_context)

    def resolve_expression(self, *args, **kwargs):
        res = super(GeoFunc, self).resolve_expression(*args, **kwargs)
        base_srid = res.srid
        if not base_srid:
            raise TypeError("Geometry functions can only operate on geometric content.")

        for pos, expr in enumerate(res.source_expressions[1:], start=1):
            if isinstance(expr, GeomValue) and expr.srid != base_srid:
                # Automatic SRID conversion so objects are comparable
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


class GeomValue(Value):
    geography = False

    @property
    def srid(self):
        return self.value.srid

    def as_sql(self, compiler, connection):
        return '%s(%%s, %s)' % (connection.ops.from_text, self.srid), [connection.ops.Adapter(self.value)]

    def as_mysql(self, compiler, connection):
        return '%s(%%s)' % (connection.ops.from_text), [connection.ops.Adapter(self.value)]

    def as_postgresql(self, compiler, connection):
        if self.geography:
            self.value = connection.ops.Adapter(self.value, geography=self.geography)
        else:
            self.value = connection.ops.Adapter(self.value)
        return super(GeomValue, self).as_sql(compiler, connection)


class GeoFuncWithGeoParam(GeoFunc):
    def __init__(self, expression, geom, *expressions, **extra):
        if not isinstance(geom, Geometry):
            raise TypeError("Please provide a geometry object.")
        if not hasattr(geom, 'srid') or not geom.srid:
            raise ValueError("Please provide a geometry attribute with a defined SRID.")
        super(GeoFuncWithGeoParam, self).__init__(expression, GeomValue(geom), *expressions, **extra)


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
    output_field_class = AreaField
    arity = 1

    def as_sql(self, compiler, connection, **extra_context):
        if connection.ops.geography:
            self.output_field.area_att = 'sq_m'
        else:
            # Getting the area units of the geographic field.
            geo_field = self.geo_field
            if geo_field.geodetic(connection):
                if connection.features.supports_area_geodetic:
                    self.output_field.area_att = 'sq_m'
                else:
                    # TODO: Do we want to support raw number areas for geodetic fields?
                    raise NotImplementedError('Area on geodetic coordinate systems not supported.')
            else:
                units_name = geo_field.units_name(connection)
                if units_name:
                    self.output_field.area_att = AreaMeasure.unit_attname(units_name)
        return super(Area, self).as_sql(compiler, connection, **extra_context)

    def as_oracle(self, compiler, connection):
        self.output_field = AreaField('sq_m')  # Oracle returns area in units of meters.
        return super(Area, self).as_oracle(compiler, connection)

    def as_sqlite(self, compiler, connection, **extra_context):
        if self.geo_field.geodetic(connection):
            extra_context['template'] = '%(function)s(%(expressions)s, %(spheroid)d)'
            extra_context['spheroid'] = True
        return self.as_sql(compiler, connection, **extra_context)


class AsGeoJSON(GeoFunc):
    output_field_class = TextField

    def __init__(self, expression, bbox=False, crs=False, precision=8, **extra):
        expressions = [expression]
        if precision is not None:
            expressions.append(self._handle_param(precision, 'precision', int))
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
            expressions.append(self._handle_param(precision, 'precision', int))
        super(AsGML, self).__init__(*expressions, **extra)

    def as_oracle(self, compiler, connection, **extra_context):
        source_expressions = self.get_source_expressions()
        version = source_expressions[0]
        clone = self.copy()
        clone.set_source_expressions([source_expressions[1]])
        extra_context['function'] = 'SDO_UTIL.TO_GML311GEOMETRY' if version.value == 3 else 'SDO_UTIL.TO_GMLGEOMETRY'
        return super(AsGML, clone).as_sql(compiler, connection, **extra_context)


class AsKML(AsGML):
    def as_sqlite(self, compiler, connection):
        # No version parameter
        self.source_expressions.pop(0)
        return super(AsKML, self).as_sql(compiler, connection)


class AsSVG(GeoFunc):
    output_field_class = TextField

    def __init__(self, expression, relative=False, precision=8, **extra):
        relative = relative if hasattr(relative, 'resolve_expression') else int(relative)
        expressions = [
            expression,
            relative,
            self._handle_param(precision, 'precision', int),
        ]
        super(AsSVG, self).__init__(*expressions, **extra)


class BoundingCircle(OracleToleranceMixin, GeoFunc):
    def __init__(self, expression, num_seg=48, **extra):
        super(BoundingCircle, self).__init__(*[expression, num_seg], **extra)

    def as_oracle(self, compiler, connection):
        clone = self.copy()
        clone.set_source_expressions([self.get_source_expressions()[0]])
        return super(BoundingCircle, clone).as_oracle(compiler, connection)


class Centroid(OracleToleranceMixin, GeoFunc):
    arity = 1


class Difference(OracleToleranceMixin, GeoFuncWithGeoParam):
    arity = 2


class DistanceResultMixin(object):
    def source_is_geography(self):
        return self.get_source_fields()[0].geography and self.srid == 4326

    def convert_value(self, value, expression, connection, context):
        if value is None:
            return None
        geo_field = self.geo_field
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


class Distance(DistanceResultMixin, OracleToleranceMixin, GeoFuncWithGeoParam):
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
        if self.source_is_geography():
            # Set parameters as geography if base field is geography
            for pos, expr in enumerate(
                    self.source_expressions[self.geom_param_pos + 1:], start=self.geom_param_pos + 1):
                if isinstance(expr, GeomValue):
                    expr.geography = True
        elif geo_field.geodetic(connection):
            # Geometry fields with geodetic (lon/lat) coordinates need special distance functions
            if self.spheroid:
                # DistanceSpheroid is more accurate and resource intensive than DistanceSphere
                self.function = connection.ops.spatial_function_name('DistanceSpheroid')
                # Replace boolean param by the real spheroid of the base field
                self.source_expressions[2] = Value(geo_field._spheroid)
            else:
                self.function = connection.ops.spatial_function_name('DistanceSphere')
        return super(Distance, self).as_sql(compiler, connection)

    def as_oracle(self, compiler, connection):
        if self.spheroid:
            self.source_expressions.pop(2)
        return super(Distance, self).as_oracle(compiler, connection)

    def as_sqlite(self, compiler, connection, **extra_context):
        if self.spheroid:
            self.source_expressions.pop(2)
        if self.geo_field.geodetic(connection):
            # SpatiaLite returns NULL instead of zero on geodetic coordinates
            extra_context['template'] = 'COALESCE(%(function)s(%(expressions)s, %(spheroid)s), 0)'
            extra_context['spheroid'] = int(bool(self.spheroid))
        return super(Distance, self).as_sql(compiler, connection, **extra_context)


class Envelope(GeoFunc):
    arity = 1


class ForceRHR(GeoFunc):
    arity = 1


class GeoHash(GeoFunc):
    output_field_class = TextField

    def __init__(self, expression, precision=None, **extra):
        expressions = [expression]
        if precision is not None:
            expressions.append(self._handle_param(precision, 'precision', int))
        super(GeoHash, self).__init__(*expressions, **extra)


class Intersection(OracleToleranceMixin, GeoFuncWithGeoParam):
    arity = 2


class IsValid(OracleToleranceMixin, GeoFunc):
    output_field_class = BooleanField

    def as_oracle(self, compiler, connection, **extra_context):
        sql, params = super(IsValid, self).as_oracle(compiler, connection, **extra_context)
        return "CASE %s WHEN 'TRUE' THEN 1 ELSE 0 END" % sql, params


class Length(DistanceResultMixin, OracleToleranceMixin, GeoFunc):
    output_field_class = FloatField

    def __init__(self, expr1, spheroid=True, **extra):
        self.spheroid = spheroid
        super(Length, self).__init__(expr1, **extra)

    def as_sql(self, compiler, connection):
        geo_field = GeometryField(srid=self.srid)  # Fake field to get SRID info
        if geo_field.geodetic(connection) and not connection.features.supports_length_geodetic:
            raise NotImplementedError("This backend doesn't support Length on geodetic fields")
        return super(Length, self).as_sql(compiler, connection)

    def as_postgresql(self, compiler, connection):
        geo_field = GeometryField(srid=self.srid)  # Fake field to get SRID info
        if self.source_is_geography():
            self.source_expressions.append(Value(self.spheroid))
        elif geo_field.geodetic(connection):
            # Geometry fields with geodetic (lon/lat) coordinates need length_spheroid
            self.function = connection.ops.spatial_function_name('LengthSpheroid')
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


class MakeValid(GeoFunc):
    pass


class MemSize(GeoFunc):
    output_field_class = IntegerField
    arity = 1


class NumGeometries(GeoFunc):
    output_field_class = IntegerField
    arity = 1


class NumPoints(GeoFunc):
    output_field_class = IntegerField
    arity = 1

    def as_sql(self, compiler, connection):
        if self.source_expressions[self.geom_param_pos].output_field.geom_type != 'LINESTRING':
            if not connection.features.supports_num_points_poly:
                raise TypeError('NumPoints can only operate on LineString content on this database.')
        return super(NumPoints, self).as_sql(compiler, connection)


class Perimeter(DistanceResultMixin, OracleToleranceMixin, GeoFunc):
    output_field_class = FloatField
    arity = 1

    def as_postgresql(self, compiler, connection):
        geo_field = GeometryField(srid=self.srid)  # Fake field to get SRID info
        if geo_field.geodetic(connection) and not self.source_is_geography():
            raise NotImplementedError("ST_Perimeter cannot use a non-projected non-geography field.")
        dim = min(f.dim for f in self.get_source_fields())
        if dim > 2:
            self.function = connection.ops.perimeter3d
        return super(Perimeter, self).as_sql(compiler, connection)

    def as_sqlite(self, compiler, connection):
        geo_field = GeometryField(srid=self.srid)  # Fake field to get SRID info
        if geo_field.geodetic(connection):
            raise NotImplementedError("Perimeter cannot use a non-projected field.")
        return super(Perimeter, self).as_sql(compiler, connection)


class PointOnSurface(OracleToleranceMixin, GeoFunc):
    arity = 1


class Reverse(GeoFunc):
    arity = 1


class Scale(SQLiteDecimalToFloatMixin, GeoFunc):
    def __init__(self, expression, x, y, z=0.0, **extra):
        expressions = [
            expression,
            self._handle_param(x, 'x', NUMERIC_TYPES),
            self._handle_param(y, 'y', NUMERIC_TYPES),
        ]
        if z != 0.0:
            expressions.append(self._handle_param(z, 'z', NUMERIC_TYPES))
        super(Scale, self).__init__(*expressions, **extra)


class SnapToGrid(SQLiteDecimalToFloatMixin, GeoFunc):
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


class SymDifference(OracleToleranceMixin, GeoFuncWithGeoParam):
    arity = 2


class Transform(GeoFunc):
    def __init__(self, expression, srid, **extra):
        expressions = [
            expression,
            self._handle_param(srid, 'srid', int),
        ]
        if 'output_field' not in extra:
            extra['output_field'] = GeometryField(srid=srid)
        super(Transform, self).__init__(*expressions, **extra)

    @property
    def srid(self):
        # Make srid the resulting srid of the transformation
        return self.source_expressions[self.geom_param_pos + 1].value


class Translate(Scale):
    def as_sqlite(self, compiler, connection):
        if len(self.source_expressions) < 4:
            # Always provide the z parameter for ST_Translate
            self.source_expressions.append(Value(0))
        return super(Translate, self).as_sqlite(compiler, connection)


class Union(OracleToleranceMixin, GeoFuncWithGeoParam):
    arity = 2
