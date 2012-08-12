"""
21. Specifying 'choices' for a field

Most fields take a ``choices`` parameter, which should be a tuple of tuples
specifying which are the valid values for that field.

For each field that has ``choices``, a model instance gets a
``get_fieldname_display()`` method, where ``fieldname`` is the name of the
field. This method returns the "human-readable" value of the field.
"""

from django.db import models
from django.utils.encoding import python_2_unicode_compatible


GENDER_CHOICES = (
    ('M', 'Male'),
    ('F', 'Female'),
)

@python_2_unicode_compatible
class Person(models.Model):
    name = models.CharField(max_length=20)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)

    def __str__(self):
        return self.name
