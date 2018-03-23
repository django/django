import math

from django.db.models import FloatField, Func, Transform


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
        # Cast FloatField to DecimalField as PostgreSQL doesn't support
        # LOG(double precision, double precision) by default.
        return as_postgresql_log_mod(self, compiler, connection)


class Mod(Func):
    function = 'MOD'
    arity = 2
    output_field = FloatField()

    def as_postgresql(self, compiler, connection):
        # Cast FloatField to DecimalField as PostgreSQL doesn't support
        # LOG(double precision, double precision) by default.
        return as_postgresql_log_mod(self, compiler, connection)


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


def as_postgresql_log_mod(obj, compiler, connection):
        # Cast FloatField to DecimalField as PostgreSQL doesn't support
        # LOG(double precision, double precision) by default.
        clone = obj.copy()
        sources = obj.get_source_expressions()
        if any(isinstance(s.output_field, FloatField) for s in sources):
            class Tonumeric(Func):

                def as_postgresql(self, compiler1=compiler, connection1=connection):
                    return self.as_sql(compiler1, connection1, template='(%(expressions)s)::numeric')

            clone.set_source_expressions([
                Tonumeric(expression) if isinstance(expression.output_field, FloatField)
                else expression for expression in sources
            ])
        return clone.as_sql(compiler, connection)
