"""
11. Relating an object to itself, many-to-one

To define a many-to-one relationship between a model and itself, use
``ForeignKey('self')``.

In this example, a ``Category`` is related to itself. That is, each
``Category`` has a parent ``Category``.

Set ``related_name`` to designate what the reverse relationship is called.
"""

from django.core import meta

class Category(meta.Model):
    name = meta.CharField(maxlength=20)
    parent = meta.ForeignKey('self', null=True, related_name='child')
    class META:
        module_name = 'categories'

    def __repr__(self):
        return self.name

API_TESTS = """
# Create a few Category objects.
>>> r = Category(id=None, name='Root category', parent=None)
>>> r.save()
>>> c = Category(id=None, name='Child category', parent=r)
>>> c.save()

>>> r.get_child_list()
[Child category]
>>> r.get_child(name__startswith='Child')
Child category
>>> r.get_parent()
Traceback (most recent call last):
    ...
DoesNotExist

>>> c.get_child_list()
[]
>>> c.get_parent()
Root category
"""
