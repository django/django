"""Models for test_natural.py"""
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.encoding import python_2_unicode_compatible


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


@python_2_unicode_compatible
class TaggedItem(models.Model):
    """A tag on an item."""
    tag = models.SlugField()
    content_type = models.ForeignKey(ContentType, models.CASCADE)
    object_id = models.PositiveIntegerField()

    content_object = GenericForeignKey()

    class Meta:
        ordering = ["tag", "content_type__model"]

    def __str__(self):
        return self.tag

    @property
    def data(self):
        return self.content_object
