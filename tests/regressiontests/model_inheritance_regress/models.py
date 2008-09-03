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

class Supplier(models.Model):
    restaurant = models.ForeignKey(Restaurant)

class Parent(models.Model):
    created = models.DateTimeField(default=datetime.datetime.now)

class Child(Parent):
    name = models.CharField(max_length=10)

class SelfRefParent(models.Model):
    parent_data = models.IntegerField()
    self_data = models.ForeignKey('self', null=True)

class SelfRefChild(SelfRefParent):
    child_data = models.IntegerField()

class Article(models.Model):
    headline = models.CharField(max_length=100)
    pub_date = models.DateTimeField()
    class Meta:
        ordering = ('-pub_date', 'headline')

    def __unicode__(self):
        return self.headline

class ArticleWithAuthor(Article):
    author = models.CharField(max_length=100)

class M2MBase(models.Model):
    articles = models.ManyToManyField(Article)

class M2MChild(M2MBase):
    name = models.CharField(max_length=50)

class Evaluation(Article):
    quality = models.IntegerField()

    class Meta:
        abstract = True

class QualityControl(Evaluation):
    assignee = models.CharField(max_length=50)


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
>>> [sorted(d.items()) for d in dicts] == [[('name', u"Guido's House of Pasta"), ('serves_hot_dogs', True)]]
True

>>> dicts = ItalianRestaurant.objects.values('name','serves_hot_dogs','serves_gnocchi')
>>> [sorted(d.items()) for d in dicts] == [[('name', u"Guido's House of Pasta"), ('serves_gnocchi', True), ('serves_hot_dogs', True)]]
True

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
>>> [sorted(d.items()) for d in dicts] == [[('name', u"Guido's All New House of Pasta"), ('serves_hot_dogs', False)]]
True

>>> dicts = ItalianRestaurant.objects.values('name','serves_hot_dogs','serves_gnocchi')
>>> [sorted(d.items()) for d in dicts] == [[('name', u"Guido's All New House of Pasta"), ('serves_gnocchi', False), ('serves_hot_dogs', False)]]
True

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
>>> [sorted(d.items()) for d in dicts] == [[('name', u"Guido's All New House of Pasta"), ('serves_gnocchi', False), ('serves_hot_dogs', False)]]
True

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

# Regression test for #6755
>>> r = Restaurant(serves_pizza=False)
>>> r.save()
>>> r.id == r.place_ptr_id
True
>>> orig_id = r.id
>>> r = Restaurant(place_ptr_id=orig_id, serves_pizza=True)
>>> r.save()
>>> r.id == orig_id
True
>>> r.id == r.place_ptr_id
True

# Regression test for #7488. This looks a little crazy, but it's the equivalent
# of what the admin interface has to do for the edit-inline case.
>>> Supplier.objects.filter(restaurant=Restaurant(name='xx', address='yy'))
[]

# Regression test for #7853
# If the parent class has a self-referential link, make sure that any updates
# to that link via the child update the right table.

>>> obj = SelfRefChild.objects.create(child_data=37, parent_data=42)
>>> obj.delete()

# Regression tests for #8076 - get_(next/previous)_by_date should 
>>> c1 = ArticleWithAuthor(headline='ArticleWithAuthor 1', author="Person 1", pub_date=datetime.datetime(2005, 8, 1, 3, 0))
>>> c1.save()
>>> c2 = ArticleWithAuthor(headline='ArticleWithAuthor 2', author="Person 2", pub_date=datetime.datetime(2005, 8, 1, 10, 0))
>>> c2.save()
>>> c3 = ArticleWithAuthor(headline='ArticleWithAuthor 3', author="Person 3", pub_date=datetime.datetime(2005, 8, 2))
>>> c3.save()

>>> c1.get_next_by_pub_date()
<ArticleWithAuthor: ArticleWithAuthor 2>
>>> c2.get_next_by_pub_date()
<ArticleWithAuthor: ArticleWithAuthor 3>
>>> c3.get_next_by_pub_date()
Traceback (most recent call last):
    ...
DoesNotExist: ArticleWithAuthor matching query does not exist.
>>> c3.get_previous_by_pub_date()
<ArticleWithAuthor: ArticleWithAuthor 2>
>>> c2.get_previous_by_pub_date()
<ArticleWithAuthor: ArticleWithAuthor 1>
>>> c1.get_previous_by_pub_date()
Traceback (most recent call last):
    ...
DoesNotExist: ArticleWithAuthor matching query does not exist.

# Regression test for #8825: Make sure all inherited fields (esp. m2m fields, in
# this case) appear on the child class.
>>> M2MChild.objects.filter(articles__isnull=False)
[]

# All fields from an ABC, including those inherited non-abstractly should be
# available on child classes (#7588). Creating this instance should work
# without error.
>>> _ = QualityControl.objects.create(headline="Problems in Django", pub_date=datetime.datetime.now(), quality=10, assignee="adrian")

"""}
