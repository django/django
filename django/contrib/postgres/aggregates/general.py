import warnings

from django.contrib.postgres.fields import ArrayField
from django.db.models import Aggregate, BooleanField, JSONField, \
    StringAgg as _StringAgg, Value
from django.utils.deprecation import RemovedInDjango60Warning

from .mixins import _DeprecatedOrdering

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


class ArrayAgg(_DeprecatedOrdering, Aggregate):
    function = "ARRAY_AGG"
    allow_distinct = True
    allow_order_by = True

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


class JSONBAgg(_DeprecatedOrdering, Aggregate):
    function = "JSONB_AGG"
    allow_distinct = True
    allow_order_by = True
    output_field = JSONField()


class StringAgg(_DeprecatedOrdering, _StringAgg):

    def __init__(self, expression, delimiter, **extra):
        warnings.warn(
            "The PostgreSQL specific StringAgg function is deprecated. Use "
            "django.db.models.aggregate.StringAgg instead.",
            category=RemovedInDjango60Warning,
        )

        if isinstance(delimiter, str):
            warnings.warn(
                "String delimiters will be converted to F statements instead of Value"
                "statements. Explicit Value instances should be used instead.",
                category=RemovedInDjango60Warning,
            )

            delimiter = Value(delimiter)

        super().__init__(expression, delimiter, **extra)
