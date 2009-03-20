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

__test__ = {"tests": """
Even though the default manager filters out some records, we must still be able
to save (particularly, save by updating existing records) those filtered
instances. This is a regression test for #8990, #9527
>>> related = RelatedModel.objects.create(name="xyzzy")
>>> obj = RestrictedModel.objects.create(name="hidden", related=related)
>>> obj.name = "still hidden"
>>> obj.save()

# If the hidden object wasn't seen during the save process, there would now be
# two objects in the database.
>>> RestrictedModel.plain_manager.count()
1

Deleting related objects should also not be distracted by a restricted manager
on the related object. This is a regression test for #2698.
>>> RestrictedModel.plain_manager.all().delete()
>>> for name, public in (('one', True), ('two', False), ('three', False)):
...     _ = RestrictedModel.objects.create(name=name, is_public=public, related=related)

# Reload the RelatedModel instance, just to avoid any instance artifacts.
>>> obj = RelatedModel.objects.get(name="xyzzy")
>>> obj.delete()

# All of the RestrictedModel instances should have been deleted, since they
# *all* pointed to the RelatedModel. If the default manager is used, only the
# public one will be deleted.
>>> RestrictedModel.plain_manager.all()
[]

# The same test case as the last one, but for one-to-one models, which are
# implemented slightly different internally, so it's a different code path.
>>> obj = RelatedModel.objects.create(name="xyzzy")
>>> _ = OneToOneRestrictedModel.objects.create(name="foo", is_public=False, related=obj)
>>> obj = RelatedModel.objects.get(name="xyzzy")
>>> obj.delete()
>>> OneToOneRestrictedModel.plain_manager.all()
[]

"""
}
