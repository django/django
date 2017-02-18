"""
Relating an object to itself, many-to-one

To define a many-to-one relationship between a model and itself, use
``ForeignKey('self')``.

In this example, a ``Category`` is related to itself. That is, each
``Category`` has a parent ``Category``.

Set ``related_name`` to designate what the reverse relationship is called.
"""

from django.db import models
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class Category(models.Model):
    name = models.CharField(max_length=20)
    parent = models.ForeignKey('self', blank=True, null=True, related_name='child_set')

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class Person(models.Model):
    full_name = models.CharField(max_length=20)
    mother = models.ForeignKey('self', null=True, related_name='mothers_child_set')
    father = models.ForeignKey('self', null=True, related_name='fathers_child_set')

    def __str__(self):
        return self.full_name
