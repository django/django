from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.db import models

class Review(models.Model):
    source = models.CharField(max_length=100)
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = generic.GenericForeignKey()

    def __unicode__(self):
        return self.source

    class Meta:
        ordering = ('source',)

class PersonManager(models.Manager):
    def get_by_natural_key(self, name):
        return self.get(name=name)

class Person(models.Model):
    objects = PersonManager()
    name = models.CharField(max_length=100)

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ('name',)

# This book manager doesn't do anything interesting; it just
# exists to strip out the 'extra_arg' argument to certain
# calls. This argument is used to establish that the BookManager
# is actually getting used when it should be.
class BookManager(models.Manager):
    def create(self, *args, **kwargs):
        kwargs.pop('extra_arg', None)
        return super(BookManager, self).create(*args, **kwargs)

    def get_or_create(self, *args, **kwargs):
        kwargs.pop('extra_arg', None)
        return super(BookManager, self).get_or_create(*args, **kwargs)

class Book(models.Model):
    objects = BookManager()
    title = models.CharField(max_length=100)
    published = models.DateField()
    authors = models.ManyToManyField(Person)
    editor = models.ForeignKey(Person, null=True, related_name='edited')
    reviews = generic.GenericRelation(Review)
    pages = models.IntegerField(default=100)

    def __unicode__(self):
        return self.title

    class Meta:
        ordering = ('title',)

class Pet(models.Model):
    name = models.CharField(max_length=100)
    owner = models.ForeignKey(Person)

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ('name',)

class UserProfile(models.Model):
    user = models.OneToOneField(User, null=True)
    flavor = models.CharField(max_length=100)

    class Meta:
        ordering = ('flavor',)
