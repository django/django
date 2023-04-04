import json
import warnings

from django.contrib.postgres.fields import ArrayField
from django.db.models import Aggregate, BooleanField, JSONField, TextField, Value
from django.utils.deprecation import RemovedInDjango51Warning

from .mixins import OrderableAggMixin

__all__ = [
    "ArrayAgg",
    "BitAnd",
    "BitOr",
    "BitXor",
    "BoolAnd",
    "BoolOr",
    "JSONBAgg",
    "StringAgg",
]


class ArrayAgg(OrderableAggMixin, Aggregate):
    function = "ARRAY_AGG"
    template = "%(function)s(%(distinct)s%(expressions)s %(ordering)s)"
    allow_distinct = True

    @property
    def output_field(self):
        return ArrayField(self.source_expressions[0].output_field)


class BitAnd(Aggregate):
    function = "BIT_AND"


class BitOr(Aggregate):
    function = "BIT_OR"


class BitXor(Aggregate):
    function = "BIT_XOR"


class BoolAnd(Aggregate):
    function = "BOOL_AND"
    output_field = BooleanField()


class BoolOr(Aggregate):
    function = "BOOL_OR"
    output_field = BooleanField()


class JSONBAgg(OrderableAggMixin, Aggregate):
    function = "JSONB_AGG"
    template = "%(function)s(%(distinct)s%(expressions)s %(ordering)s)"
    allow_distinct = True
    output_field = JSONField()

    # RemovedInDjango51Warning: When the deprecation ends, remove __init__().
    def __init__(self, *expressions, default=None, **extra):
        super().__init__(*expressions, default=default, **extra)
        if (
            isinstance(default, Value)
            and isinstance(default.value, str)
            and not isinstance(default.output_field, JSONField)
        ):
            value = default.value
            try:
                decoded = json.loads(value)
            except json.JSONDecodeError:
                warnings.warn(
                    "Passing a Value() with an output_field that isn't a JSONField as "
                    "JSONBAgg(default) is deprecated. Pass default="
                    f"Value({value!r}, output_field=JSONField()) instead.",
                    stacklevel=2,
                    category=RemovedInDjango51Warning,
                )
                self.default.output_field = self.output_field
            else:
                self.default = Value(decoded, self.output_field)
                warnings.warn(
                    "Passing an encoded JSON string as JSONBAgg(default) is "
                    f"deprecated. Pass default={decoded!r} instead.",
                    stacklevel=2,
                    category=RemovedInDjango51Warning,
                )


class StringAgg(OrderableAggMixin, Aggregate):
    function = "STRING_AGG"
    template = "%(function)s(%(distinct)s%(expressions)s %(ordering)s)"
    allow_distinct = True
    output_field = TextField()

    def __init__(self, expression, delimiter, **extra):
        delimiter_expr = Value(str(delimiter))
        super().__init__(expression, delimiter_expr, **extra)
