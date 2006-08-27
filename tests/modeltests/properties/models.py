"""
22. Using properties on models

Use properties on models just like on any other Python object.
"""

from django.db import models

class Person(models.Model):
    first_name = models.CharField(maxlength=30)
    last_name = models.CharField(maxlength=30)

    def _get_full_name(self):
        return "%s %s" % (self.first_name, self.last_name)

    def _set_full_name(self, combined_name):
        self.first_name, self.last_name = combined_name.split(' ', 1)

    full_name = property(_get_full_name)

    full_name_2 = property(_get_full_name, _set_full_name)

__test__ = {'API_TESTS':"""
>>> a = Person(first_name='John', last_name='Lennon')
>>> a.save()
>>> a.full_name
'John Lennon'

# The "full_name" property hasn't provided a "set" method.
>>> a.full_name = 'Paul McCartney'
Traceback (most recent call last):
    ...
AttributeError: can't set attribute

# But "full_name_2" has, and it can be used to initialise the class.
>>> a2 = Person(full_name_2 = 'Paul McCartney')
>>> a2.save()
>>> a2.first_name
'Paul'
"""}
