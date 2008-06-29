"""
Regression tests for the interaction between model inheritance and
select_related().
"""

from django.db import models

class Place(models.Model):
    name = models.CharField(max_length=50)

    class Meta:
        ordering = ('name',)

    def __unicode__(self):
        return u"%s the place" % self.name

class Restaurant(Place):
    serves_sushi = models.BooleanField()
    serves_steak = models.BooleanField()

    def __unicode__(self):
        return u"%s the restaurant" % self.name

class Person(models.Model):
    name = models.CharField(max_length=50)
    favorite_restaurant = models.ForeignKey(Restaurant)

    def __unicode__(self):
        return self.name

__test__ = {'API_TESTS':"""
Regression test for #7246

>>> r1 = Restaurant.objects.create(name="Nobu", serves_sushi=True, serves_steak=False)
>>> r2 = Restaurant.objects.create(name="Craft", serves_sushi=False, serves_steak=True)
>>> p1 = Person.objects.create(name="John", favorite_restaurant=r1)
>>> p2 = Person.objects.create(name="Jane", favorite_restaurant=r2)

>>> Person.objects.order_by('name').select_related()
[<Person: Jane>, <Person: John>]

>>> jane = Person.objects.order_by('name').select_related('favorite_restaurant')[0]
>>> jane.favorite_restaurant.name
u'Craft'

"""}

