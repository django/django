from datetime import date
from unittest import mock

from django.contrib.auth import (
    BACKEND_SESSION_KEY, SESSION_KEY, authenticate, get_user, signals,
)
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.hashers import MD5PasswordHasher
from django.contrib.auth.models import AnonymousUser, Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ImproperlyConfigured, PermissionDenied
from django.http import HttpRequest
from django.test import (
    SimpleTestCase, TestCase, modify_settings, override_settings,
)

from .models import (
    CustomPermissionsUser, CustomUser, CustomUserWithoutIsActiveField,
    ExtensionUser, UUIDUser,
)


class CountingMD5PasswordHasher(MD5PasswordHasher):
    """Hasher that counts how many times it computes a hash."""

    calls = 0

    def encode(self, *args, **kwargs):
        type(self).calls += 1
        return super().encode(*args, **kwargs)


class BaseModelBackendTest:
    """
    A base class for tests that need to validate the ModelBackend
    with different User models. Subclasses should define a class
    level UserModel attribute, and a create_users() method to
    construct two users for test purposes.
    """
    backend = 'django.contrib.auth.backends.ModelBackend'

    def setUp(self):
        self.patched_settings = modify_settings(
            AUTHENTICATION_BACKENDS={'append': self.backend},
        )
        self.patched_settings.enable()
        self.create_users()

    def tearDown(self):
        self.patched_settings.disable()
        # The custom_perms test messes with ContentTypes, which will
        # be cached; flush the cache to ensure there are no side effects
        # Refs #14975, #14925
        ContentType.objects.clear_cache()

    def test_has_perm(self):
        user = self.UserModel._default_manager.get(pk=self.user.pk)
        self.assertIs(user.has_perm('auth.test'), False)

        user.is_staff = True
        user.save()
        self.assertIs(user.has_perm('auth.test'), False)

        user.is_superuser = True
        user.save()
        self.assertIs(user.has_perm('auth.test'), True)

        user.is_staff = True
        user.is_superuser = True
        user.is_active = False
        user.save()
        self.assertIs(user.has_perm('auth.test'), False)

    def test_custom_perms(self):
        user = self.UserModel._default_manager.get(pk=self.user.pk)
        content_type = ContentType.objects.get_for_model(Group)
        perm = Permission.objects.create(name='test', content_type=content_type, codename='test')
        user.user_permissions.add(perm)

        # reloading user to purge the _perm_cache
        user = self.UserModel._default_manager.get(pk=self.user.pk)
        self.assertEqual(user.get_all_permissions(), {'auth.test'})
        self.assertEqual(user.get_group_permissions(), set())
        self.assertIs(user.has_module_perms('Group'), False)
        self.assertIs(user.has_module_perms('auth'), True)

        perm = Permission.objects.create(name='test2', content_type=content_type, codename='test2')
        user.user_permissions.add(perm)
        perm = Permission.objects.create(name='test3', content_type=content_type, codename='test3')
        user.user_permissions.add(perm)
        user = self.UserModel._default_manager.get(pk=self.user.pk)
        self.assertEqual(user.get_all_permissions(), {'auth.test2', 'auth.test', 'auth.test3'})
        self.assertIs(user.has_perm('test'), False)
        self.assertIs(user.has_perm('auth.test'), True)
        self.assertIs(user.has_perms(['auth.test2', 'auth.test3']), True)

        perm = Permission.objects.create(name='test_group', content_type=content_type, codename='test_group')
        group = Group.objects.create(name='test_group')
        group.permissions.add(perm)
        user.groups.add(group)
        user = self.UserModel._default_manager.get(pk=self.user.pk)
        exp = {'auth.test2', 'auth.test', 'auth.test3', 'auth.test_group'}
        self.assertEqual(user.get_all_permissions(), exp)
        self.assertEqual(user.get_group_permissions(), {'auth.test_group'})
        self.assertIs(user.has_perms(['auth.test3', 'auth.test_group']), True)

        user = AnonymousUser()
        self.assertIs(user.has_perm('test'), False)
        self.assertIs(user.has_perms(['auth.test2', 'auth.test3']), False)

    def test_has_no_object_perm(self):
        """Regressiontest for #12462"""
        user = self.UserModel._default_manager.get(pk=self.user.pk)
        content_type = ContentType.objects.get_for_model(Group)
        perm = Permission.objects.create(name='test', content_type=content_type, codename='test')
        user.user_permissions.add(perm)

        self.assertIs(user.has_perm('auth.test', 'object'), False)
        self.assertEqual(user.get_all_permissions('object'), set())
        self.assertIs(user.has_perm('auth.test'), True)
        self.assertEqual(user.get_all_permissions(), {'auth.test'})

    def test_anonymous_has_no_permissions(self):
        """
        #17903 -- Anonymous users shouldn't have permissions in
        ModelBackend.get_(all|user|group)_permissions().
        """
        backend = ModelBackend()

        user = self.UserModel._default_manager.get(pk=self.user.pk)
        content_type = ContentType.objects.get_for_model(Group)
        user_perm = Permission.objects.create(name='test', content_type=content_type, codename='test_user')
        group_perm = Permission.objects.create(name='test2', content_type=content_type, codename='test_group')
        user.user_permissions.add(user_perm)

        group = Group.objects.create(name='test_group')
        user.groups.add(group)
        group.permissions.add(group_perm)

        self.assertEqual(backend.get_all_permissions(user), {'auth.test_user', 'auth.test_group'})
        self.assertEqual(backend.get_user_permissions(user), {'auth.test_user'})
        self.assertEqual(backend.get_group_permissions(user), {'auth.test_group'})

        with mock.patch.object(self.UserModel, 'is_anonymous', True):
            self.assertEqual(backend.get_all_permissions(user), set())
            self.assertEqual(backend.get_user_permissions(user), set())
            self.assertEqual(backend.get_group_permissions(user), set())

    def test_inactive_has_no_permissions(self):
        """
        #17903 -- Inactive users shouldn't have permissions in
        ModelBackend.get_(all|user|group)_permissions().
        """
        backend = ModelBackend()

        user = self.UserModel._default_manager.get(pk=self.user.pk)
        content_type = ContentType.objects.get_for_model(Group)
        user_perm = Permission.objects.create(name='test', content_type=content_type, codename='test_user')
        group_perm = Permission.objects.create(name='test2', content_type=content_type, codename='test_group')
        user.user_permissions.add(user_perm)

        group = Group.objects.create(name='test_group')
        user.groups.add(group)
        group.permissions.add(group_perm)

        self.assertEqual(backend.get_all_permissions(user), {'auth.test_user', 'auth.test_group'})
        self.assertEqual(backend.get_user_permissions(user), {'auth.test_user'})
        self.assertEqual(backend.get_group_permissions(user), {'auth.test_group'})

        user.is_active = False
        user.save()

        self.assertEqual(backend.get_all_permissions(user), set())
        self.assertEqual(backend.get_user_permissions(user), set())
        self.assertEqual(backend.get_group_permissions(user), set())

    def test_get_all_superuser_permissions(self):
        """A superuser has all permissions. Refs #14795."""
        user = self.UserModel._default_manager.get(pk=self.superuser.pk)
        self.assertEqual(len(user.get_all_permissions()), len(Permission.objects.all()))

    @override_settings(PASSWORD_HASHERS=['auth_tests.test_auth_backends.CountingMD5PasswordHasher'])
    def test_authentication_timing(self):
        """Hasher is run once regardless of whether the user exists. Refs #20760."""
        # Re-set the password, because this tests overrides PASSWORD_HASHERS
        self.user.set_password('test')
        self.user.save()

        CountingMD5PasswordHasher.calls = 0
        username = getattr(self.user, self.UserModel.USERNAME_FIELD)
        authenticate(username=username, password='test')
        self.assertEqual(CountingMD5PasswordHasher.calls, 1)

        CountingMD5PasswordHasher.calls = 0
        authenticate(username='no_such_user', password='test')
        self.assertEqual(CountingMD5PasswordHasher.calls, 1)


