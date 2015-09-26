# -*- coding: utf-8 -*-
"""
Serialization

``django.core.serializers`` provides interfaces to converting Django
``QuerySet`` objects to and from "flat" data (i.e. strings).
"""
from __future__ import unicode_literals

from decimal import Decimal

from django.contrib.contenttypes.fields import (
    GenericForeignKey, GenericRelation,
)
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import six
from django.utils.encoding import python_2_unicode_compatible


class CategoryMetaDataManager(models.Manager):

    def get_by_natural_key(self, kind, name):
        return self.get(kind=kind, name=name)


@python_2_unicode_compatible
class CategoryMetaData(models.Model):
    kind = models.CharField(max_length=10)
    name = models.CharField(max_length=10)
    value = models.CharField(max_length=10)
    objects = CategoryMetaDataManager()

    class Meta:
        unique_together = (('kind', 'name'),)

    def __str__(self):
        return '[%s:%s]=%s' % (self.kind, self.name, self.value)

    def natural_key(self):
        return (self.kind, self.name)


@python_2_unicode_compatible
class Category(models.Model):
    name = models.CharField(max_length=20)
    meta_data = models.ForeignKey(CategoryMetaData, models.SET_NULL, null=True, default=None)

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class Author(models.Model):
    name = models.CharField(max_length=20)

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class Article(models.Model):
    author = models.ForeignKey(Author, models.CASCADE)
    headline = models.CharField(max_length=50)
    pub_date = models.DateTimeField()
    categories = models.ManyToManyField(Category)
    meta_data = models.ManyToManyField(CategoryMetaData)

    class Meta:
        ordering = ('pub_date',)

    def __str__(self):
        return self.headline


@python_2_unicode_compatible
class AuthorProfile(models.Model):
    author = models.OneToOneField(Author, models.CASCADE, primary_key=True)
    date_of_birth = models.DateField()

    def __str__(self):
        return "Profile of %s" % self.author


@python_2_unicode_compatible
class Actor(models.Model):
    name = models.CharField(max_length=20, primary_key=True)

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class Movie(models.Model):
    actor = models.ForeignKey(Actor, models.CASCADE)
    title = models.CharField(max_length=50)
    price = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))

    class Meta:
        ordering = ('title',)

    def __str__(self):
        return self.title


class Score(models.Model):
    score = models.FloatField()


@python_2_unicode_compatible
class Team(object):
    def __init__(self, title):
        self.title = title

    def __str__(self):
        raise NotImplementedError("Not so simple")

    def to_string(self):
        return "%s" % self.title


class TeamField(models.CharField):

    def __init__(self):
        super(TeamField, self).__init__(max_length=100)

    def get_db_prep_save(self, value, connection):
        return six.text_type(value.title)

    def to_python(self, value):
        if isinstance(value, Team):
            return value
        return Team(value)

    def from_db_value(self, value, expression, connection, context):
        return Team(value)

    def value_to_string(self, obj):
        return self.value_from_object(obj).to_string()

    def deconstruct(self):
        name, path, args, kwargs = super(TeamField, self).deconstruct()
        del kwargs['max_length']
        return name, path, args, kwargs


@python_2_unicode_compatible
class Player(models.Model):
    name = models.CharField(max_length=50)
    rank = models.IntegerField()
    team = TeamField()

    def __str__(self):
        return '%s (%d) playing for %s' % (self.name, self.rank, self.team.to_string())


class BaseModel(models.Model):
    parent_data = models.IntegerField()


class ProxyBaseModel(BaseModel):
    class Meta:
        proxy = True


class ProxyProxyBaseModel(ProxyBaseModel):
    class Meta:
        proxy = True


class ComplexModel(models.Model):
    field1 = models.CharField(max_length=10)
    field2 = models.CharField(max_length=10)
    field3 = models.CharField(max_length=10)


# ******** Models for test_natural.py ***********

class NaturalKeyAnchorManager(models.Manager):
    def get_by_natural_key(self, data):
        return self.get(data=data)


class NaturalKeyAnchor(models.Model):
    objects = NaturalKeyAnchorManager()

    data = models.CharField(max_length=100, unique=True)
    title = models.CharField(max_length=100, null=True)

    def natural_key(self):
        return (self.data,)


class FKDataNaturalKey(models.Model):
    data = models.ForeignKey(NaturalKeyAnchor, models.SET_NULL, null=True)


# ******** Models for test_data.py ***********
# The following classes are for testing basic data marshalling, including
# NULL values, where allowed.
# The basic idea is to have a model for each Django data type.

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


class BaseModel(models.Model):
    parent_data = models.IntegerField()


class InheritBaseModel(BaseModel):
    child_data = models.IntegerField()


class ExplicitInheritBaseModel(BaseModel):
    parent = models.OneToOneField(BaseModel, models.CASCADE)
    child_data = models.IntegerField()


class LengthModel(models.Model):
    data = models.IntegerField()

    def __len__(self):
        return self.data
