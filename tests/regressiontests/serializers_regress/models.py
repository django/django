"""
A test spanning all the capabilities of all the serializers.

This class sets up a model for each model field type 
(except for image types, because of the PIL dependency).
"""

from django.db import models
from django.contrib.contenttypes.models import ContentType

# The following classes are for testing basic data 
# marshalling, including NULL values.

class BooleanData(models.Model):
    data = models.BooleanField(null=True)
    
class CharData(models.Model):
    data = models.CharField(maxlength=30, null=True)

class DateData(models.Model):
    data = models.DateField(null=True)

class DateTimeData(models.Model):
    data = models.DateTimeField(null=True)

class EmailData(models.Model):
    data = models.EmailField(null=True)

class FileData(models.Model):
    data = models.FileField(null=True, upload_to='/foo/bar')

class FilePathData(models.Model):
    data = models.FilePathField(null=True)

class FloatData(models.Model):
    data = models.FloatField(null=True, decimal_places=3, max_digits=5)

class IntegerData(models.Model):
    data = models.IntegerField(null=True)

# class ImageData(models.Model):
#    data = models.ImageField(null=True)

class IPAddressData(models.Model):
    data = models.IPAddressField(null=True)

class NullBooleanData(models.Model):
    data = models.NullBooleanField(null=True)

class PhoneData(models.Model):
    data = models.PhoneNumberField(null=True)

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
    data = models.USStateField(null=True)

class XMLData(models.Model):
    data = models.XMLField(null=True)
    
class Tag(models.Model):
    """A tag on an item."""
    data = models.SlugField()
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()

    content_object = models.GenericForeignKey()

    class Meta:
        ordering = ["data"]

class GenericData(models.Model):
    data = models.CharField(maxlength=30)

    tags = models.GenericRelation(Tag)
    
# The following test classes are all for validation
# of related objects; in particular, forward, backward,
# and self references.
    
class Anchor(models.Model):
    """This is a model that can be used as 
    something for other models to point at"""
    
    data = models.CharField(maxlength=30)
    
class FKData(models.Model):
    data = models.ForeignKey(Anchor, null=True)
    
class M2MData(models.Model):
    data = models.ManyToManyField(Anchor, null=True)
    
class O2OData(models.Model):
    data = models.OneToOneField(Anchor, null=True)

class FKSelfData(models.Model):
    data = models.ForeignKey('self', null=True)
    
class M2MSelfData(models.Model):
    data = models.ManyToManyField('self', null=True, symmetrical=False)

# The following test classes are for validating the
# deserialization of objects that use a user-defined
# field as the primary key.
# Some of these data types have been commented out
# because they can't be used as a primary key on one
# or all database backends.

class BooleanPKData(models.Model):
    data = models.BooleanField(primary_key=True)
    
class CharPKData(models.Model):
    data = models.CharField(maxlength=30, primary_key=True)

# class DatePKData(models.Model):
#    data = models.DateField(primary_key=True)

# class DateTimePKData(models.Model):
#    data = models.DateTimeField(primary_key=True)

class EmailPKData(models.Model):
    data = models.EmailField(primary_key=True)

class FilePKData(models.Model):
    data = models.FileField(primary_key=True, upload_to='/foo/bar')

class FilePathPKData(models.Model):
    data = models.FilePathField(primary_key=True)

class FloatPKData(models.Model):
    data = models.FloatField(primary_key=True, decimal_places=3, max_digits=5)

class IntegerPKData(models.Model):
    data = models.IntegerField(primary_key=True)

# class ImagePKData(models.Model):
#    data = models.ImageField(primary_key=True)

class IPAddressPKData(models.Model):
    data = models.IPAddressField(primary_key=True)

class NullBooleanPKData(models.Model):
    data = models.NullBooleanField(primary_key=True)

class PhonePKData(models.Model):
    data = models.PhoneNumberField(primary_key=True)

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
    data = models.USStateField(primary_key=True)

# class XMLPKData(models.Model):
#     data = models.XMLField(primary_key=True)

