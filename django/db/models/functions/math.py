import math

from django.db.models import FloatField, Func, Transform
from .comparison import Cast


class Abs(Transform):
    function = 'ABS'
    lookup_name = 'abs'


class ACos(Transform):
    function = 'ACOS'
    lookup_name = 'acos'
    output_field = FloatField()


class ASin(Transform):
    function = 'ASIN'
    lookup_name = 'asin'
    output_field = FloatField()


class ATan(Transform):
    function = 'ATAN'
    lookup_name = 'atan'
    output_field = FloatField()


class ATan2(Func):
    function = 'ATAN2'
    arity = 2
    output_field = FloatField()


class Ceil(Transform):
    function = 'CEILING'
    lookup_name = 'ceil'

    def as_oracle(self, compiler, connection):
        return super().as_sql(compiler, connection, function='CEIL')


class Cos(Transform):
    function = 'COS'
    lookup_name = 'cos'
    output_field = FloatField()


class Cot(Transform):
    function = 'COT'
    lookup_name = 'cot'
    output_field = FloatField()

    def as_oracle(self, compiler, connection):
        return super().as_sql(compiler, connection, template='(1 / TAN(%(expressions)s))')


class Degrees(Transform):
    function = 'DEGREES'
    lookup_name = 'degrees'
    output_field = FloatField()

    def as_oracle(self, compiler, connection):
        return super().as_sql(compiler, connection, template='((%%(expressions)s) * 180 / %s)' % math.pi)


class Exp(Transform):
    function = 'EXP'
    lookup_name = 'exp'
    output_field = FloatField()


class Floor(Transform):
    function = 'FLOOR'
    lookup_name = 'floor'


class Ln(Transform):
    function = 'LN'
    lookup_name = 'ln'
    output_field = FloatField()


class Log(Func):
    function = 'LOG'
    arity = 2
    output_field = FloatField()

    def as_postgresql(self, compiler, connection):
        # POstgresql doesn't support Log(double precision, double precision),
        # so convert Floatfields to numeric if present.
        if self.output_field.get_internal_type() == 'FloatField':
            expressions = [
                Cast(expression, numeric) for expression in self.get_source_expressions()
            ]
            clone = self.copy()
            clone.set_source_expressions(expressions)
            return super(Log, clone).as_sql(
                compiler, connection, function='LOG', template='%(function)s(%(expressions)s)'
            )
        return self.as_sql(compiler, connection)


class Mod(Func):
    function = 'MOD'
    arity = 2
    output_field = FloatField()

    def as_postgresql(self, compiler, connection):
        # POstgresql doesn't support Log(double precision, double precision),
        # so convert Floatfields to numeric.
        if self.output_field.get_internal_type() == 'FloatField':
            expressions = [
                Cast(expression, numeric) for expression in self.get_source_expressions()
            ]
            clone = self.copy()
            clone.set_source_expressions(expressions)
            return super(Mod, clone).as_sql(
                compiler, connection, function='MOD', template='%(function)s(%(expressions)s)'
            )
        return self.as_sql(compiler, connection)


class Pi(Func):
    function = 'PI'
    arity = 0
    output_field = FloatField()

    def as_oracle(self, compiler, connection):
        return super().as_sql(compiler, connection, template=str(math.pi))


class Power(Func):
    function = 'POWER'
    arity = 2
    output_field = FloatField()


class Radians(Transform):
    function = 'RADIANS'
    lookup_name = 'radians'
    output_field = FloatField()

    def as_oracle(self, compiler, connection):
        return super().as_sql(compiler, connection, template='((%%(expressions)s) * %s / 180)' % math.pi)


class Round(Transform):
    function = 'ROUND'
    lookup_name = 'round'


class Sin(Transform):
    function = 'SIN'
    lookup_name = 'sin'
    output_field = FloatField()


class Sqrt(Transform):
    function = 'SQRT'
    lookup_name = 'sqrt'
    output_field = FloatField()


class Tan(Transform):
    function = 'TAN'
    lookup_name = 'tan'
    output_field = FloatField()
