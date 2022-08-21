from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models


class Review(models.Model):
    source = models.CharField(max_length=100)
    content_type = models.ForeignKey(ContentType, models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey()

    class Meta:
        ordering = ("source",)

    def __str__(self):
        return self.source


class PersonManager(models.Manager):
    def get_by_natural_key(self, name):
        return self.get(name=name)


class Person(models.Model):
    name = models.CharField(max_length=100, unique=True)

    objects = PersonManager()

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return self.name


# This book manager doesn't do anything interesting; it just
# exists to strip out the 'extra_arg' argument to certain
# calls. This argument is used to establish that the BookManager
# is actually getting used when it should be.
class BookManager(models.Manager):
    def create(self, *args, extra_arg=None, **kwargs):
        return super().create(*args, **kwargs)

    def get_or_create(self, *args, extra_arg=None, **kwargs):
        return super().get_or_create(*args, **kwargs)


class Book(models.Model):
    title = models.CharField(max_length=100, unique_for_date="published")
    published = models.DateField()
    authors = models.ManyToManyField(Person)
    editor = models.ForeignKey(
        Person, models.SET_NULL, null=True, related_name="edited"
    )
    reviews = GenericRelation(Review)
    pages = models.IntegerField(default=100)

    objects = BookManager()

    class Meta:
        ordering = ("title",)

    def __str__(self):
        return self.title


class Pet(models.Model):
    name = models.CharField(max_length=100)
    owner = models.ForeignKey(Person, models.CASCADE)

    class Meta:
        ordering = ("name",)


class UserProfile(models.Model):
    user = models.OneToOneField(User, models.SET_NULL, null=True)
    flavor = models.CharField(max_length=100)

    class Meta:
        ordering = ("flavor",)
