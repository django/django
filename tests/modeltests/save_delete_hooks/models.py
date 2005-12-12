"""
13. Adding hooks before/after saving and deleting

Django provides hooks for executing arbitrary code around ``save()`` and
``delete()``. Just add any of the following methods to your model:

    * ``_pre_save()`` is called before an object is saved.
    * ``_post_save()`` is called after an object is saved.
    * ``_pre_delete()`` is called before an object is deleted.
    * ``_post_delete()`` is called after an object is deleted.
"""

from django.core import meta

class Person(meta.Model):
    first_name = meta.CharField(maxlength=20)
    last_name = meta.CharField(maxlength=20)

    def __repr__(self):
        return "%s %s" % (self.first_name, self.last_name)

    def _pre_save(self):
        print "Before save"

    def _post_save(self):
        print "After save"

    def _pre_delete(self):
        print "Before deletion"

    def _post_delete(self):
        print "After deletion"

API_TESTS = """
>>> p1 = Person(first_name='John', last_name='Smith')
>>> p1.save()
Before save
After save

>>> Person.objects.get_list()
[John Smith]

>>> p1.delete()
Before deletion
After deletion

>>> Person.objects.get_list()
[]
"""
