# -*- coding: utf-8 -*-
from django.db import models
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class Village(models.Model):
    name = models.CharField(max_length=100)


@python_2_unicode_compatible
class Population(models.Model):
    village = models.ForeignKey(Village)
    total = models.IntegerField()


@python_2_unicode_compatible
class City(models.Model):
    id = models.AutoField(primary_key=True, big=True)
    name = models.CharField(max_length=100)


@python_2_unicode_compatible
class Weather(models.Model):
    city = models.ForeignKey(City)
    temp = models.IntegerField()
