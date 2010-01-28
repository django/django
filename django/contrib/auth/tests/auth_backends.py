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
        user.is_staff = True
        user.is_superuser = True
        user.is_active = False
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

    def test_has_no_object_perm(self):
        """Regressiontest for #12462"""
        user = User.objects.get(username='test')
        content_type=ContentType.objects.get_for_model(Group)
        perm = Permission.objects.create(name='test', content_type=content_type, codename='test')
        user.user_permissions.add(perm)
        user.save()

        self.assertEqual(user.has_perm('auth.test', 'object'), False)
        self.assertEqual(user.get_all_permissions('object'), set([]))
        self.assertEqual(user.has_perm('auth.test'), True)
        self.assertEqual(user.get_all_permissions(), set(['auth.test']))


class TestObj(object):
    pass


class SimpleRowlevelBackend(object):
    supports_object_permissions = True

    # This class also supports tests for anonymous user permissions,
    # via subclasses which just set the 'supports_anonymous_user' attribute.

    def has_perm(self, user, perm, obj=None):
        if not obj:
            return # We only support row level perms

        if isinstance(obj, TestObj):
            if user.username == 'test2':
                return True
            elif user.is_anonymous() and perm == 'anon':
                # not reached due to supports_anonymous_user = False
                return True
        return False

    def has_module_perms(self, user, app_label):
        return app_label == "app1"

    def get_all_permissions(self, user, obj=None):
        if not obj:
            return [] # We only support row level perms

        if not isinstance(obj, TestObj):
            return ['none']

        if user.is_anonymous():
            return ['anon']
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
    """
    Tests for auth backend that supports object level permissions
    """
    backend = 'django.contrib.auth.tests.auth_backends.SimpleRowlevelBackend'

    def setUp(self):
        self.curr_auth = settings.AUTHENTICATION_BACKENDS
        settings.AUTHENTICATION_BACKENDS = self.curr_auth + (self.backend,)
        self.user1 = User.objects.create_user('test', 'test@example.com', 'test')
        self.user2 = User.objects.create_user('test2', 'test2@example.com', 'test')
        self.user3 = User.objects.create_user('test3', 'test3@example.com', 'test')

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
        self.user3.groups.add(group)
        self.assertEqual(self.user3.get_group_permissions(TestObj()), set(['group_perm']))


class AnonymousUserBackend(SimpleRowlevelBackend):

    supports_anonymous_user = True


class NoAnonymousUserBackend(SimpleRowlevelBackend):

    supports_anonymous_user = False


class AnonymousUserBackendTest(TestCase):
    """
    Tests for AnonymousUser delegating to backend if it has 'supports_anonymous_user' = True
    """

    backend = 'django.contrib.auth.tests.auth_backends.AnonymousUserBackend'

    def setUp(self):
        self.curr_auth = settings.AUTHENTICATION_BACKENDS
        settings.AUTHENTICATION_BACKENDS = (self.backend,)
        self.user1 = AnonymousUser()

    def tearDown(self):
        settings.AUTHENTICATION_BACKENDS = self.curr_auth

    def test_has_perm(self):
        self.assertEqual(self.user1.has_perm('perm', TestObj()), False)
        self.assertEqual(self.user1.has_perm('anon', TestObj()), True)

    def test_has_perms(self):
        self.assertEqual(self.user1.has_perms(['anon'], TestObj()), True)
        self.assertEqual(self.user1.has_perms(['anon', 'perm'], TestObj()), False)

    def test_has_module_perms(self):
        self.assertEqual(self.user1.has_module_perms("app1"), True)
        self.assertEqual(self.user1.has_module_perms("app2"), False)

    def test_get_all_permissions(self):
        self.assertEqual(self.user1.get_all_permissions(TestObj()), set(['anon']))


class NoAnonymousUserBackendTest(TestCase):
    """
    Tests that AnonymousUser does not delegate to backend if it has 'supports_anonymous_user' = False
    """
    backend = 'django.contrib.auth.tests.auth_backends.NoAnonymousUserBackend'

    def setUp(self):
        self.curr_auth = settings.AUTHENTICATION_BACKENDS
        settings.AUTHENTICATION_BACKENDS = self.curr_auth + (self.backend,)
        self.user1 = AnonymousUser()

    def tearDown(self):
        settings.AUTHENTICATION_BACKENDS = self.curr_auth

    def test_has_perm(self):
        self.assertEqual(self.user1.has_perm('perm', TestObj()), False)
        self.assertEqual(self.user1.has_perm('anon', TestObj()), False)

    def test_has_perms(self):
        self.assertEqual(self.user1.has_perms(['anon'], TestObj()), False)

    def test_has_module_perms(self):
        self.assertEqual(self.user1.has_module_perms("app1"), False)
        self.assertEqual(self.user1.has_module_perms("app2"), False)

    def test_get_all_permissions(self):
        self.assertEqual(self.user1.get_all_permissions(TestObj()), set())
