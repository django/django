"""
Regression tests for custom manager classes.
"""

from django.db import models
from django.utils.encoding import python_2_unicode_compatible


class RestrictedManager(models.Manager):
    """
    A manager that filters out non-public instances.
    """
    def get_queryset(self):
        return super(RestrictedManager, self).get_queryset().filter(is_public=True)

@python_2_unicode_compatible
class RelatedModel(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name

@python_2_unicode_compatible
class RestrictedModel(models.Model):
    name = models.CharField(max_length=50)
    is_public = models.BooleanField(default=False)
    related = models.ForeignKey(RelatedModel)

    objects = RestrictedManager()
    plain_manager = models.Manager()

    def __str__(self):
        return self.name

@python_2_unicode_compatible
class OneToOneRestrictedModel(models.Model):
    name = models.CharField(max_length=50)
    is_public = models.BooleanField(default=False)
    related = models.OneToOneField(RelatedModel)

    objects = RestrictedManager()
    plain_manager = models.Manager()

    def __str__(self):
        return self.name
