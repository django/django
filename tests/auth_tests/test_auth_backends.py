import sys
from datetime import date
from unittest import mock

from asgiref.sync import sync_to_async

from django.contrib.auth import (
    BACKEND_SESSION_KEY,
    SESSION_KEY,
    _clean_credentials,
    aauthenticate,
    authenticate,
    get_user,
    signals,
)
from django.contrib.auth.backends import BaseBackend, ModelBackend
from django.contrib.auth.hashers import MD5PasswordHasher
from django.contrib.auth.models import AnonymousUser, Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ImproperlyConfigured, PermissionDenied
from django.http import HttpRequest
from django.test import (
    RequestFactory,
    SimpleTestCase,
    TestCase,
    modify_settings,
    override_settings,
)
from django.views.debug import technical_500_response
from django.views.decorators.debug import sensitive_variables

from .models import (
    CustomPermissionsUser,
    CustomUser,
    CustomUserWithoutIsActiveField,
    ExtensionUser,
    UUIDUser,
)


class SimpleBackend(BaseBackend):
    def get_user_permissions(self, user_obj, obj=None):
        return ["user_perm"]

    def get_group_permissions(self, user_obj, obj=None):
        return ["group_perm"]


@override_settings(
    AUTHENTICATION_BACKENDS=["auth_tests.test_auth_backends.SimpleBackend"]
)
class BaseBackendTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("test", "test@example.com", "test")

    def test_get_user_permissions(self):
        self.assertEqual(self.user.get_user_permissions(), {"user_perm"})

    async def test_aget_user_permissions(self):
        self.assertEqual(await self.user.aget_user_permissions(), {"user_perm"})

    def test_get_group_permissions(self):
        self.assertEqual(self.user.get_group_permissions(), {"group_perm"})

    async def test_aget_group_permissions(self):
        self.assertEqual(await self.user.aget_group_permissions(), {"group_perm"})

    def test_get_all_permissions(self):
        self.assertEqual(self.user.get_all_permissions(), {"user_perm", "group_perm"})

    async def test_aget_all_permissions(self):
        self.assertEqual(
            await self.user.aget_all_permissions(), {"user_perm", "group_perm"}
        )

    def test_has_perm(self):
        self.assertIs(self.user.has_perm("user_perm"), True)
        self.assertIs(self.user.has_perm("group_perm"), True)
        self.assertIs(self.user.has_perm("other_perm", TestObj()), False)

    async def test_ahas_perm(self):
        self.assertIs(await self.user.ahas_perm("user_perm"), True)
        self.assertIs(await self.user.ahas_perm("group_perm"), True)
        self.assertIs(await self.user.ahas_perm("other_perm", TestObj()), False)

    def test_has_perms_perm_list_invalid(self):
        msg = "perm_list must be an iterable of permissions."
        with self.assertRaisesMessage(ValueError, msg):
            self.user.has_perms("user_perm")
        with self.assertRaisesMessage(ValueError, msg):
            self.user.has_perms(object())

    async def test_ahas_perms_perm_list_invalid(self):
        msg = "perm_list must be an iterable of permissions."
        with self.assertRaisesMessage(ValueError, msg):
            await self.user.ahas_perms("user_perm")
        with self.assertRaisesMessage(ValueError, msg):
            await self.user.ahas_perms(object())


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

    backend = "django.contrib.auth.backends.ModelBackend"

    @classmethod
    def setUpClass(cls):
        cls.enterClassContext(
            modify_settings(AUTHENTICATION_BACKENDS={"append": cls.backend})
        )
        super().setUpClass()

    def setUp(self):
        # The custom_perms test messes with ContentTypes, which will be cached.
        # Flush the cache to ensure there are no side effects.
        self.addCleanup(ContentType.objects.clear_cache)
        self.create_users()

    def test_has_perm(self):
        user = self.UserModel._default_manager.get(pk=self.user.pk)
        self.assertIs(user.has_perm("auth.test"), False)

        user.is_staff = True
        user.save()
        self.assertIs(user.has_perm("auth.test"), False)

        user.is_superuser = True
        user.save()
        self.assertIs(user.has_perm("auth.test"), True)

        user.is_staff = True
        user.is_superuser = True
        user.is_active = False
        user.save()
        self.assertIs(user.has_perm("auth.test"), False)

    async def test_ahas_perm(self):
        user = await self.UserModel._default_manager.aget(pk=self.user.pk)
        self.assertIs(await user.ahas_perm("auth.test"), False)

        user.is_staff = True
        await user.asave()
        self.assertIs(await user.ahas_perm("auth.test"), False)

        user.is_superuser = True
        await user.asave()
        self.assertIs(await user.ahas_perm("auth.test"), True)
        self.assertIs(await user.ahas_module_perms("auth"), True)

        user.is_staff = True
        user.is_superuser = True
        user.is_active = False
        await user.asave()
        self.assertIs(await user.ahas_perm("auth.test"), False)

    def test_custom_perms(self):
        user = self.UserModel._default_manager.get(pk=self.user.pk)
        content_type = ContentType.objects.get_for_model(Group)
        perm = Permission.objects.create(
            name="test", content_type=content_type, codename="test"
        )
        user.user_permissions.add(perm)

        # reloading user to purge the _perm_cache
        user = self.UserModel._default_manager.get(pk=self.user.pk)
        self.assertEqual(user.get_all_permissions(), {"auth.test"})
        self.assertEqual(user.get_user_permissions(), {"auth.test"})
        self.assertEqual(user.get_group_permissions(), set())
        self.assertIs(user.has_module_perms("Group"), False)
        self.assertIs(user.has_module_perms("auth"), True)

        perm = Permission.objects.create(
            name="test2", content_type=content_type, codename="test2"
        )
        user.user_permissions.add(perm)
        perm = Permission.objects.create(
            name="test3", content_type=content_type, codename="test3"
        )
        user.user_permissions.add(perm)
        user = self.UserModel._default_manager.get(pk=self.user.pk)
        expected_user_perms = {"auth.test2", "auth.test", "auth.test3"}
        self.assertEqual(user.get_all_permissions(), expected_user_perms)
        self.assertIs(user.has_perm("test"), False)
        self.assertIs(user.has_perm("auth.test"), True)
        self.assertIs(user.has_perms(["auth.test2", "auth.test3"]), True)

        perm = Permission.objects.create(
            name="test_group", content_type=content_type, codename="test_group"
        )
        group = Group.objects.create(name="test_group")
        group.permissions.add(perm)
        user.groups.add(group)
        user = self.UserModel._default_manager.get(pk=self.user.pk)
        self.assertEqual(
            user.get_all_permissions(), {*expected_user_perms, "auth.test_group"}
        )
        self.assertEqual(user.get_user_permissions(), expected_user_perms)
        self.assertEqual(user.get_group_permissions(), {"auth.test_group"})
        self.assertIs(user.has_perms(["auth.test3", "auth.test_group"]), True)

        user = AnonymousUser()
        self.assertIs(user.has_perm("test"), False)
        self.assertIs(user.has_perms(["auth.test2", "auth.test3"]), False)

    async def test_acustom_perms(self):
        user = await self.UserModel._default_manager.aget(pk=self.user.pk)
        content_type = await sync_to_async(ContentType.objects.get_for_model)(Group)
        perm = await Permission.objects.acreate(
            name="test", content_type=content_type, codename="test"
        )
        await user.user_permissions.aadd(perm)

        # Reloading user to purge the _perm_cache.
        user = await self.UserModel._default_manager.aget(pk=self.user.pk)
        self.assertEqual(await user.aget_all_permissions(), {"auth.test"})
        self.assertEqual(await user.aget_user_permissions(), {"auth.test"})
        self.assertEqual(await user.aget_group_permissions(), set())
        self.assertIs(await user.ahas_module_perms("Group"), False)
        self.assertIs(await user.ahas_module_perms("auth"), True)

        perm = await Permission.objects.acreate(
            name="test2", content_type=content_type, codename="test2"
        )
        await user.user_permissions.aadd(perm)
        perm = await Permission.objects.acreate(
            name="test3", content_type=content_type, codename="test3"
        )
        await user.user_permissions.aadd(perm)
        user = await self.UserModel._default_manager.aget(pk=self.user.pk)
        expected_user_perms = {"auth.test2", "auth.test", "auth.test3"}
        self.assertEqual(await user.aget_all_permissions(), expected_user_perms)
        self.assertIs(await user.ahas_perm("test"), False)
        self.assertIs(await user.ahas_perm("auth.test"), True)
        self.assertIs(await user.ahas_perms(["auth.test2", "auth.test3"]), True)

        perm = await Permission.objects.acreate(
            name="test_group", content_type=content_type, codename="test_group"
        )
        group = await Group.objects.acreate(name="test_group")
        await group.permissions.aadd(perm)
        await user.groups.aadd(group)
        user = await self.UserModel._default_manager.aget(pk=self.user.pk)
        self.assertEqual(
            await user.aget_all_permissions(), {*expected_user_perms, "auth.test_group"}
        )
        self.assertEqual(await user.aget_user_permissions(), expected_user_perms)
        self.assertEqual(await user.aget_group_permissions(), {"auth.test_group"})
        self.assertIs(await user.ahas_perms(["auth.test3", "auth.test_group"]), True)

        user = AnonymousUser()
        self.assertIs(await user.ahas_perm("test"), False)
        self.assertIs(await user.ahas_perms(["auth.test2", "auth.test3"]), False)

    def test_has_no_object_perm(self):
        """Regressiontest for #12462"""
        user = self.UserModel._default_manager.get(pk=self.user.pk)
        content_type = ContentType.objects.get_for_model(Group)
        perm = Permission.objects.create(
            name="test", content_type=content_type, codename="test"
        )
        user.user_permissions.add(perm)

        self.assertIs(user.has_perm("auth.test", "object"), False)
        self.assertEqual(user.get_all_permissions("object"), set())
        self.assertIs(user.has_perm("auth.test"), True)
        self.assertEqual(user.get_all_permissions(), {"auth.test"})

    async def test_ahas_no_object_perm(self):
        """See test_has_no_object_perm()"""
        user = await self.UserModel._default_manager.aget(pk=self.user.pk)
        content_type = await sync_to_async(ContentType.objects.get_for_model)(Group)
        perm = await Permission.objects.acreate(
            name="test", content_type=content_type, codename="test"
        )
        await user.user_permissions.aadd(perm)

        self.assertIs(await user.ahas_perm("auth.test", "object"), False)
        self.assertEqual(await user.aget_all_permissions("object"), set())
        self.assertIs(await user.ahas_perm("auth.test"), True)
        self.assertEqual(await user.aget_all_permissions(), {"auth.test"})

    def test_anonymous_has_no_permissions(self):
        """
        #17903 -- Anonymous users shouldn't have permissions in
        ModelBackend.get_(all|user|group)_permissions().
        """
        backend = ModelBackend()

        user = self.UserModel._default_manager.get(pk=self.user.pk)
        content_type = ContentType.objects.get_for_model(Group)
        user_perm = Permission.objects.create(
            name="test", content_type=content_type, codename="test_user"
        )
        group_perm = Permission.objects.create(
            name="test2", content_type=content_type, codename="test_group"
        )
        user.user_permissions.add(user_perm)

        group = Group.objects.create(name="test_group")
        user.groups.add(group)
        group.permissions.add(group_perm)

        self.assertEqual(
            backend.get_all_permissions(user), {"auth.test_user", "auth.test_group"}
        )
        self.assertEqual(backend.get_user_permissions(user), {"auth.test_user"})
        self.assertEqual(backend.get_group_permissions(user), {"auth.test_group"})

        with mock.patch.object(self.UserModel, "is_anonymous", True):
            self.assertEqual(backend.get_all_permissions(user), set())
            self.assertEqual(backend.get_user_permissions(user), set())
            self.assertEqual(backend.get_group_permissions(user), set())

    async def test_aanonymous_has_no_permissions(self):
        """See test_anonymous_has_no_permissions()"""
        backend = ModelBackend()

        user = await self.UserModel._default_manager.aget(pk=self.user.pk)
        content_type = await sync_to_async(ContentType.objects.get_for_model)(Group)
        user_perm = await Permission.objects.acreate(
            name="test", content_type=content_type, codename="test_user"
        )
        group_perm = await Permission.objects.acreate(
            name="test2", content_type=content_type, codename="test_group"
        )
        await user.user_permissions.aadd(user_perm)

        group = await Group.objects.acreate(name="test_group")
        await user.groups.aadd(group)
        await group.permissions.aadd(group_perm)

        self.assertEqual(
            await backend.aget_all_permissions(user),
            {"auth.test_user", "auth.test_group"},
        )
        self.assertEqual(await backend.aget_user_permissions(user), {"auth.test_user"})
        self.assertEqual(
            await backend.aget_group_permissions(user), {"auth.test_group"}
        )

        with mock.patch.object(self.UserModel, "is_anonymous", True):
            self.assertEqual(await backend.aget_all_permissions(user), set())
            self.assertEqual(await backend.aget_user_permissions(user), set())
            self.assertEqual(await backend.aget_group_permissions(user), set())

    def test_inactive_has_no_permissions(self):
        """
        #17903 -- Inactive users shouldn't have permissions in
        ModelBackend.get_(all|user|group)_permissions().
        """
        backend = ModelBackend()

        user = self.UserModel._default_manager.get(pk=self.user.pk)
        content_type = ContentType.objects.get_for_model(Group)
        user_perm = Permission.objects.create(
            name="test", content_type=content_type, codename="test_user"
        )
        group_perm = Permission.objects.create(
            name="test2", content_type=content_type, codename="test_group"
        )
        user.user_permissions.add(user_perm)

        group = Group.objects.create(name="test_group")
        user.groups.add(group)
        group.permissions.add(group_perm)

        self.assertEqual(
            backend.get_all_permissions(user), {"auth.test_user", "auth.test_group"}
        )
        self.assertEqual(backend.get_user_permissions(user), {"auth.test_user"})
        self.assertEqual(backend.get_group_permissions(user), {"auth.test_group"})

        user.is_active = False
        user.save()

        self.assertEqual(backend.get_all_permissions(user), set())
        self.assertEqual(backend.get_user_permissions(user), set())
        self.assertEqual(backend.get_group_permissions(user), set())

    async def test_ainactive_has_no_permissions(self):
        """See test_inactive_has_no_permissions()"""
        backend = ModelBackend()

        user = await self.UserModel._default_manager.aget(pk=self.user.pk)
        content_type = await sync_to_async(ContentType.objects.get_for_model)(Group)
        user_perm = await Permission.objects.acreate(
            name="test", content_type=content_type, codename="test_user"
        )
        group_perm = await Permission.objects.acreate(
            name="test2", content_type=content_type, codename="test_group"
        )
        await user.user_permissions.aadd(user_perm)

        group = await Group.objects.acreate(name="test_group")
        await user.groups.aadd(group)
        await group.permissions.aadd(group_perm)

        self.assertEqual(
            await backend.aget_all_permissions(user),
            {"auth.test_user", "auth.test_group"},
        )
        self.assertEqual(await backend.aget_user_permissions(user), {"auth.test_user"})
        self.assertEqual(
            await backend.aget_group_permissions(user), {"auth.test_group"}
        )

        user.is_active = False
        await user.asave()

        self.assertEqual(await backend.aget_all_permissions(user), set())
        self.assertEqual(await backend.aget_user_permissions(user), set())
        self.assertEqual(await backend.aget_group_permissions(user), set())

    def test_get_all_superuser_permissions(self):
        """A superuser has all permissions. Refs #14795."""
        user = self.UserModel._default_manager.get(pk=self.superuser.pk)
        self.assertEqual(len(user.get_all_permissions()), len(Permission.objects.all()))

    async def test_aget_all_superuser_permissions(self):
        """See test_get_all_superuser_permissions()"""
        user = await self.UserModel._default_manager.aget(pk=self.superuser.pk)
        self.assertEqual(
            len(await user.aget_all_permissions()), await Permission.objects.acount()
        )

    @override_settings(
        PASSWORD_HASHERS=["auth_tests.test_auth_backends.CountingMD5PasswordHasher"]
    )
    def test_authentication_timing(self):
        """Hasher is run once regardless of whether the user exists. Refs #20760."""
        # Re-set the password, because this tests overrides PASSWORD_HASHERS
        self.user.set_password("test")
        self.user.save()

        CountingMD5PasswordHasher.calls = 0
        username = getattr(self.user, self.UserModel.USERNAME_FIELD)
        authenticate(username=username, password="test")
        self.assertEqual(CountingMD5PasswordHasher.calls, 1)

        CountingMD5PasswordHasher.calls = 0
        authenticate(username="no_such_user", password="test")
        self.assertEqual(CountingMD5PasswordHasher.calls, 1)

    @override_settings(
        PASSWORD_HASHERS=["auth_tests.test_auth_backends.CountingMD5PasswordHasher"]
    )
    async def test_aauthentication_timing(self):
        """See test_authentication_timing()"""
        # Re-set the password, because this tests overrides PASSWORD_HASHERS.
        self.user.set_password("test")
        await self.user.asave()

        CountingMD5PasswordHasher.calls = 0
        username = getattr(self.user, self.UserModel.USERNAME_FIELD)
        await aauthenticate(username=username, password="test")
        self.assertEqual(CountingMD5PasswordHasher.calls, 1)

        CountingMD5PasswordHasher.calls = 0
        await aauthenticate(username="no_such_user", password="test")
        self.assertEqual(CountingMD5PasswordHasher.calls, 1)

    @override_settings(
        PASSWORD_HASHERS=["auth_tests.test_auth_backends.CountingMD5PasswordHasher"]
    )
    def test_authentication_without_credentials(self):
        CountingMD5PasswordHasher.calls = 0
        for credentials in (
            {},
            {"username": getattr(self.user, self.UserModel.USERNAME_FIELD)},
            {"password": "test"},
        ):
            with self.subTest(credentials=credentials):
                with self.assertNumQueries(0):
                    authenticate(**credentials)
                self.assertEqual(CountingMD5PasswordHasher.calls, 0)


