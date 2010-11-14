"""
26. Invalid models

This example exists purely to point out errors in models.
"""

from django.contrib.contenttypes import generic
from django.db import models

class FieldErrors(models.Model):
    charfield = models.CharField()
    charfield2 = models.CharField(max_length=-1)
    charfield3 = models.CharField(max_length="bad")
    decimalfield = models.DecimalField()
    decimalfield2 = models.DecimalField(max_digits=-1, decimal_places=-1)
    decimalfield3 = models.DecimalField(max_digits="bad", decimal_places="bad")
    filefield = models.FileField()
    choices = models.CharField(max_length=10, choices='bad')
    choices2 = models.CharField(max_length=10, choices=[(1,2,3),(1,2,3)])
    index = models.CharField(max_length=10, db_index='bad')
    field_ = models.CharField(max_length=10)
    nullbool = models.BooleanField(null=True)

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
    year = models.PositiveIntegerField() #1960
    make = models.CharField(max_length=10) #Aston Martin
    name = models.CharField(max_length=10) #DB 4 GT

class Car(models.Model):
    colour = models.CharField(max_length=5)
    model = models.ForeignKey(Model)

class MissingRelations(models.Model):
    rel1 = models.ForeignKey("Rel1")
    rel2 = models.ManyToManyField("Rel2")

class MissingManualM2MModel(models.Model):
    name = models.CharField(max_length=5)
    missing_m2m = models.ManyToManyField(Model, through="MissingM2MModel")

class Person(models.Model):
    name = models.CharField(max_length=5)

class Group(models.Model):
    name = models.CharField(max_length=5)
    primary = models.ManyToManyField(Person, through="Membership", related_name="primary")
    secondary = models.ManyToManyField(Person, through="Membership", related_name="secondary")
    tertiary = models.ManyToManyField(Person, through="RelationshipDoubleFK", related_name="tertiary")

class GroupTwo(models.Model):
    name = models.CharField(max_length=5)
    primary = models.ManyToManyField(Person, through="Membership")
    secondary = models.ManyToManyField(Group, through="MembershipMissingFK")

class Membership(models.Model):
    person = models.ForeignKey(Person)
    group = models.ForeignKey(Group)
    not_default_or_null = models.CharField(max_length=5)

class MembershipMissingFK(models.Model):
    person = models.ForeignKey(Person)

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
    first = models.ForeignKey(Person, related_name="first_related_name")
    second = models.ForeignKey(Person, related_name="second_related_name")
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
    unique_people = models.ManyToManyField(Person, unique=True)

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

class Tag(models.Model):
   name = models.CharField("name", max_length=20)

class TaggedObject(models.Model):
   object_id = models.PositiveIntegerField("Object ID")
   tag = models.ForeignKey(Tag)
   content_object = generic.GenericForeignKey()

class UserTaggedObject(models.Model):
   object_tag = models.ForeignKey(TaggedObject)

class ArticleAttachment(models.Model):
   tags = generic.GenericRelation(TaggedObject)
   user_tags = generic.GenericRelation(UserTaggedObject)

