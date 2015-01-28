from django.contrib.postgres.fields import (
    ArrayField, BigIntegerRangeField, DateRangeField, DateTimeRangeField,
    FloatRangeField, HStoreField, IntegerRangeField,
)
from django.db import connection, models


class IntegerArrayModel(models.Model):
    field = ArrayField(models.IntegerField())


class NullableIntegerArrayModel(models.Model):
    field = ArrayField(models.IntegerField(), blank=True, null=True)


class CharArrayModel(models.Model):
    field = ArrayField(models.CharField(max_length=10))


class DateTimeArrayModel(models.Model):
    datetimes = ArrayField(models.DateTimeField())
    dates = ArrayField(models.DateField())
    times = ArrayField(models.TimeField())


class NestedIntegerArrayModel(models.Model):
    field = ArrayField(ArrayField(models.IntegerField()))


class OtherTypesArrayModel(models.Model):
    ips = ArrayField(models.GenericIPAddressField())
    uuids = ArrayField(models.UUIDField())
    decimals = ArrayField(models.DecimalField(max_digits=5, decimal_places=2))


class HStoreModel(models.Model):
    field = HStoreField(blank=True, null=True)


class CharFieldModel(models.Model):
    field = models.CharField(max_length=16)


class TextFieldModel(models.Model):
    field = models.TextField()


# Only create this model for databases which support it
if connection.vendor == 'postgresql' and connection.pg_version >= 90200:
    class RangesModel(models.Model):
        ints = IntegerRangeField(blank=True, null=True)
        bigints = BigIntegerRangeField(blank=True, null=True)
        floats = FloatRangeField(blank=True, null=True)
        timestamps = DateTimeRangeField(blank=True, null=True)
        dates = DateRangeField(blank=True, null=True)
else:
    # create an object with this name so we don't have failing imports
    class RangesModel(object):
        pass


class ArrayFieldSubclass(ArrayField):
    def __init__(self, *args, **kwargs):
        super(ArrayFieldSubclass, self).__init__(models.IntegerField())
