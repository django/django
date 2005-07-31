"""
11. Relating an object to itself, many-to-one

To define a many-to-one relationship between a model and itself, use
``ForeignKey('self')``.

In this example, a ``Category`` is related to itself. That is, each
``Category`` has a parent ``Category``.

Because of this recursive relationship, we need to tell Django what the
relationships should be called. Set ``rel_name`` for this, and set
``related_name`` to designate what the reverse relationship is called.
"""

from django.core import meta

class Category(meta.Model):
    module_name = 'categories'
    fields = (
        meta.CharField('name', maxlength=20),
        meta.ForeignKey('self', null=True,
            rel_name='parent', related_name='child'),
    )

    def __repr__(self):
        return self.name

API_TESTS = """
# Create a few Category objects.
>>> r = categories.Category(id=None, name='Root category', parent_id=None)
>>> r.save()
>>> c = categories.Category(id=None, name='Child category', parent_id=r.id)
>>> c.save()

>>> r.get_child_list()
[Child category]
>>> r.get_child(name__startswith='Child')
Child category
>>> r.get_parent()
Traceback (most recent call last):
    ...
CategoryDoesNotExist

>>> c.get_child_list()
[]
>>> c.get_parent()
Root category
"""
