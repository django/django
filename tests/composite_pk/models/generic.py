from django.contrib.contenttypes.fields import GenericRelation
from django.db import models


class Dummy(models.Model):
    pk = models.CompositePrimaryKey(
        "small_integer",
        "integer",
        "big_integer",
        "datetime",
        "date",
        "uuid",
        "char",
    )

    small_integer = models.SmallIntegerField()
    integer = models.IntegerField()
    big_integer = models.BigIntegerField()
    datetime = models.DateTimeField()
    date = models.DateField()
    uuid = models.UUIDField()
    char = models.CharField(max_length=5)

    tags = GenericRelation("Tag", related_query_name="dummy")
