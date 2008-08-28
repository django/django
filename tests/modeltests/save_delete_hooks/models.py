"""
13. Adding hooks before/after saving and deleting

To execute arbitrary code around ``save()`` and ``delete()``, just subclass
the methods.
"""

from django.db import models

class Person(models.Model):
    first_name = models.CharField(max_length=20)
    last_name = models.CharField(max_length=20)

    def __unicode__(self):
        return u"%s %s" % (self.first_name, self.last_name)

    def save(self, force_insert=False, force_update=False):
        print "Before save"
         # Call the "real" save() method
        super(Person, self).save(force_insert, force_update)
        print "After save"

    def delete(self):
        print "Before deletion"
        super(Person, self).delete() # Call the "real" delete() method
        print "After deletion"

__test__ = {'API_TESTS':"""
>>> p1 = Person(first_name='John', last_name='Smith')
>>> p1.save()
Before save
After save

>>> Person.objects.all()
[<Person: John Smith>]

>>> p1.delete()
Before deletion
After deletion

>>> Person.objects.all()
[]
"""}
