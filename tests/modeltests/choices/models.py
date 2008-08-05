"""
21. Specifying 'choices' for a field

Most fields take a ``choices`` parameter, which should be a tuple of tuples
specifying which are the valid values for that field.

For each field that has ``choices``, a model instance gets a
``get_fieldname_display()`` method, where ``fieldname`` is the name of the
field. This method returns the "human-readable" value of the field.
"""

from django.db import models

GENDER_CHOICES = (
    ('M', 'Male'),
    ('F', 'Female'),
)

class Person(models.Model):
    name = models.CharField(max_length=20)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)

    def __unicode__(self):
        return self.name

__test__ = {'API_TESTS':"""
>>> a = Person(name='Adrian', gender='M')
>>> a.save()
>>> s = Person(name='Sara', gender='F')
>>> s.save()
>>> a.gender
'M'
>>> s.gender
'F'
>>> a.get_gender_display()
u'Male'
>>> s.get_gender_display()
u'Female'

# If the value for the field doesn't correspond to a valid choice,
# the value itself is provided as a display value.
>>> a.gender = ''
>>> a.get_gender_display()
u''

>>> a.gender = 'U'
>>> a.get_gender_display()
u'U'

"""}
