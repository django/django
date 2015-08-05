"""
One-to-one relationships

To define a one-to-one relationship, use ``OneToOneField()``.

In this example, a ``Place`` optionally can be a ``Restaurant``.
"""
from __future__ import unicode_literals

from django.db import models
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class Place(models.Model):
    name = models.CharField(max_length=50)
    address = models.CharField(max_length=80)

    def __str__(self):
        return "%s the place" % self.name


@python_2_unicode_compatible
class Restaurant(models.Model):
    place = models.OneToOneField(Place, primary_key=True)
    serves_hot_dogs = models.BooleanField(default=False)
    serves_pizza = models.BooleanField(default=False)

    def __str__(self):
        return "%s the restaurant" % self.place.name


@python_2_unicode_compatible
class Bar(models.Model):
    place = models.OneToOneField(Place)
    serves_cocktails = models.BooleanField(default=True)

    def __str__(self):
        return "%s the bar" % self.place.name


class UndergroundBar(models.Model):
    place = models.OneToOneField(Place, null=True)
    serves_cocktails = models.BooleanField(default=True)


@python_2_unicode_compatible
class Waiter(models.Model):
    restaurant = models.ForeignKey(Restaurant)
    name = models.CharField(max_length=50)

    def __str__(self):
        return "%s the waiter at %s" % (self.name, self.restaurant)


@python_2_unicode_compatible
class Favorites(models.Model):
    name = models.CharField(max_length=50)
    restaurants = models.ManyToManyField(Restaurant)

    def __str__(self):
        return "Favorites for %s" % self.name


class ManualPrimaryKey(models.Model):
    primary_key = models.CharField(max_length=10, primary_key=True)
    name = models.CharField(max_length=50)


class RelatedModel(models.Model):
    link = models.OneToOneField(ManualPrimaryKey)
    name = models.CharField(max_length=50)


@python_2_unicode_compatible
class MultiModel(models.Model):
    link1 = models.OneToOneField(Place)
    link2 = models.OneToOneField(ManualPrimaryKey)
    name = models.CharField(max_length=50)

    def __str__(self):
        return "Multimodel %s" % self.name


class Target(models.Model):
    name = models.CharField(max_length=50)


class Pointer(models.Model):
    other = models.OneToOneField(Target, primary_key=True)


class Pointer2(models.Model):
    other = models.OneToOneField(Target, related_name='second_pointer')


class HiddenPointer(models.Model):
    target = models.OneToOneField(Target, related_name='hidden+')


# Test related objects visibility.
class SchoolManager(models.Manager):
    def get_queryset(self):
        return super(SchoolManager, self).get_queryset().filter(is_public=True)


class School(models.Model):
    is_public = models.BooleanField(default=False)
    objects = SchoolManager()


class DirectorManager(models.Manager):
    def get_queryset(self):
        return super(DirectorManager, self).get_queryset().filter(is_temp=False)


class Director(models.Model):
    is_temp = models.BooleanField(default=False)
    school = models.OneToOneField(School)
    objects = DirectorManager()
