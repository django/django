"""
Various complex queries that have been problematic in the past.
"""

import threading

from django.db import models

class DumbCategory(models.Model):
    pass

class NamedCategory(DumbCategory):
    name = models.CharField(max_length=10)

class Tag(models.Model):
    name = models.CharField(max_length=10)
    parent = models.ForeignKey('self', blank=True, null=True,
            related_name='children')
    category = models.ForeignKey(NamedCategory, null=True, default=None)

    class Meta:
        ordering = ['name']

    def __unicode__(self):
        return self.name

class Note(models.Model):
    note = models.CharField(max_length=100)
    misc = models.CharField(max_length=10)

    class Meta:
        ordering = ['note']

    def __unicode__(self):
        return self.note

    def __init__(self, *args, **kwargs):
        super(Note, self).__init__(*args, **kwargs)
        # Regression for #13227 -- having an attribute that
        # is unpickleable doesn't stop you from cloning queries
        # that use objects of that type as an argument.
        self.lock = threading.Lock()

class Annotation(models.Model):
    name = models.CharField(max_length=10)
    tag = models.ForeignKey(Tag)
    notes = models.ManyToManyField(Note)

    def __unicode__(self):
        return self.name

class ExtraInfo(models.Model):
    info = models.CharField(max_length=100)
    note = models.ForeignKey(Note)

    class Meta:
        ordering = ['info']

    def __unicode__(self):
        return self.info

class Author(models.Model):
    name = models.CharField(max_length=10)
    num = models.IntegerField(unique=True)
    extra = models.ForeignKey(ExtraInfo)

    class Meta:
        ordering = ['name']

    def __unicode__(self):
        return self.name

class Item(models.Model):
    name = models.CharField(max_length=10)
    created = models.DateTimeField()
    modified = models.DateTimeField(blank=True, null=True)
    tags = models.ManyToManyField(Tag, blank=True, null=True)
    creator = models.ForeignKey(Author)
    note = models.ForeignKey(Note)

    class Meta:
        ordering = ['-note', 'name']

    def __unicode__(self):
        return self.name

class Report(models.Model):
    name = models.CharField(max_length=10)
    creator = models.ForeignKey(Author, to_field='num', null=True)

    def __unicode__(self):
        return self.name

class Ranking(models.Model):
    rank = models.IntegerField()
    author = models.ForeignKey(Author)

    class Meta:
        # A complex ordering specification. Should stress the system a bit.
        ordering = ('author__extra__note', 'author__name', 'rank')

    def __unicode__(self):
        return '%d: %s' % (self.rank, self.author.name)

class Cover(models.Model):
    title = models.CharField(max_length=50)
    item = models.ForeignKey(Item)

    class Meta:
        ordering = ['item']

    def __unicode__(self):
        return self.title

class Number(models.Model):
    num = models.IntegerField()

    def __unicode__(self):
        return unicode(self.num)

# Symmetrical m2m field with a normal field using the reverse accesor name
# ("valid").
class Valid(models.Model):
    valid = models.CharField(max_length=10)
    parent = models.ManyToManyField('self')

    class Meta:
        ordering = ['valid']

# Some funky cross-linked models for testing a couple of infinite recursion
# cases.
class X(models.Model):
    y = models.ForeignKey('Y')

class Y(models.Model):
    x1 = models.ForeignKey(X, related_name='y1')

# Some models with a cycle in the default ordering. This would be bad if we
# didn't catch the infinite loop.
class LoopX(models.Model):
    y = models.ForeignKey('LoopY')

    class Meta:
        ordering = ['y']

class LoopY(models.Model):
    x = models.ForeignKey(LoopX)

    class Meta:
        ordering = ['x']

class LoopZ(models.Model):
    z = models.ForeignKey('self')

    class Meta:
        ordering = ['z']

# A model and custom default manager combination.
class CustomManager(models.Manager):
    def get_query_set(self):
        qs = super(CustomManager, self).get_query_set()
        return qs.filter(public=True, tag__name='t1')

