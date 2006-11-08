"""
>>> from django.contrib.auth.models import User, Permission
>>> from django.db.models.loading import get_app
>>> from django.contrib.auth.management import create_permissions
>>> from django.contrib.auth import has_permission, has_permissions

>>> from regressiontests.generic_auth.models import Person

>>> app = get_app('generic_auth')
>>> create_permissions(app, [], 0)

Create and register an authorization handler that acts similarly to Django's 
model level permissions. This version doesn't take group permissions into 
account however.

>>> def default_has_permission(user, permission, obj):
...    if not user.is_active:
...        return False
...    if user.is_superuser:
...        return True
...    return permission in user.user_permissions.select_related()
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


Let's create a simple role-based implementation of has_permission that allows 
change and delete access to the creator of an object, but denies access to 
everyone else. The creator is just a foreign key from the object in question
to the django.contrib.auth.models.User model.

First, we create the actual implementation.

>>> def is_creator(user, permission, object):
...     if user.is_superuser:
...         return True
...     # if no object was provided, fall back to Model level permissions
...     if not object:
...         return permission in user.user_permissions.select_related()
...     return user == object.creator
...


The we register is_creator to handle calls to has_permission for the
appropriate models (in this case User, Permision, and Article).

>>> from django.contrib.auth.models import User, Permission
>>> from django.contrib.auth import has_permission
>>> from regressiontests.generic_auth.models import Article

>>> has_permission.register(is_creator, User, Permission, Article)


Create an Article for our tests, and set it's `owner` attribute to the user we
created above.

>>> article = Article(name='test', body='test', creator=user)
>>> article.save()


Set up some convenient reverences to the various permission objects.

>>> add_permission = Article._meta.get_add_permission()
>>> change_permission = Article._meta.get_change_permission()
>>> delete_permission = Article._meta.get_delete_permission()

Adding isn't tied to a particular object, and we haven't given the user
permission to add Articles yet, so this should fail.

>>> has_permission(user, add_permission)
False

But the user *is* the creator of `article`, so they *should* have change and
delete permissions for that article.

>>> has_permission(user, change_permission, article)
True
>>> has_permission(user, delete_permission, article)
True


Give the user add Article permissions.

>>> user.user_permissions.add(add_permission)
>>> user.save()


Make sure it worked.

>>> has_permission(user, add_permission, article)
True


"""
