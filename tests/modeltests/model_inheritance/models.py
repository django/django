"""
XX. Model inheritance

"""

from django.db import models

class Place(models.Model):
    name = models.CharField(maxlength=50)
    address = models.CharField(maxlength=80)

    def __repr__(self):
        return "%s the place" % self.name

class Restaurant(Place):
    serves_hot_dogs = models.BooleanField()
    serves_pizza = models.BooleanField()

    def __repr__(self):
        return "%s the restaurant" % self.name

class ItalianRestaurant(Restaurant):
    serves_gnocchi = models.BooleanField()

    def __repr__(self):
        return "%s the italian restaurant" % self.name

API_TESTS = """
# Make sure Restaurant has the right fields in the right order.
>>> [f.name for f in Restaurant._meta.fields]
['id', 'name', 'address', 'serves_hot_dogs', 'serves_pizza']

# Make sure ItalianRestaurant has the right fields in the right order.
>>> [f.name for f in ItalianRestaurant._meta.fields]
['id', 'name', 'address', 'serves_hot_dogs', 'serves_pizza', 'serves_gnocchi']

# Create a couple of Places.
>>> p1 = Place(name='Master Shakes', address='666 W. Jersey')
>>> p1.save()
>>> p2 = Place(name='Ace Hardware', address='1013 N. Ashland')
>>> p2.save()

# Test constructor for Restaurant.
>>> r = Restaurant(name='Demon Dogs', address='944 W. Fullerton', serves_hot_dogs=True, serves_pizza=False)
>>> r.save()

# Test the constructor for ItalianRestaurant.
>>> ir = ItalianRestaurant(name='Ristorante Miron', address='1234 W. Elm', serves_hot_dogs=False, serves_pizza=False, serves_gnocchi=True)
>>> ir.save()


"""