class ModelBackendTest(BaseModelBackendTest, TestCase):
    """
    Tests for the ModelBackend using the default User model.
    """

    UserModel = User
    user_credentials = {"username": "test", "password": "test"}

    def create_users(self):
        self.user = User.objects.create_user(
            email="test@example.com", **self.user_credentials
        )
        self.superuser = User.objects.create_superuser(
            username="test2",
            email="test2@example.com",
            password="test",
        )

    def test_authenticate_inactive(self):
        """
        An inactive user can't authenticate.
        """
        self.assertEqual(authenticate(**self.user_credentials), self.user)
        self.user.is_active = False
        self.user.save()
        self.assertIsNone(authenticate(**self.user_credentials))

    async def test_aauthenticate_inactive(self):
        """
        An inactive user can't authenticate.
        """
        self.assertEqual(await aauthenticate(**self.user_credentials), self.user)
        self.user.is_active = False
        await self.user.asave()
        self.assertIsNone(await aauthenticate(**self.user_credentials))

    @override_settings(AUTH_USER_MODEL="auth_tests.CustomUserWithoutIsActiveField")
    def test_authenticate_user_without_is_active_field(self):
        """
        A custom user without an `is_active` field is allowed to authenticate.
        """
        user = CustomUserWithoutIsActiveField.objects._create_user(
            username="test",
            email="test@example.com",
            password="test",
        )
        self.assertEqual(authenticate(username="test", password="test"), user)

    @override_settings(AUTH_USER_MODEL="auth_tests.CustomUserWithoutIsActiveField")
    async def test_aauthenticate_user_without_is_active_field(self):
        """
        A custom user without an `is_active` field is allowed to authenticate.
        """
        user = await CustomUserWithoutIsActiveField.objects._acreate_user(
            username="test",
            email="test@example.com",
            password="test",
        )
        self.assertEqual(await aauthenticate(username="test", password="test"), user)


