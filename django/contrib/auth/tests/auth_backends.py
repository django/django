from __future__ import unicode_literals
from datetime import date

from django.conf import settings
from django.contrib.auth.models import User, Group, Permission, AnonymousUser
from django.contrib.auth.tests.utils import skipIfCustomUser
from django.contrib.auth.tests.custom_user import ExtensionUser, CustomPermissionsUser, CustomUser
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ImproperlyConfigured
from django.contrib.auth import authenticate, get_user
from django.http import HttpRequest
from django.test import TestCase
from django.test.utils import override_settings


class BaseModelBackendTest(object):
    """
    A base class for tests that need to validate the ModelBackend
    with different User models. Subclasses should define a class
    level UserModel attribute, and a create_users() method to
    construct two users for test purposes.
    """
    backend = 'django.contrib.auth.backends.ModelBackend'

    def setUp(self):
        self.curr_auth = settings.AUTHENTICATION_BACKENDS
        settings.AUTHENTICATION_BACKENDS = (self.backend,)
        self.create_users()

    def tearDown(self):
        settings.AUTHENTICATION_BACKENDS = self.curr_auth
        # The custom_perms test messes with ContentTypes, which will
        # be cached; flush the cache to ensure there are no side effects
        # Refs #14975, #14925
        ContentType.objects.clear_cache()

    def test_has_perm(self):
        user = self.UserModel._default_manager.get(pk=self.user.pk)
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
        user = self.UserModel._default_manager.get(pk=self.user.pk)
        content_type = ContentType.objects.get_for_model(Group)
        perm = Permission.objects.create(name='test', content_type=content_type, codename='test')
        user.user_permissions.add(perm)
        user.save()

        # reloading user to purge the _perm_cache
        user = self.UserModel._default_manager.get(pk=self.user.pk)
        self.assertEqual(user.get_all_permissions() == set(['auth.test']), True)
        self.assertEqual(user.get_group_permissions(), set([]))
        self.assertEqual(user.has_module_perms('Group'), False)
        self.assertEqual(user.has_module_perms('auth'), True)
        perm = Permission.objects.create(name='test2', content_type=content_type, codename='test2')
        user.user_permissions.add(perm)
        user.save()
        perm = Permission.objects.create(name='test3', content_type=content_type, codename='test3')
        user.user_permissions.add(perm)
        user.save()
        user = self.UserModel._default_manager.get(pk=self.user.pk)
        self.assertEqual(user.get_all_permissions(), set(['auth.test2', 'auth.test', 'auth.test3']))
        self.assertEqual(user.has_perm('test'), False)
        self.assertEqual(user.has_perm('auth.test'), True)
        self.assertEqual(user.has_perms(['auth.test2', 'auth.test3']), True)
        perm = Permission.objects.create(name='test_group', content_type=content_type, codename='test_group')
        group = Group.objects.create(name='test_group')
        group.permissions.add(perm)
        group.save()
        user.groups.add(group)
        user = self.UserModel._default_manager.get(pk=self.user.pk)
        exp = set(['auth.test2', 'auth.test', 'auth.test3', 'auth.test_group'])
        self.assertEqual(user.get_all_permissions(), exp)
        self.assertEqual(user.get_group_permissions(), set(['auth.test_group']))
        self.assertEqual(user.has_perms(['auth.test3', 'auth.test_group']), True)

        user = AnonymousUser()
        self.assertEqual(user.has_perm('test'), False)
        self.assertEqual(user.has_perms(['auth.test2', 'auth.test3']), False)

    def test_has_no_object_perm(self):
        """Regressiontest for #12462"""
        user = self.UserModel._default_manager.get(pk=self.user.pk)
        content_type = ContentType.objects.get_for_model(Group)
        perm = Permission.objects.create(name='test', content_type=content_type, codename='test')
        user.user_permissions.add(perm)
        user.save()

        self.assertEqual(user.has_perm('auth.test', 'object'), False)
        self.assertEqual(user.get_all_permissions('object'), set([]))
        self.assertEqual(user.has_perm('auth.test'), True)
        self.assertEqual(user.get_all_permissions(), set(['auth.test']))

    def test_get_all_superuser_permissions(self):
        "A superuser has all permissions. Refs #14795"
        user = self.UserModel._default_manager.get(pk=self.superuser.pk)
        self.assertEqual(len(user.get_all_permissions()), len(Permission.objects.all()))