class ModelBackendTest(BaseModelBackendTest, TestCase):
    """
    Tests for the ModelBackend using the default User model.
    """
    UserModel = User
    user_credentials = {'username': 'test', 'password': 'test'}

    def create_users(self):
        self.user = User.objects.create_user(email='test@example.com', **self.user_credentials)
        self.superuser = User.objects.create_superuser(
            username='test2',
            email='test2@example.com',
            password='test',
        )

    def test_authenticate_inactive(self):
        """
        An inactive user can't authenticate.
        """
        self.assertEqual(authenticate(**self.user_credentials), self.user)
        self.user.is_active = False
        self.user.save()
        self.assertIsNone(authenticate(**self.user_credentials))

    @override_settings(AUTH_USER_MODEL='auth_tests.CustomUserWithoutIsActiveField')
    def test_authenticate_user_without_is_active_field(self):
        """
        A custom user without an `is_active` field is allowed to authenticate.
        """
        user = CustomUserWithoutIsActiveField.objects._create_user(
            username='test', email='test@example.com', password='test',
        )
        self.assertEqual(authenticate(username='test', password='test'), user)


@override_settings(AUTH_USER_MODEL='auth_tests.ExtensionUser')
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


@override_settings(AUTH_USER_MODEL='auth_tests.CustomPermissionsUser')
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


