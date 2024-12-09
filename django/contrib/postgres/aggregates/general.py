import warnings

from django.contrib.postgres.fields import ArrayField
from django.db.models import Aggregate, BooleanField, JSONField
from django.db.models import StringAgg as _StringAgg
from django.db.models import Value
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
        if isinstance(delimiter, str):
            warnings.warn(
                "delimiter: str will be resolved as a field reference instead "
                "of a string literal on Django 6.0. Pass "
                f"`delimiter=Value({delimiter!r})` to preserve the previous behaviour.",
                category=RemovedInDjango60Warning,
                stacklevel=2,
            )

            delimiter = Value(delimiter)

        warnings.warn(
            "The PostgreSQL specific StringAgg function is deprecated. Use "
            "django.db.models.aggregate.StringAgg instead.",
            category=RemovedInDjango60Warning,
            stacklevel=2,
        )

        super().__init__(expression, delimiter, **extra)