@skipIfCustomUser
class ModelBackendTest(BaseModelBackendTest, TestCase):
    """
    Tests for the ModelBackend using the default User model.
    """
    UserModel = User

    def create_users(self):
        self.user = User.objects.create_user(
            username='test',
            email='test@example.com',
            password='test',
        )
        self.superuser = User.objects.create_superuser(
            username='test2',
            email='test2@example.com',
            password='test',
        )


@override_settings(AUTH_USER_MODEL='auth.ExtensionUser')
class ExtensionUserModelBackendTest(BaseModelBackendTest, TestCase):
    """
    Tests for the ModelBackend using the custom ExtensionUser model.

    This isn't a perfect test, because both the User and ExtensionUser are
    synchronized to the database, which wouldn't ordinary happen in
    production. As a result, it doesn't catch errors caused by the non-
    existence of the User table.

    The specific problem is queries on .filter(groups__user) et al, which
    makes an implicit assumption that the user model is called 'User'. In
    production, the auth.User table won't exist, so the requested join
    won't exist either; in testing, the auth.User *does* exist, and
    so does the join. However, the join table won't contain any useful
    data; for testing, we check that the data we expect actually does exist.
    """

    UserModel = ExtensionUser

    def create_users(self):
        self.user = ExtensionUser._default_manager.create_user(
            username='test',
            email='test@example.com',
            password='test',
            date_of_birth=date(2006, 4, 25)
        )
        self.superuser = ExtensionUser._default_manager.create_superuser(
            username='test2',
            email='test2@example.com',
            password='test',
            date_of_birth=date(1976, 11, 8)
        )


@override_settings(AUTH_USER_MODEL='auth.CustomPermissionsUser')
class CustomPermissionsUserModelBackendTest(BaseModelBackendTest, TestCase):
    """
    Tests for the ModelBackend using the CustomPermissionsUser model.

    As with the ExtensionUser test, this isn't a perfect test, because both
    the User and CustomPermissionsUser are synchronized to the database,
    which wouldn't ordinary happen in production.
    """

    UserModel = CustomPermissionsUser

    def create_users(self):
        self.user = CustomPermissionsUser._default_manager.create_user(
            email='test@example.com',
            password='test',
            date_of_birth=date(2006, 4, 25)
        )
        self.superuser = CustomPermissionsUser._default_manager.create_superuser(
            email='test2@example.com',
            password='test',
            date_of_birth=date(1976, 11, 8)
        )


@override_settings(AUTH_USER_MODEL='auth.CustomUser')
class CustomUserModelBackendAuthenticateTest(TestCase):
    """
    Tests that the model backend can accept a credentials kwarg labeled with
    custom user model's USERNAME_FIELD.
    """

    def test_authenticate(self):
        test_user = CustomUser._default_manager.create_user(
            email='test@example.com',
            password='test',
            date_of_birth=date(2006, 4, 25)
        )
        authenticated_user = authenticate(email='test@example.com', password='test')
        self.assertEqual(test_user, authenticated_user)



class TestObj(object):
    pass


