"""
Indirection layer for PostgreSQL-specific fields, so the tests don't fail when
run with a backend other than PostgreSQL.
"""
import enum

from django.db import models

try:
    from django.contrib.postgres.fields import CICharField  # RemovedInDjango51Warning.
    from django.contrib.postgres.fields import CIEmailField  # RemovedInDjango51Warning.
    from django.contrib.postgres.fields import CITextField  # RemovedInDjango51Warning.
    from django.contrib.postgres.fields import (
        ArrayField,
        BigIntegerRangeField,
        DateRangeField,
        DateTimeRangeField,
        DecimalRangeField,
        HStoreField,
        IntegerRangeField,
    )
    from django.contrib.postgres.search import SearchVector, SearchVectorField
except ImportError:

    class DummyArrayField(models.Field):
        def __init__(self, base_field, size=None, **kwargs):
            super().__init__(**kwargs)

        def deconstruct(self):
            name, path, args, kwargs = super().deconstruct()
            kwargs.update(
                {
                    "base_field": "",
                    "size": 1,
                }
            )
            return name, path, args, kwargs

    class DummyContinuousRangeField(models.Field):
        def __init__(self, *args, default_bounds="[)", **kwargs):
            super().__init__(**kwargs)

        def deconstruct(self):
            name, path, args, kwargs = super().deconstruct()
            kwargs["default_bounds"] = "[)"
            return name, path, args, kwargs

    ArrayField = DummyArrayField
    BigIntegerRangeField = models.Field
    CICharField = models.Field  # RemovedInDjango51Warning.
    CIEmailField = models.Field  # RemovedInDjango51Warning.
    CITextField = models.Field  # RemovedInDjango51Warning.
    DateRangeField = models.Field
    DateTimeRangeField = DummyContinuousRangeField
    DecimalRangeField = DummyContinuousRangeField
    HStoreField = models.Field
    IntegerRangeField = models.Field
    SearchVector = models.Expression
    SearchVectorField = models.Field


class EnumField(models.CharField):
    def get_prep_value(self, value):
        return value.value if isinstance(value, enum.Enum) else value
