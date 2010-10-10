from datetime import date, timedelta

from django.conf import settings
from django.contrib.auth.models import User, AnonymousUser
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.test import TestCase


class TokenGeneratorTest(TestCase):

    def test_make_token(self):
        """
        Ensure that we can make a token and that it is valid
        """
        user = User.objects.create_user('tokentestuser', 'test2@example.com', 'testpw')
        p0 = PasswordResetTokenGenerator()
        tk1 = p0.make_token(user)
        self.assertTrue(p0.check_token(user, tk1))

    def test_10265(self):
        """
        Ensure that the token generated for a user created in the same request
        will work correctly.
        """
        # See ticket #10265
        user = User.objects.create_user('comebackkid', 'test3@example.com', 'testpw')
        p0 = PasswordResetTokenGenerator()
        tk1 = p0.make_token(user)
        reload = User.objects.get(username='comebackkid')
        tk2 = p0.make_token(reload)
        self.assertEqual(tk1, tk2)

    def test_timeout(self):
        """
        Ensure we can use the token after n days, but no greater.
        """
        # Uses a mocked version of PasswordResetTokenGenerator so we can change
        # the value of 'today'
        class Mocked(PasswordResetTokenGenerator):
            def __init__(self, today):
                self._today_val = today
            def _today(self):
                return self._today_val

        user = User.objects.create_user('tokentestuser', 'test2@example.com', 'testpw')
        p0 = PasswordResetTokenGenerator()
        tk1 = p0.make_token(user)
        p1 = Mocked(date.today() + timedelta(settings.PASSWORD_RESET_TIMEOUT_DAYS))
        self.assertTrue(p1.check_token(user, tk1))

        p2 = Mocked(date.today() + timedelta(settings.PASSWORD_RESET_TIMEOUT_DAYS + 1))
        self.assertFalse(p2.check_token(user, tk1))
