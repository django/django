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

class StudentWorker(Student, Worker):
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

#
# Abstract base classes with related models where the sub-class has the
# same name in a different app and inherits from the same abstract base
# class.
# NOTE: The actual API tests for the following classes are in
#       model_inheritance_same_model_name/models.py - They are defined
#       here in order to have the name conflict between apps
#

class Title(models.Model):
    title = models.CharField(max_length=50)

class NamedURL(models.Model):
    title = models.ForeignKey(Title, related_name='attached_%(app_label)s_%(class)s_set')
    url = models.URLField()

    class Meta:
        abstract = True

class Copy(NamedURL):
    content = models.TextField()

    def __unicode__(self):
        return self.content
