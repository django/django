from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.db import models


class Episode(models.Model):
    name = models.CharField(max_length=100)
    length = models.CharField(max_length=100, blank=True)
    author = models.CharField(max_length=100, blank=True)


class Media(models.Model):
    """
    Media that can associated to any object.
    """
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = generic.GenericForeignKey()
    url = models.URLField()
    description = models.CharField(max_length=100, blank=True)
    keywords = models.CharField(max_length=100, blank=True)

    def __unicode__(self):
        return self.url

#
# These models let us test the different GenericInline settings at
# different urls in the admin site.
#

#
# Generic inline with extra = 0
#

class EpisodeExtra(Episode):
    pass


#
# Generic inline with extra and max_num
#
class EpisodeMaxNum(Episode):
    pass


#
# Generic inline with unique_together
#
class Category(models.Model):
    name = models.CharField(max_length=50)


class PhoneNumber(models.Model):
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = generic.GenericForeignKey('content_type', 'object_id')
    phone_number = models.CharField(max_length=30)
    category = models.ForeignKey(Category, null=True, blank=True)

    class Meta:
        unique_together = (('content_type', 'object_id', 'phone_number',),)


class Contact(models.Model):
    name = models.CharField(max_length=50)
    phone_numbers = generic.GenericRelation(PhoneNumber)

#
# Generic inline with can_delete=False
#
class EpisodePermanent(Episode):
    pass


