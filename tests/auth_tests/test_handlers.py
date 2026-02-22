from unittest import mock

from django.contrib.auth.handlers.modwsgi import check_password, groups_for_user
from django.contrib.auth.hashers import get_hasher
from django.contrib.auth.models import Group, User
from django.test import TransactionTestCase, override_settings

from .models import CustomUser


# This must be a TransactionTestCase because the WSGI auth handler performs
# its own transaction management.
class ModWsgiHandlerTestCase(TransactionTestCase):
    """
    Tests for the mod_wsgi authentication handler
    """

    available_apps = [
        "django.contrib.auth",
        "django.contrib.contenttypes",
        "auth_tests",
    ]

    def test_check_password(self):
        """
        check_password() returns the correct values as per
        https://modwsgi.readthedocs.io/en/develop/user-guides/access-control-mechanisms.html#apache-authentication-provider
        """
        User.objects.create_user("test", "test@example.com", "test")

        # User not in database
        self.assertIsNone(check_password({}, "unknown", ""))

        # Valid user with correct password
        self.assertIs(check_password({}, "test", "test"), True)

        # Valid user with incorrect password
        self.assertIs(check_password({}, "test", "incorrect"), False)

        # correct password, but user is inactive
        User.objects.filter(username="test").update(is_active=False)
        self.assertIsNone(check_password({}, "test", "test"))

    @override_settings(AUTH_USER_MODEL="auth_tests.CustomUser")
    def test_check_password_custom_user(self):
        """
        check_password() returns the correct values as per
        https://modwsgi.readthedocs.io/en/develop/user-guides/access-control-mechanisms.html#apache-authentication-provider
        with a custom user installed.
        """
        CustomUser._default_manager.create_user(
            "test@example.com", "1990-01-01", "test"
        )

        # User not in database
        self.assertIsNone(check_password({}, "unknown", ""))

        # Valid user with correct password'
        self.assertIs(check_password({}, "test@example.com", "test"), True)

        # Valid user with incorrect password
        self.assertIs(check_password({}, "test@example.com", "incorrect"), False)

    def test_groups_for_user(self):
        """
        groups_for_user() returns correct values as per
        https://modwsgi.readthedocs.io/en/develop/user-guides/access-control-mechanisms.html#apache-group-authorisation
        """
        user1 = User.objects.create_user("test", "test@example.com", "test")
        User.objects.create_user("test1", "test1@example.com", "test1")
        group = Group.objects.create(name="test_group")
        user1.groups.add(group)

        # User not in database
        self.assertEqual(groups_for_user({}, "unknown"), [])

        self.assertEqual(groups_for_user({}, "test"), [b"test_group"])
        self.assertEqual(groups_for_user({}, "test1"), [])

    def test_check_password_fake_runtime(self):
        """
        Hasher is run once regardless of whether the user exists. Refs #20760.
        """
        User.objects.create_user("test", "test@example.com", "test")
        User.objects.create_user("inactive", "test@nono.com", "test", is_active=False)
        User.objects.create_user("unusable", "test@nono.com")

        hasher = get_hasher()

        for username, password in [
            ("test", "test"),
            ("test", "wrong"),
            ("inactive", "test"),
            ("inactive", "wrong"),
            ("unusable", "test"),
            ("doesnotexist", "test"),
        ]:
            with (
                self.subTest(username=username, password=password),
                mock.patch.object(hasher, "encode") as mock_make_password,
            ):
                check_password({}, username, password)
                mock_make_password.assert_called_once()
