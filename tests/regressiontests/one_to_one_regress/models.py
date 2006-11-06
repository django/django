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

class Favorites(models.Model):
    name = models.CharField(maxlength = 50)
    restaurants = models.ManyToManyField(Restaurant)

    def __str__(self):
        return "Favorites for %s" % self.name

__test__ = {'API_TESTS':"""
# Regression test for #1064 and #1506: Check that we create models via the m2m
# relation if the remote model has a OneToOneField.
>>> p1 = Place(name='Demon Dogs', address='944 W. Fullerton')
>>> p1.save()
>>> r = Restaurant(place=p1, serves_hot_dogs=True, serves_pizza=False)
>>> r.save()
>>> f = Favorites(name = 'Fred')
>>> f.save()
>>> f.restaurants = [r]
>>> f.restaurants.all()
[<Restaurant: Demon Dogs the restaurant>]
"""}
