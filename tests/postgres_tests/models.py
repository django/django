from django.db import connection, models

from .fields import (
    ArrayField, BigIntegerRangeField, DateRangeField, DateTimeRangeField,
    FloatRangeField, HStoreField, IntegerRangeField, JSONField,
)


class PostgreSQLModel(models.Model):
    class Meta:
        abstract = True
        required_db_vendor = 'postgresql'


class IntegerArrayModel(PostgreSQLModel):
    field = ArrayField(models.IntegerField())


class NullableIntegerArrayModel(PostgreSQLModel):
    field = ArrayField(models.IntegerField(), blank=True, null=True)


class CharArrayModel(PostgreSQLModel):
    field = ArrayField(models.CharField(max_length=10))


class DateTimeArrayModel(PostgreSQLModel):
    datetimes = ArrayField(models.DateTimeField())
    dates = ArrayField(models.DateField())
    times = ArrayField(models.TimeField())


class NestedIntegerArrayModel(PostgreSQLModel):
    field = ArrayField(ArrayField(models.IntegerField()))


class OtherTypesArrayModel(PostgreSQLModel):
    ips = ArrayField(models.GenericIPAddressField())
    uuids = ArrayField(models.UUIDField())
    decimals = ArrayField(models.DecimalField(max_digits=5, decimal_places=2))


class HStoreModel(PostgreSQLModel):
    field = HStoreField(blank=True, null=True)


class CharFieldModel(models.Model):
    field = models.CharField(max_length=16)


class TextFieldModel(models.Model):
    field = models.TextField()


# Only create this model for postgres >= 9.2
if connection.vendor == 'postgresql' and connection.pg_version >= 90200:
    class RangesModel(PostgreSQLModel):
        ints = IntegerRangeField(blank=True, null=True)
        bigints = BigIntegerRangeField(blank=True, null=True)
        floats = FloatRangeField(blank=True, null=True)
        timestamps = DateTimeRangeField(blank=True, null=True)
        dates = DateRangeField(blank=True, null=True)

    class RangeLookupsModel(PostgreSQLModel):
        parent = models.ForeignKey(RangesModel, blank=True, null=True)
        integer = models.IntegerField(blank=True, null=True)
        big_integer = models.BigIntegerField(blank=True, null=True)
        float = models.FloatField(blank=True, null=True)
        timestamp = models.DateTimeField(blank=True, null=True)
        date = models.DateField(blank=True, null=True)

else:
    # create an object with this name so we don't have failing imports
    class RangesModel(object):
        pass

    class RangeLookupsModel(object):
        pass


# Only create this model for postgres >= 9.4
if connection.vendor == 'postgresql' and connection.pg_version >= 90400:
    class JSONModel(models.Model):
        field = JSONField(blank=True, null=True)
else:
    # create an object with this name so we don't have failing imports
    class JSONModel(object):
        pass


class ArrayFieldSubclass(ArrayField):
    def __init__(self, *args, **kwargs):
        super(ArrayFieldSubclass, self).__init__(models.IntegerField())


class AggregateTestModel(models.Model):
    """
    To test postgres-specific general aggregation functions
    """
    char_field = models.CharField(max_length=30, blank=True)
    integer_field = models.IntegerField(null=True)
    boolean_field = models.NullBooleanField()


class StatTestModel(models.Model):
    """
    To test postgres-specific aggregation functions for statistics
    """
    int1 = models.IntegerField()
    int2 = models.IntegerField()
    related_field = models.ForeignKey(AggregateTestModel, null=True)


class NowTestModel(models.Model):
    when = models.DateTimeField(null=True, default=None)
