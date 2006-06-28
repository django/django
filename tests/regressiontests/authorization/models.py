from django.db import models

class TestModel(models.Model):
    name = models.CharField(maxlength=255)
    
    class Admin:
        pass

API_TESTS = """
# Let's create a default implementation of has_permission. For now, It should 
# just call user.has_permission(permission) for the given django.contrib.auth.models.User. 
# Eventually the user.has_permission implementation should be extracted here.
>>> from django.contrib.auth import has_permission
>>> def user_has_permission(user, permission, object=None):
...     return user.has_perm(permission)

# Then let's register that function to be called when we get an instance of
# django.contrib.auth.models.User and a string as the permission. We use str
# as the permission type for convenience. It would be annoying to grab the
# actual Permission object instead of just using the codename. This feels kind
# of limiting, but can be revisited later.
>>> from django.contrib.auth.models import User
>>> has_permission.register(User, str, TestModel, user_has_permission)

# Now make sure it works.
>>> admin = User(username='admin', password='test', email='test@example.com', is_superuser=True)
>>> admin.save()
>>> has_permission(admin, 'testmodel.add', TestModel())
True

# Now let's create an implemetation for AnonymousUsers... it should always
# return False.
>>> def anon_has_permission(user, permission, object=None):
...     return False

# Register it like before, but for AnonymousUser rather than User.
>>> from django.contrib.auth.models import AnonymousUser
>>> has_permission.register(AnonymousUser, str, TestModel, anon_has_permission)

# And make sure it works.
>>> anonymous = AnonymousUser()
>>> has_permission(anonymous, 'testmodel.add', TestModel())
False

# Let's double check that the function we registered for User still works (we're
# not just replacing the implementation of has_permission)
>>> has_permission(admin, 'testmodel.add', TestModel())
True

"""
