from django.contrib.auth.models import User
from django.db import models


# Forward declared intermediate model
class Membership(models.Model):
    person = models.ForeignKey('Person', models.CASCADE)
    group = models.ForeignKey('Group', models.CASCADE)
    price = models.IntegerField(default=100)

    def __str__(self):
        return "%s is a member of %s" % (self.person.name, self.group.name)


# using custom id column to test ticket #11107
class UserMembership(models.Model):
    id = models.AutoField(db_column='usermembership_id', primary_key=True)
    user = models.ForeignKey(User, models.CASCADE)
    group = models.ForeignKey('Group', models.CASCADE)
    price = models.IntegerField(default=100)

    def __str__(self):
        return "%s is a user and member of %s" % (self.user.username, self.group.name)


class Person(models.Model):
    name = models.CharField(max_length=128)

    def __str__(self):
        return self.name


class Group(models.Model):
    name = models.CharField(max_length=128)
    # Membership object defined as a class
    members = models.ManyToManyField(Person, through=Membership)
    user_members = models.ManyToManyField(User, through='UserMembership')

    def __str__(self):
        return self.name


# Using to_field on the through model
class Car(models.Model):
    make = models.CharField(max_length=20, unique=True, null=True)
    drivers = models.ManyToManyField('Driver', through='CarDriver')

    def __str__(self):
        return "%s" % self.make


class Driver(models.Model):
    name = models.CharField(max_length=20, unique=True, null=True)

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return "%s" % self.name


class CarDriver(models.Model):
    car = models.ForeignKey('Car', models.CASCADE, to_field='make')
    driver = models.ForeignKey('Driver', models.CASCADE, to_field='name')

    def __str__(self):
        return "pk=%s car=%s driver=%s" % (str(self.pk), self.car, self.driver)


# Through models using multi-table inheritance
class Event(models.Model):
    name = models.CharField(max_length=50, unique=True)
    people = models.ManyToManyField('Person', through='IndividualCompetitor')
    special_people = models.ManyToManyField(
        'Person',
        through='ProxiedIndividualCompetitor',
        related_name='special_event_set',
    )
    teams = models.ManyToManyField('Group', through='CompetingTeam')


class Competitor(models.Model):
    event = models.ForeignKey(Event, models.CASCADE)


class IndividualCompetitor(Competitor):
    person = models.ForeignKey(Person, models.CASCADE)


class CompetingTeam(Competitor):
    team = models.ForeignKey(Group, models.CASCADE)


class ProxiedIndividualCompetitor(IndividualCompetitor):
    class Meta:
        proxy = True
