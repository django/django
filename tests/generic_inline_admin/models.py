from django.contrib.contenttypes.fields import (
    GenericForeignKey, GenericRelation,
)
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.encoding import python_2_unicode_compatible


class Episode(models.Model):
    name = models.CharField(max_length=100)
    length = models.CharField(max_length=100, blank=True)
    author = models.CharField(max_length=100, blank=True)


@python_2_unicode_compatible
class Media(models.Model):
    """
    Media that can associated to any object.
    """
    content_type = models.ForeignKey(ContentType, models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey()
    url = models.URLField()
    description = models.CharField(max_length=100, blank=True)
    keywords = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.url


#
# Generic inline with unique_together
#
class Category(models.Model):
    name = models.CharField(max_length=50)


class PhoneNumber(models.Model):
    content_type = models.ForeignKey(ContentType, models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    phone_number = models.CharField(max_length=30)
    category = models.ForeignKey(Category, models.SET_NULL, null=True, blank=True)

    class Meta:
        unique_together = (('content_type', 'object_id', 'phone_number',),)


class Contact(models.Model):
    name = models.CharField(max_length=50)
    phone_numbers = GenericRelation(PhoneNumber, related_query_name='phone_numbers')


#
# Generic inline with can_delete=False
#
class EpisodePermanent(Episode):
    pass
