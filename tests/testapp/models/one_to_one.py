"""
10. One-to-one relationships

To define a many-to-one relationship, use ``OneToOneField()``.

In this example, a ``Place`` optionally can be a ``Restaurant``.
"""

from django.core import meta

class Place(meta.Model):
    fields = (
        meta.CharField('name', maxlength=50),
        meta.CharField('address', maxlength=80),
    )

    def __repr__(self):
        return "%s the place" % self.name

class Restaurant(meta.Model):
    fields = (
        meta.OneToOneField(Place),
        meta.BooleanField('serves_hot_dogs'),
        meta.BooleanField('serves_pizza'),
    )

    def __repr__(self):
        return "%s the restaurant" % self.get_place().name

API_TESTS = """
# Create a couple of Places.
>>> p1 = places.Place(id=None, name='Demon Dogs', address='944 W. Fullerton')
>>> p1.save()
>>> p2 = places.Place(id=None, name='Ace Hardware', address='1013 N. Ashland')
>>> p2.save()

# Create a Restaurant. Pass the ID of the "parent" object as this object's ID.
>>> r = restaurants.Restaurant(id=p1.id, serves_hot_dogs=True, serves_pizza=False)
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
RestaurantDoesNotExist: Restaurant does not exist for {'id__exact': 2L}

# restaurants.get_list() just returns the Restaurants, not the Places.
>>> restaurants.get_list()
[Demon Dogs the restaurant]

# places.get_list() returns all Places, regardless of whether they have
# Restaurants.
>>> places.get_list(order_by=['name'])
[Ace Hardware the place, Demon Dogs the place]
"""
