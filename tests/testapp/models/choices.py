"""
21. Specifying 'choices' for a field

Most fields take a ``choices`` parameter, which should be a tuple of tuples
specifying which are the valid values for that field.

For each field that has ``choices``, a model instance gets a
``get_fieldname_display()`` method, where ``fieldname`` is the name of the
field. This method returns the "human-readable" value of the field.
"""

from django.core import meta

GENDER_CHOICES = (
    ('M', 'Male'),
    ('F', 'Female'),
)

class Person(meta.Model):
    name = meta.CharField(maxlength=20)
    gender = meta.CharField(maxlength=1, choices=GENDER_CHOICES)

    def __repr__(self):
        return self.name

API_TESTS = """
>>> a = Person(name='Adrian', gender='M')
>>> a.save()
>>> s = Person(name='Sara', gender='F')
>>> s.save()
>>> a.gender
'M'
>>> s.gender
'F'
>>> a.get_gender_display()
'Male'
>>> s.get_gender_display()
'Female'
"""
