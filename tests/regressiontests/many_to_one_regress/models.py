"""
Regression tests for a few FK bugs: #1578, #6886
"""

from django.db import models

# If ticket #1578 ever slips back in, these models will not be able to be
# created (the field names being lower-cased versions of their opposite
# classes is important here).

class First(models.Model):
    second = models.IntegerField()

class Second(models.Model):
    first = models.ForeignKey(First, related_name = 'the_first')

# Protect against repetition of #1839, #2415 and #2536.
class Third(models.Model):
    name = models.CharField(max_length=20)
    third = models.ForeignKey('self', null=True, related_name='child_set')

class Parent(models.Model):
    name = models.CharField(max_length=20)
    bestchild = models.ForeignKey('Child', null=True, related_name='favored_by')

class Child(models.Model):
    name = models.CharField(max_length=20)
    parent = models.ForeignKey(Parent)


__test__ = {'API_TESTS':"""
>>> Third.objects.create(id='3', name='An example')
<Third: Third object>
>>> parent = Parent(name = 'fred')
>>> parent.save()
>>> Child.objects.create(name='bam-bam', parent=parent)
<Child: Child object>

#
# Tests of ForeignKey assignment and the related-object cache (see #6886)
#
>>> p = Parent.objects.create(name="Parent")
>>> c = Child.objects.create(name="Child", parent=p)

# Look up the object again so that we get a "fresh" object
>>> c = Child.objects.get(name="Child")
>>> p = c.parent

# Accessing the related object again returns the exactly same object
>>> c.parent is p
True

# But if we kill the cache, we get a new object
>>> del c._parent_cache
>>> c.parent is p
False

# Assigning a new object results in that object getting cached immediately
>>> p2 = Parent.objects.create(name="Parent 2")
>>> c.parent = p2
>>> c.parent is p2
True

# Assigning None fails: Child.parent is null=False
>>> c.parent = None
Traceback (most recent call last):
    ...
ValueError: Cannot assign None: "Child.parent" does not allow null values.

# You also can't assign an object of the wrong type here
>>> c.parent = First(id=1, second=1)
Traceback (most recent call last):
    ...
ValueError: Cannot assign "<First: First object>": "Child.parent" must be a "Parent" instance.

"""}
