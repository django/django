import math

from django.db.models.expressions import Func
from django.db.models.fields import FloatField, IntegerField
from django.db.models.functions import Cast
from django.db.models.functions.mixins import (
    FixDecimalInputMixin, NumericOutputFieldMixin,
)
from django.db.models.lookups import Transform


class HyperbolicFallbackMixin:

    def as_mysql(self, compiler, connection, **extra_context):
        return super().as_sql(compiler, connection, template=self.fallback, **extra_context)

    def as_oracle(self, compiler, connection, **extra_context):
        extra = {} if not self.is_inverse else {'template': self.fallback}
        return super().as_sql(compiler, connection, **extra, **extra_context)

    def as_postgresql(self, compiler, connection, **extra_context):
        extra = {} if connection.features.is_postgresql_12 else {'template': self.fallback}
        return super().as_sql(compiler, connection, **extra, **extra_context)


class Abs(Transform):
    function = 'ABS'
    lookup_name = 'abs'


class ACos(NumericOutputFieldMixin, Transform):
    function = 'ACOS'
    lookup_name = 'acos'


class ACosh(HyperbolicFallbackMixin, NumericOutputFieldMixin, Transform):
    function = 'ACOSH'
    lookup_name = 'acosh'
    fallback = '(LN((%(expressions)s) + SQRT(POWER((%(expressions)s), 2) - 1)))'
    is_inverse = True


class ASin(NumericOutputFieldMixin, Transform):
    function = 'ASIN'
    lookup_name = 'asin'


class ASinh(HyperbolicFallbackMixin, NumericOutputFieldMixin, Transform):
    function = 'ASINH'
    lookup_name = 'asinh'
    fallback = '(LN((%(expressions)s) + SQRT(POWER((%(expressions)s), 2) + 1)))'
    is_inverse = True


class ATan(NumericOutputFieldMixin, Transform):
    function = 'ATAN'
    lookup_name = 'atan'


class ATanh(HyperbolicFallbackMixin, NumericOutputFieldMixin, Transform):
    function = 'ATANH'
    lookup_name = 'atanh'
    fallback = '(LN((1 + (%(expressions)s)) / (1 - (%(expressions)s))) / 2)'
    is_inverse = True


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


class Cosh(HyperbolicFallbackMixin, NumericOutputFieldMixin, Transform):
    function = 'COSH'
    lookup_name = 'cosh'
    fallback = '((POWER(EXP(1), (%(expressions)s)) + POWER(EXP(1), -1 * (%(expressions)s))) / 2)'
    is_inverse = False


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


class Log2(FixDecimalInputMixin, NumericOutputFieldMixin, Transform):
    function = 'LOG2'
    lookup_name = 'log2'

    def as_oracle(self, compiler, connection, **extra_context):
        return super().as_sql(compiler, connection, template='LOG(2, (%(expressions)s))', **extra_context)

    def as_postgresql(self, compiler, connection, **extra_context):
        return super().as_postgresql(compiler, connection, template='LOG(2, (%(expressions)s))', **extra_context)


class Log10(FixDecimalInputMixin, NumericOutputFieldMixin, Transform):
    function = 'LOG10'
    lookup_name = 'log10'

    def as_oracle(self, compiler, connection, **extra_context):
        return super().as_sql(compiler, connection, template='LOG(10, (%(expressions)s))', **extra_context)

    def as_postgresql(self, compiler, connection, **extra_context):
        if connection.features.is_postgresql_12:
            return super().as_sql(compiler, connection, **extra_context)
        return super().as_postgresql(compiler, connection, template='LOG(10, (%(expressions)s))', **extra_context)


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
        # Don't use built-in RANDOM function as we want value in range [0, 1).
        return super().as_sql(compiler, connection, function='RAND', **extra_context)


class Round(Transform):
    function = 'ROUND'
    lookup_name = 'round'


class Sign(Transform):
    function = 'SIGN'
    lookup_name = 'sign'


class Sin(NumericOutputFieldMixin, Transform):
    function = 'SIN'
    lookup_name = 'sin'


class Sinh(HyperbolicFallbackMixin, NumericOutputFieldMixin, Transform):
    function = 'SINH'
    lookup_name = 'sinh'
    fallback = '((POWER(EXP(1), (%(expressions)s)) - POWER(EXP(1), -1 * (%(expressions)s))) / 2)'
    is_inverse = False


class Sqrt(NumericOutputFieldMixin, Transform):
    function = 'SQRT'
    lookup_name = 'sqrt'


class Tan(NumericOutputFieldMixin, Transform):
    function = 'TAN'
    lookup_name = 'tan'


class Tanh(HyperbolicFallbackMixin, NumericOutputFieldMixin, Transform):
    function = 'Tanh'
    lookup_name = 'tanh'
    fallback = '((POWER(EXP(1), 2 * (%(expressions)s)) - 1) / (POWER(EXP(1), 2 * (%(expressions)s)) + 1))'
    is_inverse = False


class Truncate(Transform):
    function = 'TRUNC'
    lookup_name = 'truncate'

    def as_mysql(self, compiler, connection, **extra_context):
        return super().as_sql(compiler, connection, template='TRUNCATE((%(expressions)s), 0)', **extra_context)
