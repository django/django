# -*- coding:utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import models


class Target(models.Model):
    tgt_safe = models.CharField(max_length=10)
    clash1 = models.CharField(max_length=10)
    clash2 = models.CharField(max_length=10)

    clash1_set = models.CharField(max_length=10)


class Target2(models.Model):
    clash3 = models.CharField(max_length=10)
    foreign_tgt = models.ForeignKey(Target)
    clashforeign_set = models.ForeignKey(Target)

    m2m_tgt = models.ManyToManyField(Target)
    clashm2m_set = models.ManyToManyField(Target)


class Clash3(models.Model):
    src_safe = models.CharField(max_length=10)

    foreign_1 = models.ForeignKey(Target2, related_name='foreign_tgt')
    foreign_2 = models.ForeignKey(Target2, related_name='m2m_tgt')

    m2m_1 = models.ManyToManyField(Target2, related_name='foreign_tgt')
    m2m_2 = models.ManyToManyField(Target2, related_name='m2m_tgt')


class ClashForeign(models.Model):
    foreign = models.ForeignKey(Target2)


class ClashM2M(models.Model):
    m2m = models.ManyToManyField(Target2)


class SelfClashForeign(models.Model):
    src_safe = models.CharField(max_length=10)
    selfclashforeign = models.CharField(max_length=10)

    selfclashforeign_set = models.ForeignKey("SelfClashForeign")
    foreign_1 = models.ForeignKey("SelfClashForeign", related_name='id')
    foreign_2 = models.ForeignKey("SelfClashForeign", related_name='src_safe')


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


class SelfClashM2M(models.Model):
    src_safe = models.CharField(max_length=10)
    selfclashm2m = models.CharField(max_length=10)

    # Non-symmetrical M2M fields _do_ have related accessors, so
    # there is potential for clashes.
    selfclashm2m_set = models.ManyToManyField("self", symmetrical=False)

    m2m_1 = models.ManyToManyField("self", related_name='id', symmetrical=False)
    m2m_2 = models.ManyToManyField("self", related_name='src_safe', symmetrical=False)

    m2m_3 = models.ManyToManyField('self', symmetrical=False)
    m2m_4 = models.ManyToManyField('self', symmetrical=False)


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


class BadSwappableValue(models.Model):
    """A model that can be swapped out; during testing, the swappable
    value is not of the format app.model
    """
    name = models.CharField(max_length=100)

    class Meta:
        swappable = 'TEST_SWAPPED_MODEL_BAD_VALUE'


class BadSwappableModel(models.Model):
    """A model that can be swapped out; during testing, the swappable
    value references an unknown model.
    """
    name = models.CharField(max_length=100)

    class Meta:
        swappable = 'TEST_SWAPPED_MODEL_BAD_MODEL'


