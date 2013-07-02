#encoding=utf-8
"""
26. Invalid models

This example exists purely to point out errors in models.
"""

from __future__ import unicode_literals

from django.db import models

## These models are what the new tests need. All other models should be
## deleted or moved.


class Group(models.Model):
    pass


class GroupTwo(models.Model):
    field = models.ManyToManyField('Group', through="MembershipMissingFK")
    another = models.ManyToManyField('Person', through="Membership")


class Person(models.Model):
    name = models.CharField(max_length=5)


class ForeignKeyToMissingModel(models.Model):
    field = models.ForeignKey('Rel1')


class M2MToMissingModel(models.Model):
    field = models.ManyToManyField("Rel2")


class ForeignKeyToAbstractModel(models.Model):
    field = models.ForeignKey('AbstractModel')


class M2MToAbstractModel(models.Model):
    field = models.ManyToManyField('AbstractModel')


class RelationshipDoubleFK(models.Model):
    first = models.ForeignKey(Person, related_name="first_related_name")
    second = models.ForeignKey(Person, related_name="second_related_name")
    second_model = models.ForeignKey('ModelWithAmbiguousRelationship')
    date_added = models.DateTimeField()


class ModelWithAmbiguousRelationship(models.Model):
    field = models.ManyToManyField('Person',
        through="RelationshipDoubleFK", related_name='tertiary')


class Membership(models.Model):
    person = models.ForeignKey(Person)
    group = models.ForeignKey(Group)
    not_default_or_null = models.CharField(max_length=5)


class MembershipMissingFK(models.Model):
    person = models.ForeignKey(Group)
    foreign_key_to_wrong_model = models.ForeignKey(Person)


class PersonSelfRefM2M(models.Model):
    friends = models.ManyToManyField('self', through="Relationship")
    too_many_friends = models.ManyToManyField('self', through="RelationshipTripleFK")


class Relationship(models.Model):
    first = models.ForeignKey(PersonSelfRefM2M, related_name="rel_from_set")
    second = models.ForeignKey(PersonSelfRefM2M, related_name="rel_to_set")


class RelationshipTripleFK(models.Model):
    first = models.ForeignKey(PersonSelfRefM2M, related_name="rel_from_set_2")
    second = models.ForeignKey(PersonSelfRefM2M, related_name="rel_to_set_2")
    third = models.ForeignKey(PersonSelfRefM2M, related_name="too_many_by_far")


class PersonSelfRefM2MExplicit(models.Model):
    friends = models.ManyToManyField('self', through="ExplicitRelationship", symmetrical=True)


class ExplicitRelationship(models.Model):
    first = models.ForeignKey(PersonSelfRefM2MExplicit, related_name="rel_from_set")
    second = models.ForeignKey(PersonSelfRefM2MExplicit, related_name="rel_to_set")
    date_added = models.DateTimeField()


class AbstractModel(models.Model):
    name = models.CharField(max_length=10)


    class Meta:
        abstract = True


class FKTarget(models.Model):
    bad = models.IntegerField()
    good = models.IntegerField(unique=True)

class UniqueM2M(models.Model):
    field = models.ManyToManyField('Person', unique=True)
