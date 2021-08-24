import warnings

from django.contrib.postgres.fields import ArrayField
from django.db.models import Aggregate, BooleanField, JSONField, Value
from django.utils.deprecation import RemovedInDjango50Warning

from .mixins import OrderableAggMixin

__all__ = [
    "ArrayAgg",
    "BitAnd",
    "BitOr",
    "BoolAnd",
    "BoolOr",
    "JSONBAgg",
    "StringAgg",
]


# RemovedInDjango50Warning
NOT_PROVIDED = object()


class DeprecatedConvertValueMixin:
    def __init__(self, *expressions, default=NOT_PROVIDED, **extra):
        if default is NOT_PROVIDED:
            default = None
            self._default_provided = False
        else:
            self._default_provided = True
        super().__init__(*expressions, default=default, **extra)

    def convert_value(self, value, expression, connection):
        if value is None and not self._default_provided:
            warnings.warn(self.deprecation_msg, category=RemovedInDjango50Warning)
            return self.deprecation_value
        return value


class ArrayAgg(DeprecatedConvertValueMixin, OrderableAggMixin, Aggregate):
    function = "ARRAY_AGG"
    template = "%(function)s(%(distinct)s%(expressions)s %(ordering)s)"
    allow_distinct = True

    # RemovedInDjango50Warning
    deprecation_value = property(lambda self: [])
    deprecation_msg = (
        "In Django 5.0, ArrayAgg() will return None instead of an empty list "
        "if there are no rows. Pass default=None to opt into the new behavior "
        "and silence this warning or default=Value([]) to keep the previous "
        "behavior."
    )

    @property
    def output_field(self):
        return ArrayField(self.source_expressions[0].output_field)


class BitAnd(Aggregate):
    function = "BIT_AND"


class BitOr(Aggregate):
    function = "BIT_OR"


class BoolAnd(Aggregate):
    function = "BOOL_AND"
    output_field = BooleanField()


class BoolOr(Aggregate):
    function = "BOOL_OR"
    output_field = BooleanField()


class JSONBAgg(DeprecatedConvertValueMixin, OrderableAggMixin, Aggregate):
    function = "JSONB_AGG"
    template = "%(function)s(%(distinct)s%(expressions)s %(ordering)s)"
    allow_distinct = True
    output_field = JSONField()

    # RemovedInDjango50Warning
    deprecation_value = "[]"
    deprecation_msg = (
        "In Django 5.0, JSONBAgg() will return None instead of an empty list "
        "if there are no rows. Pass default=None to opt into the new behavior "
        "and silence this warning or default=Value('[]') to keep the previous "
        "behavior."
    )


class StringAgg(DeprecatedConvertValueMixin, OrderableAggMixin, Aggregate):
    function = "STRING_AGG"
    template = "%(function)s(%(distinct)s%(expressions)s %(ordering)s)"
    allow_distinct = True

    # RemovedInDjango50Warning
    deprecation_value = ""
    deprecation_msg = (
        "In Django 5.0, StringAgg() will return None instead of an empty "
        "string if there are no rows. Pass default=None to opt into the new "
        "behavior and silence this warning or default=Value('') to keep the "
        "previous behavior."
    )

    def __init__(self, expression, delimiter, **extra):
        delimiter_expr = Value(str(delimiter))
        super().__init__(expression, delimiter_expr, **extra)
