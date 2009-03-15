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

class RestrictedClass(models.Model):
    name = models.CharField(max_length=50)
    is_public = models.BooleanField(default=False)

    objects = RestrictedManager()
    plain_manager = models.Manager()

    def __unicode__(self):
        return self.name

__test__ = {"tests": """
Even though the default manager filters out some records, we must still be able
to save (particularly, save by updating existing records) those filtered
instances. This is a regression test for #FIXME.
>>> obj = RestrictedClass.objects.create(name="hidden")
>>> obj.name = "still hidden"
>>> obj.save()

# If the hidden object wasn't seen during the save process, there would now be
# two objects in the database.
>>> RestrictedClass.plain_manager.count()
1

"""
}