@override_settings(AUTH_USER_MODEL="auth_tests.ExtensionUser")
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
            username="test",
            email="test@example.com",
            password="test",
            date_of_birth=date(2006, 4, 25),
        )
        self.superuser = ExtensionUser._default_manager.create_superuser(
            username="test2",
            email="test2@example.com",
            password="test",
            date_of_birth=date(1976, 11, 8),
        )


@override_settings(AUTH_USER_MODEL="auth_tests.CustomPermissionsUser")
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
            email="test@example.com", password="test", date_of_birth=date(2006, 4, 25)
        )
        self.superuser = CustomPermissionsUser._default_manager.create_superuser(
            email="test2@example.com", password="test", date_of_birth=date(1976, 11, 8)
        )


@override_settings(AUTH_USER_MODEL="auth_tests.CustomUser")
class CustomUserModelBackendAuthenticateTest(TestCase):
    """
    The model backend can accept a credentials kwarg labeled with
    custom user model's USERNAME_FIELD.
    """

    def test_authenticate(self):
        test_user = CustomUser._default_manager.create_user(
            email="test@example.com", password="test", date_of_birth=date(2006, 4, 25)
        )
        authenticated_user = authenticate(email="test@example.com", password="test")
        self.assertEqual(test_user, authenticated_user)

    async def test_aauthenticate(self):
        test_user = await CustomUser._default_manager.acreate_user(
            email="test@example.com", password="test", date_of_birth=date(2006, 4, 25)
        )
        authenticated_user = await aauthenticate(
            email="test@example.com", password="test"
        )
        self.assertEqual(test_user, authenticated_user)


