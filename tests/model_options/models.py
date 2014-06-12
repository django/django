from django.db import models

from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType


# VIRTUAL field models
class AbstractVirtualRelation(models.Model):
    pass


class BaseVirtualRelation(models.Model):
    pass


class ConcreteVirtualRelation(models.Model):
    pass


# FOREIGN KEY models
class AbstractRelatedObject(models.Model):
    pass


class BaseRelatedObject(models.Model):
    pass


class ConcreteRelatedObject(models.Model):
    pass


# M2M models
class AbstractRelatedM2M(models.Model):
    pass


class BaseRelatedM2M(models.Model):
    pass


class ConcreteRelatedM2M(models.Model):
    pass


# Models
class AbstractPerson(models.Model):
    class Meta:
        abstract = True
    data_abstract = models.CharField(max_length=10)
    fk_abstract = models.ForeignKey(AbstractRelatedObject)
    m2m_abstract = models.ManyToManyField(AbstractRelatedM2M)
    data_not_concrete_abstract = models.ForeignObject(AbstractVirtualRelation,
            from_fields=['abstract_non_concrete_id'], to_fields=['id'])


class BasePerson(AbstractPerson):
    data_base = models.CharField(max_length=10)
    fk_base = models.ForeignKey(BaseRelatedObject)
    m2m_base = models.ManyToManyField(BaseRelatedM2M)
    data_not_concrete_base = models.ForeignObject(BaseVirtualRelation,
            from_fields=['base_non_concrete_id'], to_fields=['id'])
    friends = models.ManyToManyField(
        'self', related_name='friends', symmetrical=True)
    following = models.ManyToManyField(
        'self', related_name='followers', symmetrical=False)

    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type',
                                       'object_id')


class Person(BasePerson):
    data_inherited = models.CharField(max_length=10)
    fk_inherited = models.ForeignKey(ConcreteRelatedObject)
    m2m_inherited = models.ManyToManyField(ConcreteRelatedM2M)
    data_not_concrete_inherited = models.ForeignObject(ConcreteVirtualRelation,
            from_fields=['model_non_concrete_id'], to_fields=['id'])


class ProxyPerson(Person):
    class Meta:
        proxy = True


# Models with FK pointing to Person
class Computer(models.Model):
    person = models.ForeignKey(BasePerson)


class ComputerHidden(models.Model):
    person = models.ForeignKey(BasePerson,
                               related_name='+')


class Watch(models.Model):
    person = models.ForeignKey(Person)


class WatchHidden(models.Model):
    person = models.ForeignKey(Person,
                               related_name='+')


class Hometown(models.Model):
    person = models.ForeignKey(ProxyPerson)


class HometownHidden(models.Model):
    person = models.ForeignKey(ProxyPerson,
                               related_name='+')


# Models with M2M pointing to Person
class Car(models.Model):
    people = models.ManyToManyField(BasePerson)


class CarHidden(models.Model):
    people = models.ManyToManyField(BasePerson,
                               related_name='+')


class Photo(models.Model):
    people = models.ManyToManyField(Person)


class PhotoHidden(models.Model):
    people = models.ManyToManyField(Person,
                                    related_name='+')
