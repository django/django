"""
Many-to-one relationships that can be null

To define a many-to-one relationship that can have a null foreign key, use
``ForeignKey()`` with ``null=True`` .
"""

from django.db import models


class Reporter(models.Model):
    name = models.CharField(max_length=30)


class Article(models.Model):
    headline = models.CharField(max_length=100)
    reporter = models.ForeignKey(Reporter, models.SET_NULL, null=True)

    class Meta:
        ordering = ("headline",)

    def __str__(self):
        return self.headline


class Car(models.Model):
    make = models.CharField(max_length=100, null=True, unique=True)


class Driver(models.Model):
    car = models.ForeignKey(
        Car, models.SET_NULL, to_field="make", null=True, related_name="drivers"
    )
