from django.contrib.auth.middleware import AuthenticationMiddleware
from django.contrib.auth.models import User
from django.http import HttpRequest
from django.test import TestCase


class TestSessionAuthenticationMiddleware(TestCase):
    def setUp(self):
        self.user_password = 'test_password'
        self.user = User.objects.create_user('test_user',
                                             'test@example.com',
                                             self.user_password)

        self.middleware = AuthenticationMiddleware()
        self.assertTrue(self.client.login(
            username=self.user.username,
            password=self.user_password,
        ))
        self.request = HttpRequest()
        self.request.session = self.client.session

    def test_changed_password_doesnt_invalidate_session(self):
        """
        Changing a user's password shouldn't invalidate the session if session
        verification isn't activated.
        """
        session_key = self.request.session.session_key
        self.middleware.process_request(self.request)
        self.assertIsNotNone(self.request.user)
        self.assertFalse(self.request.user.is_anonymous())

        # After password change, user should remain logged in.
        self.user.set_password('new_password')
        self.user.save()
        self.middleware.process_request(self.request)
        self.assertIsNotNone(self.request.user)
        self.assertFalse(self.request.user.is_anonymous())
        self.assertEqual(session_key, self.request.session.session_key)

    def test_changed_password_invalidates_session_with_middleware(self):
        session_key = self.request.session.session_key
        with self.modify_settings(MIDDLEWARE_CLASSES={'append': ['django.contrib.auth.middleware.SessionAuthenticationMiddleware']}):
            # After password change, user should be anonymous
            self.user.set_password('new_password')
            self.user.save()
            self.middleware.process_request(self.request)
            self.assertIsNotNone(self.request.user)
            self.assertTrue(self.request.user.is_anonymous())
        # session should be flushed
        self.assertNotEqual(session_key, self.request.session.session_key)
