from __future__ import unicode_literals

from django.apps.registry import Apps
from django.db import models


# We're testing app registry presence on load, so this is handy.

new_apps = Apps(['apps'])


class TotallyNormal(models.Model):
    name = models.CharField(max_length=255)


class SoAlternative(models.Model):
    name = models.CharField(max_length=255)

    class Meta:
        apps = new_apps

new_apps_2 = Apps(['apps'])


class Relation(models.Model):
    class Meta:
        apps = new_apps_2


class ProxyRelation(Relation):
    class Meta:
        apps = new_apps_2
        proxy = True


class AbstractPerson(models.Model):
    # DATA fields
    data_abstract = models.CharField(max_length=10)

    # M2M fields
    m2m_abstract = models.ManyToManyField(Relation, related_name='m2m_abstract_rel')
    friends_abstract = models.ManyToManyField('self', related_name='friends_abstract', symmetrical=True)
    following_abstract = models.ManyToManyField('self', related_name='followers_abstract', symmetrical=False)

    class Meta:
        apps = new_apps_2
        abstract = True


class BasePerson(AbstractPerson):
    # DATA fields
    data_base = models.CharField(max_length=10)
    fk_base = models.ForeignKey(Relation, related_name='fk_base_rel')

    # M2M fields
    m2m_base = models.ManyToManyField(Relation, related_name='m2m_base_rel')
    friends_base = models.ManyToManyField('self', related_name='friends_base', symmetrical=True)
    following_base = models.ManyToManyField('self', related_name='followers_base', symmetrical=False)

    # VIRTUAL fields
    data_not_concrete_base = models.ForeignObject(
        Relation,
        from_fields=['base_non_concrete_id'],
        to_fields=['id'],
        related_name='fo_base_rel',
    )

    class Meta:
        apps = new_apps_2


class Person(models.Model):
    data_base = models.CharField(max_length=10)
    fk_to_proxy = models.ForeignKey(ProxyRelation, related_name='fk_to_proxy')

    class Meta:
        apps = new_apps_2
