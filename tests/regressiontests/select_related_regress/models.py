from django.db import models

class Building(models.Model):
    name = models.CharField(max_length=10)

    def __unicode__(self):
        return u"Building: %s" % self.name

class Device(models.Model):
    building = models.ForeignKey('Building')
    name = models.CharField(max_length=10)

    def __unicode__(self):
        return u"device '%s' in building %s" % (self.name, self.building)

class Port(models.Model):
    device = models.ForeignKey('Device')
    port_number = models.CharField(max_length=10)

    def __unicode__(self):
        return u"%s/%s" % (self.device.name, self.port_number)

class Connection(models.Model):
    start = models.ForeignKey(Port, related_name='connection_start',
            unique=True)
    end = models.ForeignKey(Port, related_name='connection_end', unique=True)

    def __unicode__(self):
        return u"%s to %s" % (self.start, self.end)

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
class Parent(models.Model):
    name = models.CharField(max_length=10)

    def __unicode__(self):
        return self.name

class Child(Parent):
    value = models.IntegerField()

class Item(models.Model):
    name = models.CharField(max_length=10)
    child = models.ForeignKey(Child, null=True)

    def __unicode__(self):
        return self.name
