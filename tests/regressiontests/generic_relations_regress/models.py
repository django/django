from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.db import models


__all__ = ('Link', 'Place', 'Restaurant', 'Person', 'Address',
           'CharLink', 'TextLink', 'OddRelation1', 'OddRelation2',
           'Contact', 'Organization', 'Note')

class Link(models.Model):
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = generic.GenericForeignKey()

    def __unicode__(self):
        return "Link to %s id=%s" % (self.content_type, self.object_id)

class Place(models.Model):
    name = models.CharField(max_length=100)
    links = generic.GenericRelation(Link)

    def __unicode__(self):
        return "Place: %s" % self.name

class Restaurant(Place):
    def __unicode__(self):
        return "Restaurant: %s" % self.name

class Address(models.Model):
    street = models.CharField(max_length=80)
    city = models.CharField(max_length=50)
    state = models.CharField(max_length=2)
    zipcode = models.CharField(max_length=5)
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = generic.GenericForeignKey()

    def __unicode__(self):
        return '%s %s, %s %s' % (self.street, self.city, self.state, self.zipcode)

class Person(models.Model):
    account = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=128)
    addresses = generic.GenericRelation(Address)

    def __unicode__(self):
        return self.name

class CharLink(models.Model):
    content_type = models.ForeignKey(ContentType)
    object_id = models.CharField(max_length=100)
    content_object = generic.GenericForeignKey()

class TextLink(models.Model):
    content_type = models.ForeignKey(ContentType)
    object_id = models.TextField()
    content_object = generic.GenericForeignKey()

class OddRelation1(models.Model):
    name = models.CharField(max_length=100)
    clinks = generic.GenericRelation(CharLink)

class OddRelation2(models.Model):
    name = models.CharField(max_length=100)
    tlinks = generic.GenericRelation(TextLink)

# models for test_q_object_or:
class Note(models.Model):
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = generic.GenericForeignKey()
    note = models.TextField()

class Contact(models.Model):
    notes = generic.GenericRelation(Note)

class Organization(models.Model):
    name = models.CharField(max_length=255)
    contacts = models.ManyToManyField(Contact, related_name='organizations')

