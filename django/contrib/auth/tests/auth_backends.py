from django.conf import settings
from django.contrib.auth.models import User, Group, Permission, AnonymousUser
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase


class BackendTest(TestCase):

    backend = 'django.contrib.auth.backends.ModelBackend'

    def setUp(self):
        self.curr_auth = settings.AUTHENTICATION_BACKENDS
        settings.AUTHENTICATION_BACKENDS = (self.backend,)
        User.objects.create_user('test', 'test@example.com', 'test')

    def tearDown(self):
        settings.AUTHENTICATION_BACKENDS = self.curr_auth

    def test_has_perm(self):
        user = User.objects.get(username='test')
        self.assertEqual(user.has_perm('auth.test'), False)
        user.is_staff = True
        user.save()
        self.assertEqual(user.has_perm('auth.test'), False)
        user.is_superuser = True
        user.save()
        self.assertEqual(user.has_perm('auth.test'), True)
        user.is_staff = False
        user.is_superuser = False
        user.save()
        self.assertEqual(user.has_perm('auth.test'), False)

    def test_custom_perms(self):
        user = User.objects.get(username='test')
        content_type=ContentType.objects.get_for_model(Group)
        perm = Permission.objects.create(name='test', content_type=content_type, codename='test')
        user.user_permissions.add(perm)
        user.save()

        # reloading user to purge the _perm_cache
        user = User.objects.get(username='test')
        self.assertEqual(user.get_all_permissions() == set([u'auth.test']), True)
        self.assertEqual(user.get_group_permissions(), set([]))
        self.assertEqual(user.has_module_perms('Group'), False)
        self.assertEqual(user.has_module_perms('auth'), True)
        perm = Permission.objects.create(name='test2', content_type=content_type, codename='test2')
        user.user_permissions.add(perm)
        user.save()
        perm = Permission.objects.create(name='test3', content_type=content_type, codename='test3')
        user.user_permissions.add(perm)
        user.save()
        user = User.objects.get(username='test')
        self.assertEqual(user.get_all_permissions(), set([u'auth.test2', u'auth.test', u'auth.test3']))
        self.assertEqual(user.has_perm('test'), False)
        self.assertEqual(user.has_perm('auth.test'), True)
        self.assertEqual(user.has_perms(['auth.test2', 'auth.test3']), True)
        perm = Permission.objects.create(name='test_group', content_type=content_type, codename='test_group')
        group = Group.objects.create(name='test_group')
        group.permissions.add(perm)
        group.save()
        user.groups.add(group)
        user = User.objects.get(username='test')
        exp = set([u'auth.test2', u'auth.test', u'auth.test3', u'auth.test_group'])
        self.assertEqual(user.get_all_permissions(), exp)
        self.assertEqual(user.get_group_permissions(), set([u'auth.test_group']))
        self.assertEqual(user.has_perms(['auth.test3', 'auth.test_group']), True)

        user = AnonymousUser()
        self.assertEqual(user.has_perm('test'), False)
        self.assertEqual(user.has_perms(['auth.test2', 'auth.test3']), False)


class TestObj(object):
    pass


class SimpleRowlevelBackend(object):
    supports_object_permissions = True

    def has_perm(self, user, perm, obj=None):
        if not obj:
            return # We only support row level perms

        if isinstance(obj, TestObj):
            if user.username == 'test2':
                return True
            elif isinstance(user, AnonymousUser) and perm == 'anon':
                return True
        return False

    def get_all_permissions(self, user, obj=None):
        if not obj:
            return [] # We only support row level perms

        if not isinstance(obj, TestObj):
            return ['none']

        if user.username == 'test2':
            return ['simple', 'advanced']
        else:
            return ['simple']

    def get_group_permissions(self, user, obj=None):
        if not obj:
            return # We only support row level perms

        if not isinstance(obj, TestObj):
            return ['none']

        if 'test_group' in [group.name for group in user.groups.all()]:
            return ['group_perm']
        else:
            return ['none']


class RowlevelBackendTest(TestCase):

    backend = 'django.contrib.auth.tests.auth_backends.SimpleRowlevelBackend'

    def setUp(self):
        self.curr_auth = settings.AUTHENTICATION_BACKENDS
        settings.AUTHENTICATION_BACKENDS = self.curr_auth + (self.backend,)
        self.user1 = User.objects.create_user('test', 'test@example.com', 'test')
        self.user2 = User.objects.create_user('test2', 'test2@example.com', 'test')
        self.user3 = AnonymousUser()
        self.user4 = User.objects.create_user('test4', 'test4@example.com', 'test')

    def tearDown(self):
        settings.AUTHENTICATION_BACKENDS = self.curr_auth

    def test_has_perm(self):
        self.assertEqual(self.user1.has_perm('perm', TestObj()), False)
        self.assertEqual(self.user2.has_perm('perm', TestObj()), True)
        self.assertEqual(self.user2.has_perm('perm'), False)
        self.assertEqual(self.user2.has_perms(['simple', 'advanced'], TestObj()), True)
        self.assertEqual(self.user3.has_perm('perm', TestObj()), False)
        self.assertEqual(self.user3.has_perm('anon', TestObj()), False)
        self.assertEqual(self.user3.has_perms(['simple', 'advanced'], TestObj()), False)

    def test_get_all_permissions(self):
        self.assertEqual(self.user1.get_all_permissions(TestObj()), set(['simple']))
        self.assertEqual(self.user2.get_all_permissions(TestObj()), set(['simple', 'advanced']))
        self.assertEqual(self.user2.get_all_permissions(), set([]))

    def test_get_group_permissions(self):
        content_type=ContentType.objects.get_for_model(Group)
        group = Group.objects.create(name='test_group')
        self.user4.groups.add(group)
        self.assertEqual(self.user4.get_group_permissions(TestObj()), set(['group_perm']))
