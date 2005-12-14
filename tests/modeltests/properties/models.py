"""
22. Using properties on models
"""

from django.core import meta

class Person(meta.Model):
    first_name = meta.CharField(maxlength=30)
    last_name = meta.CharField(maxlength=30)

    def _get_full_name(self):
        return "%s %s" % (self.first_name, self.last_name)
    full_name = property(_get_full_name)

API_TESTS = """
>>> a = Person(first_name='John', last_name='Lennon')
>>> a.save()
>>> a.full_name
'John Lennon'

# The "full_name" property hasn't provided a "set" method.
>>> a.full_name = 'Paul McCartney'
Traceback (most recent call last):
    ...
AttributeError: can't set attribute
"""
