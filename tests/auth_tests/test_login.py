from django.contrib import auth
from django.contrib.auth.models import AnonymousUser, User
from django.http import HttpRequest
from django.test import TestCase
from django.utils.deprecation import RemovedInDjango61Warning


class TestLogin(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="testuser", password="password")

    def setUp(self):
        self.request = HttpRequest()
        self.request.session = self.client.session

    def test_user_login(self):
        auth.login(self.request, self.user)
        self.assertEqual(self.request.session[auth.SESSION_KEY], str(self.user.pk))

    def test_inactive_user(self):
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])

        auth.login(self.request, self.user)
        self.assertEqual(self.request.session[auth.SESSION_KEY], str(self.user.pk))

    # RemovedInDjango61Warning: When the deprecation ends, replace with:
    # def test_without_user(self):
    def test_without_user_no_request_user(self):
        # RemovedInDjango61Warning: When the deprecation ends, replace with:
        # with self.assertRaisesMessage(
        #     AttributeError,
        #     "'NoneType' object has no attribute 'get_session_auth_hash'",
        # ):
        #     auth.login(self.request, None)
        with (
            self.assertRaisesMessage(
                AttributeError,
                "'HttpRequest' object has no attribute 'user'",
            ),
            self.assertWarnsMessage(
                RemovedInDjango61Warning,
                "Fallback to request.user when user is None will be removed.",
            ),
        ):
            auth.login(self.request, None)

    # RemovedInDjango61Warning: When the deprecation ends, remove completely.
    def test_without_user_anonymous_request(self):
        self.request.user = AnonymousUser()
        with (
            self.assertRaisesMessage(
                AttributeError,
                "'AnonymousUser' object has no attribute '_meta'",
            ),
            self.assertWarnsMessage(
                RemovedInDjango61Warning,
                "Fallback to request.user when user is None will be removed.",
            ),
        ):
            auth.login(self.request, None)

    # RemovedInDjango61Warning: When the deprecation ends, remove completely.
    def test_without_user_authenticated_request(self):
        self.request.user = self.user
        self.assertNotIn(auth.SESSION_KEY, self.request.session)

        msg = "Fallback to request.user when user is None will be removed."
        with self.assertWarnsMessage(RemovedInDjango61Warning, msg):
            auth.login(self.request, None)
        self.assertEqual(self.request.session[auth.SESSION_KEY], str(self.user.pk))
