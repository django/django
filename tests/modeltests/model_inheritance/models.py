"""
XX. Model inheritance

Model inheritance exists in two varieties:
    - abstract base classes which are a way of specifying common
      information inherited by the subclasses. They don't exist as a separate
      model.
    - non-abstract base classes (the default), which are models in their own
      right with their own database tables and everything. Their subclasses
      have references back to them, created automatically.

Both styles are demonstrated here.
"""

from django.db import models

#
# Abstract base classes
#

class CommonInfo(models.Model):
    name = models.CharField(max_length=50)
    age = models.PositiveIntegerField()

    class Meta:
        abstract = True
        ordering = ['name']

    def __unicode__(self):
        return u'%s %s' % (self.__class__.__name__, self.name)

class Worker(CommonInfo):
    job = models.CharField(max_length=50)

class Student(CommonInfo):
    school_class = models.CharField(max_length=10)

    class Meta:
        pass

#
# Abstract base classes with related models
#

class Post(models.Model):
    title = models.CharField(max_length=50)

class Attachment(models.Model):
    post = models.ForeignKey(Post, related_name='attached_%(class)s_set')
    content = models.TextField()

    class Meta:
        abstract = True

    def __unicode__(self):
        return self.content

class Comment(Attachment):
    is_spam = models.BooleanField()

class Link(Attachment):
    url = models.URLField()

#
# Multi-table inheritance
#

class Chef(models.Model):
    name = models.CharField(max_length=50)

    def __unicode__(self):
        return u"%s the chef" % self.name

class Place(models.Model):
    name = models.CharField(max_length=50)
    address = models.CharField(max_length=80)

    def __unicode__(self):
        return u"%s the place" % self.name

class Rating(models.Model):
    rating = models.IntegerField(null=True, blank=True)

    class Meta:
        abstract = True
        ordering = ['-rating']

class Restaurant(Place, Rating):
    serves_hot_dogs = models.BooleanField()
    serves_pizza = models.BooleanField()
    chef = models.ForeignKey(Chef, null=True, blank=True)

    class Meta(Rating.Meta):
        db_table = 'my_restaurant'

    def __unicode__(self):
        return u"%s the restaurant" % self.name

class ItalianRestaurant(Restaurant):
    serves_gnocchi = models.BooleanField()

    def __unicode__(self):
        return u"%s the italian restaurant" % self.name

class Supplier(Place):
    customers = models.ManyToManyField(Restaurant, related_name='provider')

    def __unicode__(self):
        return u"%s the supplier" % self.name

class ParkingLot(Place):
    # An explicit link to the parent (we can control the attribute name).
    parent = models.OneToOneField(Place, primary_key=True, parent_link=True)
    main_site = models.ForeignKey(Place, related_name='lot')

    def __unicode__(self):
        return u"%s the parking lot" % self.name

