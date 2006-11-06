"""
>>> from django.contrib.auth.models import User, Permission
>>> from django.db.models.loading import get_app
>>> from django.contrib.auth.management import create_permissions
>>> from django.contrib.auth import has_permission, has_permissions

>>> from regressiontests.generic_auth.models import Person

>>> app = get_app('generic_auth')
>>> create_permissions(app, [], 0)

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


Give the user add and change permissions for Person models.

>>> user.user_permissions.add(add_permission)
>>> user.user_permissions.add(change_permission)
>>> user.save()


Make sure has_permission knows the user has add and delete permissions on Person
objects.

>>> has_permission(user, add_permission)
True
>>> has_permission(user, change_permission, person)
True


Make sure the user doesn't have the delete permission though.

>>> has_permission(user, delete_permission, person)
False


There is also a has_permissions function for convenience. It takes a list of 
permissions rather than a single one.

>>> has_permissions(user, [add_permission, change_permission], person)
True
>>> has_permissions(user, [add_permission, delete_permission], person)
False

"""
