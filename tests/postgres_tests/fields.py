"""
Indirection layer for PostgreSQL-specific fields, so the tests don't fail when
run with a backend other than PostgreSQL.
"""
import enum

from django.core.exceptions import ImproperlyConfigured
from django.db import models

try:
    from django.db.backends.postgresql.base import DatabaseWrapper  # NOQA
    from django.contrib.postgres.fields import (
        ArrayField, BigIntegerRangeField, BigSerialField, CICharField, CIEmailField,
        CITextField, DateRangeField, DateTimeRangeField, DecimalRangeField,
        HStoreField, IntegerRangeField, SmallSerialField, SerialField
    )
    from django.contrib.postgres.search import SearchVectorField
except (ImportError, ImproperlyConfigured):
    from django.db.backends.dummy.base import DatabaseWrapper  # NOQA

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
    BigSerialField = models.Field
    CICharField = models.Field
    CIEmailField = models.Field
    CITextField = models.Field
    DateRangeField = models.Field
    DateTimeRangeField = models.Field
    DecimalRangeField = models.Field
    HStoreField = models.Field
    IntegerRangeField = models.Field
    SmallSerialField = models.Field
    SearchVectorField = models.Field
    SerialField = models.Field


class EnumField(models.CharField):
    def get_prep_value(self, value):
        return value.value if isinstance(value, enum.Enum) else value