__test__ = {'API_TESTS':"""
# The Student and Worker models both have 'name' and 'age' fields on them and
# inherit the __unicode__() method, just as with normal Python subclassing.
# This is useful if you want to factor out common information for programming
# purposes, but still completely independent separate models at the database
# level.

>>> w = Worker(name='Fred', age=35, job='Quarry worker')
>>> w.save()
>>> w2 = Worker(name='Barney', age=34, job='Quarry worker')
>>> w2.save()
>>> s = Student(name='Pebbles', age=5, school_class='1B')
>>> s.save()
>>> unicode(w)
u'Worker Fred'
>>> unicode(s)
u'Student Pebbles'

# The children inherit the Meta class of their parents (if they don't specify
# their own).
>>> Worker.objects.values('name')
[{'name': u'Barney'}, {'name': u'Fred'}]

# Since Student does not subclass CommonInfo's Meta, it has the effect of
# completely overriding it. So ordering by name doesn't take place for Students.
>>> Student._meta.ordering
[]

# However, the CommonInfo class cannot be used as a normal model (it doesn't
# exist as a model).
>>> CommonInfo.objects.all()
Traceback (most recent call last):
    ...
AttributeError: type object 'CommonInfo' has no attribute 'objects'

# Create a Post
>>> post = Post(title='Lorem Ipsum')
>>> post.save()

# The Post model has distinct accessors for the Comment and Link models.
>>> post.attached_comment_set.create(content='Save $ on V1agr@', is_spam=True)
<Comment: Save $ on V1agr@>
>>> post.attached_link_set.create(content='The Web framework for perfectionists with deadlines.', url='http://www.djangoproject.com/')
<Link: The Web framework for perfectionists with deadlines.>

# The Post model doesn't have an attribute called 'attached_%(class)s_set'.
>>> getattr(post, 'attached_%(class)s_set')
Traceback (most recent call last):
    ...
AttributeError: 'Post' object has no attribute 'attached_%(class)s_set'

# The Place/Restaurant/ItalianRestaurant models all exist as independent
# models. However, the subclasses also have transparent access to the fields of
# their ancestors.

# Create a couple of Places.
>>> p1 = Place(name='Master Shakes', address='666 W. Jersey')
>>> p1.save()
>>> p2 = Place(name='Ace Hardware', address='1013 N. Ashland')
>>> p2.save()

Test constructor for Restaurant.
>>> r = Restaurant(name='Demon Dogs', address='944 W. Fullerton',serves_hot_dogs=True, serves_pizza=False, rating=2)
>>> r.save()

# Test the constructor for ItalianRestaurant.
>>> c = Chef(name="Albert")
>>> c.save()
>>> ir = ItalianRestaurant(name='Ristorante Miron', address='1234 W. Ash', serves_hot_dogs=False, serves_pizza=False, serves_gnocchi=True, rating=4, chef=c)
>>> ir.save()
>>> ItalianRestaurant.objects.filter(address='1234 W. Ash')
[<ItalianRestaurant: Ristorante Miron the italian restaurant>]

>>> ir.address = '1234 W. Elm'
>>> ir.save()
>>> ItalianRestaurant.objects.filter(address='1234 W. Elm')
[<ItalianRestaurant: Ristorante Miron the italian restaurant>]

# Make sure Restaurant and ItalianRestaurant have the right fields in the right
# order.
>>> [f.name for f in Restaurant._meta.fields]
['id', 'name', 'address', 'place_ptr', 'rating', 'serves_hot_dogs', 'serves_pizza', 'chef']
>>> [f.name for f in ItalianRestaurant._meta.fields]
['id', 'name', 'address', 'place_ptr', 'rating', 'serves_hot_dogs', 'serves_pizza', 'chef', 'restaurant_ptr', 'serves_gnocchi']
>>> Restaurant._meta.ordering
['-rating']

# Even though p.supplier for a Place 'p' (a parent of a Supplier), a Restaurant
# object cannot access that reverse relation, since it's not part of the
# Place-Supplier Hierarchy.
>>> Place.objects.filter(supplier__name='foo')
[]
>>> Restaurant.objects.filter(supplier__name='foo')
Traceback (most recent call last):
    ...
FieldError: Cannot resolve keyword 'supplier' into field. Choices are: address, chef, id, italianrestaurant, lot, name, place_ptr, provider, rating, serves_hot_dogs, serves_pizza

# Parent fields can be used directly in filters on the child model.
>>> Restaurant.objects.filter(name='Demon Dogs')
[<Restaurant: Demon Dogs the restaurant>]
>>> ItalianRestaurant.objects.filter(address='1234 W. Elm')
[<ItalianRestaurant: Ristorante Miron the italian restaurant>]

# Filters against the parent model return objects of the parent's type.
>>> Place.objects.filter(name='Demon Dogs')
[<Place: Demon Dogs the place>]

# Since the parent and child are linked by an automatically created
# OneToOneField, you can get from the parent to the child by using the child's
# name.
>>> place = Place.objects.get(name='Demon Dogs')
>>> place.restaurant
<Restaurant: Demon Dogs the restaurant>

>>> Place.objects.get(name='Ristorante Miron').restaurant.italianrestaurant
<ItalianRestaurant: Ristorante Miron the italian restaurant>
>>> Restaurant.objects.get(name='Ristorante Miron').italianrestaurant
<ItalianRestaurant: Ristorante Miron the italian restaurant>

# This won't work because the Demon Dogs restaurant is not an Italian
# restaurant.
>>> place.restaurant.italianrestaurant
Traceback (most recent call last):
    ...
DoesNotExist: ItalianRestaurant matching query does not exist.

# Related objects work just as they normally do.

>>> s1 = Supplier(name="Joe's Chickens", address='123 Sesame St')
>>> s1.save()
>>> s1.customers = [r, ir]
>>> s2 = Supplier(name="Luigi's Pasta", address='456 Sesame St')
>>> s2.save()
>>> s2.customers = [ir]

# This won't work because the Place we select is not a Restaurant (it's a
# Supplier).
>>> p = Place.objects.get(name="Joe's Chickens")
>>> p.restaurant
Traceback (most recent call last):
    ...
DoesNotExist: Restaurant matching query does not exist.

# But we can descend from p to the Supplier child, as expected.
>>> p.supplier
<Supplier: Joe's Chickens the supplier>

>>> ir.provider.order_by('-name')
[<Supplier: Luigi's Pasta the supplier>, <Supplier: Joe's Chickens the supplier>]

>>> Restaurant.objects.filter(provider__name__contains="Chickens")
[<Restaurant: Ristorante Miron the restaurant>, <Restaurant: Demon Dogs the restaurant>]
>>> ItalianRestaurant.objects.filter(provider__name__contains="Chickens")
[<ItalianRestaurant: Ristorante Miron the italian restaurant>]

>>> park1 = ParkingLot(name='Main St', address='111 Main St', main_site=s1)
>>> park1.save()
>>> park2 = ParkingLot(name='Well Lit', address='124 Sesame St', main_site=ir)
>>> park2.save()

>>> Restaurant.objects.get(lot__name='Well Lit')
<Restaurant: Ristorante Miron the restaurant>

# The update() command can update fields in parent and child classes at once
# (although it executed multiple SQL queries to do so).
>>> Restaurant.objects.filter(serves_hot_dogs=True, name__contains='D').update(name='Demon Puppies', serves_hot_dogs=False)
1
>>> r1 = Restaurant.objects.get(pk=r.pk)
>>> r1.serves_hot_dogs == False
True
>>> r1.name
u'Demon Puppies'

# The values() command also works on fields from parent models.
>>> d = {'rating': 4, 'name': u'Ristorante Miron'}
>>> list(ItalianRestaurant.objects.values('name', 'rating')) == [d]
True

# select_related works with fields from the parent object as if they were a
# normal part of the model.
>>> from django import db
>>> from django.conf import settings
>>> settings.DEBUG = True
>>> db.reset_queries()
>>> ItalianRestaurant.objects.all()[0].chef
<Chef: Albert the chef>
>>> len(db.connection.queries)
2
>>> ItalianRestaurant.objects.select_related('chef')[0].chef
<Chef: Albert the chef>
>>> len(db.connection.queries)
3
>>> settings.DEBUG = False

"""}
