"""
10. One-to-one relationships

To define a one-to-one relationship, use ``OneToOneField()``.

In this example, a ``Place`` optionally can be a ``Restaurant``.
"""

from django.db import models, transaction, IntegrityError

class Place(models.Model):
    name = models.CharField(max_length=50)
    address = models.CharField(max_length=80)

    def __unicode__(self):
        return u"%s the place" % self.name

class Restaurant(models.Model):
    place = models.OneToOneField(Place, primary_key=True)
    serves_hot_dogs = models.BooleanField()
    serves_pizza = models.BooleanField()

    def __unicode__(self):
        return u"%s the restaurant" % self.place.name

class Waiter(models.Model):
    restaurant = models.ForeignKey(Restaurant)
    name = models.CharField(max_length=50)

    def __unicode__(self):
        return u"%s the waiter at %s" % (self.name, self.restaurant)

class ManualPrimaryKey(models.Model):
    primary_key = models.CharField(max_length=10, primary_key=True)
    name = models.CharField(max_length = 50)

class RelatedModel(models.Model):
    link = models.OneToOneField(ManualPrimaryKey)
    name = models.CharField(max_length = 50)

class MultiModel(models.Model):
    link1 = models.OneToOneField(Place)
    link2 = models.OneToOneField(ManualPrimaryKey)
    name = models.CharField(max_length=50)

    def __unicode__(self):
        return u"Multimodel %s" % self.name
