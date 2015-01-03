from django.contrib.postgres.fields import ArrayField, HStoreField
from django.db import models


class IntegerArrayModel(models.Model):
    field = ArrayField(models.IntegerField())


class NullableIntegerArrayModel(models.Model):
    field = ArrayField(models.IntegerField(), blank=True, null=True)


class CharArrayModel(models.Model):
    field = ArrayField(models.CharField(max_length=10))


class DateTimeArrayModel(models.Model):
    field = ArrayField(models.DateTimeField())


class NestedIntegerArrayModel(models.Model):
    field = ArrayField(ArrayField(models.IntegerField()))


class HStoreModel(models.Model):
    field = HStoreField(blank=True, null=True)


class CharFieldModel(models.Model):
    field = models.CharField(max_length=16)


class TextFieldModel(models.Model):
    field = models.TextField()


class ArrayFieldSubclass(ArrayField):
    def __init__(self, *args, **kwargs):
        super(ArrayFieldSubclass, self).__init__(models.IntegerField())
