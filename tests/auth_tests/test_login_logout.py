from django.contrib import auth
from django.contrib.auth.models import AnonymousUser, User
from django.http import HttpRequest
from django.test import TestCase
from django.utils.deprecation import RemovedInDjango60Warning


class TestLogin(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="testuser", password="password")

    def setUp(self):
        self.request = HttpRequest()
        self.request.session = self.client.session

    def test_success(self):
        """
        Logs in the user and sets the user in the request's session.
        """
        auth.login(self.request, self.user)

        self.assertEqual(self.request.session[auth.SESSION_KEY], str(self.user.pk))

    def test_inactive_user(self):
        """
        Does not verify that the user is allowed to log in.
        """
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])

        auth.login(self.request, self.user)

        self.assertEqual(self.request.session[auth.SESSION_KEY], str(self.user.pk))

    def test_without_user_no_request_user(self):
        with self.assertRaisesMessage(
            AttributeError,
            "'HttpRequest' object has no attribute 'user'",
        ):
            auth.login(self.request, None)

    def test_without_user_anonymous_request(self):
        self.request.user = AnonymousUser()
        with self.assertRaisesMessage(
            AttributeError,
            "'AnonymousUser' object has no attribute '_meta'",
        ):
            auth.login(self.request, None)

    def test_without_user_authenticated_request(self):
        self.request.user = self.user

        self.assertNotIn(auth.SESSION_KEY, self.request.session)

        msg = "Fallback to request.user when user is None will be removed."
        with self.assertWarnsMessage(RemovedInDjango60Warning, msg):
            auth.login(self.request, None)

        self.assertEqual(self.request.session[auth.SESSION_KEY], str(self.user.pk))


class TestLogout(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="testuser", password="password")

    def setUp(self):
        self.request = HttpRequest()
        self.request.session = self.client.session
        self.request.user = AnonymousUser()

    def test_logout_without_login(self):
        """
        Resets the session regardless of whether a user is logged in.
        """
        self.request.session["test"] = "test"
        session_key = self.request.session.session_key

        auth.logout(self.request)

        self.assertNotEqual(session_key, self.request.session.session_key)
        self.assertNotIn("test", self.request.session)

    def test_logout_after_login(self):
        """
        Logs out the user and removes the user from the request's session.
        """
        # Log in the user.
        auth.login(self.request, self.user)
        session_key = self.request.session.session_key
        self.assertEqual(self.request.session[auth.SESSION_KEY], str(self.user.pk))

        # Log out the user.
        auth.logout(self.request)

        self.assertNotEqual(session_key, self.request.session.session_key)
        self.assertNotIn(auth.SESSION_KEY, self.request.session)
