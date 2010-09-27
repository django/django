"""
Tests for various ways of registering models with the admin site.
"""

from django.db import models

class Person(models.Model):
    name = models.CharField(max_length=200)

class Place(models.Model):
    name = models.CharField(max_length=200)
