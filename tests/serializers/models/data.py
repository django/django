"""
******** Models for test_data.py ***********
The following classes are for testing basic data marshalling, including
NULL values, where allowed.
The basic idea is to have a model for each Django data type.
"""
from __future__ import unicode_literals

from django.contrib.contenttypes.fields import (
    GenericForeignKey, GenericRelation,
)
from django.contrib.contenttypes.models import ContentType
from django.db import models

from .base import BaseModel


class BinaryData(models.Model):
    data = models.BinaryField(null=True)


class BooleanData(models.Model):
    data = models.BooleanField(default=False)


class CharData(models.Model):
    data = models.CharField(max_length=30, null=True)


class DateData(models.Model):
    data = models.DateField(null=True)


class DateTimeData(models.Model):
    data = models.DateTimeField(null=True)


class DecimalData(models.Model):
    data = models.DecimalField(null=True, decimal_places=3, max_digits=5)


class EmailData(models.Model):
    data = models.EmailField(null=True)


class FileData(models.Model):
    data = models.FileField(null=True, upload_to='/foo/bar')


class FilePathData(models.Model):
    data = models.FilePathField(null=True)


class FloatData(models.Model):
    data = models.FloatField(null=True)


class IntegerData(models.Model):
    data = models.IntegerField(null=True)


class BigIntegerData(models.Model):
    data = models.BigIntegerField(null=True)

# class ImageData(models.Model):
#    data = models.ImageField(null=True)


class GenericIPAddressData(models.Model):
    data = models.GenericIPAddressField(null=True)


class NullBooleanData(models.Model):
    data = models.NullBooleanField(null=True)


class PositiveIntegerData(models.Model):
    data = models.PositiveIntegerField(null=True)


class PositiveSmallIntegerData(models.Model):
    data = models.PositiveSmallIntegerField(null=True)


class SlugData(models.Model):
    data = models.SlugField(null=True)


class SmallData(models.Model):
    data = models.SmallIntegerField(null=True)


class TextData(models.Model):
    data = models.TextField(null=True)


class TimeData(models.Model):
    data = models.TimeField(null=True)


class Tag(models.Model):
    """A tag on an item."""
    data = models.SlugField()
    content_type = models.ForeignKey(ContentType, models.CASCADE)
    object_id = models.PositiveIntegerField()

    content_object = GenericForeignKey()

    class Meta:
        ordering = ["data"]


class GenericData(models.Model):
    data = models.CharField(max_length=30)

    tags = GenericRelation(Tag)

# The following test classes are all for validation
# of related objects; in particular, forward, backward,
# and self references.


class Anchor(models.Model):
    """This is a model that can be used as
    something for other models to point at"""

    data = models.CharField(max_length=30)

    class Meta:
        ordering = ('id',)


class UniqueAnchor(models.Model):
    """This is a model that can be used as
    something for other models to point at"""

    data = models.CharField(unique=True, max_length=30)


class FKData(models.Model):
    data = models.ForeignKey(Anchor, models.SET_NULL, null=True)


class M2MData(models.Model):
    data = models.ManyToManyField(Anchor)


class O2OData(models.Model):
    # One to one field can't be null here, since it is a PK.
    data = models.OneToOneField(Anchor, models.CASCADE, primary_key=True)


class FKSelfData(models.Model):
    data = models.ForeignKey('self', models.CASCADE, null=True)


class M2MSelfData(models.Model):
    data = models.ManyToManyField('self', symmetrical=False)


class FKDataToField(models.Model):
    data = models.ForeignKey(UniqueAnchor, models.SET_NULL, null=True, to_field='data')


class FKDataToO2O(models.Model):
    data = models.ForeignKey(O2OData, models.SET_NULL, null=True)


class M2MIntermediateData(models.Model):
    data = models.ManyToManyField(Anchor, through='Intermediate')


class Intermediate(models.Model):
    left = models.ForeignKey(M2MIntermediateData, models.CASCADE)
    right = models.ForeignKey(Anchor, models.CASCADE)
    extra = models.CharField(max_length=30, blank=True, default="doesn't matter")

# The following test classes are for validating the
# deserialization of objects that use a user-defined
# field as the primary key.
# Some of these data types have been commented out
# because they can't be used as a primary key on one
# or all database backends.


class BooleanPKData(models.Model):
    data = models.BooleanField(primary_key=True, default=False)


class CharPKData(models.Model):
    data = models.CharField(max_length=30, primary_key=True)

# class DatePKData(models.Model):
#    data = models.DateField(primary_key=True)

# class DateTimePKData(models.Model):
#    data = models.DateTimeField(primary_key=True)


class DecimalPKData(models.Model):
    data = models.DecimalField(primary_key=True, decimal_places=3, max_digits=5)


class EmailPKData(models.Model):
    data = models.EmailField(primary_key=True)

# class FilePKData(models.Model):
#    data = models.FileField(primary_key=True, upload_to='/foo/bar')


class FilePathPKData(models.Model):
    data = models.FilePathField(primary_key=True)


class FloatPKData(models.Model):
    data = models.FloatField(primary_key=True)


class IntegerPKData(models.Model):
    data = models.IntegerField(primary_key=True)

# class ImagePKData(models.Model):
#    data = models.ImageField(primary_key=True)


class GenericIPAddressPKData(models.Model):
    data = models.GenericIPAddressField(primary_key=True)

# This is just a Boolean field with null=True, and we can't test a PK value of NULL.
# class NullBooleanPKData(models.Model):
#     data = models.NullBooleanField(primary_key=True)


class PositiveIntegerPKData(models.Model):
    data = models.PositiveIntegerField(primary_key=True)


class PositiveSmallIntegerPKData(models.Model):
    data = models.PositiveSmallIntegerField(primary_key=True)


class SlugPKData(models.Model):
    data = models.SlugField(primary_key=True)


class SmallPKData(models.Model):
    data = models.SmallIntegerField(primary_key=True)

# class TextPKData(models.Model):
#     data = models.TextField(primary_key=True)

# class TimePKData(models.Model):
#    data = models.TimeField(primary_key=True)


class UUIDData(models.Model):
    data = models.UUIDField(primary_key=True)


class FKToUUID(models.Model):
    data = models.ForeignKey(UUIDData, models.CASCADE)


# Tests for handling fields with pre_save functions, or
# models with save functions that modify data


class AutoNowDateTimeData(models.Model):
    data = models.DateTimeField(null=True, auto_now=True)


class ModifyingSaveData(models.Model):
    data = models.IntegerField(null=True)

    def save(self, *args, **kwargs):
        """
        A save method that modifies the data in the object.
        Verifies that a user-defined save() method isn't called when objects
        are deserialized (#4459).
        """
        self.data = 666
        super(ModifyingSaveData, self).save(*args, **kwargs)

# Tests for serialization of models using inheritance.
# Regression for #7202, #7350


class AbstractBaseModel(models.Model):
    parent_data = models.IntegerField()

    class Meta:
        abstract = True


class InheritAbstractModel(AbstractBaseModel):
    child_data = models.IntegerField()


class InheritBaseModel(BaseModel):
    child_data = models.IntegerField()


class ExplicitInheritBaseModel(BaseModel):
    parent = models.OneToOneField(BaseModel, models.CASCADE, parent_link=True)
    child_data = models.IntegerField()


class LengthModel(models.Model):
    data = models.IntegerField()

    def __len__(self):
        return self.data
