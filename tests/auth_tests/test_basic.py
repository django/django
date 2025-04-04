from django.conf import settings
from django.contrib.auth import aget_user, get_user, get_user_model
from django.contrib.auth.models import AnonymousUser, User
from django.core.exceptions import ImproperlyConfigured
from django.db import IntegrityError
from django.http import HttpRequest
from django.test import TestCase, override_settings
from django.utils import translation

from .models import CustomUser


class BasicTestCase(TestCase):
    def test_user(self):
        "Users can be created and can set their password"
        u = User.objects.create_user("testuser", "test@example.com", "testpw")
        self.assertTrue(u.has_usable_password())
        self.assertFalse(u.check_password("bad"))
        self.assertTrue(u.check_password("testpw"))

        # Check we can manually set an unusable password
        u.set_unusable_password()
        u.save()
        self.assertFalse(u.check_password("testpw"))
        self.assertFalse(u.has_usable_password())
        u.set_password("testpw")
        self.assertTrue(u.check_password("testpw"))
        u.set_password(None)
        self.assertFalse(u.has_usable_password())

        # Check username getter
        self.assertEqual(u.get_username(), "testuser")

        # Check authentication/permissions
        self.assertFalse(u.is_anonymous)
        self.assertTrue(u.is_authenticated)
        self.assertFalse(u.is_staff)
        self.assertTrue(u.is_active)
        self.assertFalse(u.is_superuser)

        # Check API-based user creation with no password
        u2 = User.objects.create_user("testuser2", "test2@example.com")
        self.assertFalse(u2.has_usable_password())

    async def test_acreate(self):
        u = await User.objects.acreate_user("testuser", "test@example.com", "testpw")
        self.assertTrue(u.has_usable_password())
        self.assertFalse(await u.acheck_password("bad"))
        self.assertTrue(await u.acheck_password("testpw"))

    def test_unicode_username(self):
        User.objects.create_user("jörg")
        User.objects.create_user("Григорий")
        # Two equivalent Unicode normalized usernames are duplicates.
        omega_username = "iamtheΩ"  # U+03A9 GREEK CAPITAL LETTER OMEGA
        ohm_username = "iamtheΩ"  # U+2126 OHM SIGN
        User.objects.create_user(ohm_username)
        with self.assertRaises(IntegrityError):
            User.objects.create_user(omega_username)

    def test_user_no_email(self):
        "Users can be created without an email"
        cases = [
            {},
            {"email": ""},
            {"email": None},
        ]
        for i, kwargs in enumerate(cases):
            with self.subTest(**kwargs):
                u = User.objects.create_user("testuser{}".format(i), **kwargs)
                self.assertEqual(u.email, "")

    def test_superuser(self):
        "Check the creation and properties of a superuser"
        super = User.objects.create_superuser("super", "super@example.com", "super")
        self.assertTrue(super.is_superuser)
        self.assertTrue(super.is_active)
        self.assertTrue(super.is_staff)

    async def test_asuperuser(self):
        "Check the creation and properties of a superuser"
        super = await User.objects.acreate_superuser(
            "super", "super@example.com", "super"
        )
        self.assertTrue(super.is_superuser)
        self.assertTrue(super.is_active)
        self.assertTrue(super.is_staff)

    def test_superuser_no_email_or_password(self):
        cases = [
            {},
            {"email": ""},
            {"email": None},
            {"password": None},
        ]
        for i, kwargs in enumerate(cases):
            with self.subTest(**kwargs):
                superuser = User.objects.create_superuser("super{}".format(i), **kwargs)
                self.assertEqual(superuser.email, "")
                self.assertFalse(superuser.has_usable_password())

    def test_get_user_model(self):
        "The current user model can be retrieved"
        self.assertEqual(get_user_model(), User)

    @override_settings(AUTH_USER_MODEL="auth_tests.CustomUser")
    def test_swappable_user(self):
        "The current user model can be swapped out for another"
        self.assertEqual(get_user_model(), CustomUser)
        with self.assertRaises(AttributeError):
            User.objects.all()

    @override_settings(AUTH_USER_MODEL="badsetting")
    def test_swappable_user_bad_setting(self):
        "The alternate user setting must point to something in the format app.model"
        msg = "AUTH_USER_MODEL must be of the form 'app_label.model_name'"
        with self.assertRaisesMessage(ImproperlyConfigured, msg):
            get_user_model()

    @override_settings(AUTH_USER_MODEL="thismodel.doesntexist")
    def test_swappable_user_nonexistent_model(self):
        "The current user model must point to an installed model"
        msg = (
            "AUTH_USER_MODEL refers to model 'thismodel.doesntexist' "
            "that has not been installed"
        )
        with self.assertRaisesMessage(ImproperlyConfigured, msg):
            get_user_model()

    def test_user_verbose_names_translatable(self):
        "Default User model verbose names are translatable (#19945)"
        with translation.override("en"):
            self.assertEqual(User._meta.verbose_name, "user")
            self.assertEqual(User._meta.verbose_name_plural, "users")
        with translation.override("es"):
            self.assertEqual(User._meta.verbose_name, "usuario")
            self.assertEqual(User._meta.verbose_name_plural, "usuarios")


class TestGetUser(TestCase):
    def test_get_user_anonymous(self):
        request = HttpRequest()
        request.session = self.client.session
        user = get_user(request)
        self.assertIsInstance(user, AnonymousUser)

    async def test_aget_user_anonymous(self):
        request = HttpRequest()
        request.session = await self.client.asession()
        user = await aget_user(request)
        self.assertIsInstance(user, AnonymousUser)

    def test_get_user(self):
        created_user = User.objects.create_user(
            "testuser", "test@example.com", "testpw"
        )
        self.client.login(username="testuser", password="testpw")
        request = HttpRequest()
        request.session = self.client.session
        user = get_user(request)
        self.assertIsInstance(user, User)
        self.assertEqual(user.username, created_user.username)

    def test_get_user_fallback_secret(self):
        created_user = User.objects.create_user(
            "testuser", "test@example.com", "testpw"
        )
        self.client.login(username="testuser", password="testpw")
        request = HttpRequest()
        request.session = self.client.session
        prev_session_key = request.session.session_key
        with override_settings(
            SECRET_KEY="newsecret",
            SECRET_KEY_FALLBACKS=[settings.SECRET_KEY],
        ):
            user = get_user(request)
            self.assertIsInstance(user, User)
            self.assertEqual(user.username, created_user.username)
            self.assertNotEqual(request.session.session_key, prev_session_key)
        # Remove the fallback secret.
        # The session hash should be updated using the current secret.
        with override_settings(SECRET_KEY="newsecret"):
            user = get_user(request)
            self.assertIsInstance(user, User)
            self.assertEqual(user.username, created_user.username)

    async def test_aget_user_fallback_secret(self):
        created_user = await User.objects.acreate_user(
            "testuser", "test@example.com", "testpw"
        )
        await self.client.alogin(username="testuser", password="testpw")
        request = HttpRequest()
        request.session = await self.client.asession()
        prev_session_key = request.session.session_key
        with override_settings(
            SECRET_KEY="newsecret",
            SECRET_KEY_FALLBACKS=[settings.SECRET_KEY],
        ):
            user = await aget_user(request)
            self.assertIsInstance(user, User)
            self.assertEqual(user.username, created_user.username)
            self.assertNotEqual(request.session.session_key, prev_session_key)
        # Remove the fallback secret.
        # The session hash should be updated using the current secret.
        with override_settings(SECRET_KEY="newsecret"):
            user = await aget_user(request)
            self.assertIsInstance(user, User)
            self.assertEqual(user.username, created_user.username)
