#encoding=utf-8
"""
26. Invalid models

This example exists purely to point out errors in models.
"""

from __future__ import unicode_literals

from django.db import connection, models


class FieldErrors(models.Model):
    field_ = models.CharField(max_length=10)
    generic_ip_notnull_blank = models.GenericIPAddressField(null=False, blank=True)


class Target(models.Model):
    tgt_safe = models.CharField(max_length=10)
    clash1 = models.CharField(max_length=10)
    clash2 = models.CharField(max_length=10)

    clash1_set = models.CharField(max_length=10)


class Clash1(models.Model):
    src_safe = models.CharField(max_length=10)

    foreign = models.ForeignKey(Target)
    m2m = models.ManyToManyField(Target)


class Clash2(models.Model):
    src_safe = models.CharField(max_length=10)

    foreign_1 = models.ForeignKey(Target, related_name='id')
    foreign_2 = models.ForeignKey(Target, related_name='src_safe')

    m2m_1 = models.ManyToManyField(Target, related_name='id')
    m2m_2 = models.ManyToManyField(Target, related_name='src_safe')


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


class Car(models.Model):
    colour = models.CharField(max_length=5)
    model = models.ForeignKey(Model)


class MissingRelations(models.Model):
    rel1 = models.ForeignKey("Rel1")
    rel2 = models.ManyToManyField("Rel2")


class MissingManualM2MModel(models.Model):
    name = models.CharField(max_length=5)
    missing_m2m = models.ManyToManyField(Model, through="MissingM2MModel")


class OldPerson(models.Model):
    name = models.CharField(max_length=5)


class Group(models.Model):
    name = models.CharField(max_length=5)
    primary = models.ManyToManyField(OldPerson, through="Membership", related_name="primary")
    secondary = models.ManyToManyField(OldPerson, through="Membership", related_name="secondary")
    tertiary = models.ManyToManyField(OldPerson, through="RelationshipDoubleFK", related_name="tertiary")


class GroupTwo(models.Model):
    name = models.CharField(max_length=5)
    primary = models.ManyToManyField(OldPerson, through="Membership")
    secondary = models.ManyToManyField(Group, through="MembershipMissingFK")


class Membership(models.Model):
    person = models.ForeignKey(OldPerson)
    group = models.ForeignKey(Group)
    not_default_or_null = models.CharField(max_length=5)


class MembershipMissingFK(models.Model):
    person = models.ForeignKey(OldPerson)


class PersonSelfRefM2M(models.Model):
    name = models.CharField(max_length=5)
    friends = models.ManyToManyField('self', through="Relationship")
    too_many_friends = models.ManyToManyField('self', through="RelationshipTripleFK")


class PersonSelfRefM2MExplicit(models.Model):
    name = models.CharField(max_length=5)
    friends = models.ManyToManyField('self', through="ExplicitRelationship", symmetrical=True)


class Relationship(models.Model):
    first = models.ForeignKey(PersonSelfRefM2M, related_name="rel_from_set")
    second = models.ForeignKey(PersonSelfRefM2M, related_name="rel_to_set")
    date_added = models.DateTimeField()


class ExplicitRelationship(models.Model):
    first = models.ForeignKey(PersonSelfRefM2MExplicit, related_name="rel_from_set")
    second = models.ForeignKey(PersonSelfRefM2MExplicit, related_name="rel_to_set")
    date_added = models.DateTimeField()


class RelationshipTripleFK(models.Model):
    first = models.ForeignKey(PersonSelfRefM2M, related_name="rel_from_set_2")
    second = models.ForeignKey(PersonSelfRefM2M, related_name="rel_to_set_2")
    third = models.ForeignKey(PersonSelfRefM2M, related_name="too_many_by_far")
    date_added = models.DateTimeField()


class RelationshipDoubleFK(models.Model):
    first = models.ForeignKey(OldPerson, related_name="first_related_name")
    second = models.ForeignKey(OldPerson, related_name="second_related_name")
    third = models.ForeignKey(Group, related_name="rel_to_set")
    date_added = models.DateTimeField()


class AbstractModel(models.Model):
    name = models.CharField(max_length=10)

    class Meta:
        abstract = True


class AbstractRelationModel(models.Model):
    fk1 = models.ForeignKey('AbstractModel')
    fk2 = models.ManyToManyField('AbstractModel')