model_errors = """
old_invalid_models.clash3: Accessor for field 'foreign_1' clashes with field 'Target2.foreign_tgt'. Add a related_name argument to the definition for 'foreign_1'.
old_invalid_models.clash3: Accessor for field 'foreign_1' clashes with related m2m field 'Target2.foreign_tgt'. Add a related_name argument to the definition for 'foreign_1'.
old_invalid_models.clash3: Reverse query name for field 'foreign_1' clashes with field 'Target2.foreign_tgt'. Add a related_name argument to the definition for 'foreign_1'.
old_invalid_models.clash3: Reverse query name for field 'foreign_1' clashes with related m2m field 'Target2.foreign_tgt'. Add a related_name argument to the definition for 'foreign_1'.
old_invalid_models.clash3: Accessor for field 'foreign_2' clashes with m2m field 'Target2.m2m_tgt'. Add a related_name argument to the definition for 'foreign_2'.
old_invalid_models.clash3: Accessor for field 'foreign_2' clashes with related m2m field 'Target2.m2m_tgt'. Add a related_name argument to the definition for 'foreign_2'.
old_invalid_models.clash3: Reverse query name for field 'foreign_2' clashes with m2m field 'Target2.m2m_tgt'. Add a related_name argument to the definition for 'foreign_2'.
old_invalid_models.clash3: Reverse query name for field 'foreign_2' clashes with related m2m field 'Target2.m2m_tgt'. Add a related_name argument to the definition for 'foreign_2'.
old_invalid_models.clash3: Accessor for m2m field 'm2m_1' clashes with field 'Target2.foreign_tgt'. Add a related_name argument to the definition for 'm2m_1'.
old_invalid_models.clash3: Accessor for m2m field 'm2m_1' clashes with related field 'Target2.foreign_tgt'. Add a related_name argument to the definition for 'm2m_1'.
old_invalid_models.clash3: Reverse query name for m2m field 'm2m_1' clashes with field 'Target2.foreign_tgt'. Add a related_name argument to the definition for 'm2m_1'.
old_invalid_models.clash3: Reverse query name for m2m field 'm2m_1' clashes with related field 'Target2.foreign_tgt'. Add a related_name argument to the definition for 'm2m_1'.
old_invalid_models.clash3: Accessor for m2m field 'm2m_2' clashes with m2m field 'Target2.m2m_tgt'. Add a related_name argument to the definition for 'm2m_2'.
old_invalid_models.clash3: Accessor for m2m field 'm2m_2' clashes with related field 'Target2.m2m_tgt'. Add a related_name argument to the definition for 'm2m_2'.
old_invalid_models.clash3: Reverse query name for m2m field 'm2m_2' clashes with m2m field 'Target2.m2m_tgt'. Add a related_name argument to the definition for 'm2m_2'.
old_invalid_models.clash3: Reverse query name for m2m field 'm2m_2' clashes with related field 'Target2.m2m_tgt'. Add a related_name argument to the definition for 'm2m_2'.
old_invalid_models.clashforeign: Accessor for field 'foreign' clashes with field 'Target2.clashforeign_set'. Add a related_name argument to the definition for 'foreign'.
old_invalid_models.clashm2m: Accessor for m2m field 'm2m' clashes with m2m field 'Target2.clashm2m_set'. Add a related_name argument to the definition for 'm2m'.
old_invalid_models.target2: Accessor for field 'foreign_tgt' clashes with related m2m field 'Target.target2_set'. Add a related_name argument to the definition for 'foreign_tgt'.
old_invalid_models.target2: Accessor for field 'foreign_tgt' clashes with related m2m field 'Target.target2_set'. Add a related_name argument to the definition for 'foreign_tgt'.
old_invalid_models.target2: Accessor for field 'foreign_tgt' clashes with related field 'Target.target2_set'. Add a related_name argument to the definition for 'foreign_tgt'.
old_invalid_models.target2: Accessor for field 'clashforeign_set' clashes with related m2m field 'Target.target2_set'. Add a related_name argument to the definition for 'clashforeign_set'.
old_invalid_models.target2: Accessor for field 'clashforeign_set' clashes with related m2m field 'Target.target2_set'. Add a related_name argument to the definition for 'clashforeign_set'.
old_invalid_models.target2: Accessor for field 'clashforeign_set' clashes with related field 'Target.target2_set'. Add a related_name argument to the definition for 'clashforeign_set'.
old_invalid_models.target2: Accessor for m2m field 'm2m_tgt' clashes with related field 'Target.target2_set'. Add a related_name argument to the definition for 'm2m_tgt'.
old_invalid_models.target2: Accessor for m2m field 'm2m_tgt' clashes with related field 'Target.target2_set'. Add a related_name argument to the definition for 'm2m_tgt'.
old_invalid_models.target2: Accessor for m2m field 'm2m_tgt' clashes with related m2m field 'Target.target2_set'. Add a related_name argument to the definition for 'm2m_tgt'.
old_invalid_models.target2: Accessor for m2m field 'm2m_tgt' clashes with related m2m field 'Target.target2_set'. Add a related_name argument to the definition for 'm2m_tgt'.
old_invalid_models.target2: Accessor for m2m field 'm2m_tgt' clashes with related m2m field 'Target.target2_set'. Add a related_name argument to the definition for 'm2m_tgt'.
old_invalid_models.target2: Accessor for m2m field 'clashm2m_set' clashes with related field 'Target.target2_set'. Add a related_name argument to the definition for 'clashm2m_set'.
old_invalid_models.target2: Accessor for m2m field 'clashm2m_set' clashes with related field 'Target.target2_set'. Add a related_name argument to the definition for 'clashm2m_set'.
old_invalid_models.target2: Accessor for m2m field 'clashm2m_set' clashes with related m2m field 'Target.target2_set'. Add a related_name argument to the definition for 'clashm2m_set'.
old_invalid_models.target2: Accessor for m2m field 'clashm2m_set' clashes with related m2m field 'Target.target2_set'. Add a related_name argument to the definition for 'clashm2m_set'.
old_invalid_models.target2: Accessor for m2m field 'clashm2m_set' clashes with related m2m field 'Target.target2_set'. Add a related_name argument to the definition for 'clashm2m_set'.
old_invalid_models.selfclashforeign: Accessor for field 'selfclashforeign_set' clashes with field 'SelfClashForeign.selfclashforeign_set'. Add a related_name argument to the definition for 'selfclashforeign_set'.
old_invalid_models.selfclashforeign: Reverse query name for field 'selfclashforeign_set' clashes with field 'SelfClashForeign.selfclashforeign'. Add a related_name argument to the definition for 'selfclashforeign_set'.
old_invalid_models.selfclashforeign: Accessor for field 'foreign_1' clashes with field 'SelfClashForeign.id'. Add a related_name argument to the definition for 'foreign_1'.
old_invalid_models.selfclashforeign: Reverse query name for field 'foreign_1' clashes with field 'SelfClashForeign.id'. Add a related_name argument to the definition for 'foreign_1'.
old_invalid_models.selfclashforeign: Accessor for field 'foreign_2' clashes with field 'SelfClashForeign.src_safe'. Add a related_name argument to the definition for 'foreign_2'.
old_invalid_models.selfclashforeign: Reverse query name for field 'foreign_2' clashes with field 'SelfClashForeign.src_safe'. Add a related_name argument to the definition for 'foreign_2'.
old_invalid_models.selfclashm2m: Accessor for m2m field 'selfclashm2m_set' clashes with m2m field 'SelfClashM2M.selfclashm2m_set'. Add a related_name argument to the definition for 'selfclashm2m_set'.
old_invalid_models.selfclashm2m: Reverse query name for m2m field 'selfclashm2m_set' clashes with field 'SelfClashM2M.selfclashm2m'. Add a related_name argument to the definition for 'selfclashm2m_set'.
old_invalid_models.selfclashm2m: Accessor for m2m field 'selfclashm2m_set' clashes with related m2m field 'SelfClashM2M.selfclashm2m_set'. Add a related_name argument to the definition for 'selfclashm2m_set'.
old_invalid_models.selfclashm2m: Accessor for m2m field 'm2m_1' clashes with field 'SelfClashM2M.id'. Add a related_name argument to the definition for 'm2m_1'.
old_invalid_models.selfclashm2m: Accessor for m2m field 'm2m_2' clashes with field 'SelfClashM2M.src_safe'. Add a related_name argument to the definition for 'm2m_2'.
old_invalid_models.selfclashm2m: Reverse query name for m2m field 'm2m_1' clashes with field 'SelfClashM2M.id'. Add a related_name argument to the definition for 'm2m_1'.
old_invalid_models.selfclashm2m: Reverse query name for m2m field 'm2m_2' clashes with field 'SelfClashM2M.src_safe'. Add a related_name argument to the definition for 'm2m_2'.
old_invalid_models.selfclashm2m: Accessor for m2m field 'm2m_3' clashes with m2m field 'SelfClashM2M.selfclashm2m_set'. Add a related_name argument to the definition for 'm2m_3'.
old_invalid_models.selfclashm2m: Accessor for m2m field 'm2m_3' clashes with related m2m field 'SelfClashM2M.selfclashm2m_set'. Add a related_name argument to the definition for 'm2m_3'.
old_invalid_models.selfclashm2m: Accessor for m2m field 'm2m_3' clashes with related m2m field 'SelfClashM2M.selfclashm2m_set'. Add a related_name argument to the definition for 'm2m_3'.
old_invalid_models.selfclashm2m: Accessor for m2m field 'm2m_4' clashes with m2m field 'SelfClashM2M.selfclashm2m_set'. Add a related_name argument to the definition for 'm2m_4'.
old_invalid_models.selfclashm2m: Accessor for m2m field 'm2m_4' clashes with related m2m field 'SelfClashM2M.selfclashm2m_set'. Add a related_name argument to the definition for 'm2m_4'.
old_invalid_models.selfclashm2m: Accessor for m2m field 'm2m_4' clashes with related m2m field 'SelfClashM2M.selfclashm2m_set'. Add a related_name argument to the definition for 'm2m_4'.
old_invalid_models.selfclashm2m: Reverse query name for m2m field 'm2m_3' clashes with field 'SelfClashM2M.selfclashm2m'. Add a related_name argument to the definition for 'm2m_3'.
old_invalid_models.selfclashm2m: Reverse query name for m2m field 'm2m_4' clashes with field 'SelfClashM2M.selfclashm2m'. Add a related_name argument to the definition for 'm2m_4'.
old_invalid_models.group: The model Group has two manually-defined m2m relations through the model Membership, which is not permitted. Please consider using an extra field on your intermediary model instead.
old_invalid_models.badswappablevalue: TEST_SWAPPED_MODEL_BAD_VALUE is not of the form 'app_label.app_name'.
old_invalid_models.badswappablemodel: Model has been swapped out for 'not_an_app.Target' which has not been installed or is abstract.
old_invalid_models.badindextogether1: "index_together" refers to field_that_does_not_exist, a field that doesn't exist.
old_invalid_models.duplicatecolumnnamemodel1: Field 'bar' has column name 'foo' that is already used.
old_invalid_models.duplicatecolumnnamemodel2: Field 'bar' has column name 'bar' that is already used.
old_invalid_models.duplicatecolumnnamemodel4: Field 'bar' has column name 'baz' that is already used.
"""

