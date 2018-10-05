"""
Indirection layer for PostgreSQL-specific fields, so the tests don't fail when
run with a backend other than PostgreSQL.
"""
from django.db import models

try:
    from django.contrib.postgres.fields import (
        ArrayField, BigIntegerRangeField, CICharField, CIEmailField,
        CITextField, DateRangeField, DateTimeRangeField, DecimalRangeField,
        HStoreField, IntegerRangeField, JSONField,
    )
    from django.contrib.postgres.search import SearchVectorField
except ImportError:
    class DummyArrayField(models.Field):
        def __init__(self, base_field, size=None, **kwargs):
            super().__init__(**kwargs)

        def deconstruct(self):
            name, path, args, kwargs = super().deconstruct()
            kwargs.update({
                'base_field': '',
                'size': 1,
            })
            return name, path, args, kwargs

    class DummyJSONField(models.Field):
        def __init__(self, encoder=None, **kwargs):
            super().__init__(**kwargs)

    class DummyRangeField(models.Field):
        def __init__(self, *args, bounds='[)', **kwargs):
            super().__init__(**kwargs)

    ArrayField = DummyArrayField
    BigIntegerRangeField = DummyRangeField
    CICharField = models.Field
    CIEmailField = models.Field
    CITextField = models.Field
    DateRangeField = DummyRangeField
    DateTimeRangeField = DummyRangeField
    DecimalRangeField = DummyRangeField
    HStoreField = models.Field
    IntegerRangeField = DummyRangeField
    JSONField = DummyJSONField
    SearchVectorField = models.Field