class UniqueM2M(models.Model):
    """ Model to test for unique ManyToManyFields, which are invalid. """
    unique_people = models.ManyToManyField(OldPerson, unique=True)


class NonUniqueFKTarget1(models.Model):
    """ Model to test for non-unique FK target in yet-to-be-defined model: expect an error """
    tgt = models.ForeignKey('FKTarget', to_field='bad')


class UniqueFKTarget1(models.Model):
    """ Model to test for unique FK target in yet-to-be-defined model: expect no error """
    tgt = models.ForeignKey('FKTarget', to_field='good')


class FKTarget(models.Model):
    bad = models.IntegerField()
    good = models.IntegerField(unique=True)


class NonUniqueFKTarget2(models.Model):
    """ Model to test for non-unique FK target in previously seen model: expect an error """
    tgt = models.ForeignKey(FKTarget, to_field='bad')


class UniqueFKTarget2(models.Model):
    """ Model to test for unique FK target in previously seen model: expect no error """
    tgt = models.ForeignKey(FKTarget, to_field='good')


class NonExistingOrderingWithSingleUnderscore(models.Model):
    class Meta:
        ordering = ("does_not_exist",)


class InvalidSetNull(models.Model):
    fk = models.ForeignKey('self', on_delete=models.SET_NULL)


class InvalidSetDefault(models.Model):
    fk = models.ForeignKey('self', on_delete=models.SET_DEFAULT)


class UnicodeForeignKeys(models.Model):
    """Foreign keys which can translate to ascii should be OK, but fail if
    they're not."""
    good = models.ForeignKey('FKTarget')
    also_good = models.ManyToManyField('FKTarget', related_name='unicode2')

    # In Python 3 this should become legal, but currently causes unicode errors
    # when adding the errors in core/management/validation.py
    #bad = models.ForeignKey('★')


class PrimaryKeyNull(models.Model):
    my_pk_field = models.IntegerField(primary_key=True, null=True)


class OrderByPKModel(models.Model):
    """
    Model to test that ordering by pk passes validation.
    Refs #8291
    """
    name = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ('pk',)


class SwappableModel(models.Model):
    """A model that can be, but isn't swapped out.

    References to this model *shoudln't* raise any validation error.
    """
    name = models.CharField(max_length=100)

    class Meta:
        swappable = 'TEST_SWAPPABLE_MODEL'


