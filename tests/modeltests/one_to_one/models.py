"""
10. One-to-one relationships

To define a one-to-one relationship, use ``OneToOneField()``.

In this example, a ``Place`` optionally can be a ``Restaurant``.
"""

from django.db import models

class Place(models.Model):
    name = models.CharField(maxlength=50)
    address = models.CharField(maxlength=80)

    def __str__(self):
        return "%s the place" % self.name

class Restaurant(models.Model):
    place = models.OneToOneField(Place)
    serves_hot_dogs = models.BooleanField()
    serves_pizza = models.BooleanField()

    def __str__(self):
        return "%s the restaurant" % self.place.name

class Waiter(models.Model):
    restaurant = models.ForeignKey(Restaurant)
    name = models.CharField(maxlength=50)

    def __str__(self):
        return "%s the waiter at %s" % (self.name, self.restaurant)

class ManualPrimaryKey(models.Model):
    primary_key = models.CharField(maxlength=10, primary_key=True)
    name = models.CharField(maxlength = 50)

class RelatedModel(models.Model):
    link = models.OneToOneField(ManualPrimaryKey)
    name = models.CharField(maxlength = 50)

__test__ = {'API_TESTS':"""
# Create a couple of Places.
>>> p1 = Place(name='Demon Dogs', address='944 W. Fullerton')
>>> p1.save()
>>> p2 = Place(name='Ace Hardware', address='1013 N. Ashland')
>>> p2.save()

# Create a Restaurant. Pass the ID of the "parent" object as this object's ID.
>>> r = Restaurant(place=p1, serves_hot_dogs=True, serves_pizza=False)
>>> r.save()

# A Restaurant can access its place.
>>> r.place
<Place: Demon Dogs the place>

# A Place can access its restaurant, if available.
>>> p1.restaurant
<Restaurant: Demon Dogs the restaurant>

# p2 doesn't have an associated restaurant.
>>> p2.restaurant
Traceback (most recent call last):
    ...
DoesNotExist: Restaurant matching query does not exist.

# Set the place using assignment notation. Because place is the primary key on Restaurant,
# the save will create a new restaurant
>>> r.place = p2
>>> r.save()
>>> p2.restaurant
<Restaurant: Ace Hardware the restaurant>
>>> r.place
<Place: Ace Hardware the place>

# Set the place back again, using assignment in the reverse direction
# Need to reget restaurant object first, because the reverse set
# can't update the existing restaurant instance
>>> p1.restaurant = r
>>> r.save()
>>> p1.restaurant
<Restaurant: Demon Dogs the restaurant>

>>> r = Restaurant.objects.get(pk=1)
>>> r.place
<Place: Demon Dogs the place>

# Restaurant.objects.all() just returns the Restaurants, not the Places.
# Note that there are two restaurants - Ace Hardware the Restaurant was created
# in the call to r.place = p2. This means there are multiple restaurants referencing
# a single place...
>>> Restaurant.objects.all()
[<Restaurant: Demon Dogs the restaurant>, <Restaurant: Ace Hardware the restaurant>]

# Place.objects.all() returns all Places, regardless of whether they have
# Restaurants.
>>> Place.objects.order_by('name')
[<Place: Ace Hardware the place>, <Place: Demon Dogs the place>]

>>> Restaurant.objects.get(place__id__exact=1)
<Restaurant: Demon Dogs the restaurant>
>>> Restaurant.objects.get(pk=1)
<Restaurant: Demon Dogs the restaurant>
>>> Restaurant.objects.get(place__exact=1)
<Restaurant: Demon Dogs the restaurant>
>>> Restaurant.objects.get(place__exact=p1)
<Restaurant: Demon Dogs the restaurant>
>>> Restaurant.objects.get(place=1)
<Restaurant: Demon Dogs the restaurant>
>>> Restaurant.objects.get(place=p1)
<Restaurant: Demon Dogs the restaurant>
>>> Restaurant.objects.get(place__pk=1)
<Restaurant: Demon Dogs the restaurant>
>>> Restaurant.objects.get(place__name__startswith="Demon")
<Restaurant: Demon Dogs the restaurant>

>>> Place.objects.get(id__exact=1)
<Place: Demon Dogs the place>
>>> Place.objects.get(pk=1)
<Place: Demon Dogs the place>
>>> Place.objects.get(restaurant__place__exact=1)
<Place: Demon Dogs the place>
>>> Place.objects.get(restaurant__place__exact=p1)
<Place: Demon Dogs the place>
>>> Place.objects.get(restaurant__pk=1)
<Place: Demon Dogs the place>
>>> Place.objects.get(restaurant=1)
<Place: Demon Dogs the place>
>>> Place.objects.get(restaurant=r)
<Place: Demon Dogs the place>
>>> Place.objects.get(restaurant__exact=1)
<Place: Demon Dogs the place>
>>> Place.objects.get(restaurant__exact=r)
<Place: Demon Dogs the place>

# Add a Waiter to the Restaurant.
>>> w = r.waiter_set.create(name='Joe')
>>> w.save()
>>> w
<Waiter: Joe the waiter at Demon Dogs the restaurant>

# Query the waiters
>>> Waiter.objects.filter(restaurant__place__pk=1)
[<Waiter: Joe the waiter at Demon Dogs the restaurant>]
>>> Waiter.objects.filter(restaurant__place__exact=1)
[<Waiter: Joe the waiter at Demon Dogs the restaurant>]
>>> Waiter.objects.filter(restaurant__place__exact=p1)
[<Waiter: Joe the waiter at Demon Dogs the restaurant>]
>>> Waiter.objects.filter(restaurant__pk=1)
[<Waiter: Joe the waiter at Demon Dogs the restaurant>]
>>> Waiter.objects.filter(id__exact=1)
[<Waiter: Joe the waiter at Demon Dogs the restaurant>]
>>> Waiter.objects.filter(pk=1)
[<Waiter: Joe the waiter at Demon Dogs the restaurant>]
>>> Waiter.objects.filter(restaurant=1)
[<Waiter: Joe the waiter at Demon Dogs the restaurant>]
>>> Waiter.objects.filter(restaurant=r)
[<Waiter: Joe the waiter at Demon Dogs the restaurant>]

# Delete the restaurant; the waiter should also be removed
>>> r = Restaurant.objects.get(pk=1)
>>> r.delete()

# One-to-one fields still work if you create your own primary key
>>> o1 = ManualPrimaryKey(primary_key="abc123", name="primary")
>>> o1.save()
>>> o2 = RelatedModel(link=o1, name="secondary")
>>> o2.save()
"""}
