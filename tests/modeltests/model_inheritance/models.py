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

API_TESTS = """
# Make sure Restaurant has the right fields in the right order.
>>> [f.name for f in Restaurant._meta.fields]
['id', 'name', 'address', 'serves_hot_dogs', 'serves_pizza']

"""