@override_settings(AUTH_USER_MODEL="auth_tests.UUIDUser")
class UUIDUserTests(TestCase):
    def test_login(self):
        """
        A custom user with a UUID primary key should be able to login.
        """
        user = UUIDUser.objects.create_user(username="uuid", password="test")
        self.assertTrue(self.client.login(username="uuid", password="test"))
        self.assertEqual(
            UUIDUser.objects.get(pk=self.client.session[SESSION_KEY]), user
        )

    async def test_alogin(self):
        """See test_login()"""
        user = await UUIDUser.objects.acreate_user(username="uuid", password="test")
        self.assertTrue(await self.client.alogin(username="uuid", password="test"))
        session_key = await self.client.session.aget(SESSION_KEY)
        self.assertEqual(await UUIDUser.objects.aget(pk=session_key), user)


class TestObj:
    pass


class SimpleRowlevelBackend:
    def has_perm(self, user, perm, obj=None):
        if not obj:
            return  # We only support row level perms

        if isinstance(obj, TestObj):
            if user.username == "test2":
                return True
            elif user.is_anonymous and perm == "anon":
                return True
            elif not user.is_active and perm == "inactive":
                return True
        return False

    async def ahas_perm(self, user, perm, obj=None):
        return self.has_perm(user, perm, obj)

    def has_module_perms(self, user, app_label):
        return (user.is_anonymous or user.is_active) and app_label == "app1"

    async def ahas_module_perms(self, user, app_label):
        return self.has_module_perms(user, app_label)

    def get_all_permissions(self, user, obj=None):
        if not obj:
            return []  # We only support row level perms

        if not isinstance(obj, TestObj):
            return ["none"]

        if user.is_anonymous:
            return ["anon"]
        if user.username == "test2":
            return ["simple", "advanced"]
        else:
            return ["simple"]

    async def aget_all_permissions(self, user, obj=None):
        return self.get_all_permissions(user, obj)

    def get_group_permissions(self, user, obj=None):
        if not obj:
            return  # We only support row level perms

        if not isinstance(obj, TestObj):
            return ["none"]

        if "test_group" in [group.name for group in user.groups.all()]:
            return ["group_perm"]
        else:
            return ["none"]


