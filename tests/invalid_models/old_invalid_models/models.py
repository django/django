# -*- coding:utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import models


class Target(models.Model):
    tgt_safe = models.CharField(max_length=10)
    clash1 = models.CharField(max_length=10)
    clash2 = models.CharField(max_length=10)

    clash1_set = models.CharField(max_length=10)

class ValidM2M(models.Model):
    src_safe = models.CharField(max_length=10)
    validm2m = models.CharField(max_length=10)

    # M2M fields are symmetrical by default. Symmetrical M2M fields
    # on self don't require a related accessor, so many potential
    # clashes are avoided.
    validm2m_set = models.ManyToManyField("self")

    m2m_1 = models.ManyToManyField("self", related_name='id')
    m2m_2 = models.ManyToManyField("self", related_name='src_safe')

    m2m_3 = models.ManyToManyField('self')
    m2m_4 = models.ManyToManyField('self')


class Model(models.Model):
    "But it's valid to call a model Model."
    year = models.PositiveIntegerField()  # 1960
    make = models.CharField(max_length=10)  # Aston Martin
    name = models.CharField(max_length=10)  # DB 4 GT


class Person(models.Model):
    name = models.CharField(max_length=5)


class Group(models.Model):
    name = models.CharField(max_length=5)
    primary = models.ManyToManyField(Person, through="Membership", related_name="primary")
    secondary = models.ManyToManyField(Person, through="Membership", related_name="secondary")


class Membership(models.Model):
    person = models.ForeignKey(Person)
    group = models.ForeignKey(Group)
    not_default_or_null = models.CharField(max_length=5)


class UniqueFKTarget1(models.Model):
    """ Model to test for unique FK target in yet-to-be-defined model: expect no error """
    tgt = models.ForeignKey('FKTarget', to_field='good')


class FKTarget(models.Model):
    good = models.IntegerField(unique=True)


class UniqueFKTarget2(models.Model):
    """ Model to test for unique FK target in previously seen model: expect no error """
    tgt = models.ForeignKey(FKTarget, to_field='good')


class UnicodeForeignKeys(models.Model):
    """Foreign keys which can translate to ascii should be OK, but fail if
    they're not."""
    good = models.ForeignKey('FKTarget')
    also_good = models.ManyToManyField('FKTarget', related_name='unicode2')

    # In Python 3 this should become legal, but currently causes unicode errors
    # when adding the errors in core/management/validation.py
    #bad = models.ForeignKey('★')


class OrderByPKModel(models.Model):
    """
    Model to test that ordering by pk passes validation.
    Refs #8291
    """
    name = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ('pk',)


class SwappedModel(models.Model):
    """A model that is swapped out.

    The foreign keys and m2m relations on this model *shouldn't*
    install related accessors, so there shouldn't be clashes with
    the equivalent names on the replacement.
    """
    name = models.CharField(max_length=100)

    foreign = models.ForeignKey(Target, related_name='swappable_fk_set')
    m2m = models.ManyToManyField(Target, related_name='swappable_m2m_set')

    class Meta:
        swappable = 'TEST_SWAPPED_MODEL'


class ReplacementModel(models.Model):
    """A replacement model for swapping purposes."""
    name = models.CharField(max_length=100)

    foreign = models.ForeignKey(Target, related_name='swappable_fk_set')
    m2m = models.ManyToManyField(Target, related_name='swappable_m2m_set')


class SwappingModel(models.Model):
    """ Uses SwappedModel. """

    foreign_key = models.ForeignKey(settings.TEST_SWAPPED_MODEL,
        related_name='swapping_foreign_key')
    m2m = models.ManyToManyField(settings.TEST_SWAPPED_MODEL,
        related_name='swapping_m2m')


model_errors = """
old_invalid_models.group: The model Group has two manually-defined m2m relations through the model Membership, which is not permitted. Please consider using an extra field on your intermediary model instead.
old_invalid_models.duplicatecolumnnamemodel1: Field 'bar' has column name 'foo' that is already used.
old_invalid_models.duplicatecolumnnamemodel2: Field 'bar' has column name 'bar' that is already used.
old_invalid_models.duplicatecolumnnamemodel4: Field 'bar' has column name 'baz' that is already used.
"""

"""
# Error messages predated by a character:
# - 'x' -- the test was rewritten
# - 'm' -- the test is actually a model test, not a field test; not rewritten

m invalid_models.group: The model Group has two manually-defined m2m relations through the model Membership, which is not permitted. Please consider using an extra field on your intermediary model instead.
m invalid_models.duplicatecolumnnamemodel1: Field 'bar' has column name 'foo' that is already used.
m invalid_models.duplicatecolumnnamemodel2: Field 'bar' has column name 'bar' that is already used.
m invalid_models.duplicatecolumnnamemodel4: Field 'bar' has column name 'baz' that is already used.
"""
