import math
import sys

from django.db.models import DecimalField, FloatField, Func, Transform
from django.db.models.functions import Cast


class DecimalInputMixin:

    def as_postgresql(self, compiler, connection):
        # Cast FloatField to DecimalField as PostgreSQL doesn't support the
        # following function signatures by default:
        # - LOG(double precision, double precision)
        # - MOD(double precision, double precision)
        output_field = DecimalField(decimal_places=sys.float_info.dig, max_digits=1000)
        clone = self.copy()
        clone.set_source_expressions([
            Cast(expression, output_field) if isinstance(expression.output_field, FloatField)
            else expression for expression in self.get_source_expressions()
        ])
        return clone.as_sql(compiler, connection)


class OutputFieldMixin:

    def _resolve_output_field(self):
        sources = self.get_source_expressions()
        if any(isinstance(s.output_field, DecimalField) for s in sources):
            return DecimalField()
        else:
            return FloatField()


class Abs(Transform):
    function = 'ABS'
    lookup_name = 'abs'


class ACos(OutputFieldMixin, Transform):
    function = 'ACOS'
    lookup_name = 'acos'


class ASin(OutputFieldMixin, Transform):
    function = 'ASIN'
    lookup_name = 'asin'


class ATan(OutputFieldMixin, Transform):
    function = 'ATAN'
    lookup_name = 'atan'


class ATan2(OutputFieldMixin, Func):
    function = 'ATAN2'
    arity = 2


class Ceil(Transform):
    function = 'CEILING'
    lookup_name = 'ceil'

    def as_oracle(self, compiler, connection):
        return super().as_sql(compiler, connection, function='CEIL')


class Cos(OutputFieldMixin, Transform):
    function = 'COS'
    lookup_name = 'cos'


class Cot(OutputFieldMixin, Transform):
    function = 'COT'
    lookup_name = 'cot'

    def as_oracle(self, compiler, connection):
        return super().as_sql(compiler, connection, template='(1 / TAN(%(expressions)s))')


class Degrees(OutputFieldMixin, Transform):
    function = 'DEGREES'
    lookup_name = 'degrees'

    def as_oracle(self, compiler, connection):
        return super().as_sql(compiler, connection, template='((%%(expressions)s) * 180 / %s)' % math.pi)


class Exp(OutputFieldMixin, Transform):
    function = 'EXP'
    lookup_name = 'exp'


class Floor(Transform):
    function = 'FLOOR'
    lookup_name = 'floor'


class Ln(OutputFieldMixin, Transform):
    function = 'LN'
    lookup_name = 'ln'


class Log(DecimalInputMixin, OutputFieldMixin, Func):
    function = 'LOG'
    arity = 2


class Mod(DecimalInputMixin, OutputFieldMixin, Func):
    function = 'MOD'
    arity = 2


class Pi(OutputFieldMixin, Func):
    function = 'PI'
    arity = 0

    def as_oracle(self, compiler, connection):
        return super().as_sql(compiler, connection, template=str(math.pi))


class Power(OutputFieldMixin, Func):
    function = 'POWER'
    arity = 2


class Radians(OutputFieldMixin, Transform):
    function = 'RADIANS'
    lookup_name = 'radians'

    def as_oracle(self, compiler, connection):
        return super().as_sql(compiler, connection, template='((%%(expressions)s) * %s / 180)' % math.pi)


class Round(Transform):
    function = 'ROUND'
    lookup_name = 'round'


class Sin(OutputFieldMixin, Transform):
    function = 'SIN'
    lookup_name = 'sin'


class Sqrt(OutputFieldMixin, Transform):
    function = 'SQRT'
    lookup_name = 'sqrt'


class Tan(OutputFieldMixin, Transform):
    function = 'TAN'
    lookup_name = 'tan'