class SwappedModel(models.Model):
    """A model that is swapped out.

    References to this model *should* raise a validation error.
    Requires TEST_SWAPPED_MODEL to be defined in the test environment;
    this is guaranteed by the test runner using @override_settings.

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


class HardReferenceModel(models.Model):
    fk_1 = models.ForeignKey(SwappableModel, related_name='fk_hardref1')
    fk_2 = models.ForeignKey('old_invalid_models.SwappableModel', related_name='fk_hardref2')
    fk_3 = models.ForeignKey(SwappedModel, related_name='fk_hardref3')
    fk_4 = models.ForeignKey('old_invalid_models.SwappedModel', related_name='fk_hardref4')
    m2m_1 = models.ManyToManyField(SwappableModel, related_name='m2m_hardref1')
    m2m_2 = models.ManyToManyField('old_invalid_models.SwappableModel', related_name='m2m_hardref2')
    m2m_3 = models.ManyToManyField(SwappedModel, related_name='m2m_hardref3')
    m2m_4 = models.ManyToManyField('old_invalid_models.SwappedModel', related_name='m2m_hardref4')


class BadIndexTogether1(models.Model):
    class Meta:
        index_together = [
            ["field_that_does_not_exist"],
        ]


model_errors = """
old_invalid_models.fielderrors: "field_": Field names cannot end with underscores, because this would lead to ambiguous queryset filters.
old_invalid_models.fielderrors: "generic_ip_notnull_blank": GenericIPAddressField can not accept blank values if null values are not allowed, as blank values are stored as null.
old_invalid_models.clash1: Accessor for field 'foreign' clashes with field 'Target.clash1_set'. Add a related_name argument to the definition for 'foreign'.
old_invalid_models.clash1: Accessor for field 'foreign' clashes with related m2m field 'Target.clash1_set'. Add a related_name argument to the definition for 'foreign'.
old_invalid_models.clash1: Reverse query name for field 'foreign' clashes with field 'Target.clash1'. Add a related_name argument to the definition for 'foreign'.
old_invalid_models.clash1: Accessor for m2m field 'm2m' clashes with field 'Target.clash1_set'. Add a related_name argument to the definition for 'm2m'.
old_invalid_models.clash1: Accessor for m2m field 'm2m' clashes with related field 'Target.clash1_set'. Add a related_name argument to the definition for 'm2m'.
old_invalid_models.clash1: Reverse query name for m2m field 'm2m' clashes with field 'Target.clash1'. Add a related_name argument to the definition for 'm2m'.
old_invalid_models.clash2: Accessor for field 'foreign_1' clashes with field 'Target.id'. Add a related_name argument to the definition for 'foreign_1'.
old_invalid_models.clash2: Accessor for field 'foreign_1' clashes with related m2m field 'Target.id'. Add a related_name argument to the definition for 'foreign_1'.
old_invalid_models.clash2: Reverse query name for field 'foreign_1' clashes with field 'Target.id'. Add a related_name argument to the definition for 'foreign_1'.
old_invalid_models.clash2: Reverse query name for field 'foreign_1' clashes with related m2m field 'Target.id'. Add a related_name argument to the definition for 'foreign_1'.
old_invalid_models.clash2: Accessor for field 'foreign_2' clashes with related m2m field 'Target.src_safe'. Add a related_name argument to the definition for 'foreign_2'.
old_invalid_models.clash2: Reverse query name for field 'foreign_2' clashes with related m2m field 'Target.src_safe'. Add a related_name argument to the definition for 'foreign_2'.
old_invalid_models.clash2: Accessor for m2m field 'm2m_1' clashes with field 'Target.id'. Add a related_name argument to the definition for 'm2m_1'.
old_invalid_models.clash2: Accessor for m2m field 'm2m_1' clashes with related field 'Target.id'. Add a related_name argument to the definition for 'm2m_1'.
old_invalid_models.clash2: Reverse query name for m2m field 'm2m_1' clashes with field 'Target.id'. Add a related_name argument to the definition for 'm2m_1'.
old_invalid_models.clash2: Reverse query name for m2m field 'm2m_1' clashes with related field 'Target.id'. Add a related_name argument to the definition for 'm2m_1'.
old_invalid_models.clash2: Accessor for m2m field 'm2m_2' clashes with related field 'Target.src_safe'. Add a related_name argument to the definition for 'm2m_2'.
old_invalid_models.clash2: Reverse query name for m2m field 'm2m_2' clashes with related field 'Target.src_safe'. Add a related_name argument to the definition for 'm2m_2'.
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
old_invalid_models.missingrelations: 'rel1' has a relation with model Rel1, which has either not been installed or is abstract.
old_invalid_models.missingrelations: 'rel2' has an m2m relation with model Rel2, which has either not been installed or is abstract.
old_invalid_models.grouptwo: 'primary' is a manually-defined m2m relation through model Membership, which does not have foreign keys to OldPerson and GroupTwo
old_invalid_models.grouptwo: 'secondary' is a manually-defined m2m relation through model MembershipMissingFK, which does not have foreign keys to Group and GroupTwo
old_invalid_models.missingmanualm2mmodel: 'missing_m2m' specifies an m2m relation through model MissingM2MModel, which has not been installed
old_invalid_models.group: The model Group has two manually-defined m2m relations through the model Membership, which is not permitted. Please consider using an extra field on your intermediary model instead.
old_invalid_models.group: Intermediary model RelationshipDoubleFK has more than one foreign key to OldPerson, which is ambiguous and is not permitted.
old_invalid_models.personselfrefm2m: Many-to-many fields with intermediate tables cannot be symmetrical.
old_invalid_models.personselfrefm2m: Intermediary model RelationshipTripleFK has more than two foreign keys to PersonSelfRefM2M, which is ambiguous and is not permitted.
old_invalid_models.personselfrefm2mexplicit: Many-to-many fields with intermediate tables cannot be symmetrical.
old_invalid_models.abstractrelationmodel: 'fk1' has a relation with model AbstractModel, which has either not been installed or is abstract.
old_invalid_models.abstractrelationmodel: 'fk2' has an m2m relation with model AbstractModel, which has either not been installed or is abstract.
old_invalid_models.uniquem2m: ManyToManyFields cannot be unique.  Remove the unique argument on 'unique_people'.
old_invalid_models.nonuniquefktarget1: Field 'bad' under model 'FKTarget' must have a unique=True constraint.
old_invalid_models.nonuniquefktarget2: Field 'bad' under model 'FKTarget' must have a unique=True constraint.
old_invalid_models.nonexistingorderingwithsingleunderscore: "ordering" refers to "does_not_exist", a field that doesn't exist.
old_invalid_models.invalidsetnull: 'fk' specifies on_delete=SET_NULL, but cannot be null.
old_invalid_models.invalidsetdefault: 'fk' specifies on_delete=SET_DEFAULT, but has no default value.
old_invalid_models.hardreferencemodel: 'fk_3' defines a relation with the model 'old_invalid_models.SwappedModel', which has been swapped out. Update the relation to point at settings.TEST_SWAPPED_MODEL.
old_invalid_models.hardreferencemodel: 'fk_4' defines a relation with the model 'old_invalid_models.SwappedModel', which has been swapped out. Update the relation to point at settings.TEST_SWAPPED_MODEL.
old_invalid_models.hardreferencemodel: 'm2m_3' defines a relation with the model 'old_invalid_models.SwappedModel', which has been swapped out. Update the relation to point at settings.TEST_SWAPPED_MODEL.
old_invalid_models.hardreferencemodel: 'm2m_4' defines a relation with the model 'old_invalid_models.SwappedModel', which has been swapped out. Update the relation to point at settings.TEST_SWAPPED_MODEL.
old_invalid_models.badswappablevalue: TEST_SWAPPED_MODEL_BAD_VALUE is not of the form 'app_label.app_name'.
old_invalid_models.badswappablemodel: Model has been swapped out for 'not_an_app.Target' which has not been installed or is abstract.
old_invalid_models.badindextogether1: "index_together" refers to field_that_does_not_exist, a field that doesn't exist.
"""

if not connection.features.interprets_empty_strings_as_nulls:
    model_errors += """old_invalid_models.primarykeynull: "my_pk_field": Primary key fields cannot have null=True."""


"""
# Error messages predated by a character:
# - 'x' -- the test was rewritten
# - 'm' -- the test is actually a model test, not a field test; not rewritten

