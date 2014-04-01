from django.contrib.auth.middleware import SessionAuthenticationMiddleware
from django.contrib.auth.models import User
from django.http import HttpRequest
from django.test import TestCase


class TestSessionAuthenticationMiddleware(TestCase):
    def setUp(self):
        self.user_password = 'test_password'
        self.user = User.objects.create_user('test_user',
                                             'test@example.com',
                                             self.user_password)

    def test_changed_password_invalidates_session(self):
        """
        Tests that changing a user's password invalidates the session.
        """
        verification_middleware = SessionAuthenticationMiddleware()
        self.assertTrue(self.client.login(
            username=self.user.username,
            password=self.user_password,
        ))
        request = HttpRequest()
        request.session = self.client.session
        request.user = self.user
        verification_middleware.process_request(request)
        self.assertIsNotNone(request.user)
        self.assertFalse(request.user.is_anonymous())

        # After password change, user should be anonymous
        request.user.set_password('new_password')
        request.user.save()
        verification_middleware.process_request(request)
        self.assertIsNotNone(request.user)
        self.assertTrue(request.user.is_anonymous())
