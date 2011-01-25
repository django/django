from django.db import models

from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType

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
