import warnings

from django.contrib.postgres.fields import ArrayField
from django.db.models import Aggregate
from django.db.models import BitAnd as _BitAnd
from django.db.models import BitOr as _BitOr
from django.db.models import BitXor as _BitXor
from django.db.models import BooleanField, JSONField
from django.utils.deprecation import RemovedInDjango2028Warning

__all__ = [
    "ArrayAgg",
    "BitAnd",  # RemovedInDjango2028Warning
    "BitOr",  # RemovedInDjango2028Warning
    "BitXor",  # RemovedInDjango2028Warning
    "BoolAnd",
    "BoolOr",
    "JSONBAgg",
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
            category=RemovedInDjango2028Warning,
            stacklevel=2,
        )
        super().__init__(expression, **extra)


class BitOr(_BitOr):
    def __init__(self, expression, **extra):
        warnings.warn(
            "The PostgreSQL-specific BitOr function is deprecated. Use "
            "django.db.models.aggregates.BitOr instead.",
            category=RemovedInDjango2028Warning,
            stacklevel=2,
        )
        super().__init__(expression, **extra)


class BitXor(_BitXor):
    def __init__(self, expression, **extra):
        warnings.warn(
            "The PostgreSQL-specific BitXor function is deprecated. Use "
            "django.db.models.aggregates.BitXor instead.",
            category=RemovedInDjango2028Warning,
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