@modify_settings(
    AUTHENTICATION_BACKENDS={
        "append": "auth_tests.test_auth_backends.SimpleRowlevelBackend",
    }
)
class RowlevelBackendTest(TestCase):
    """
    Tests for auth backend that supports object level permissions
    """

    @classmethod
    def setUpTestData(cls):
        cls.user1 = User.objects.create_user("test", "test@example.com", "test")
        cls.user2 = User.objects.create_user("test2", "test2@example.com", "test")
        cls.user3 = User.objects.create_user("test3", "test3@example.com", "test")

    def tearDown(self):
        # The get_group_permissions test messes with ContentTypes, which will
        # be cached; flush the cache to ensure there are no side effects
        # Refs #14975, #14925
        ContentType.objects.clear_cache()

    def test_has_perm(self):
        self.assertIs(self.user1.has_perm("perm", TestObj()), False)
        self.assertIs(self.user2.has_perm("perm", TestObj()), True)
        self.assertIs(self.user2.has_perm("perm"), False)
        self.assertIs(self.user2.has_perms(["simple", "advanced"], TestObj()), True)
        self.assertIs(self.user3.has_perm("perm", TestObj()), False)
        self.assertIs(self.user3.has_perm("anon", TestObj()), False)
        self.assertIs(self.user3.has_perms(["simple", "advanced"], TestObj()), False)

    def test_get_all_permissions(self):
        self.assertEqual(self.user1.get_all_permissions(TestObj()), {"simple"})
        self.assertEqual(
            self.user2.get_all_permissions(TestObj()), {"simple", "advanced"}
        )
        self.assertEqual(self.user2.get_all_permissions(), set())

    def test_get_group_permissions(self):
        group = Group.objects.create(name="test_group")
        self.user3.groups.add(group)
        self.assertEqual(self.user3.get_group_permissions(TestObj()), {"group_perm"})


