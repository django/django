"""
>>> from models import User
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
"""