@override_settings(AUTH_USER_MODEL='auth_tests.CustomUser')
class CustomUserModelBackendAuthenticateTest(TestCase):
    """
    The model backend can accept a credentials kwarg labeled with
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


@override_settings(AUTH_USER_MODEL='auth_tests.UUIDUser')
class UUIDUserTests(TestCase):

    def test_login(self):
        """
        A custom user with a UUID primary key should be able to login.
        """
        user = UUIDUser.objects.create_user(username='uuid', password='test')
        self.assertTrue(self.client.login(username='uuid', password='test'))
        self.assertEqual(UUIDUser.objects.get(pk=self.client.session[SESSION_KEY]), user)


class TestObj:
    pass


class SimpleRowlevelBackend:
    def has_perm(self, user, perm, obj=None):
        if not obj:
            return  # We only support row level perms

        if isinstance(obj, TestObj):
            if user.username == 'test2':
                return True
            elif user.is_anonymous and perm == 'anon':
                return True
            elif not user.is_active and perm == 'inactive':
                return True
        return False

    def has_module_perms(self, user, app_label):
        if not user.is_anonymous and not user.is_active:
            return False
        return app_label == "app1"

    def get_all_permissions(self, user, obj=None):
        if not obj:
            return []  # We only support row level perms

        if not isinstance(obj, TestObj):
            return ['none']

        if user.is_anonymous:
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


@modify_settings(AUTHENTICATION_BACKENDS={
    'append': 'auth_tests.test_auth_backends.SimpleRowlevelBackend',
})
class RowlevelBackendTest(TestCase):
    """
    Tests for auth backend that supports object level permissions
    """

    def setUp(self):
        self.user1 = User.objects.create_user('test', 'test@example.com', 'test')
        self.user2 = User.objects.create_user('test2', 'test2@example.com', 'test')
        self.user3 = User.objects.create_user('test3', 'test3@example.com', 'test')

    def tearDown(self):
        # The get_group_permissions test messes with ContentTypes, which will
        # be cached; flush the cache to ensure there are no side effects
        # Refs #14975, #14925
        ContentType.objects.clear_cache()

    def test_has_perm(self):
        self.assertIs(self.user1.has_perm('perm', TestObj()), False)
        self.assertIs(self.user2.has_perm('perm', TestObj()), True)
        self.assertIs(self.user2.has_perm('perm'), False)
        self.assertIs(self.user2.has_perms(['simple', 'advanced'], TestObj()), True)
        self.assertIs(self.user3.has_perm('perm', TestObj()), False)
        self.assertIs(self.user3.has_perm('anon', TestObj()), False)
        self.assertIs(self.user3.has_perms(['simple', 'advanced'], TestObj()), False)

    def test_get_all_permissions(self):
        self.assertEqual(self.user1.get_all_permissions(TestObj()), {'simple'})
        self.assertEqual(self.user2.get_all_permissions(TestObj()), {'simple', 'advanced'})
        self.assertEqual(self.user2.get_all_permissions(), set())

    def test_get_group_permissions(self):
        group = Group.objects.create(name='test_group')
        self.user3.groups.add(group)
        self.assertEqual(self.user3.get_group_permissions(TestObj()), {'group_perm'})


@override_settings(
    AUTHENTICATION_BACKENDS=['auth_tests.test_auth_backends.SimpleRowlevelBackend'],
)
class AnonymousUserBackendTest(SimpleTestCase):
    """
    Tests for AnonymousUser delegating to backend.
    """

    def setUp(self):
        self.user1 = AnonymousUser()

    def test_has_perm(self):
        self.assertIs(self.user1.has_perm('perm', TestObj()), False)
        self.assertIs(self.user1.has_perm('anon', TestObj()), True)

    def test_has_perms(self):
        self.assertIs(self.user1.has_perms(['anon'], TestObj()), True)
        self.assertIs(self.user1.has_perms(['anon', 'perm'], TestObj()), False)

    def test_has_module_perms(self):
        self.assertIs(self.user1.has_module_perms("app1"), True)
        self.assertIs(self.user1.has_module_perms("app2"), False)

    def test_get_all_permissions(self):
        self.assertEqual(self.user1.get_all_permissions(TestObj()), {'anon'})


@override_settings(AUTHENTICATION_BACKENDS=[])
class NoBackendsTest(TestCase):
    """
    An appropriate error is raised if no auth backends are provided.
    """
    def setUp(self):
        self.user = User.objects.create_user('test', 'test@example.com', 'test')

    def test_raises_exception(self):
        msg = (
            'No authentication backends have been defined. '
            'Does AUTHENTICATION_BACKENDS contain anything?'
        )
        with self.assertRaisesMessage(ImproperlyConfigured, msg):
            self.user.has_perm(('perm', TestObj()))


@override_settings(AUTHENTICATION_BACKENDS=['auth_tests.test_auth_backends.SimpleRowlevelBackend'])
class InActiveUserBackendTest(TestCase):
    """
    Tests for an inactive user
    """

    def setUp(self):
        self.user1 = User.objects.create_user('test', 'test@example.com', 'test')
        self.user1.is_active = False
        self.user1.save()

    def test_has_perm(self):
        self.assertIs(self.user1.has_perm('perm', TestObj()), False)
        self.assertIs(self.user1.has_perm('inactive', TestObj()), True)

    def test_has_module_perms(self):
        self.assertIs(self.user1.has_module_perms("app1"), False)
        self.assertIs(self.user1.has_module_perms("app2"), False)


class PermissionDeniedBackend:
    """
    Always raises PermissionDenied in `authenticate`, `has_perm` and `has_module_perms`.
    """

    def authenticate(self, request, username=None, password=None):
        raise PermissionDenied

    def has_perm(self, user_obj, perm, obj=None):
        raise PermissionDenied

    def has_module_perms(self, user_obj, app_label):
        raise PermissionDenied


class PermissionDeniedBackendTest(TestCase):
    """
    Other backends are not checked once a backend raises PermissionDenied
    """
    backend = 'auth_tests.test_auth_backends.PermissionDeniedBackend'

    def setUp(self):
        self.user1 = User.objects.create_user('test', 'test@example.com', 'test')
        self.user_login_failed = []
        signals.user_login_failed.connect(self.user_login_failed_listener)

    def tearDown(self):
        signals.user_login_failed.disconnect(self.user_login_failed_listener)

    def user_login_failed_listener(self, sender, credentials, **kwargs):
        self.user_login_failed.append(credentials)

    @modify_settings(AUTHENTICATION_BACKENDS={'prepend': backend})
    def test_permission_denied(self):
        "user is not authenticated after a backend raises permission denied #2550"
        self.assertIsNone(authenticate(username='test', password='test'))
        # user_login_failed signal is sent.
        self.assertEqual(self.user_login_failed, [{'password': '********************', 'username': 'test'}])

    @modify_settings(AUTHENTICATION_BACKENDS={'append': backend})
    def test_authenticates(self):
        self.assertEqual(authenticate(username='test', password='test'), self.user1)

    @modify_settings(AUTHENTICATION_BACKENDS={'prepend': backend})
    def test_has_perm_denied(self):
        content_type = ContentType.objects.get_for_model(Group)
        perm = Permission.objects.create(name='test', content_type=content_type, codename='test')
        self.user1.user_permissions.add(perm)

        self.assertIs(self.user1.has_perm('auth.test'), False)
        self.assertIs(self.user1.has_module_perms('auth'), False)

    @modify_settings(AUTHENTICATION_BACKENDS={'append': backend})
    def test_has_perm(self):
        content_type = ContentType.objects.get_for_model(Group)
        perm = Permission.objects.create(name='test', content_type=content_type, codename='test')
        self.user1.user_permissions.add(perm)

        self.assertIs(self.user1.has_perm('auth.test'), True)
        self.assertIs(self.user1.has_module_perms('auth'), True)


class NewModelBackend(ModelBackend):
    pass


class ChangedBackendSettingsTest(TestCase):
    """
    Tests for changes in the settings.AUTHENTICATION_BACKENDS
    """
    backend = 'auth_tests.test_auth_backends.NewModelBackend'

    TEST_USERNAME = 'test_user'
    TEST_PASSWORD = 'test_password'
    TEST_EMAIL = 'test@example.com'

    def setUp(self):
        User.objects.create_user(self.TEST_USERNAME, self.TEST_EMAIL, self.TEST_PASSWORD)

    @override_settings(AUTHENTICATION_BACKENDS=[backend])
    def test_changed_backend_settings(self):
        """
        Removing a backend configured in AUTHENTICATION_BACKENDS makes already
        logged-in users disconnect.
        """
        # Get a session for the test user
        self.assertTrue(self.client.login(
            username=self.TEST_USERNAME,
            password=self.TEST_PASSWORD)
        )
        # Prepare a request object
        request = HttpRequest()
        request.session = self.client.session
        # Remove NewModelBackend
        with self.settings(AUTHENTICATION_BACKENDS=[
                'django.contrib.auth.backends.ModelBackend']):
            # Get the user from the request
            user = get_user(request)

            # Assert that the user retrieval is successful and the user is
            # anonymous as the backend is not longer available.
            self.assertIsNotNone(user)
            self.assertTrue(user.is_anonymous)


class TypeErrorBackend:
    """
    Always raises TypeError.
    """

    def authenticate(self, request, username=None, password=None):
        raise TypeError


class SkippedBackend:
    def authenticate(self):
        # Doesn't accept any credentials so is skipped by authenticate().
        pass


class AuthenticateTests(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user('test', 'test@example.com', 'test')

    @override_settings(AUTHENTICATION_BACKENDS=['auth_tests.test_auth_backends.TypeErrorBackend'])
    def test_type_error_raised(self):
        """A TypeError within a backend is propagated properly (#18171)."""
        with self.assertRaises(TypeError):
            authenticate(username='test', password='test')

    @override_settings(AUTHENTICATION_BACKENDS=(
        'auth_tests.test_auth_backends.SkippedBackend',
        'django.contrib.auth.backends.ModelBackend',
    ))
    def test_skips_backends_without_arguments(self):
        """
        A backend (SkippedBackend) is ignored if it doesn't accept the
        credentials as arguments.
        """
        self.assertEqual(authenticate(username='test', password='test'), self.user1)


class ImproperlyConfiguredUserModelTest(TestCase):
    """
    An exception from within get_user_model() is propagated and doesn't
    raise an UnboundLocalError (#21439).
    """
    def setUp(self):
        self.user1 = User.objects.create_user('test', 'test@example.com', 'test')
        self.client.login(username='test', password='test')

    @override_settings(AUTH_USER_MODEL='thismodel.doesntexist')
    def test_does_not_shadow_exception(self):
        # Prepare a request object
        request = HttpRequest()
        request.session = self.client.session

        msg = (
            "AUTH_USER_MODEL refers to model 'thismodel.doesntexist' "
            "that has not been installed"
        )
        with self.assertRaisesMessage(ImproperlyConfigured, msg):
            get_user(request)


class ImportedModelBackend(ModelBackend):
    pass


class CustomModelBackend(ModelBackend):
    pass


class OtherModelBackend(ModelBackend):
    pass


class ImportedBackendTests(TestCase):
    """
    #23925 - The backend path added to the session should be the same
    as the one defined in AUTHENTICATION_BACKENDS setting.
    """

    backend = 'auth_tests.backend_alias.ImportedModelBackend'

    @override_settings(AUTHENTICATION_BACKENDS=[backend])
    def test_backend_path(self):
        username = 'username'
        password = 'password'
        User.objects.create_user(username, 'email', password)
        self.assertTrue(self.client.login(username=username, password=password))
        request = HttpRequest()
        request.session = self.client.session
        self.assertEqual(request.session[BACKEND_SESSION_KEY], self.backend)


class SelectingBackendTests(TestCase):
    backend = 'auth_tests.test_auth_backends.CustomModelBackend'
    other_backend = 'auth_tests.test_auth_backends.OtherModelBackend'
    username = 'username'
    password = 'password'

    def assertBackendInSession(self, backend):
        request = HttpRequest()
        request.session = self.client.session
        self.assertEqual(request.session[BACKEND_SESSION_KEY], backend)

    @override_settings(AUTHENTICATION_BACKENDS=[backend])
    def test_backend_path_login_without_authenticate_single_backend(self):
        user = User.objects.create_user(self.username, 'email', self.password)
        self.client._login(user)
        self.assertBackendInSession(self.backend)

    @override_settings(AUTHENTICATION_BACKENDS=[backend, other_backend])
    def test_backend_path_login_without_authenticate_multiple_backends(self):
        user = User.objects.create_user(self.username, 'email', self.password)
        expected_message = (
            'You have multiple authentication backends configured and '
            'therefore must provide the `backend` argument or set the '
            '`backend` attribute on the user.'
        )
        with self.assertRaisesMessage(ValueError, expected_message):
            self.client._login(user)

    @override_settings(AUTHENTICATION_BACKENDS=[backend, other_backend])
    def test_backend_path_login_with_explicit_backends(self):
        user = User.objects.create_user(self.username, 'email', self.password)
        self.client._login(user, self.other_backend)
        self.assertBackendInSession(self.other_backend)


@override_settings(AUTHENTICATION_BACKENDS=['django.contrib.auth.backends.AllowAllUsersModelBackend'])
class AllowAllUsersModelBackendTest(TestCase):
    """
    Inactive users may authenticate with the AllowAllUsersModelBackend.
    """
    user_credentials = {'username': 'test', 'password': 'test'}

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email='test@example.com', is_active=False,
            **cls.user_credentials
        )

    def test_authenticate(self):
        self.assertFalse(self.user.is_active)
        self.assertEqual(authenticate(**self.user_credentials), self.user)

    def test_get_user(self):
        self.client.force_login(self.user)
        request = HttpRequest()
        request.session = self.client.session
        user = get_user(request)
        self.assertEqual(user, self.user)
