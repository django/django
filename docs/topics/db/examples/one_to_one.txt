########################
One-to-one relationships
########################

.. highlight:: pycon

To define a one-to-one relationship, use :ref:`ref-onetoone`.

In this example, a ``Place`` optionally can be a ``Restaurant``:

.. code-block:: python

    from django.db import models

    class Place(models.Model):
        name = models.CharField(max_length=50)
        address = models.CharField(max_length=80)

        # On Python 3: def __str__(self):
        def __unicode__(self):
            return u"%s the place" % self.name

    class Restaurant(models.Model):
        place = models.OneToOneField(Place, primary_key=True)
        serves_hot_dogs = models.BooleanField()
        serves_pizza = models.BooleanField()

        # On Python 3: def __str__(self):
        def __unicode__(self):
            return u"%s the restaurant" % self.place.name

    class Waiter(models.Model):
        restaurant = models.ForeignKey(Restaurant)
        name = models.CharField(max_length=50)

        # On Python 3: def __str__(self):
        def __unicode__(self):
            return u"%s the waiter at %s" % (self.name, self.restaurant)

What follows are examples of operations that can be performed using the Python
API facilities.

Create a couple of Places::

    >>> p1 = Place(name='Demon Dogs', address='944 W. Fullerton')
    >>> p1.save()
    >>> p2 = Place(name='Ace Hardware', address='1013 N. Ashland')
    >>> p2.save()

Create a Restaurant. Pass the ID of the "parent" object as this object's ID::

    >>> r = Restaurant(place=p1, serves_hot_dogs=True, serves_pizza=False)
    >>> r.save()

A Restaurant can access its place::

    >>> r.place
    <Place: Demon Dogs the place>

A Place can access its restaurant, if available::

    >>> p1.restaurant
    <Restaurant: Demon Dogs the restaurant>

p2 doesn't have an associated restaurant::

    >>> p2.restaurant
    Traceback (most recent call last):
        ...
    DoesNotExist: Restaurant matching query does not exist.

Set the place using assignment notation. Because place is the primary key on
Restaurant, the save will create a new restaurant::

    >>> r.place = p2
    >>> r.save()
    >>> p2.restaurant
    <Restaurant: Ace Hardware the restaurant>
    >>> r.place
    <Place: Ace Hardware the place>

Set the place back again, using assignment in the reverse direction::

    >>> p1.restaurant = r
    >>> p1.restaurant
    <Restaurant: Demon Dogs the restaurant>

Restaurant.objects.all() just returns the Restaurants, not the Places.  Note
that there are two restaurants - Ace Hardware the Restaurant was created in the
call to r.place = p2::

    >>> Restaurant.objects.all()
    [<Restaurant: Demon Dogs the restaurant>, <Restaurant: Ace Hardware the restaurant>]

Place.objects.all() returns all Places, regardless of whether they have
Restaurants::

    >>> Place.objects.order_by('name')
    [<Place: Ace Hardware the place>, <Place: Demon Dogs the place>]

You can query the models using :ref:`lookups across relationships <lookups-that-span-relationships>`::

    >>> Restaurant.objects.get(place=p1)
    <Restaurant: Demon Dogs the restaurant>
    >>> Restaurant.objects.get(place__pk=1)
    <Restaurant: Demon Dogs the restaurant>
    >>> Restaurant.objects.filter(place__name__startswith="Demon")
    [<Restaurant: Demon Dogs the restaurant>]
    >>> Restaurant.objects.exclude(place__address__contains="Ashland")
    [<Restaurant: Demon Dogs the restaurant>]

This of course works in reverse::

    >>> Place.objects.get(pk=1)
    <Place: Demon Dogs the place>
    >>> Place.objects.get(restaurant__place__exact=p1)
    <Place: Demon Dogs the place>
    >>> Place.objects.get(restaurant=r)
    <Place: Demon Dogs the place>
    >>> Place.objects.get(restaurant__place__name__startswith="Demon")
    <Place: Demon Dogs the place>

Add a Waiter to the Restaurant::

    >>> w = r.waiter_set.create(name='Joe')
    >>> w.save()
    >>> w
    <Waiter: Joe the waiter at Demon Dogs the restaurant>

Query the waiters::

    >>> Waiter.objects.filter(restaurant__place=p1)
    [<Waiter: Joe the waiter at Demon Dogs the restaurant>]
    >>> Waiter.objects.filter(restaurant__place__name__startswith="Demon")
    [<Waiter: Joe the waiter at Demon Dogs the restaurant>]