"""
# Error messages predated by a character:
# - 'x' -- the test was rewritten
# - 'm' -- the test is actually a model test, not a field test; not rewritten

m invalid_models.clash3: Accessor for field 'foreign_1' clashes with field 'Target2.foreign_tgt'. Add a related_name argument to the definition for 'foreign_1'.
m invalid_models.clash3: Accessor for field 'foreign_1' clashes with related m2m field 'Target2.foreign_tgt'. Add a related_name argument to the definition for 'foreign_1'.
m invalid_models.clash3: Reverse query name for field 'foreign_1' clashes with field 'Target2.foreign_tgt'. Add a related_name argument to the definition for 'foreign_1'.
m invalid_models.clash3: Reverse query name for field 'foreign_1' clashes with related m2m field 'Target2.foreign_tgt'. Add a related_name argument to the definition for 'foreign_1'.
m invalid_models.clash3: Accessor for field 'foreign_2' clashes with m2m field 'Target2.m2m_tgt'. Add a related_name argument to the definition for 'foreign_2'.
m invalid_models.clash3: Accessor for field 'foreign_2' clashes with related m2m field 'Target2.m2m_tgt'. Add a related_name argument to the definition for 'foreign_2'.
m invalid_models.clash3: Reverse query name for field 'foreign_2' clashes with m2m field 'Target2.m2m_tgt'. Add a related_name argument to the definition for 'foreign_2'.
m invalid_models.clash3: Reverse query name for field 'foreign_2' clashes with related m2m field 'Target2.m2m_tgt'. Add a related_name argument to the definition for 'foreign_2'.
m invalid_models.clash3: Accessor for m2m field 'm2m_1' clashes with field 'Target2.foreign_tgt'. Add a related_name argument to the definition for 'm2m_1'.
m invalid_models.clash3: Accessor for m2m field 'm2m_1' clashes with related field 'Target2.foreign_tgt'. Add a related_name argument to the definition for 'm2m_1'.
m invalid_models.clash3: Reverse query name for m2m field 'm2m_1' clashes with field 'Target2.foreign_tgt'. Add a related_name argument to the definition for 'm2m_1'.
m invalid_models.clash3: Reverse query name for m2m field 'm2m_1' clashes with related field 'Target2.foreign_tgt'. Add a related_name argument to the definition for 'm2m_1'.
m invalid_models.clash3: Accessor for m2m field 'm2m_2' clashes with m2m field 'Target2.m2m_tgt'. Add a related_name argument to the definition for 'm2m_2'.
m invalid_models.clash3: Accessor for m2m field 'm2m_2' clashes with related field 'Target2.m2m_tgt'. Add a related_name argument to the definition for 'm2m_2'.
m invalid_models.clash3: Reverse query name for m2m field 'm2m_2' clashes with m2m field 'Target2.m2m_tgt'. Add a related_name argument to the definition for 'm2m_2'.
m invalid_models.clash3: Reverse query name for m2m field 'm2m_2' clashes with related field 'Target2.m2m_tgt'. Add a related_name argument to the definition for 'm2m_2'.
m invalid_models.clashforeign: Accessor for field 'foreign' clashes with field 'Target2.clashforeign_set'. Add a related_name argument to the definition for 'foreign'.
m invalid_models.clashm2m: Accessor for m2m field 'm2m' clashes with m2m field 'Target2.clashm2m_set'. Add a related_name argument to the definition for 'm2m'.
m invalid_models.target2: Accessor for field 'foreign_tgt' clashes with related m2m field 'Target.target2_set'. Add a related_name argument to the definition for 'foreign_tgt'.
m invalid_models.target2: Accessor for field 'foreign_tgt' clashes with related m2m field 'Target.target2_set'. Add a related_name argument to the definition for 'foreign_tgt'.
m invalid_models.target2: Accessor for field 'foreign_tgt' clashes with related field 'Target.target2_set'. Add a related_name argument to the definition for 'foreign_tgt'.
m invalid_models.target2: Accessor for field 'clashforeign_set' clashes with related m2m field 'Target.target2_set'. Add a related_name argument to the definition for 'clashforeign_set'.
m invalid_models.target2: Accessor for field 'clashforeign_set' clashes with related m2m field 'Target.target2_set'. Add a related_name argument to the definition for 'clashforeign_set'.
m invalid_models.target2: Accessor for field 'clashforeign_set' clashes with related field 'Target.target2_set'. Add a related_name argument to the definition for 'clashforeign_set'.
m invalid_models.target2: Accessor for m2m field 'm2m_tgt' clashes with related field 'Target.target2_set'. Add a related_name argument to the definition for 'm2m_tgt'.
m invalid_models.target2: Accessor for m2m field 'm2m_tgt' clashes with related field 'Target.target2_set'. Add a related_name argument to the definition for 'm2m_tgt'.
m invalid_models.target2: Accessor for m2m field 'm2m_tgt' clashes with related m2m field 'Target.target2_set'. Add a related_name argument to the definition for 'm2m_tgt'.
m invalid_models.target2: Accessor for m2m field 'm2m_tgt' clashes with related m2m field 'Target.target2_set'. Add a related_name argument to the definition for 'm2m_tgt'.
m invalid_models.target2: Accessor for m2m field 'm2m_tgt' clashes with related m2m field 'Target.target2_set'. Add a related_name argument to the definition for 'm2m_tgt'.
m invalid_models.target2: Accessor for m2m field 'clashm2m_set' clashes with related field 'Target.target2_set'. Add a related_name argument to the definition for 'clashm2m_set'.
m invalid_models.target2: Accessor for m2m field 'clashm2m_set' clashes with related field 'Target.target2_set'. Add a related_name argument to the definition for 'clashm2m_set'.
m invalid_models.target2: Accessor for m2m field 'clashm2m_set' clashes with related m2m field 'Target.target2_set'. Add a related_name argument to the definition for 'clashm2m_set'.
m invalid_models.target2: Accessor for m2m field 'clashm2m_set' clashes with related m2m field 'Target.target2_set'. Add a related_name argument to the definition for 'clashm2m_set'.
m invalid_models.target2: Accessor for m2m field 'clashm2m_set' clashes with related m2m field 'Target.target2_set'. Add a related_name argument to the definition for 'clashm2m_set'.
m invalid_models.selfclashforeign: Accessor for field 'selfclashforeign_set' clashes with field 'SelfClashForeign.selfclashforeign_set'. Add a related_name argument to the definition for 'selfclashforeign_set'.
m invalid_models.selfclashforeign: Reverse query name for field 'selfclashforeign_set' clashes with field 'SelfClashForeign.selfclashforeign'. Add a related_name argument to the definition for 'selfclashforeign_set'.
m invalid_models.selfclashforeign: Accessor for field 'foreign_1' clashes with field 'SelfClashForeign.id'. Add a related_name argument to the definition for 'foreign_1'.
m invalid_models.selfclashforeign: Reverse query name for field 'foreign_1' clashes with field 'SelfClashForeign.id'. Add a related_name argument to the definition for 'foreign_1'.
m invalid_models.selfclashforeign: Accessor for field 'foreign_2' clashes with field 'SelfClashForeign.src_safe'. Add a related_name argument to the definition for 'foreign_2'.
m invalid_models.selfclashforeign: Reverse query name for field 'foreign_2' clashes with field 'SelfClashForeign.src_safe'. Add a related_name argument to the definition for 'foreign_2'.
m invalid_models.selfclashm2m: Accessor for m2m field 'selfclashm2m_set' clashes with m2m field 'SelfClashM2M.selfclashm2m_set'. Add a related_name argument to the definition for 'selfclashm2m_set'.
m invalid_models.selfclashm2m: Reverse query name for m2m field 'selfclashm2m_set' clashes with field 'SelfClashM2M.selfclashm2m'. Add a related_name argument to the definition for 'selfclashm2m_set'.
m invalid_models.selfclashm2m: Accessor for m2m field 'selfclashm2m_set' clashes with related m2m field 'SelfClashM2M.selfclashm2m_set'. Add a related_name argument to the definition for 'selfclashm2m_set'.
m invalid_models.selfclashm2m: Accessor for m2m field 'm2m_1' clashes with field 'SelfClashM2M.id'. Add a related_name argument to the definition for 'm2m_1'.
m invalid_models.selfclashm2m: Accessor for m2m field 'm2m_2' clashes with field 'SelfClashM2M.src_safe'. Add a related_name argument to the definition for 'm2m_2'.
m invalid_models.selfclashm2m: Reverse query name for m2m field 'm2m_1' clashes with field 'SelfClashM2M.id'. Add a related_name argument to the definition for 'm2m_1'.
m invalid_models.selfclashm2m: Reverse query name for m2m field 'm2m_2' clashes with field 'SelfClashM2M.src_safe'. Add a related_name argument to the definition for 'm2m_2'.
m invalid_models.selfclashm2m: Accessor for m2m field 'm2m_3' clashes with m2m field 'SelfClashM2M.selfclashm2m_set'. Add a related_name argument to the definition for 'm2m_3'.
m invalid_models.selfclashm2m: Accessor for m2m field 'm2m_3' clashes with related m2m field 'SelfClashM2M.selfclashm2m_set'. Add a related_name argument to the definition for 'm2m_3'.
m invalid_models.selfclashm2m: Accessor for m2m field 'm2m_3' clashes with related m2m field 'SelfClashM2M.selfclashm2m_set'. Add a related_name argument to the definition for 'm2m_3'.
m invalid_models.selfclashm2m: Accessor for m2m field 'm2m_4' clashes with m2m field 'SelfClashM2M.selfclashm2m_set'. Add a related_name argument to the definition for 'm2m_4'.
m invalid_models.selfclashm2m: Accessor for m2m field 'm2m_4' clashes with related m2m field 'SelfClashM2M.selfclashm2m_set'. Add a related_name argument to the definition for 'm2m_4'.
m invalid_models.selfclashm2m: Accessor for m2m field 'm2m_4' clashes with related m2m field 'SelfClashM2M.selfclashm2m_set'. Add a related_name argument to the definition for 'm2m_4'.
m invalid_models.selfclashm2m: Reverse query name for m2m field 'm2m_3' clashes with field 'SelfClashM2M.selfclashm2m'. Add a related_name argument to the definition for 'm2m_3'.
m invalid_models.selfclashm2m: Reverse query name for m2m field 'm2m_4' clashes with field 'SelfClashM2M.selfclashm2m'. Add a related_name argument to the definition for 'm2m_4'.
m invalid_models.group: The model Group has two manually-defined m2m relations through the model Membership, which is not permitted. Please consider using an extra field on your intermediary model instead.
m invalid_models.badswappablevalue: TEST_SWAPPED_MODEL_BAD_VALUE is not of the form 'app_label.app_name'.
m invalid_models.badswappablemodel: Model has been swapped out for 'not_an_app.Target' which has not been installed or is abstract.
m invalid_models.badindextogether1: "index_together" refers to field_that_does_not_exist, a field that doesn't exist.
m invalid_models.duplicatecolumnnamemodel1: Field 'bar' has column name 'foo' that is already used.
m invalid_models.duplicatecolumnnamemodel2: Field 'bar' has column name 'bar' that is already used.
m invalid_models.duplicatecolumnnamemodel4: Field 'bar' has column name 'baz' that is already used.
"""
