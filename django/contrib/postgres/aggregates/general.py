from django.contrib.postgres.fields import ArrayField
from django.db.models import Aggregate, BooleanField, JSONField, TextField

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


class StringAgg(_DeprecatedOrdering, Aggregate):
    function = "STRING_AGG"
    allow_distinct = True
    allow_order_by = True
    output_field = TextField()