@override_settings(
    AUTHENTICATION_BACKENDS=["auth_tests.test_auth_backends.SimpleRowlevelBackend"],
)
class AnonymousUserBackendTest(SimpleTestCase):
    """
    Tests for AnonymousUser delegating to backend.
    """

    def setUp(self):
        self.user1 = AnonymousUser()

    def test_has_perm(self):
        self.assertIs(self.user1.has_perm("perm", TestObj()), False)
        self.assertIs(self.user1.has_perm("anon", TestObj()), True)

    async def test_ahas_perm(self):
        self.assertIs(await self.user1.ahas_perm("perm", TestObj()), False)
        self.assertIs(await self.user1.ahas_perm("anon", TestObj()), True)

    def test_has_perms(self):
        self.assertIs(self.user1.has_perms(["anon"], TestObj()), True)
        self.assertIs(self.user1.has_perms(["anon", "perm"], TestObj()), False)

    async def test_ahas_perms(self):
        self.assertIs(await self.user1.ahas_perms(["anon"], TestObj()), True)
        self.assertIs(await self.user1.ahas_perms(["anon", "perm"], TestObj()), False)

    def test_has_perms_perm_list_invalid(self):
        msg = "perm_list must be an iterable of permissions."
        with self.assertRaisesMessage(ValueError, msg):
            self.user1.has_perms("perm")
        with self.assertRaisesMessage(ValueError, msg):
            self.user1.has_perms(object())

    async def test_ahas_perms_perm_list_invalid(self):
        msg = "perm_list must be an iterable of permissions."
        with self.assertRaisesMessage(ValueError, msg):
            await self.user1.ahas_perms("perm")
        with self.assertRaisesMessage(ValueError, msg):
            await self.user1.ahas_perms(object())

    def test_has_module_perms(self):
        self.assertIs(self.user1.has_module_perms("app1"), True)
        self.assertIs(self.user1.has_module_perms("app2"), False)

    async def test_ahas_module_perms(self):
        self.assertIs(await self.user1.ahas_module_perms("app1"), True)
        self.assertIs(await self.user1.ahas_module_perms("app2"), False)

    def test_get_all_permissions(self):
        self.assertEqual(self.user1.get_all_permissions(TestObj()), {"anon"})

    async def test_aget_all_permissions(self):
        self.assertEqual(await self.user1.aget_all_permissions(TestObj()), {"anon"})


@override_settings(AUTHENTICATION_BACKENDS=[])
class NoBackendsTest(TestCase):
    """
    An appropriate error is raised if no auth backends are provided.
    """

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("test", "test@example.com", "test")

    def test_raises_exception(self):
        msg = (
            "No authentication backends have been defined. "
            "Does AUTHENTICATION_BACKENDS contain anything?"
        )
        with self.assertRaisesMessage(ImproperlyConfigured, msg):
            self.user.has_perm(("perm", TestObj()))

    async def test_araises_exception(self):
        msg = (
            "No authentication backends have been defined. "
            "Does AUTHENTICATION_BACKENDS contain anything?"
        )
        with self.assertRaisesMessage(ImproperlyConfigured, msg):
            await self.user.ahas_perm(("perm", TestObj()))


@override_settings(
    AUTHENTICATION_BACKENDS=["auth_tests.test_auth_backends.SimpleRowlevelBackend"]
)
class InActiveUserBackendTest(TestCase):
    """
    Tests for an inactive user
    """

    @classmethod
    def setUpTestData(cls):
        cls.user1 = User.objects.create_user("test", "test@example.com", "test")
        cls.user1.is_active = False
        cls.user1.save()

    def test_has_perm(self):
        self.assertIs(self.user1.has_perm("perm", TestObj()), False)
        self.assertIs(self.user1.has_perm("inactive", TestObj()), True)

    def test_has_module_perms(self):
        self.assertIs(self.user1.has_module_perms("app1"), False)
        self.assertIs(self.user1.has_module_perms("app2"), False)


class PermissionDeniedBackend:
    """
    Always raises PermissionDenied in `authenticate`, `has_perm` and `has_module_perms`.
    """

    def authenticate(self, request, username=None, password=None):
        raise PermissionDenied

    async def aauthenticate(self, request, username=None, password=None):
        raise PermissionDenied

    def has_perm(self, user_obj, perm, obj=None):
        raise PermissionDenied

    async def ahas_perm(self, user_obj, perm, obj=None):
        raise PermissionDenied

    def has_module_perms(self, user_obj, app_label):
        raise PermissionDenied

    async def ahas_module_perms(self, user_obj, app_label):
        raise PermissionDenied


