"""
13. Adding hooks before/after saving and deleting

To execute arbitrary code around ``save()`` and ``delete()``, just subclass
the methods.
"""

from django.db import models

class Person(models.Model):
    first_name = models.CharField(maxlength=20)
    last_name = models.CharField(maxlength=20)

    def __repr__(self):
        return "%s %s" % (self.first_name, self.last_name)

    def save(self):
        print "Before save"
        super(Person, self).save() # Call the "real" save() method
        print "After save"

    def delete(self):
        print "Before deletion"
        super(Person, self).delete() # Call the "real" delete() method
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
