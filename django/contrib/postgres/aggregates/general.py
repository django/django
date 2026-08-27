import warnings

from django.contrib.postgres.fields import ArrayField
from django.db.models import Aggregate
from django.db.models import BitAnd as _BitAnd
from django.db.models import BitOr as _BitOr
from django.db.models import BitXor as _BitXor
from django.db.models import BooleanField, JSONField
from django.db.models import StringAgg as _StringAgg
from django.db.models import Value
from django.utils.deprecation import RemovedInDjango70Warning

__all__ = [
    "ArrayAgg",
    "BitAnd",  # RemovedInDjango70Warning
    "BitOr",  # RemovedInDjango70Warning
    "BitXor",  # RemovedInDjango70Warning
    "BoolAnd",
    "BoolOr",
    "JSONBAgg",
    "StringAgg",  # RemovedInDjango70Warning.
]


class ArrayAgg(Aggregate):
    function = "ARRAY_AGG"
    allow_distinct = True
    allow_order_by = True

    @property
    def output_field(self):
        return ArrayField(self.source_expressions[0].output_field)


class BitAnd(_BitAnd):
    def __init__(self, expression, **extra):
        warnings.warn(
            "The PostgreSQL-specific BitAnd function is deprecated. Use "
            "django.db.models.aggregates.BitAnd instead.",
            category=RemovedInDjango70Warning,
            stacklevel=2,
        )
        super().__init__(expression, **extra)


class BitOr(_BitOr):
    def __init__(self, expression, **extra):
        warnings.warn(
            "The PostgreSQL-specific BitOr function is deprecated. Use "
            "django.db.models.aggregates.BitOr instead.",
            category=RemovedInDjango70Warning,
            stacklevel=2,
        )
        super().__init__(expression, **extra)


class BitXor(_BitXor):
    def __init__(self, expression, **extra):
        warnings.warn(
            "The PostgreSQL-specific BitXor function is deprecated. Use "
            "django.db.models.aggregates.BitXor instead.",
            category=RemovedInDjango70Warning,
            stacklevel=2,
        )
        super().__init__(expression, **extra)


class BoolAnd(Aggregate):
    function = "BOOL_AND"
    output_field = BooleanField()


class BoolOr(Aggregate):
    function = "BOOL_OR"
    output_field = BooleanField()


class JSONBAgg(Aggregate):
    function = "JSONB_AGG"
    allow_distinct = True
    allow_order_by = True
    output_field = JSONField()


# RemovedInDjango70Warning: When the deprecation ends, remove completely.
class StringAgg(_StringAgg):

    def __init__(self, expression, delimiter, **extra):
        if isinstance(delimiter, str):
            warnings.warn(
                "delimiter: str will be resolved as a field reference instead "
                "of a string literal on Django 7.0. Pass "
                f"`delimiter=Value({delimiter!r})` to preserve the previous behavior.",
                category=RemovedInDjango70Warning,
                stacklevel=2,
            )

            delimiter = Value(delimiter)

        warnings.warn(
            "The PostgreSQL specific StringAgg function is deprecated. Use "
            "django.db.models.aggregates.StringAgg instead.",
            category=RemovedInDjango70Warning,
            stacklevel=2,
        )

        super().__init__(expression, delimiter, **extra)
