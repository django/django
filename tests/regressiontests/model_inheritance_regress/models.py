"""
Regression tests for Model inheritance behaviour.
"""

import datetime

from django.db import models

# Python 2.3 doesn't have sorted()
try:
    sorted
except NameError:
    from django.utils.itercompat import sorted

class Place(models.Model):
    name = models.CharField(max_length=50)
    address = models.CharField(max_length=80)

    class Meta:
        ordering = ('name',)

    def __unicode__(self):
        return u"%s the place" % self.name

class Restaurant(Place):
    serves_hot_dogs = models.BooleanField()
    serves_pizza = models.BooleanField()

    def __unicode__(self):
        return u"%s the restaurant" % self.name

class ItalianRestaurant(Restaurant):
    serves_gnocchi = models.BooleanField()

    def __unicode__(self):
        return u"%s the italian restaurant" % self.name

class ParkingLot(Place):
    # An explicit link to the parent (we can control the attribute name).
    parent = models.OneToOneField(Place, primary_key=True, parent_link=True)
    capacity = models.IntegerField()

    def __unicode__(self):
        return u"%s the parking lot" % self.name

class Parent(models.Model):
    created = models.DateTimeField(default=datetime.datetime.now)

class Child(Parent):
    name = models.CharField(max_length=10)

__test__ = {'API_TESTS':"""
# Regression for #7350, #7202
# Check that when you create a Parent object with a specific reference to an
# existent child instance, saving the Parent doesn't duplicate the child. This
# behaviour is only activated during a raw save - it is mostly relevant to
# deserialization, but any sort of CORBA style 'narrow()' API would require a
# similar approach.

# Create a child-parent-grandparent chain
>>> place1 = Place(name="Guido's House of Pasta", address='944 W. Fullerton')
>>> place1.save_base(raw=True)
>>> restaurant = Restaurant(place_ptr=place1, serves_hot_dogs=True, serves_pizza=False)
>>> restaurant.save_base(raw=True)
>>> italian_restaurant = ItalianRestaurant(restaurant_ptr=restaurant, serves_gnocchi=True)
>>> italian_restaurant.save_base(raw=True)

# Create a child-parent chain with an explicit parent link
>>> place2 = Place(name='Main St', address='111 Main St')
>>> place2.save_base(raw=True)
>>> park = ParkingLot(parent=place2, capacity=100)
>>> park.save_base(raw=True)

# Check that no extra parent objects have been created.
>>> Place.objects.all()
[<Place: Guido's House of Pasta the place>, <Place: Main St the place>]

>>> dicts = Restaurant.objects.values('name','serves_hot_dogs')
>>> [sorted(d.items()) for d in dicts]
[[('name', u"Guido's House of Pasta"), ('serves_hot_dogs', True)]]

>>> dicts = ItalianRestaurant.objects.values('name','serves_hot_dogs','serves_gnocchi')
>>> [sorted(d.items()) for d in dicts]
[[('name', u"Guido's House of Pasta"), ('serves_gnocchi', True), ('serves_hot_dogs', True)]]

>>> dicts = ParkingLot.objects.values('name','capacity')
>>> [sorted(d.items()) for d in dicts]
[[('capacity', 100), ('name', u'Main St')]]

# You can also update objects when using a raw save.
>>> place1.name = "Guido's All New House of Pasta"
>>> place1.save_base(raw=True)

>>> restaurant.serves_hot_dogs = False
>>> restaurant.save_base(raw=True)

>>> italian_restaurant.serves_gnocchi = False
>>> italian_restaurant.save_base(raw=True)

>>> place2.name='Derelict lot'
>>> place2.save_base(raw=True)

>>> park.capacity = 50
>>> park.save_base(raw=True)

# No extra parent objects after an update, either.
>>> Place.objects.all()
[<Place: Derelict lot the place>, <Place: Guido's All New House of Pasta the place>]

>>> dicts = Restaurant.objects.values('name','serves_hot_dogs')
>>> [sorted(d.items()) for d in dicts]
[[('name', u"Guido's All New House of Pasta"), ('serves_hot_dogs', False)]]

>>> dicts = ItalianRestaurant.objects.values('name','serves_hot_dogs','serves_gnocchi')
>>> [sorted(d.items()) for d in dicts]
[[('name', u"Guido's All New House of Pasta"), ('serves_gnocchi', False), ('serves_hot_dogs', False)]]

>>> dicts = ParkingLot.objects.values('name','capacity')
>>> [sorted(d.items()) for d in dicts]
[[('capacity', 50), ('name', u'Derelict lot')]]

# If you try to raw_save a parent attribute onto a child object,
# the attribute will be ignored.

>>> italian_restaurant.name = "Lorenzo's Pasta Hut"
>>> italian_restaurant.save_base(raw=True)

# Note that the name has not changed
# - name is an attribute of Place, not ItalianRestaurant
>>> dicts = ItalianRestaurant.objects.values('name','serves_hot_dogs','serves_gnocchi')
>>> [sorted(d.items()) for d in dicts]
[[('name', u"Guido's All New House of Pasta"), ('serves_gnocchi', False), ('serves_hot_dogs', False)]]

# Regressions tests for #7105: dates() queries should be able to use fields
# from the parent model as easily as the child.
>>> obj = Child.objects.create(name='child', created=datetime.datetime(2008, 6, 26, 17, 0, 0))
>>> Child.objects.dates('created', 'month')
[datetime.datetime(2008, 6, 1, 0, 0)]

# Regression test for #7276: calling delete() on a model with multi-table
# inheritance should delete the associated rows from any ancestor tables, as
# well as any descendent objects.

>>> ident = ItalianRestaurant.objects.all()[0].id
>>> Place.objects.get(pk=ident)
<Place: Guido's All New House of Pasta the place>
>>> xx = Restaurant.objects.create(name='a', address='xx', serves_hot_dogs=True, serves_pizza=False)

# This should delete both Restuarants, plus the related places, plus the ItalianRestaurant.
>>> Restaurant.objects.all().delete()

>>> Place.objects.get(pk=ident)
Traceback (most recent call last):
...
DoesNotExist: Place matching query does not exist.

>>> ItalianRestaurant.objects.get(pk=ident)
Traceback (most recent call last):
...
DoesNotExist: ItalianRestaurant matching query does not exist.

"""}
