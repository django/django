"""
XX. Permissions

"""

from django.db import models

class Person(models.Model):
    name = models.CharField(maxlength=20)

API_TESTS = """
>>> from django.contrib.auth.models import User, Permission
>>> from django.db.models.loading import get_app
>>> from django.contrib.auth.management import create_permissions
>>> from django.contrib.auth import has_permission

>>> app = get_app('generic_auth')
>>> create_permissions(app, [])
Adding permission 'person | Can add person'
Adding permission 'person | Can change person'
Adding permission 'person | Can delete person'


Create and register an authorization handler that acts like Django's model
level permissions

>>> def default_has_permission(user, permission, obj):
...     p_name = "%s.%s" % (permission.content_type.app_label, permission.codename)
...     return user.has_perm(p_name)
...     
>>> has_permission.register(default_has_permission, User, Permission, Person)
>>> has_permission.register(default_has_permission, User, Permission)


Create a new user

>>> user = User.objects.create_user('test', 'test@example.com', 'password')
>>> user.save()


Create a Person that we'll check from access to.

>>> person = Person(name='test')
>>> person.save()


Get permissions from the model

>>> opts = Person._meta
>>> add_permission = opts.get_add_permission()
>>> change_permission = opts.get_change_permission()
>>> delete_permission = opts.get_delete_permission()


Give the user add, change, and delete permissions for Person models, then check that permission.

>>> user.user_permissions.add(add_permission)
>>> user.user_permissions.add(change_permission)
>>> user.user_permissions.add(delete_permission)
>>> user.save()


The user should have add, change, and delete permissions now. Make sure they do.

>>> has_permission(user, add_permission)
True
>>> has_permission(user, change_permission, person)
True
>>> has_permission(user, delete_permission, person)
True

"""
