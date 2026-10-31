from django.contrib.postgres.fields import ArrayField
from django.db.models import Aggregate, BooleanField, JSONField

__all__ = [
    "ArrayAgg",
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