class PermissionDeniedBackendTest(TestCase):
    """
    Other backends are not checked once a backend raises PermissionDenied
    """

    backend = "auth_tests.test_auth_backends.PermissionDeniedBackend"

    @classmethod
    def setUpTestData(cls):
        cls.user1 = User.objects.create_user("test", "test@example.com", "test")

    def setUp(self):
        self.user_login_failed = []
        signals.user_login_failed.connect(self.user_login_failed_listener)
        self.addCleanup(
            signals.user_login_failed.disconnect, self.user_login_failed_listener
        )

    def user_login_failed_listener(self, sender, credentials, **kwargs):
        self.user_login_failed.append(credentials)

    @modify_settings(AUTHENTICATION_BACKENDS={"prepend": backend})
    def test_permission_denied(self):
        "user is not authenticated after a backend raises permission denied #2550"
        self.assertIsNone(authenticate(username="test", password="test"))
        # user_login_failed signal is sent.
        self.assertEqual(
            self.user_login_failed,
            [{"password": "********************", "username": "test"}],
        )

    @modify_settings(AUTHENTICATION_BACKENDS={"prepend": backend})
    async def test_aauthenticate_permission_denied(self):
        self.assertIsNone(await aauthenticate(username="test", password="test"))
        # user_login_failed signal is sent.
        self.assertEqual(
            self.user_login_failed,
            [{"password": "********************", "username": "test"}],
        )

    @modify_settings(AUTHENTICATION_BACKENDS={"append": backend})
    def test_authenticates(self):
        self.assertEqual(authenticate(username="test", password="test"), self.user1)

    @modify_settings(AUTHENTICATION_BACKENDS={"append": backend})
    async def test_aauthenticate(self):
        self.assertEqual(
            await aauthenticate(username="test", password="test"), self.user1
        )

    @modify_settings(AUTHENTICATION_BACKENDS={"prepend": backend})
    def test_has_perm_denied(self):
        content_type = ContentType.objects.get_for_model(Group)
        perm = Permission.objects.create(
            name="test", content_type=content_type, codename="test"
        )
        self.user1.user_permissions.add(perm)

        self.assertIs(self.user1.has_perm("auth.test"), False)
        self.assertIs(self.user1.has_module_perms("auth"), False)

    @modify_settings(AUTHENTICATION_BACKENDS={"prepend": backend})
    async def test_ahas_perm_denied(self):
        content_type = await sync_to_async(ContentType.objects.get_for_model)(Group)
        perm = await Permission.objects.acreate(
            name="test", content_type=content_type, codename="test"
        )
        await self.user1.user_permissions.aadd(perm)

        self.assertIs(await self.user1.ahas_perm("auth.test"), False)
        self.assertIs(await self.user1.ahas_module_perms("auth"), False)

    @modify_settings(AUTHENTICATION_BACKENDS={"append": backend})
    def test_has_perm(self):
        content_type = ContentType.objects.get_for_model(Group)
        perm = Permission.objects.create(
            name="test", content_type=content_type, codename="test"
        )
        self.user1.user_permissions.add(perm)

        self.assertIs(self.user1.has_perm("auth.test"), True)
        self.assertIs(self.user1.has_module_perms("auth"), True)

    @modify_settings(AUTHENTICATION_BACKENDS={"append": backend})
    async def test_ahas_perm(self):
        content_type = await sync_to_async(ContentType.objects.get_for_model)(Group)
        perm = await Permission.objects.acreate(
            name="test", content_type=content_type, codename="test"
        )
        await self.user1.user_permissions.aadd(perm)

        self.assertIs(await self.user1.ahas_perm("auth.test"), True)
        self.assertIs(await self.user1.ahas_module_perms("auth"), True)


class NewModelBackend(ModelBackend):
    pass


class ChangedBackendSettingsTest(TestCase):
    """
    Tests for changes in the settings.AUTHENTICATION_BACKENDS
    """

    backend = "auth_tests.test_auth_backends.NewModelBackend"

    TEST_USERNAME = "test_user"
    TEST_PASSWORD = "test_password"
    TEST_EMAIL = "test@example.com"

    @classmethod
    def setUpTestData(cls):
        User.objects.create_user(cls.TEST_USERNAME, cls.TEST_EMAIL, cls.TEST_PASSWORD)

    @override_settings(AUTHENTICATION_BACKENDS=[backend])
    def test_changed_backend_settings(self):
        """
        Removing a backend configured in AUTHENTICATION_BACKENDS makes already
        logged-in users disconnect.
        """
        # Get a session for the test user
        self.assertTrue(
            self.client.login(
                username=self.TEST_USERNAME,
                password=self.TEST_PASSWORD,
            )
        )
        # Prepare a request object
        request = HttpRequest()
        request.session = self.client.session
        # Remove NewModelBackend
        with self.settings(
            AUTHENTICATION_BACKENDS=["django.contrib.auth.backends.ModelBackend"]
        ):
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

    @sensitive_variables("password")
    def authenticate(self, request, username=None, password=None):
        raise TypeError

    @sensitive_variables("password")
    async def aauthenticate(self, request, username=None, password=None):
        raise TypeError


class SkippedBackend:
    def authenticate(self):
        # Doesn't accept any credentials so is skipped by authenticate().
        pass


class SkippedBackendWithDecoratedMethod:
    @sensitive_variables()
    def authenticate(self):
        pass


class AuthenticateTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user1 = User.objects.create_user("test", "test@example.com", "test")

    def setUp(self):
        self.sensitive_password = "mypassword"

    @override_settings(
        AUTHENTICATION_BACKENDS=["auth_tests.test_auth_backends.TypeErrorBackend"]
    )
    def test_type_error_raised(self):
        """A TypeError within a backend is propagated properly (#18171)."""
        with self.assertRaises(TypeError):
            authenticate(username="test", password="test")

    @override_settings(
        AUTHENTICATION_BACKENDS=["auth_tests.test_auth_backends.TypeErrorBackend"]
    )
    def test_authenticate_sensitive_variables(self):
        try:
            authenticate(username="testusername", password=self.sensitive_password)
        except TypeError:
            exc_info = sys.exc_info()
        rf = RequestFactory()
        response = technical_500_response(rf.get("/"), *exc_info)
        self.assertNotContains(response, self.sensitive_password, status_code=500)
        self.assertContains(response, "TypeErrorBackend", status_code=500)
        self.assertContains(
            response,
            '<tr><td>credentials</td><td class="code">'
            "<pre>&#39;********************&#39;</pre></td></tr>",
            html=True,
            status_code=500,
        )

    @override_settings(
        AUTHENTICATION_BACKENDS=["auth_tests.test_auth_backends.TypeErrorBackend"]
    )
    async def test_aauthenticate_sensitive_variables(self):
        try:
            await aauthenticate(
                username="testusername", password=self.sensitive_password
            )
        except TypeError:
            exc_info = sys.exc_info()
        rf = RequestFactory()
        response = technical_500_response(rf.get("/"), *exc_info)
        self.assertNotContains(response, self.sensitive_password, status_code=500)
        self.assertContains(response, "TypeErrorBackend", status_code=500)
        self.assertContains(
            response,
            '<tr><td>credentials</td><td class="code">'
            "<pre>&#39;********************&#39;</pre></td></tr>",
            html=True,
            status_code=500,
        )

    def test_clean_credentials_sensitive_variables(self):
        try:
            # Passing in a list to cause an exception
            _clean_credentials([1, self.sensitive_password])
        except TypeError:
            exc_info = sys.exc_info()
        rf = RequestFactory()
        response = technical_500_response(rf.get("/"), *exc_info)
        self.assertNotContains(response, self.sensitive_password, status_code=500)
        self.assertContains(
            response,
            '<tr><td>credentials</td><td class="code">'
            "<pre>&#39;********************&#39;</pre></td></tr>",
            html=True,
            status_code=500,
        )

    @override_settings(
        AUTHENTICATION_BACKENDS=(
            "auth_tests.test_auth_backends.SkippedBackend",
            "django.contrib.auth.backends.ModelBackend",
        )
    )
    def test_skips_backends_without_arguments(self):
        """
        A backend (SkippedBackend) is ignored if it doesn't accept the
        credentials as arguments.
        """
        self.assertEqual(authenticate(username="test", password="test"), self.user1)

    @override_settings(
        AUTHENTICATION_BACKENDS=(
            "auth_tests.test_auth_backends.SkippedBackendWithDecoratedMethod",
            "django.contrib.auth.backends.ModelBackend",
        )
    )
    def test_skips_backends_with_decorated_method(self):
        self.assertEqual(authenticate(username="test", password="test"), self.user1)


class ImproperlyConfiguredUserModelTest(TestCase):
    """
    An exception from within get_user_model() is propagated and doesn't
    raise an UnboundLocalError (#21439).
    """

    @classmethod
    def setUpTestData(cls):
        cls.user1 = User.objects.create_user("test", "test@example.com", "test")

    def setUp(self):
        self.client.login(username="test", password="test")

    @override_settings(AUTH_USER_MODEL="thismodel.doesntexist")
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

    backend = "auth_tests.backend_alias.ImportedModelBackend"

    @override_settings(AUTHENTICATION_BACKENDS=[backend])
    def test_backend_path(self):
        username = "username"
        password = "password"
        User.objects.create_user(username, "email", password)
        self.assertTrue(self.client.login(username=username, password=password))
        request = HttpRequest()
        request.session = self.client.session
        self.assertEqual(request.session[BACKEND_SESSION_KEY], self.backend)


class SelectingBackendTests(TestCase):
    backend = "auth_tests.test_auth_backends.CustomModelBackend"
    other_backend = "auth_tests.test_auth_backends.OtherModelBackend"
    username = "username"
    password = "password"

    def assertBackendInSession(self, backend):
        request = HttpRequest()
        request.session = self.client.session
        self.assertEqual(request.session[BACKEND_SESSION_KEY], backend)

    @override_settings(AUTHENTICATION_BACKENDS=[backend])
    def test_backend_path_login_without_authenticate_single_backend(self):
        user = User.objects.create_user(self.username, "email", self.password)
        self.client._login(user)
        self.assertBackendInSession(self.backend)

    @override_settings(AUTHENTICATION_BACKENDS=[backend, other_backend])
    def test_backend_path_login_without_authenticate_multiple_backends(self):
        user = User.objects.create_user(self.username, "email", self.password)
        expected_message = (
            "You have multiple authentication backends configured and "
            "therefore must provide the `backend` argument or set the "
            "`backend` attribute on the user."
        )
        with self.assertRaisesMessage(ValueError, expected_message):
            self.client._login(user)

    def test_non_string_backend(self):
        user = User.objects.create_user(self.username, "email", self.password)
        expected_message = (
            "backend must be a dotted import path string (got "
            "<class 'django.contrib.auth.backends.ModelBackend'>)."
        )
        with self.assertRaisesMessage(TypeError, expected_message):
            self.client._login(user, backend=ModelBackend)

    @override_settings(AUTHENTICATION_BACKENDS=[backend, other_backend])
    def test_backend_path_login_with_explicit_backends(self):
        user = User.objects.create_user(self.username, "email", self.password)
        self.client._login(user, self.other_backend)
        self.assertBackendInSession(self.other_backend)


@override_settings(
    AUTHENTICATION_BACKENDS=["django.contrib.auth.backends.AllowAllUsersModelBackend"]
)
class AllowAllUsersModelBackendTest(TestCase):
    """
    Inactive users may authenticate with the AllowAllUsersModelBackend.
    """

    user_credentials = {"username": "test", "password": "test"}

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="test@example.com", is_active=False, **cls.user_credentials
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
