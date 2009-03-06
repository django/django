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

class UndergroundBar(models.Model):
    place = models.OneToOneField(Place, null=True)
    serves_cocktails = models.BooleanField()

class Favorites(models.Model):
    name = models.CharField(max_length = 50)
    restaurants = models.ManyToManyField(Restaurant)

    def __unicode__(self):
        return u"Favorites for %s" % self.name

class Target(models.Model):
    pass

class Pointer(models.Model):
    other = models.OneToOneField(Target, primary_key=True)

class Pointer2(models.Model):
    other = models.OneToOneField(Target)

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

#
# Regression test for #6886 (the related-object cache)
#

# Look up the objects again so that we get "fresh" objects
>>> p = Place.objects.get(name="Demon Dogs")
>>> r = p.restaurant

# Accessing the related object again returns the exactly same object
>>> p.restaurant is r
True

# But if we kill the cache, we get a new object
>>> del p._restaurant_cache
>>> p.restaurant is r
False

# Reassigning the Restaurant object results in an immediate cache update
# We can't use a new Restaurant because that'll violate one-to-one, but
# with a new *instance* the is test below will fail if #6886 regresses.
>>> r2 = Restaurant.objects.get(pk=r.pk)
>>> p.restaurant = r2
>>> p.restaurant is r2
True

# Assigning None succeeds if field is null=True.
>>> ug_bar = UndergroundBar.objects.create(place=p, serves_cocktails=False)
>>> ug_bar.place = None
>>> ug_bar.place is None
True

# Assigning None fails: Place.restaurant is null=False
>>> p.restaurant = None
Traceback (most recent call last):
    ...
ValueError: Cannot assign None: "Place.restaurant" does not allow null values.

# You also can't assign an object of the wrong type here
>>> p.restaurant = p
Traceback (most recent call last):
    ...
ValueError: Cannot assign "<Place: Demon Dogs the place>": "Place.restaurant" must be a "Restaurant" instance.

# Creation using keyword argument should cache the related object.
>>> p = Place.objects.get(name="Demon Dogs")
>>> r = Restaurant(place=p)
>>> r.place is p
True

# Creation using keyword argument and unsaved related instance (#8070).
>>> p = Place()
>>> r = Restaurant(place=p)
>>> r.place is p
True

# Creation using attname keyword argument and an id will cause the related
# object to be fetched.
>>> p = Place.objects.get(name="Demon Dogs")
>>> r = Restaurant(place_id=p.id)
>>> r.place is p
False
>>> r.place == p
True

# Regression test for #9968: filtering reverse one-to-one relations with
# primary_key=True was misbehaving. We test both (primary_key=True & False)
# cases here to prevent any reappearance of the problem.
>>> _ = Target.objects.create()
>>> Target.objects.filter(pointer=None)
[<Target: Target object>]
>>> Target.objects.exclude(pointer=None)
[]
>>> Target.objects.filter(pointer2=None)
[<Target: Target object>]
>>> Target.objects.exclude(pointer2=None)
[]

"""}
