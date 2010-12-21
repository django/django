"""
A test spanning all the capabilities of all the serializers.

This class sets up a model for each model field type
(except for image types, because of the PIL dependency).
"""

from django.db import models
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.contrib.localflavor.us.models import USStateField, PhoneNumberField

# The following classes are for testing basic data
# marshalling, including NULL values, where allowed.

class BooleanData(models.Model):
    data = models.BooleanField()

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

class IPAddressData(models.Model):
    data = models.IPAddressField(null=True)

class NullBooleanData(models.Model):
    data = models.NullBooleanField(null=True)

class PhoneData(models.Model):
    data = PhoneNumberField(null=True)

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

class USStateData(models.Model):
    data = USStateField(null=True)

class XMLData(models.Model):
    data = models.XMLField(null=True)

class Tag(models.Model):
    """A tag on an item."""
    data = models.SlugField()
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()

    content_object = generic.GenericForeignKey()

    class Meta:
        ordering = ["data"]

class GenericData(models.Model):
    data = models.CharField(max_length=30)

    tags = generic.GenericRelation(Tag)

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
    data = models.ForeignKey(Anchor, null=True)

class M2MData(models.Model):
    data = models.ManyToManyField(Anchor, null=True)

class O2OData(models.Model):
    # One to one field can't be null here, since it is a PK.
    data = models.OneToOneField(Anchor, primary_key=True)

class FKSelfData(models.Model):
    data = models.ForeignKey('self', null=True)

class M2MSelfData(models.Model):
    data = models.ManyToManyField('self', null=True, symmetrical=False)

class FKDataToField(models.Model):
    data = models.ForeignKey(UniqueAnchor, null=True, to_field='data')

class FKDataToO2O(models.Model):
    data = models.ForeignKey(O2OData, null=True)

class M2MIntermediateData(models.Model):
    data = models.ManyToManyField(Anchor, null=True, through='Intermediate')

class Intermediate(models.Model):
    left = models.ForeignKey(M2MIntermediateData)
    right = models.ForeignKey(Anchor)
    extra = models.CharField(max_length=30, blank=True, default="doesn't matter")

# The following test classes are for validating the
# deserialization of objects that use a user-defined
# field as the primary key.
# Some of these data types have been commented out
# because they can't be used as a primary key on one
# or all database backends.

class BooleanPKData(models.Model):
    data = models.BooleanField(primary_key=True)

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

class IPAddressPKData(models.Model):
    data = models.IPAddressField(primary_key=True)

# This is just a Boolean field with null=True, and we can't test a PK value of NULL.
# class NullBooleanPKData(models.Model):
#     data = models.NullBooleanField(primary_key=True)

class PhonePKData(models.Model):
    data = PhoneNumberField(primary_key=True)

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

class USStatePKData(models.Model):
    data = USStateField(primary_key=True)

# class XMLPKData(models.Model):
#     data = models.XMLField(primary_key=True)

class ComplexModel(models.Model):
    field1 = models.CharField(max_length=10)
    field2 = models.CharField(max_length=10)
    field3 = models.CharField(max_length=10)

# Tests for handling fields with pre_save functions, or
# models with save functions that modify data
class AutoNowDateTimeData(models.Model):
    data = models.DateTimeField(null=True, auto_now=True)

class ModifyingSaveData(models.Model):
    data = models.IntegerField(null=True)

    def save(self):
        "A save method that modifies the data in the object"
        self.data = 666
        super(ModifyingSaveData, self).save(raw)

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
    parent = models.OneToOneField(BaseModel)
    child_data = models.IntegerField()

class LengthModel(models.Model):
    data = models.IntegerField()

    def __len__(self):
        return self.data

#Tests for natural keys.
class BookManager(models.Manager):
    def get_by_natural_key(self, isbn13):
        return self.get(isbn13=isbn13)

class Book(models.Model):
    isbn13 = models.CharField(max_length=14)
    title = models.CharField(max_length=100)

    objects = BookManager()

    def natural_key(self):
        return (self.isbn13,)
