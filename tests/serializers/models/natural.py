"""Models for test_natural.py"""
import uuid

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


class FooManager(models.Manager):
    def get_by_natural_key(self, name):
        return self.get(name=name)


class Foo(models.Model):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)

    objects = FooManager()

    def natural_key(self):
        return (self.name,)