model_errors = """invalid_models.fielderrors: "charfield": CharFields require a "max_length" attribute that is a positive integer.
invalid_models.fielderrors: "charfield2": CharFields require a "max_length" attribute that is a positive integer.
invalid_models.fielderrors: "charfield3": CharFields require a "max_length" attribute that is a positive integer.
invalid_models.fielderrors: "decimalfield": DecimalFields require a "decimal_places" attribute that is a non-negative integer.
invalid_models.fielderrors: "decimalfield": DecimalFields require a "max_digits" attribute that is a positive integer.
invalid_models.fielderrors: "decimalfield2": DecimalFields require a "decimal_places" attribute that is a non-negative integer.
invalid_models.fielderrors: "decimalfield2": DecimalFields require a "max_digits" attribute that is a positive integer.
invalid_models.fielderrors: "decimalfield3": DecimalFields require a "decimal_places" attribute that is a non-negative integer.
invalid_models.fielderrors: "decimalfield3": DecimalFields require a "max_digits" attribute that is a positive integer.
invalid_models.fielderrors: "filefield": FileFields require an "upload_to" attribute.
invalid_models.fielderrors: "choices": "choices" should be iterable (e.g., a tuple or list).
invalid_models.fielderrors: "choices2": "choices" should be a sequence of two-tuples.
invalid_models.fielderrors: "choices2": "choices" should be a sequence of two-tuples.
invalid_models.fielderrors: "index": "db_index" should be either None, True or False.
invalid_models.fielderrors: "field_": Field names cannot end with underscores, because this would lead to ambiguous queryset filters.
invalid_models.fielderrors: "nullbool": BooleanFields do not accept null values. Use a NullBooleanField instead.
invalid_models.clash1: Accessor for field 'foreign' clashes with field 'Target.clash1_set'. Add a related_name argument to the definition for 'foreign'.
invalid_models.clash1: Accessor for field 'foreign' clashes with related m2m field 'Target.clash1_set'. Add a related_name argument to the definition for 'foreign'.
invalid_models.clash1: Reverse query name for field 'foreign' clashes with field 'Target.clash1'. Add a related_name argument to the definition for 'foreign'.
invalid_models.clash1: Accessor for m2m field 'm2m' clashes with field 'Target.clash1_set'. Add a related_name argument to the definition for 'm2m'.
invalid_models.clash1: Accessor for m2m field 'm2m' clashes with related field 'Target.clash1_set'. Add a related_name argument to the definition for 'm2m'.
invalid_models.clash1: Reverse query name for m2m field 'm2m' clashes with field 'Target.clash1'. Add a related_name argument to the definition for 'm2m'.
invalid_models.clash2: Accessor for field 'foreign_1' clashes with field 'Target.id'. Add a related_name argument to the definition for 'foreign_1'.
invalid_models.clash2: Accessor for field 'foreign_1' clashes with related m2m field 'Target.id'. Add a related_name argument to the definition for 'foreign_1'.
invalid_models.clash2: Reverse query name for field 'foreign_1' clashes with field 'Target.id'. Add a related_name argument to the definition for 'foreign_1'.
invalid_models.clash2: Reverse query name for field 'foreign_1' clashes with related m2m field 'Target.id'. Add a related_name argument to the definition for 'foreign_1'.
invalid_models.clash2: Accessor for field 'foreign_2' clashes with related m2m field 'Target.src_safe'. Add a related_name argument to the definition for 'foreign_2'.
invalid_models.clash2: Reverse query name for field 'foreign_2' clashes with related m2m field 'Target.src_safe'. Add a related_name argument to the definition for 'foreign_2'.
invalid_models.clash2: Accessor for m2m field 'm2m_1' clashes with field 'Target.id'. Add a related_name argument to the definition for 'm2m_1'.
invalid_models.clash2: Accessor for m2m field 'm2m_1' clashes with related field 'Target.id'. Add a related_name argument to the definition for 'm2m_1'.
invalid_models.clash2: Reverse query name for m2m field 'm2m_1' clashes with field 'Target.id'. Add a related_name argument to the definition for 'm2m_1'.
invalid_models.clash2: Reverse query name for m2m field 'm2m_1' clashes with related field 'Target.id'. Add a related_name argument to the definition for 'm2m_1'.
invalid_models.clash2: Accessor for m2m field 'm2m_2' clashes with related field 'Target.src_safe'. Add a related_name argument to the definition for 'm2m_2'.
invalid_models.clash2: Reverse query name for m2m field 'm2m_2' clashes with related field 'Target.src_safe'. Add a related_name argument to the definition for 'm2m_2'.
invalid_models.clash3: Accessor for field 'foreign_1' clashes with field 'Target2.foreign_tgt'. Add a related_name argument to the definition for 'foreign_1'.
invalid_models.clash3: Accessor for field 'foreign_1' clashes with related m2m field 'Target2.foreign_tgt'. Add a related_name argument to the definition for 'foreign_1'.
invalid_models.clash3: Reverse query name for field 'foreign_1' clashes with field 'Target2.foreign_tgt'. Add a related_name argument to the definition for 'foreign_1'.
invalid_models.clash3: Reverse query name for field 'foreign_1' clashes with related m2m field 'Target2.foreign_tgt'. Add a related_name argument to the definition for 'foreign_1'.
invalid_models.clash3: Accessor for field 'foreign_2' clashes with m2m field 'Target2.m2m_tgt'. Add a related_name argument to the definition for 'foreign_2'.
invalid_models.clash3: Accessor for field 'foreign_2' clashes with related m2m field 'Target2.m2m_tgt'. Add a related_name argument to the definition for 'foreign_2'.
invalid_models.clash3: Reverse query name for field 'foreign_2' clashes with m2m field 'Target2.m2m_tgt'. Add a related_name argument to the definition for 'foreign_2'.
invalid_models.clash3: Reverse query name for field 'foreign_2' clashes with related m2m field 'Target2.m2m_tgt'. Add a related_name argument to the definition for 'foreign_2'.
invalid_models.clash3: Accessor for m2m field 'm2m_1' clashes with field 'Target2.foreign_tgt'. Add a related_name argument to the definition for 'm2m_1'.
invalid_models.clash3: Accessor for m2m field 'm2m_1' clashes with related field 'Target2.foreign_tgt'. Add a related_name argument to the definition for 'm2m_1'.
invalid_models.clash3: Reverse query name for m2m field 'm2m_1' clashes with field 'Target2.foreign_tgt'. Add a related_name argument to the definition for 'm2m_1'.
invalid_models.clash3: Reverse query name for m2m field 'm2m_1' clashes with related field 'Target2.foreign_tgt'. Add a related_name argument to the definition for 'm2m_1'.
invalid_models.clash3: Accessor for m2m field 'm2m_2' clashes with m2m field 'Target2.m2m_tgt'. Add a related_name argument to the definition for 'm2m_2'.
invalid_models.clash3: Accessor for m2m field 'm2m_2' clashes with related field 'Target2.m2m_tgt'. Add a related_name argument to the definition for 'm2m_2'.
invalid_models.clash3: Reverse query name for m2m field 'm2m_2' clashes with m2m field 'Target2.m2m_tgt'. Add a related_name argument to the definition for 'm2m_2'.
invalid_models.clash3: Reverse query name for m2m field 'm2m_2' clashes with related field 'Target2.m2m_tgt'. Add a related_name argument to the definition for 'm2m_2'.
invalid_models.clashforeign: Accessor for field 'foreign' clashes with field 'Target2.clashforeign_set'. Add a related_name argument to the definition for 'foreign'.
invalid_models.clashm2m: Accessor for m2m field 'm2m' clashes with m2m field 'Target2.clashm2m_set'. Add a related_name argument to the definition for 'm2m'.
invalid_models.target2: Accessor for field 'foreign_tgt' clashes with related m2m field 'Target.target2_set'. Add a related_name argument to the definition for 'foreign_tgt'.
invalid_models.target2: Accessor for field 'foreign_tgt' clashes with related m2m field 'Target.target2_set'. Add a related_name argument to the definition for 'foreign_tgt'.
invalid_models.target2: Accessor for field 'foreign_tgt' clashes with related field 'Target.target2_set'. Add a related_name argument to the definition for 'foreign_tgt'.
invalid_models.target2: Accessor for field 'clashforeign_set' clashes with related m2m field 'Target.target2_set'. Add a related_name argument to the definition for 'clashforeign_set'.
invalid_models.target2: Accessor for field 'clashforeign_set' clashes with related m2m field 'Target.target2_set'. Add a related_name argument to the definition for 'clashforeign_set'.
invalid_models.target2: Accessor for field 'clashforeign_set' clashes with related field 'Target.target2_set'. Add a related_name argument to the definition for 'clashforeign_set'.
invalid_models.target2: Accessor for m2m field 'm2m_tgt' clashes with related field 'Target.target2_set'. Add a related_name argument to the definition for 'm2m_tgt'.
invalid_models.target2: Accessor for m2m field 'm2m_tgt' clashes with related field 'Target.target2_set'. Add a related_name argument to the definition for 'm2m_tgt'.
invalid_models.target2: Accessor for m2m field 'm2m_tgt' clashes with related m2m field 'Target.target2_set'. Add a related_name argument to the definition for 'm2m_tgt'.
invalid_models.target2: Accessor for m2m field 'm2m_tgt' clashes with related m2m field 'Target.target2_set'. Add a related_name argument to the definition for 'm2m_tgt'.
invalid_models.target2: Accessor for m2m field 'm2m_tgt' clashes with related m2m field 'Target.target2_set'. Add a related_name argument to the definition for 'm2m_tgt'.
invalid_models.target2: Accessor for m2m field 'clashm2m_set' clashes with related field 'Target.target2_set'. Add a related_name argument to the definition for 'clashm2m_set'.
invalid_models.target2: Accessor for m2m field 'clashm2m_set' clashes with related field 'Target.target2_set'. Add a related_name argument to the definition for 'clashm2m_set'.
invalid_models.target2: Accessor for m2m field 'clashm2m_set' clashes with related m2m field 'Target.target2_set'. Add a related_name argument to the definition for 'clashm2m_set'.
invalid_models.target2: Accessor for m2m field 'clashm2m_set' clashes with related m2m field 'Target.target2_set'. Add a related_name argument to the definition for 'clashm2m_set'.
invalid_models.target2: Accessor for m2m field 'clashm2m_set' clashes with related m2m field 'Target.target2_set'. Add a related_name argument to the definition for 'clashm2m_set'.
invalid_models.selfclashforeign: Accessor for field 'selfclashforeign_set' clashes with field 'SelfClashForeign.selfclashforeign_set'. Add a related_name argument to the definition for 'selfclashforeign_set'.
invalid_models.selfclashforeign: Reverse query name for field 'selfclashforeign_set' clashes with field 'SelfClashForeign.selfclashforeign'. Add a related_name argument to the definition for 'selfclashforeign_set'.
invalid_models.selfclashforeign: Accessor for field 'foreign_1' clashes with field 'SelfClashForeign.id'. Add a related_name argument to the definition for 'foreign_1'.
invalid_models.selfclashforeign: Reverse query name for field 'foreign_1' clashes with field 'SelfClashForeign.id'. Add a related_name argument to the definition for 'foreign_1'.
invalid_models.selfclashforeign: Accessor for field 'foreign_2' clashes with field 'SelfClashForeign.src_safe'. Add a related_name argument to the definition for 'foreign_2'.
invalid_models.selfclashforeign: Reverse query name for field 'foreign_2' clashes with field 'SelfClashForeign.src_safe'. Add a related_name argument to the definition for 'foreign_2'.
invalid_models.selfclashm2m: Accessor for m2m field 'selfclashm2m_set' clashes with m2m field 'SelfClashM2M.selfclashm2m_set'. Add a related_name argument to the definition for 'selfclashm2m_set'.
invalid_models.selfclashm2m: Reverse query name for m2m field 'selfclashm2m_set' clashes with field 'SelfClashM2M.selfclashm2m'. Add a related_name argument to the definition for 'selfclashm2m_set'.
invalid_models.selfclashm2m: Accessor for m2m field 'selfclashm2m_set' clashes with related m2m field 'SelfClashM2M.selfclashm2m_set'. Add a related_name argument to the definition for 'selfclashm2m_set'.
invalid_models.selfclashm2m: Accessor for m2m field 'm2m_1' clashes with field 'SelfClashM2M.id'. Add a related_name argument to the definition for 'm2m_1'.
invalid_models.selfclashm2m: Accessor for m2m field 'm2m_2' clashes with field 'SelfClashM2M.src_safe'. Add a related_name argument to the definition for 'm2m_2'.
invalid_models.selfclashm2m: Reverse query name for m2m field 'm2m_1' clashes with field 'SelfClashM2M.id'. Add a related_name argument to the definition for 'm2m_1'.
invalid_models.selfclashm2m: Reverse query name for m2m field 'm2m_2' clashes with field 'SelfClashM2M.src_safe'. Add a related_name argument to the definition for 'm2m_2'.
invalid_models.selfclashm2m: Accessor for m2m field 'm2m_3' clashes with m2m field 'SelfClashM2M.selfclashm2m_set'. Add a related_name argument to the definition for 'm2m_3'.
invalid_models.selfclashm2m: Accessor for m2m field 'm2m_3' clashes with related m2m field 'SelfClashM2M.selfclashm2m_set'. Add a related_name argument to the definition for 'm2m_3'.
invalid_models.selfclashm2m: Accessor for m2m field 'm2m_3' clashes with related m2m field 'SelfClashM2M.selfclashm2m_set'. Add a related_name argument to the definition for 'm2m_3'.
invalid_models.selfclashm2m: Accessor for m2m field 'm2m_4' clashes with m2m field 'SelfClashM2M.selfclashm2m_set'. Add a related_name argument to the definition for 'm2m_4'.
invalid_models.selfclashm2m: Accessor for m2m field 'm2m_4' clashes with related m2m field 'SelfClashM2M.selfclashm2m_set'. Add a related_name argument to the definition for 'm2m_4'.
invalid_models.selfclashm2m: Accessor for m2m field 'm2m_4' clashes with related m2m field 'SelfClashM2M.selfclashm2m_set'. Add a related_name argument to the definition for 'm2m_4'.
invalid_models.selfclashm2m: Reverse query name for m2m field 'm2m_3' clashes with field 'SelfClashM2M.selfclashm2m'. Add a related_name argument to the definition for 'm2m_3'.
invalid_models.selfclashm2m: Reverse query name for m2m field 'm2m_4' clashes with field 'SelfClashM2M.selfclashm2m'. Add a related_name argument to the definition for 'm2m_4'.
invalid_models.missingrelations: 'rel1' has a relation with model Rel1, which has either not been installed or is abstract.
invalid_models.missingrelations: 'rel2' has an m2m relation with model Rel2, which has either not been installed or is abstract.
invalid_models.grouptwo: 'primary' is a manually-defined m2m relation through model Membership, which does not have foreign keys to Person and GroupTwo
invalid_models.grouptwo: 'secondary' is a manually-defined m2m relation through model MembershipMissingFK, which does not have foreign keys to Group and GroupTwo
invalid_models.missingmanualm2mmodel: 'missing_m2m' specifies an m2m relation through model MissingM2MModel, which has not been installed
invalid_models.group: The model Group has two manually-defined m2m relations through the model Membership, which is not permitted. Please consider using an extra field on your intermediary model instead.
invalid_models.group: Intermediary model RelationshipDoubleFK has more than one foreign key to Person, which is ambiguous and is not permitted.
invalid_models.personselfrefm2m: Many-to-many fields with intermediate tables cannot be symmetrical.
invalid_models.personselfrefm2m: Intermediary model RelationshipTripleFK has more than two foreign keys to PersonSelfRefM2M, which is ambiguous and is not permitted.
invalid_models.personselfrefm2mexplicit: Many-to-many fields with intermediate tables cannot be symmetrical.
invalid_models.abstractrelationmodel: 'fk1' has a relation with model AbstractModel, which has either not been installed or is abstract.
invalid_models.abstractrelationmodel: 'fk2' has an m2m relation with model AbstractModel, which has either not been installed or is abstract.
invalid_models.uniquem2m: ManyToManyFields cannot be unique.  Remove the unique argument on 'unique_people'.
invalid_models.nonuniquefktarget1: Field 'bad' under model 'FKTarget' must have a unique=True constraint.
invalid_models.nonuniquefktarget2: Field 'bad' under model 'FKTarget' must have a unique=True constraint.
invalid_models.nonexistingorderingwithsingleunderscore: "ordering" refers to "does_not_exist", a field that doesn't exist.
invalid_models.invalidsetnull: 'fk' specifies on_delete=SET_NULL, but cannot be null.
invalid_models.invalidsetdefault: 'fk' specifies on_delete=SET_DEFAULT, but has no default value.
invalid_models.articleattachment: Model 'UserTaggedObject' must have a GenericForeignKey in order to create a GenericRelation that points to it.
"""