class SimpleRowlevelBackend(object):
    def has_perm(self, user, perm, obj=None):
        if not obj:
            return  # We only support row level perms

        if isinstance(obj, TestObj):
            if user.username == 'test2':
                return True
            elif user.is_anonymous() and perm == 'anon':
                return True
            elif not user.is_active and perm == 'inactive':
                return True
        return False

    def has_module_perms(self, user, app_label):
        if not user.is_anonymous() and not user.is_active:
            return False
        return app_label == "app1"

    def get_all_permissions(self, user, obj=None):
        if not obj:
            return []  # We only support row level perms

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
            return  # We only support row level perms

        if not isinstance(obj, TestObj):
            return ['none']

        if 'test_group' in [group.name for group in user.groups.all()]:
            return ['group_perm']
        else:
            return ['none']


@skipIfCustomUser
class RowlevelBackendTest(TestCase):
    """
    Tests for auth backend that supports object level permissions
    """
    backend = 'django.contrib.auth.tests.auth_backends.SimpleRowlevelBackend'

    def setUp(self):
        self.curr_auth = settings.AUTHENTICATION_BACKENDS
        settings.AUTHENTICATION_BACKENDS = tuple(self.curr_auth) + (self.backend,)
        self.user1 = User.objects.create_user('test', 'test@example.com', 'test')
        self.user2 = User.objects.create_user('test2', 'test2@example.com', 'test')
        self.user3 = User.objects.create_user('test3', 'test3@example.com', 'test')

    def tearDown(self):
        settings.AUTHENTICATION_BACKENDS = self.curr_auth
        # The get_group_permissions test messes with ContentTypes, which will
        # be cached; flush the cache to ensure there are no side effects
        # Refs #14975, #14925
        ContentType.objects.clear_cache()

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
        group = Group.objects.create(name='test_group')
        self.user3.groups.add(group)
        self.assertEqual(self.user3.get_group_permissions(TestObj()), set(['group_perm']))


class AnonymousUserBackendTest(TestCase):
    """
    Tests for AnonymousUser delegating to backend.
    """

    backend = 'django.contrib.auth.tests.auth_backends.SimpleRowlevelBackend'

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


@skipIfCustomUser
@override_settings(AUTHENTICATION_BACKENDS=[])
class NoBackendsTest(TestCase):
    """
    Tests that an appropriate error is raised if no auth backends are provided.
    """
    def setUp(self):
        self.user = User.objects.create_user('test', 'test@example.com', 'test')

    def test_raises_exception(self):
        self.assertRaises(ImproperlyConfigured, self.user.has_perm, ('perm', TestObj(),))


@skipIfCustomUser
class InActiveUserBackendTest(TestCase):
    """
    Tests for a inactive user
    """
    backend = 'django.contrib.auth.tests.auth_backends.SimpleRowlevelBackend'

    def setUp(self):
        self.curr_auth = settings.AUTHENTICATION_BACKENDS
        settings.AUTHENTICATION_BACKENDS = (self.backend,)
        self.user1 = User.objects.create_user('test', 'test@example.com', 'test')
        self.user1.is_active = False
        self.user1.save()

    def tearDown(self):
        settings.AUTHENTICATION_BACKENDS = self.curr_auth

    def test_has_perm(self):
        self.assertEqual(self.user1.has_perm('perm', TestObj()), False)
        self.assertEqual(self.user1.has_perm('inactive', TestObj()), True)

    def test_has_module_perms(self):
        self.assertEqual(self.user1.has_module_perms("app1"), False)
        self.assertEqual(self.user1.has_module_perms("app2"), False)


@skipIfCustomUser
class ImproperlyConfiguredUserModelTest(TestCase):
    """
    Tests that an exception from within get_user_model is propagated and doesn't
    raise an UnboundLocalError.

    Regression test for ticket #21439
    """
    def setUp(self):
        self.user1 = User.objects.create_user('test', 'test@example.com', 'test')
        self.client.login(
            username='test',
            password='test'
        )

    @override_settings(AUTH_USER_MODEL='thismodel.doesntexist')
    def test_does_not_shadow_exception(self):
        # Prepare a request object
        request = HttpRequest()
        request.session = self.client.session

        self.assertRaises(ImproperlyConfigured, get_user, request)
