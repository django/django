"""
10. One-to-one relationships

To define a one-to-one relationship, use ``OneToOneField()``.

In this example, a ``Place`` optionally can be a ``Restaurant``.
"""

from django.db import models

class Place(models.Model):
    name = models.CharField(maxlength=50)
    address = models.CharField(maxlength=80)

    def __repr__(self):
        return "%s the place" % self.name

class Restaurant(models.Model):
    place = models.OneToOneField(Place)
    serves_hot_dogs = models.BooleanField()
    serves_pizza = models.BooleanField()

    def __repr__(self):
        return "%s the restaurant" % self.get_place().name

class Waiter(models.Model):
    restaurant = models.ForeignKey(Restaurant)
    name = models.CharField(maxlength=50)

    def __repr__(self):
        return "%s the waiter at %r" % (self.name, self.get_restaurant())

API_TESTS = """
# Create a couple of Places.
>>> p1 = Place(name='Demon Dogs', address='944 W. Fullerton')
>>> p1.save()
>>> p2 = Place(name='Ace Hardware', address='1013 N. Ashland')
>>> p2.save()

# Create a Restaurant. Pass the ID of the "parent" object as this object's ID.
>>> r = Restaurant(place=p1, serves_hot_dogs=True, serves_pizza=False)
>>> r.save()

# A Restaurant can access its place.
>>> r.get_place()
Demon Dogs the place

# A Place can access its restaurant, if available.
>>> p1.get_restaurant()
Demon Dogs the restaurant

# p2 doesn't have an associated restaurant.
>>> p2.get_restaurant()
Traceback (most recent call last):
    ...
DoesNotExist: Restaurant does not exist for {'place__id__exact': ...}

# Restaurant.objects.get_list() just returns the Restaurants, not the Places.
>>> Restaurant.objects.get_list()
[Demon Dogs the restaurant]

# Place.objects.get_list() returns all Places, regardless of whether they have
# Restaurants.
>>> Place.objects.get_list(order_by=['name'])
[Ace Hardware the place, Demon Dogs the place]

>>> Restaurant.objects.get_object(place__id__exact=1)
Demon Dogs the restaurant
>>> Restaurant.objects.get_object(pk=1)
Demon Dogs the restaurant
>>> Restaurant.objects.get_object(place__exact=1)
Demon Dogs the restaurant
>>> Restaurant.objects.get_object(place__pk=1)
Demon Dogs the restaurant
>>> Restaurant.objects.get_object(place__name__startswith="Demon")
Demon Dogs the restaurant

>>> Place.objects.get_object(id__exact=1)
Demon Dogs the place
>>> Place.objects.get_object(pk=1)
Demon Dogs the place
>>> Place.objects.get_object(restaurants__place__exact=1)
Demon Dogs the place
>>> Place.objects.get_object(restaurants__pk=1)
Demon Dogs the place

# Add a Waiter to the Restaurant.
>>> w = r.add_waiter(name='Joe')
>>> w.save()
>>> w
Joe the waiter at Demon Dogs the restaurant

# Query the waiters
>>> Waiter.objects.get_list(restaurant__place__exact=1)
[Joe the waiter at Demon Dogs the restaurant]
>>> Waiter.objects.get_list(restaurant__pk=1)
[Joe the waiter at Demon Dogs the restaurant]
>>> Waiter.objects.get_list(id__exact=1)
[Joe the waiter at Demon Dogs the restaurant]
>>> Waiter.objects.get_list(pk=1)
[Joe the waiter at Demon Dogs the restaurant]

# Delete the restaurant; the waiter should also be removed
>>> r = Restaurant.objects.get_object(pk=1)
>>> r.delete()
"""
