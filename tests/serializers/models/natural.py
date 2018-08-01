"""Models for test_natural.py"""
from django.db import models


class NaturalKeyAnchorManager(models.Manager):
    def get_by_natural_key(self, data):
        return self.get(data=data)


class NaturalKeyAnchor(models.Model):
    objects = NaturalKeyAnchorManager()

    data = models.CharField(max_length=100, unique=True)
    title = models.CharField(max_length=100, null=True)

    def natural_key(self):
        return (self.data,)


class FKDataNaturalKey(models.Model):
    data = models.ForeignKey(NaturalKeyAnchor, models.SET_NULL, null=True)


class NaturalKeyThing(models.Model):
    key = models.CharField(max_length=100)
    other_thing = models.ForeignKey('NaturalKeyThing', on_delete=models.CASCADE, null=True)
    other_things = models.ManyToManyField('NaturalKeyThing', related_name='thing_m2m_set')

    class Manager(models.Manager):
        def get_by_natural_key(self, key):
            return self.get(key=key)

    objects = Manager()

    def natural_key(self):
        return (self.key,)

    def __str__(self):
        return self.key
