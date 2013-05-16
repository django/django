from __future__ import unicode_literals

from django.db import models
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class Building(models.Model):
    name = models.CharField(max_length=10)

    def __str__(self):
        return "Building: %s" % self.name

@python_2_unicode_compatible
class Device(models.Model):
    building = models.ForeignKey('Building')
    name = models.CharField(max_length=10)

    def __str__(self):
        return "device '%s' in building %s" % (self.name, self.building)

@python_2_unicode_compatible
class Port(models.Model):
    device = models.ForeignKey('Device')
    port_number = models.CharField(max_length=10)

    def __str__(self):
        return "%s/%s" % (self.device.name, self.port_number)

@python_2_unicode_compatible
class Connection(models.Model):
    start = models.ForeignKey(Port, related_name='connection_start',
            unique=True)
    end = models.ForeignKey(Port, related_name='connection_end', unique=True)

    def __str__(self):
        return "%s to %s" % (self.start, self.end)

# Another non-tree hierarchy that exercises code paths similar to the above
# example, but in a slightly different configuration.
class TUser(models.Model):
    name = models.CharField(max_length=200)

class Person(models.Model):
    user = models.ForeignKey(TUser, unique=True)

class Organizer(models.Model):
    person = models.ForeignKey(Person)

class Student(models.Model):
    person = models.ForeignKey(Person)

class Class(models.Model):
    org = models.ForeignKey(Organizer)

class Enrollment(models.Model):
    std = models.ForeignKey(Student)
    cls = models.ForeignKey(Class)

# Models for testing bug #8036.
class Country(models.Model):
    name = models.CharField(max_length=50)

class State(models.Model):
    name = models.CharField(max_length=50)
    country = models.ForeignKey(Country)

class ClientStatus(models.Model):
    name = models.CharField(max_length=50)

class Client(models.Model):
    name = models.CharField(max_length=50)
    state = models.ForeignKey(State, null=True)
    status = models.ForeignKey(ClientStatus)

class SpecialClient(Client):
    value = models.IntegerField()

# Some model inheritance exercises
@python_2_unicode_compatible
class Parent(models.Model):
    name = models.CharField(max_length=10)

    def __str__(self):
        return self.name

class Child(Parent):
    value = models.IntegerField()

@python_2_unicode_compatible
class Item(models.Model):
    name = models.CharField(max_length=10)
    child = models.ForeignKey(Child, null=True)

    def __str__(self):
        return self.name

# Models for testing bug #19870.
@python_2_unicode_compatible
class Fowl(models.Model):
    name = models.CharField(max_length=10)

    def __str__(self):
        return self.name

class Hen(Fowl):
    pass

class Chick(Fowl):
    mother = models.ForeignKey(Hen)
