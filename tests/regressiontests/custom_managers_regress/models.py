"""
Regression tests for custom manager classes.
"""

from django.db import models


class RestrictedManager(models.Manager):
    """
    A manager that filters out non-public instances.
    """
    def get_query_set(self):
        return super(RestrictedManager, self).get_query_set().filter(is_public=True)

class RelatedModel(models.Model):
    name = models.CharField(max_length=50)

    def __unicode__(self):
        return self.name

class RestrictedModel(models.Model):
    name = models.CharField(max_length=50)
    is_public = models.BooleanField(default=False)
    related = models.ForeignKey(RelatedModel)

    objects = RestrictedManager()
    plain_manager = models.Manager()

    def __unicode__(self):
        return self.name

class OneToOneRestrictedModel(models.Model):
    name = models.CharField(max_length=50)
    is_public = models.BooleanField(default=False)
    related = models.OneToOneField(RelatedModel)

    objects = RestrictedManager()
    plain_manager = models.Manager()

    def __unicode__(self):
        return self.name
