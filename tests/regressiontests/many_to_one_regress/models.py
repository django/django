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


# Multiple paths to the same model (#7110, #7125)
class Category(models.Model):
    name = models.CharField(max_length=20)

    def __unicode__(self):
        return self.name

class Record(models.Model):
    category = models.ForeignKey(Category)

class Relation(models.Model):
    left = models.ForeignKey(Record, related_name='left_set')
    right = models.ForeignKey(Record, related_name='right_set')

    def __unicode__(self):
        return u"%s - %s" % (self.left.category.name, self.right.category.name)


__test__ = {'API_TESTS':"""
>>> Third.objects.create(id='3', name='An example')
<Third: Third object>
>>> parent = Parent(name = 'fred')
>>> parent.save()
>>> Child.objects.create(name='bam-bam', parent=parent)
<Child: Child object>

#
# Tests of ForeignKey assignment and the related-object cache (see #6886).
#
>>> p = Parent.objects.create(name="Parent")
>>> c = Child.objects.create(name="Child", parent=p)

# Look up the object again so that we get a "fresh" object.
>>> c = Child.objects.get(name="Child")
>>> p = c.parent

# Accessing the related object again returns the exactly same object.
>>> c.parent is p
True

# But if we kill the cache, we get a new object.
>>> del c._parent_cache
>>> c.parent is p
False

# Assigning a new object results in that object getting cached immediately.
>>> p2 = Parent.objects.create(name="Parent 2")
>>> c.parent = p2
>>> c.parent is p2
True

# Assigning None succeeds if field is null=True.
>>> p.bestchild = None
>>> p.bestchild is None
True

# Assigning None fails: Child.parent is null=False.
>>> c.parent = None
Traceback (most recent call last):
    ...
ValueError: Cannot assign None: "Child.parent" does not allow null values.

# You also can't assign an object of the wrong type here
>>> c.parent = First(id=1, second=1)
Traceback (most recent call last):
    ...
ValueError: Cannot assign "<First: First object>": "Child.parent" must be a "Parent" instance.

# Creation using keyword argument should cache the related object.
>>> p = Parent.objects.get(name="Parent")
>>> c = Child(parent=p)
>>> c.parent is p
True

# Creation using keyword argument and unsaved related instance (#8070).
>>> p = Parent()
>>> c = Child(parent=p)
>>> c.parent is p
True

# Creation using attname keyword argument and an id will cause the related
# object to be fetched.
>>> p = Parent.objects.get(name="Parent")
>>> c = Child(parent_id=p.id)
>>> c.parent is p
False
>>> c.parent == p
True


#
# Test of multiple ForeignKeys to the same model (bug #7125).
#
>>> c1 = Category.objects.create(name='First')
>>> c2 = Category.objects.create(name='Second')
>>> c3 = Category.objects.create(name='Third')
>>> r1 = Record.objects.create(category=c1)
>>> r2 = Record.objects.create(category=c1)
>>> r3 = Record.objects.create(category=c2)
>>> r4 = Record.objects.create(category=c2)
>>> r5 = Record.objects.create(category=c3)
>>> r = Relation.objects.create(left=r1, right=r2)
>>> r = Relation.objects.create(left=r3, right=r4)
>>> r = Relation.objects.create(left=r1, right=r3)
>>> r = Relation.objects.create(left=r5, right=r2)
>>> r = Relation.objects.create(left=r3, right=r2)

>>> Relation.objects.filter(left__category__name__in=['First'], right__category__name__in=['Second'])
[<Relation: First - Second>]

>>> Category.objects.filter(record__left_set__right__category__name='Second').order_by('name')
[<Category: First>, <Category: Second>]

"""}
