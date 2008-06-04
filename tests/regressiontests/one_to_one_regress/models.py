from django.db import models

class Place(models.Model):
    name = models.CharField(max_length=50)
    address = models.CharField(max_length=80)

    def __unicode__(self):
        return u"%s the place" % self.name

class Restaurant(models.Model):
    place = models.OneToOneField(Place)
    serves_hot_dogs = models.BooleanField()
    serves_pizza = models.BooleanField()

    def __unicode__(self):
        return u"%s the restaurant" % self.place.name

class Bar(models.Model):
    place = models.OneToOneField(Place)
    serves_cocktails = models.BooleanField()

    def __unicode__(self):
        return u"%s the bar" % self.place.name

class Favorites(models.Model):
    name = models.CharField(max_length = 50)
    restaurants = models.ManyToManyField(Restaurant)

    def __unicode__(self):
        return u"Favorites for %s" % self.name

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

# Regression test for #7173: Check that the name of the cache for the 
# reverse object is correct.
>>> b = Bar(place=p1, serves_cocktails=False)
>>> b.save()
>>> p1.restaurant
<Restaurant: Demon Dogs the restaurant>
>>> p1.bar
<Bar: Demon Dogs the bar>
"""}
