import math

from django.db.models import DecimalField, FloatField, Func, Transform
from django.db.models.functions import Cast


class Abs(Transform):
    function = 'ABS'
    lookup_name = 'abs'

    def _resolve_output_field(self):
        sources = self.get_source_expressions()
        if any(isinstance(s.output_field, DecimalField) for s in sources):
            return DecimalField()
        else:
            return FloatField()


class ACos(Transform):
    function = 'ACOS'
    lookup_name = 'acos'

    def _resolve_output_field(self):
        sources = self.get_source_expressions()
        if any(isinstance(s.output_field, DecimalField) for s in sources):
            return DecimalField()
        else:
            return FloatField()


class ASin(Transform):
    function = 'ASIN'
    lookup_name = 'asin'

    def _resolve_output_field(self):
        sources = self.get_source_expressions()
        if any(isinstance(s.output_field, DecimalField) for s in sources):
            return DecimalField()
        else:
            return FloatField()


class ATan(Transform):
    function = 'ATAN'
    lookup_name = 'atan'

    def _resolve_output_field(self):
        sources = self.get_source_expressions()
        if any(isinstance(s.output_field, DecimalField) for s in sources):
            return DecimalField()
        else:
            return FloatField()


class ATan2(Func):
    function = 'ATAN2'
    arity = 2

    def _resolve_output_field(self):
        sources = self.get_source_expressions()
        if any(isinstance(s.output_field, DecimalField) for s in sources):
            return DecimalField()
        else:
            return FloatField()


class Ceil(Transform):
    function = 'CEILING'
    lookup_name = 'ceil'

    def as_oracle(self, compiler, connection):
        return super().as_sql(compiler, connection, function='CEIL')


class Cos(Transform):
    function = 'COS'
    lookup_name = 'cos'

    def _resolve_output_field(self):
        sources = self.get_source_expressions()
        if any(isinstance(s.output_field, DecimalField) for s in sources):
            return DecimalField()
        else:
            return FloatField()


class Cot(Transform):
    function = 'COT'
    lookup_name = 'cot'

    def _resolve_output_field(self):
        sources = self.get_source_expressions()
        if any(isinstance(s.output_field, DecimalField) for s in sources):
            return DecimalField()
        else:
            return FloatField()

    def as_oracle(self, compiler, connection):
        return super().as_sql(compiler, connection, template='(1 / TAN(%(expressions)s))')


class Degrees(Transform):
    function = 'DEGREES'
    lookup_name = 'degrees'

    def _resolve_output_field(self):
        sources = self.get_source_expressions()
        if any(isinstance(s.output_field, DecimalField) for s in sources):
            return DecimalField()
        else:
            return FloatField()

    def as_oracle(self, compiler, connection):
        return super().as_sql(compiler, connection, template='((%%(expressions)s) * 180 / %s)' % math.pi)


class Exp(Transform):
    function = 'EXP'
    lookup_name = 'exp'

    def _resolve_output_field(self):
        sources = self.get_source_expressions()
        if any(isinstance(s.output_field, DecimalField) for s in sources):
            return DecimalField()
        else:
            return FloatField()


class Floor(Transform):
    function = 'FLOOR'
    lookup_name = 'floor'


class Ln(Transform):
    function = 'LN'
    lookup_name = 'ln'

    def _resolve_output_field(self):
        sources = self.get_source_expressions()
        if any(isinstance(s.output_field, DecimalField) for s in sources):
            return DecimalField()
        else:
            return FloatField()


class Log(Func):
    function = 'LOG'
    arity = 2
    output_field = FloatField()

    def as_postgresql(self, compiler, connection):
        # Cast FloatField to DecimalField as PostgreSQL doesn't support
        # LOG(double precision, double precision) by default.
        clone = self.copy()
        sources = self.get_source_expressions()
        if any(isinstance(s.output_field, DecimalField) for s in sources):
            expressions = [
                Cast(expression, numeric) if isinstance(expression.output_field, FloatField)
                else expression for expression in self.get_source_expressions()
            ]
            clone.set_source_expressions(expressions)
        return clone.as_sql(compiler, connection)


class Mod(Func):
    function = 'MOD'
    arity = 2

    def _resolve_output_field(self):
        sources = self.get_source_expressions()
        if any(isinstance(s.output_field, DecimalField) for s in sources):
            return DecimalField()
        else:
            return FloatField()

    def as_postgresql(self, compiler, connection):
        # POstgresql doesn't support Log(double precision, double precision),
        # so convert Floatfields to numeric.
        return as_postgresql_Log_Mod(self, compiler, connection)


class Pi(Func):
    function = 'PI'
    arity = 0

    def _resolve_output_field(self):
        sources = self.get_source_expressions()
        if any(isinstance(s.output_field, DecimalField) for s in sources):
            return DecimalField()
        else:
            return FloatField()

    def as_oracle(self, compiler, connection):
        return super().as_sql(compiler, connection, template=str(math.pi))


class Power(Func):
    function = 'POWER'
    arity = 2

    def _resolve_output_field(self):
        sources = self.get_source_expressions()
        if any(isinstance(s.output_field, DecimalField) for s in sources):
            return DecimalField()
        else:
            return FloatField()


class Radians(Transform):
    function = 'RADIANS'
    lookup_name = 'radians'

    def _resolve_output_field(self):
        sources = self.get_source_expressions()
        if any(isinstance(s.output_field, DecimalField) for s in sources):
            return DecimalField()
        else:
            return FloatField()

    def as_oracle(self, compiler, connection):
        return super().as_sql(compiler, connection, template='((%%(expressions)s) * %s / 180)' % math.pi)


class Round(Transform):
    function = 'ROUND'
    lookup_name = 'round'


class Sin(Transform):
    function = 'SIN'
    lookup_name = 'sin'

    def _resolve_output_field(self):
        sources = self.get_source_expressions()
        if any(isinstance(s.output_field, DecimalField) for s in sources):
            return DecimalField()
        else:
            return FloatField()


class Sqrt(Transform):
    function = 'SQRT'
    lookup_name = 'sqrt'

    def _resolve_output_field(self):
        sources = self.get_source_expressions()
        if any(isinstance(s.output_field, DecimalField) for s in sources):
            return DecimalField()
        else:
            return FloatField()


class Tan(Transform):
    function = 'TAN'
    lookup_name = 'tan'

    def _resolve_output_field(self):
        sources = self.get_source_expressions()
        if any(isinstance(s.output_field, DecimalField) for s in sources):
            return DecimalField()
        else:
            return FloatField()


def as_postgresql_Log_Mod(obj, compiler, connection):
    # Cast FloatField to DecimalField as PostgreSQL doesn't support
    # LOG(double precision, double precision) and
    # MOD(double precision, double precision) by default.
    clone = obj.copy()
    clone.set_source_expressions([
        Cast(expression, DecimalField()) if isinstance(expression.output_field, FloatField)
        else expression for expression in obj.get_source_expressions()
    ])
    return clone.as_sql(compiler, connection)
