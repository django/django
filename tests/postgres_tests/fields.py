"""
Indirection layer for PostgreSQL-specific fields, so the tests don't fail when
run with a backend other than PostgreSQL.
"""
from django.db import models

try:
    from django.contrib.postgres.fields import (
        ArrayField, BigIntegerRangeField, DateRangeField, DateTimeRangeField,
        FloatRangeField, HStoreField, IntegerRangeField, JSONField,
    )
    from django.contrib.postgres.search import SearchVectorField
except ImportError:
    class DummyArrayField(models.Field):
        def __init__(self, base_field, size=None, **kwargs):
            super(DummyArrayField, self).__init__(**kwargs)

        def deconstruct(self):
            name, path, args, kwargs = super(DummyArrayField, self).deconstruct()
            kwargs.update({
                'base_field': '',
                'size': 1,
            })
            return name, path, args, kwargs

    ArrayField = DummyArrayField
    BigIntegerRangeField = models.Field
    DateRangeField = models.Field
    DateTimeRangeField = models.Field
    FloatRangeField = models.Field
    HStoreField = models.Field
    IntegerRangeField = models.Field
    JSONField = models.Field
    SearchVectorField = models.Field
