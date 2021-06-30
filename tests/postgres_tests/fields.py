"""
Indirection layer for PostgreSQL-specific fields, so the tests don't fail when
run with a backend other than PostgreSQL.
"""
import enum

from mango.db import models

try:
    from mango.contrib.postgres.fields import (
        ArrayField, BigIntegerRangeField, CICharField, CIEmailField,
        CITextField, DateRangeField, DateTimeRangeField, DecimalRangeField,
        HStoreField, IntegerRangeField,
    )
    from mango.contrib.postgres.search import SearchVector, SearchVectorField
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

    ArrayField = DummyArrayField
    BigIntegerRangeField = models.Field
    CICharField = models.Field
    CIEmailField = models.Field
    CITextField = models.Field
    DateRangeField = models.Field
    DateTimeRangeField = models.Field
    DecimalRangeField = models.Field
    HStoreField = models.Field
    IntegerRangeField = models.Field
    SearchVector = models.Expression
    SearchVectorField = models.Field


class EnumField(models.CharField):
    def get_prep_value(self, value):
        return value.value if isinstance(value, enum.Enum) else value
