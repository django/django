"""
Tests for various ways of registering models with the admin site.
"""

from django.db import models
from django.contrib import admin

class Person(models.Model):
    name = models.CharField(max_length=200)

class Place(models.Model):
    name = models.CharField(max_length=200)

__test__ = {'API_TESTS':"""


# Bare registration
>>> site = admin.AdminSite()
>>> site.register(Person)
>>> site._registry[Person]
<django.contrib.admin.options.ModelAdmin object at ...>

# Registration with a ModelAdmin
>>> site = admin.AdminSite()
>>> class NameAdmin(admin.ModelAdmin):
...     list_display = ['name']
...     save_on_top = True

>>> site.register(Person, NameAdmin)
>>> site._registry[Person]
<regressiontests.admin_registration.models.NameAdmin object at ...>

# You can't register the same model twice
>>> site.register(Person)
Traceback (most recent call last):
    ...
AlreadyRegistered: The model Person is already registered

# Registration using **options
>>> site = admin.AdminSite()
>>> site.register(Person, search_fields=['name'])
>>> site._registry[Person].search_fields
['name']

# With both admin_class and **options the **options override the fields in
# the admin class.
>>> site = admin.AdminSite()
>>> site.register(Person, NameAdmin, search_fields=["name"], list_display=['__str__'])
>>> site._registry[Person].search_fields
['name']
>>> site._registry[Person].list_display
['__str__']
>>> site._registry[Person].save_on_top
True

# You can also register iterables instead of single classes -- a nice shortcut
>>> site = admin.AdminSite()
>>> site.register([Person, Place], search_fields=['name'])
>>> site._registry[Person]
<django.contrib.admin.sites.PersonAdmin object at ...>
>>> site._registry[Place]
<django.contrib.admin.sites.PlaceAdmin object at ...>

"""}
