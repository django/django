from datetime import datetime

from django.db import models
from django.utils.encoding import python_2_unicode_compatible


# M2M described on one of the models
@python_2_unicode_compatible
class Person(models.Model):
    name = models.CharField(max_length=128)

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return self.name

@python_2_unicode_compatible
class Group(models.Model):
    name = models.CharField(max_length=128)
    members = models.ManyToManyField(Person, through='Membership')
    custom_members = models.ManyToManyField(Person, through='CustomMembership', related_name="custom")
    nodefaultsnonulls = models.ManyToManyField(Person, through='TestNoDefaultsOrNulls', related_name="testnodefaultsnonulls")

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return self.name

@python_2_unicode_compatible
class Membership(models.Model):
    person = models.ForeignKey(Person)
    group = models.ForeignKey(Group)
    date_joined = models.DateTimeField(default=datetime.now)
    invite_reason = models.CharField(max_length=64, null=True)

    class Meta:
        ordering = ('date_joined', 'invite_reason', 'group')

    def __str__(self):
        return "%s is a member of %s" % (self.person.name, self.group.name)

@python_2_unicode_compatible
class CustomMembership(models.Model):
    person = models.ForeignKey(Person, db_column="custom_person_column", related_name="custom_person_related_name")
    group = models.ForeignKey(Group)
    weird_fk = models.ForeignKey(Membership, null=True)
    date_joined = models.DateTimeField(default=datetime.now)

    def __str__(self):
        return "%s is a member of %s" % (self.person.name, self.group.name)

    class Meta:
        db_table = "test_table"

class TestNoDefaultsOrNulls(models.Model):
    person = models.ForeignKey(Person)
    group = models.ForeignKey(Group)
    nodefaultnonull = models.CharField(max_length=5)

@python_2_unicode_compatible
class PersonSelfRefM2M(models.Model):
    name = models.CharField(max_length=5)
    friends = models.ManyToManyField('self', through="Friendship", symmetrical=False)

    def __str__(self):
        return self.name

class Friendship(models.Model):
    first = models.ForeignKey(PersonSelfRefM2M, related_name="rel_from_set")
    second = models.ForeignKey(PersonSelfRefM2M, related_name="rel_to_set")
    date_friended = models.DateTimeField()
