"""
>>> from django.contrib.auth.models import User, Group, Permission
>>> from django.contrib.contenttypes.models import ContentType

# No Permissions assigned yet, should return False except for superuser

>>> user = User.objects.create_user('test', 'test@example.com', 'test')
>>> user.has_perm("auth.test")
False
>>> user.is_staff=True
>>> user.save()
>>> user.has_perm("auth.test")
False
>>> user.is_superuser=True
>>> user.save()
>>> user.has_perm("auth.test")
True
>>> user.is_staff = False
>>> user.is_superuser = False
>>> user.save()
>>> user.has_perm("auth.test")
False
>>> content_type=ContentType.objects.get_for_model(Group)
>>> perm = Permission.objects.create(name="test", content_type=content_type, codename="test")
>>> user.user_permissions.add(perm)
>>> user.save()

# reloading user to purge the _perm_cache

>>> user = User.objects.get(username="test")
>>> user.get_all_permissions()
set([u'auth.test'])
>>> user.get_group_permissions()
set([])
>>> user.has_module_perms("Group")
False
>>> user.has_module_perms("auth")
True
>>> perm = Permission.objects.create(name="test2", content_type=content_type, codename="test2")
>>> user.user_permissions.add(perm)
>>> user.save()
>>> perm = Permission.objects.create(name="test3", content_type=content_type, codename="test3")
>>> user.user_permissions.add(perm)
>>> user.save()
>>> user = User.objects.get(username="test")
>>> user.get_all_permissions()
set([u'auth.test2', u'auth.test', u'auth.test3'])
>>> user.has_perm('test')
False
>>> user.has_perm('auth.test')
True
>>> user.has_perms(['auth.test2', 'auth.test3'])
True
>>> perm = Permission.objects.create(name="test_group", content_type=content_type, codename="test_group")
>>> group = Group.objects.create(name='test_group')
>>> group.permissions.add(perm)
>>> group.save()
>>> user.groups.add(group)
>>> user = User.objects.get(username="test")
>>> user.get_all_permissions()
set([u'auth.test2', u'auth.test', u'auth.test3', u'auth.test_group'])
>>> user.get_group_permissions()
set([u'auth.test_group'])
>>> user.has_perms(['auth.test3', 'auth.test_group'])
True
"""