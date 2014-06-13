from django.db import models

from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType


class Relation(models.Model):
    pass


# Models
class AbstractPerson(models.Model):
    class Meta:
        abstract = True

    # DATA fields
    data_abstract = models.CharField(max_length=10)
    fk_abstract = models.ForeignKey(Relation, related_name='fk_abstract_rel')

    # M2M fields
    m2m_abstract = models.ManyToManyField(Relation,
                                          related_name='m2m_abstract_rel')

    # VIRTUAL fields
    data_not_concrete_abstract = models.ForeignObject(
        Relation,
        from_fields=['abstract_non_concrete_id'],
        to_fields=['id'],
        related_name='fo_abstract_rel'
    )

    # GFK fields
    content_type_abstract = models.ForeignKey(ContentType, related_name='+')
    object_id_abstract = models.PositiveIntegerField()
    content_object_abstract = GenericForeignKey('content_type_abstract',
                                                'object_id_abstract')

    # GR fields
    generic_relation_abstract = GenericRelation(Relation)


class BasePerson(AbstractPerson):
    # DATA fields
    data_base = models.CharField(max_length=10)
    fk_base = models.ForeignKey(Relation, related_name='fk_base_rel')

    # M2M fields
    m2m_base = models.ManyToManyField(Relation, related_name='m2m_base_rel')
    friends = models.ManyToManyField('self', related_name='friends',
                                     symmetrical=True)
    following = models.ManyToManyField('self', related_name='followers',
                                       symmetrical=False)

    # VIRTUAL fields
    data_not_concrete_base = models.ForeignObject(
        Relation,
        from_fields=['base_non_concrete_id'], to_fields=['id'],
        related_name='fo_base_rel'
    )

    # GFK fields
    content_type_base = models.ForeignKey(ContentType,
                                          related_name='+')
    object_id_base = models.PositiveIntegerField()
    content_object_base = GenericForeignKey('content_type_base',
                                            'object_id_base')

    # GR fields
    generic_relation_base = GenericRelation(Relation)


class Person(BasePerson):
    # DATA fields
    data_inherited = models.CharField(max_length=10)
    fk_inherited = models.ForeignKey(Relation, related_name='fk_concrete_rel')

    # M2M Fields
    m2m_inherited = models.ManyToManyField(Relation,
                                           related_name='m2m_concrete_rel')

    # VIRTUAL fields
    data_not_concrete_inherited = models.ForeignObject(
        Relation,
        from_fields=['model_non_concrete_id'], to_fields=['id'],
        related_name='fo_concrete_rel'
    )

    # GFK fields
    content_type_concrete = models.ForeignKey(ContentType, related_name='+')
    object_id_concrete = models.PositiveIntegerField()
    content_object_concrete = GenericForeignKey('content_type_concrete',
                                                'object_id_concrete')

    # GR fields
    generic_relation_concrete = GenericRelation(Relation)


class ProxyPerson(Person):
    class Meta:
        proxy = True


# Models with FK pointing to Person
class Relating(models.Model):

    # ForeignKey to BasePerson
    baseperson = models.ForeignKey(BasePerson,
                               related_name='relating_baseperson')
    baseperson_hidden = models.ForeignKey(BasePerson,
                               related_name='+')

    # ForeignKey to Person
    person = models.ForeignKey(Person,
                               related_name='relating_person')
    person_hidden = models.ForeignKey(Person,
                                      related_name='+')

    # ForeignKey to ProxyPerson
    proxyperson = models.ForeignKey(ProxyPerson,
                                    related_name='relating_proxyperson')
    proxyperson_hidden = models.ForeignKey(ProxyPerson,
                                      related_name='+')

    # ManyToManyField to BasePerson
    basepeople = models.ManyToManyField(BasePerson,
                                        related_name='relating_basepeople')
    basepeople_hidden = models.ManyToManyField(BasePerson,
                                               related_name='+')

    # ManyToManyField to Person
    people = models.ManyToManyField(Person,
                                    related_name='relating_people')
    people_hidden = models.ManyToManyField(Person,
                                           related_name='+')
