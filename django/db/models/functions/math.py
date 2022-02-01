import math

from django.db.models.expressions import Func, Value
from django.db.models.fields import FloatField, IntegerField
from django.db.models.functions import Cast
from django.db.models.functions.mixins import (
    FixDecimalInputMixin, NumericOutputFieldMixin,
)
from django.db.models.lookups import Transform


class Abs(Transform):
    function = 'ABS'
    lookup_name = 'abs'


class ACos(NumericOutputFieldMixin, Transform):
    function = 'ACOS'
    lookup_name = 'acos'


class ASin(NumericOutputFieldMixin, Transform):
    function = 'ASIN'
    lookup_name = 'asin'


class ATan(NumericOutputFieldMixin, Transform):
    function = 'ATAN'
    lookup_name = 'atan'


class ATan2(NumericOutputFieldMixin, Func):
    function = 'ATAN2'
    arity = 2

    def as_sqlite(self, compiler, connection, **extra_context):
        if not getattr(connection.ops, 'spatialite', False) or connection.ops.spatial_version >= (5, 0, 0):
            return self.as_sql(compiler, connection)
        # This function is usually ATan2(y, x), returning the inverse tangent
        # of y / x, but it's ATan2(x, y) on SpatiaLite < 5.0.0.
        # Cast integers to float to avoid inconsistent/buggy behavior if the
        # arguments are mixed between integer and float or decimal.
        # https://www.gaia-gis.it/fossil/libspatialite/tktview?name=0f72cca3a2
        clone = self.copy()
        clone.set_source_expressions([
            Cast(expression, FloatField()) if isinstance(expression.output_field, IntegerField)
            else expression for expression in self.get_source_expressions()[::-1]
        ])
        return clone.as_sql(compiler, connection, **extra_context)


class Ceil(Transform):
    function = 'CEILING'
    lookup_name = 'ceil'

    def as_oracle(self, compiler, connection, **extra_context):
        return super().as_sql(compiler, connection, function='CEIL', **extra_context)


class Cos(NumericOutputFieldMixin, Transform):
    function = 'COS'
    lookup_name = 'cos'


class Cot(NumericOutputFieldMixin, Transform):
    function = 'COT'
    lookup_name = 'cot'

    def as_oracle(self, compiler, connection, **extra_context):
        return super().as_sql(compiler, connection, template='(1 / TAN(%(expressions)s))', **extra_context)


class Degrees(NumericOutputFieldMixin, Transform):
    function = 'DEGREES'
    lookup_name = 'degrees'

    def as_oracle(self, compiler, connection, **extra_context):
        return super().as_sql(
            compiler, connection,
            template='((%%(expressions)s) * 180 / %s)' % math.pi,
            **extra_context
        )


class Exp(NumericOutputFieldMixin, Transform):
    function = 'EXP'
    lookup_name = 'exp'


class Floor(Transform):
    function = 'FLOOR'
    lookup_name = 'floor'


class Ln(NumericOutputFieldMixin, Transform):
    function = 'LN'
    lookup_name = 'ln'


class Log(FixDecimalInputMixin, NumericOutputFieldMixin, Func):
    function = 'LOG'
    arity = 2

    def as_sqlite(self, compiler, connection, **extra_context):
        if not getattr(connection.ops, 'spatialite', False):
            return self.as_sql(compiler, connection)
        # This function is usually Log(b, x) returning the logarithm of x to
        # the base b, but on SpatiaLite it's Log(x, b).
        clone = self.copy()
        clone.set_source_expressions(self.get_source_expressions()[::-1])
        return clone.as_sql(compiler, connection, **extra_context)


class Mod(FixDecimalInputMixin, NumericOutputFieldMixin, Func):
    function = 'MOD'
    arity = 2


class Pi(NumericOutputFieldMixin, Func):
    function = 'PI'
    arity = 0

    def as_oracle(self, compiler, connection, **extra_context):
        return super().as_sql(compiler, connection, template=str(math.pi), **extra_context)


class Power(NumericOutputFieldMixin, Func):
    function = 'POWER'
    arity = 2


class Radians(NumericOutputFieldMixin, Transform):
    function = 'RADIANS'
    lookup_name = 'radians'

    def as_oracle(self, compiler, connection, **extra_context):
        return super().as_sql(
            compiler, connection,
            template='((%%(expressions)s) * %s / 180)' % math.pi,
            **extra_context
        )


class Random(NumericOutputFieldMixin, Func):
    function = 'RANDOM'
    arity = 0

    def as_mysql(self, compiler, connection, **extra_context):
        return super().as_sql(compiler, connection, function='RAND', **extra_context)

    def as_oracle(self, compiler, connection, **extra_context):
        return super().as_sql(compiler, connection, function='DBMS_RANDOM.VALUE', **extra_context)

    def as_sqlite(self, compiler, connection, **extra_context):
        return super().as_sql(compiler, connection, function='RAND', **extra_context)

    def get_group_by_cols(self, alias=None):
        return []


class Round(FixDecimalInputMixin, Transform):
    function = 'ROUND'
    lookup_name = 'round'
    arity = None  # Override Transform's arity=1 to enable passing precision.

    def __init__(self, expression, precision=0, **extra):
        super().__init__(expression, precision, **extra)

    def as_sqlite(self, compiler, connection, **extra_context):
        precision = self.get_source_expressions()[1]
        if isinstance(precision, Value) and precision.value < 0:
            raise ValueError('SQLite does not support negative precision.')
        return super().as_sqlite(compiler, connection, **extra_context)

    def _resolve_output_field(self):
        source = self.get_source_expressions()[0]
        return source.output_field


class Sign(Transform):
    function = 'SIGN'
    lookup_name = 'sign'


class Sin(NumericOutputFieldMixin, Transform):
    function = 'SIN'
    lookup_name = 'sin'


class Sqrt(NumericOutputFieldMixin, Transform):
    function = 'SQRT'
    lookup_name = 'sqrt'


class Tan(NumericOutputFieldMixin, Transform):
    function = 'TAN'
    lookup_name = 'tan'
