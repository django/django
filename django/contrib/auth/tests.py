"""
>>> from models import User, AnonymousUser
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

>>> a = AnonymousUser()
>>> a.is_authenticated()
False
>>> a.is_staff
False
>>> a.is_active
False
>>> a.groups.all()
[]
>>> a.user_permissions.all()
[]
"""