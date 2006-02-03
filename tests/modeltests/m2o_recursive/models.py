"""
11. Relating an object to itself, many-to-one

To define a many-to-one relationship between a model and itself, use
``ForeignKey('self')``.

In this example, a ``Category`` is related to itself. That is, each
``Category`` has a parent ``Category``.

Set ``related_name`` to designate what the reverse relationship is called.
"""

from django.db import models

class Category(models.Model):
    name = models.CharField(maxlength=20)
    parent = models.ForeignKey('self', null=True, related_name='child_set')

    def __repr__(self):
        return self.name

API_TESTS = """
# Create a few Category objects.
>>> r = Category(id=None, name='Root category', parent=None)
>>> r.save()
>>> c = Category(id=None, name='Child category', parent=r)
>>> c.save()

>>> r.child_set.all()
[Child category]
>>> r.child_set.get(name__startswith='Child')
Child category
>>> r.parent
Traceback (most recent call last):
    ...
DoesNotExist

>>> c.child_set.all()
[]
>>> c.parent
Root category
"""
