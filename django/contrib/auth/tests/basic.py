
BASIC_TESTS = """
>>> from django.contrib.auth.models import User, AnonymousUser
>>> u = User.objects.create_user('testuser', 'test@example.com', 'testpw')
>>> u.has_usable_password()
True
>>> u.check_password('bad')
False
>>> u.check_password('testpw')
True
>>> u.set_unusable_password()
>>> u.save()
>>> u.check_password('testpw')
False
>>> u.has_usable_password()
False
>>> u2 = User.objects.create_user('testuser2', 'test2@example.com')
>>> u2.has_usable_password()
False

>>> u.is_authenticated()
True
>>> u.is_staff
False
>>> u.is_active
True
>>> u.is_superuser
False

>>> a = AnonymousUser()
>>> a.is_authenticated()
False
>>> a.is_staff
False
>>> a.is_active
False
>>> a.is_superuser
False
>>> a.groups.all()
[]
>>> a.user_permissions.all()
[]

# superuser tests.
>>> super = User.objects.create_superuser('super', 'super@example.com', 'super')
>>> super.is_superuser
True
>>> super.is_active
True
>>> super.is_staff
True

#
# Tests for createsuperuser management command.
# It's nearly impossible to test the interactive mode -- a command test helper
# would be needed (and *awesome*) -- so just test the non-interactive mode.
# This covers most of the important validation, but not all.
#
>>> from django.core.management import call_command

>>> call_command("createsuperuser", interactive=False, username="joe", email="joe@somewhere.org")
Superuser created successfully.

>>> u = User.objects.get(username="joe")
>>> u.email
u'joe@somewhere.org'
>>> u.password
u'!'
>>> call_command("createsuperuser", interactive=False, username="joe+admin@somewhere.org", email="joe@somewhere.org")
Superuser created successfully.

>>> u = User.objects.get(username="joe+admin@somewhere.org")
>>> u.email
u'joe@somewhere.org'
>>> u.password
u'!'
"""