m invalid_models.fielderrors: "field_": Field names cannot end with underscores, because this would lead to ambiguous queryset filters.
x invalid_models.fielderrors: "generic_ip_notnull_blank": GenericIPAddressField can not accept blank values if null values are not allowed, as blank values are stored as null.
m invalid_models.clash1: Accessor for field 'foreign' clashes with field 'Target.clash1_set'. Add a related_name argument to the definition for 'foreign'.
m invalid_models.clash1: Accessor for field 'foreign' clashes with related m2m field 'Target.clash1_set'. Add a related_name argument to the definition for 'foreign'.
m invalid_models.clash1: Reverse query name for field 'foreign' clashes with field 'Target.clash1'. Add a related_name argument to the definition for 'foreign'.
m invalid_models.clash1: Accessor for m2m field 'm2m' clashes with field 'Target.clash1_set'. Add a related_name argument to the definition for 'm2m'.
m invalid_models.clash1: Accessor for m2m field 'm2m' clashes with related field 'Target.clash1_set'. Add a related_name argument to the definition for 'm2m'.
m invalid_models.clash1: Reverse query name for m2m field 'm2m' clashes with field 'Target.clash1'. Add a related_name argument to the definition for 'm2m'.
m invalid_models.clash2: Accessor for field 'foreign_1' clashes with field 'Target.id'. Add a related_name argument to the definition for 'foreign_1'.
m invalid_models.clash2: Accessor for field 'foreign_1' clashes with related m2m field 'Target.id'. Add a related_name argument to the definition for 'foreign_1'.
m invalid_models.clash2: Reverse query name for field 'foreign_1' clashes with field 'Target.id'. Add a related_name argument to the definition for 'foreign_1'.
m invalid_models.clash2: Reverse query name for field 'foreign_1' clashes with related m2m field 'Target.id'. Add a related_name argument to the definition for 'foreign_1'.
m invalid_models.clash2: Accessor for field 'foreign_2' clashes with related m2m field 'Target.src_safe'. Add a related_name argument to the definition for 'foreign_2'.
m invalid_models.clash2: Reverse query name for field 'foreign_2' clashes with related m2m field 'Target.src_safe'. Add a related_name argument to the definition for 'foreign_2'.
m invalid_models.clash2: Accessor for m2m field 'm2m_1' clashes with field 'Target.id'. Add a related_name argument to the definition for 'm2m_1'.
m invalid_models.clash2: Accessor for m2m field 'm2m_1' clashes with related field 'Target.id'. Add a related_name argument to the definition for 'm2m_1'.
m invalid_models.clash2: Reverse query name for m2m field 'm2m_1' clashes with field 'Target.id'. Add a related_name argument to the definition for 'm2m_1'.
m invalid_models.clash2: Reverse query name for m2m field 'm2m_1' clashes with related field 'Target.id'. Add a related_name argument to the definition for 'm2m_1'.
m invalid_models.clash2: Accessor for m2m field 'm2m_2' clashes with related field 'Target.src_safe'. Add a related_name argument to the definition for 'm2m_2'.
m invalid_models.clash2: Reverse query name for m2m field 'm2m_2' clashes with related field 'Target.src_safe'. Add a related_name argument to the definition for 'm2m_2'.
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
x invalid_models.missingrelations: 'rel1' has a relation with model Rel1, which has either not been installed or is abstract.
x invalid_models.missingrelations: 'rel2' has an m2m relation with model Rel2, which has either not been installed or is abstract.
x invalid_models.grouptwo: 'primary' is a manually-defined m2m relation through model Membership, which does not have foreign keys to OldPerson and GroupTwo
x invalid_models.grouptwo: 'secondary' is a manually-defined m2m relation through model MembershipMissingFK, which does not have foreign keys to Group and GroupTwo
x invalid_models.missingmanualm2mmodel: 'missing_m2m' specifies an m2m relation through model MissingM2MModel, which has not been installed
m invalid_models.group: The model Group has two manually-defined m2m relations through the model Membership, which is not permitted. Please consider using an extra field on your intermediary model instead.
x invalid_models.group: Intermediary model RelationshipDoubleFK has more than one foreign key to OldPerson, which is ambiguous and is not permitted.
x? invalid_models.personselfrefm2m: Many-to-many fields with intermediate tables cannot be symmetrical.
x? invalid_models.personselfrefm2m: Intermediary model RelationshipTripleFK has more than two foreign keys to PersonSelfRefM2M, which is ambiguous and is not permitted.
x? invalid_models.personselfrefm2mexplicit: Many-to-many fields with intermediate tables cannot be symmetrical.
x invalid_models.abstractrelationmodel: 'fk1' has a relation with model AbstractModel, which has either not been installed or is abstract.
x invalid_models.abstractrelationmodel: 'fk2' has an m2m relation with model AbstractModel, which has either not been installed or is abstract.
x invalid_models.uniquem2m: ManyToManyFields cannot be unique.  Remove the unique argument on 'unique_people'.
x invalid_models.nonuniquefktarget1: Field 'bad' under model 'FKTarget' must have a unique=True constraint.
x invalid_models.nonuniquefktarget2: Field 'bad' under model 'FKTarget' must have a unique=True constraint.
m invalid_models.nonexistingorderingwithsingleunderscore: "ordering" refers to "does_not_exist", a field that doesn't exist.
x invalid_models.invalidsetnull: 'fk' specifies on_delete=SET_NULL, but cannot be null.
x invalid_models.invalidsetdefault: 'fk' specifies on_delete=SET_DEFAULT, but has no default value.
m? invalid_models.hardreferencemodel: 'fk_3' defines a relation with the model 'invalid_models.SwappedModel', which has been swapped out. Update the relation to point at settings.TEST_SWAPPED_MODEL.
m? invalid_models.hardreferencemodel: 'fk_4' defines a relation with the model 'invalid_models.SwappedModel', which has been swapped out. Update the relation to point at settings.TEST_SWAPPED_MODEL.
m? invalid_models.hardreferencemodel: 'm2m_3' defines a relation with the model 'invalid_models.SwappedModel', which has been swapped out. Update the relation to point at settings.TEST_SWAPPED_MODEL.
m? invalid_models.hardreferencemodel: 'm2m_4' defines a relation with the model 'invalid_models.SwappedModel', which has been swapped out. Update the relation to point at settings.TEST_SWAPPED_MODEL.
m invalid_models.badswappablevalue: TEST_SWAPPED_MODEL_BAD_VALUE is not of the form 'app_label.app_name'.
m invalid_models.badswappablemodel: Model has been swapped out for 'not_an_app.Target' which has not been installed or is abstract.
m invalid_models.badindextogether1: "index_together" refers to field_that_does_not_exist, a field that doesn't exist.
"""
