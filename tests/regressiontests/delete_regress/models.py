from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.db import models


class Award(models.Model):
    name = models.CharField(max_length=25)
    object_id = models.PositiveIntegerField()
    content_type = models.ForeignKey(ContentType)
    content_object = generic.GenericForeignKey()

class AwardNote(models.Model):
    award = models.ForeignKey(Award)
    note = models.CharField(max_length=100)

class Person(models.Model):
    name = models.CharField(max_length=25)
    awards = generic.GenericRelation(Award)

class Book(models.Model):
    pagecount = models.IntegerField()

class Toy(models.Model):
    name = models.CharField(max_length=50)

class Child(models.Model):
    name = models.CharField(max_length=50)
    toys = models.ManyToManyField(Toy, through='PlayedWith')

class PlayedWith(models.Model):
    child = models.ForeignKey(Child)
    toy = models.ForeignKey(Toy)
    date = models.DateField(db_column='date_col')

class PlayedWithNote(models.Model):
    played = models.ForeignKey(PlayedWith)
    note = models.TextField()

class Contact(models.Model):
    label = models.CharField(max_length=100)

class Email(Contact):
    email_address = models.EmailField(max_length=100)

class Researcher(models.Model):
    contacts = models.ManyToManyField(Contact, related_name="research_contacts")

class Food(models.Model):
    name = models.CharField(max_length=20, unique=True)

class Eaten(models.Model):
    food = models.ForeignKey(Food, to_field="name")
    meal = models.CharField(max_length=20)


# Models for #15776

class Policy(models.Model):
    policy_number = models.CharField(max_length=10)

class Version(models.Model):
    policy = models.ForeignKey(Policy)

class Location(models.Model):
    version = models.ForeignKey(Version, blank=True, null=True)

class Item(models.Model):
    version = models.ForeignKey(Version)
    location = models.ForeignKey(Location, blank=True, null=True)

# Models for #16128

class File(models.Model):
    pass

class Image(File):
    class Meta:
        proxy = True

class Photo(Image):
    class Meta:
        proxy = True

class FooImage(models.Model):
    my_image = models.ForeignKey(Image)

class FooFile(models.Model):
    my_file = models.ForeignKey(File)

class FooPhoto(models.Model):
    my_photo = models.ForeignKey(Photo)

class FooFileProxy(FooFile):
    class Meta:
        proxy = True
