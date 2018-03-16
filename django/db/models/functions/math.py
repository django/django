from django.db.models import Func, Transform, fields
from django.db.models.fields import FloatField


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


class Cos(Transform):
    function = 'COS'
    lookup_name = 'cos'
    output_field = FloatField()


class Cot(Transform):
    function = 'COT'
    lookup_name = 'cot'
    output_field = FloatField()


class Degrees(Transform):
    function = 'DEGREES'
    lookup_name = 'degrees'
    output_field = FloatField()


class Exp(Transform):
    function = 'EXP'
    lookup_name = 'exp'


class Floor(Transform):
    function = 'FLOOR'
    lookup_name = 'floor'


class Ln(Transform):
    function = 'LN'
    lookup_name = 'ln'


class Log(Func):
    function = 'LOG'
    arity = 2
    output_field = FloatField()


class Mod(Func):
    function = 'MOD'
    arity = 2
    output_field = FloatField()


class Pi(Func):
    function = 'PI'
    arity = 0
    output_field = FloatField()


class Power(Func):
    function = 'POWER'
    arity = 2
    output_field = FloatField()


class Radians(Transform):
    function = 'RADIANS'
    lookup_name = 'radians'
    output_field = FloatField()


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
