"""
Regression tests for a few ForeignKey bugs.
"""
from __future__ import unicode_literals

from django.db import models
from django.utils.encoding import python_2_unicode_compatible

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
@python_2_unicode_compatible
class Category(models.Model):
    name = models.CharField(max_length=20)

    def __str__(self):
        return self.name

class Record(models.Model):
    category = models.ForeignKey(Category)

@python_2_unicode_compatible
class Relation(models.Model):
    left = models.ForeignKey(Record, related_name='left_set')
    right = models.ForeignKey(Record, related_name='right_set')

    def __str__(self):
        return "%s - %s" % (self.left.category.name, self.right.category.name)

class Car(models.Model):
    make = models.CharField(max_length=100, null=True, unique=True)

class Driver(models.Model):
    car = models.ForeignKey(Car, to_field='make', null=True, related_name='drivers')
