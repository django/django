"""
Tests for the update() queryset method that allows in-place, multi-object
updates.
"""

from django.db import models


class DataPoint(models.Model):
    name = models.CharField(max_length=20)
    value = models.CharField(max_length=20)
    another_value = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return self.name


class RelatedPoint(models.Model):
    name = models.CharField(max_length=20)
    data = models.ForeignKey(DataPoint, models.CASCADE)

    def __str__(self):
        return self.name


class A(models.Model):
    x = models.IntegerField(default=10)


class B(models.Model):
    a = models.ForeignKey(A, models.CASCADE)
    y = models.IntegerField(default=10)


class C(models.Model):
    y = models.IntegerField(default=10)


class D(C):
    a = models.ForeignKey(A, models.CASCADE)


class Foo(models.Model):
    target = models.CharField(max_length=10, unique=True)


class Bar(models.Model):
    foo = models.ForeignKey(Foo, models.CASCADE, to_field='target')