class ManagedModel(models.Model):
    data = models.CharField(max_length=10)
    tag = models.ForeignKey(Tag)
    public = models.BooleanField(default=True)

    objects = CustomManager()
    normal_manager = models.Manager()

    def __unicode__(self):
        return self.data

# An inter-related setup with multiple paths from Child to Detail.
class Detail(models.Model):
    data = models.CharField(max_length=10)

class MemberManager(models.Manager):
    def get_query_set(self):
        return super(MemberManager, self).get_query_set().select_related("details")

class Member(models.Model):
    name = models.CharField(max_length=10)
    details = models.OneToOneField(Detail, primary_key=True)

    objects = MemberManager()

class Child(models.Model):
    person = models.OneToOneField(Member, primary_key=True)
    parent = models.ForeignKey(Member, related_name="children")

# Custom primary keys interfered with ordering in the past.
class CustomPk(models.Model):
    name = models.CharField(max_length=10, primary_key=True)
    extra = models.CharField(max_length=10)

    class Meta:
        ordering = ['name', 'extra']

class Related(models.Model):
    custom = models.ForeignKey(CustomPk)

# An inter-related setup with a model subclass that has a nullable
# path to another model, and a return path from that model.

class Celebrity(models.Model):
    name = models.CharField("Name", max_length=20)
    greatest_fan = models.ForeignKey("Fan", null=True, unique=True)

class TvChef(Celebrity):
    pass

class Fan(models.Model):
    fan_of = models.ForeignKey(Celebrity)

# Multiple foreign keys
class LeafA(models.Model):
    data = models.CharField(max_length=10)

    def __unicode__(self):
        return self.data

class LeafB(models.Model):
    data = models.CharField(max_length=10)

class Join(models.Model):
    a = models.ForeignKey(LeafA)
    b = models.ForeignKey(LeafB)

class ReservedName(models.Model):
    name = models.CharField(max_length=20)
    order = models.IntegerField()

    def __unicode__(self):
        return self.name

# A simpler shared-foreign-key setup that can expose some problems.
class SharedConnection(models.Model):
    data = models.CharField(max_length=10)

class PointerA(models.Model):
    connection = models.ForeignKey(SharedConnection)

class PointerB(models.Model):
    connection = models.ForeignKey(SharedConnection)

# Multi-layer ordering
class SingleObject(models.Model):
    name = models.CharField(max_length=10)

    class Meta:
        ordering = ['name']

    def __unicode__(self):
        return self.name

class RelatedObject(models.Model):
    single = models.ForeignKey(SingleObject)

    class Meta:
        ordering = ['single']

class Plaything(models.Model):
    name = models.CharField(max_length=10)
    others = models.ForeignKey(RelatedObject, null=True)

    class Meta:
        ordering = ['others']

    def __unicode__(self):
        return self.name

class Article(models.Model):
    name = models.CharField(max_length=20)
    created = models.DateTimeField()

class Food(models.Model):
    name = models.CharField(max_length=20, unique=True)

    def __unicode__(self):
        return self.name

class Eaten(models.Model):
    food = models.ForeignKey(Food, to_field="name")
    meal = models.CharField(max_length=20)

    def __unicode__(self):
        return u"%s at %s" % (self.food, self.meal)

class Node(models.Model):
    num = models.IntegerField(unique=True)
    parent = models.ForeignKey("self", to_field="num", null=True)

    def __unicode__(self):
        return u"%s" % self.num

# Bug #12252
class ObjectA(models.Model):
    name = models.CharField(max_length=50)

    def __unicode__(self):
        return self.name

class ObjectB(models.Model):
    name = models.CharField(max_length=50)
    objecta = models.ForeignKey(ObjectA)
    number = models.PositiveSmallIntegerField()

    def __unicode__(self):
        return self.name

class ObjectC(models.Model):
    name = models.CharField(max_length=50)
    objecta = models.ForeignKey(ObjectA)
    objectb = models.ForeignKey(ObjectB)

    def __unicode__(self):
       return self.name
