from __future__ import unicode_literals

from django.db import models
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class Topping(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class Pizza(models.Model):
    name = models.CharField(max_length=50)
    toppings = models.ManyToManyField(Topping, blank=True)

    def __str__(self):
        return self.name
