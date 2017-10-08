from datetime import date, timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.test import TestCase


class TokenGeneratorTest(TestCase):

    def test_make_token(self):
        user = User.objects.create_user('tokentestuser', 'test2@example.com', 'testpw')
        p0 = PasswordResetTokenGenerator()
        tk1 = p0.make_token(user)
        self.assertTrue(p0.check_token(user, tk1))

    def test_10265(self):
        """
        The token generated for a user created in the same request
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
        The token is valid after n days, but no greater.
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

    def test_check_token_with_nonexistent_token_and_user(self):
        user = User.objects.create_user('tokentestuser', 'test2@example.com', 'testpw')
        p0 = PasswordResetTokenGenerator()
        tk1 = p0.make_token(user)
        self.assertIs(p0.check_token(None, tk1), False)
        self.assertIs(p0.check_token(user, None), False)

    def test_token_with_different_secret(self):
        """
        A valid token can be created with a secret other than SECRET_KEY by
        using the PasswordResetTokenGenerator.secret attribute.
        """
        user = User.objects.create_user('tokentestuser', 'test2@example.com', 'testpw')
        new_secret = 'abcdefghijkl'
        # Create and check a token with a different secret.
        p0 = PasswordResetTokenGenerator()
        p0.secret = new_secret
        tk0 = p0.make_token(user)
        self.assertTrue(p0.check_token(user, tk0))
        # Create and check a token with the default secret.
        p1 = PasswordResetTokenGenerator()
        self.assertEqual(p1.secret, settings.SECRET_KEY)
        self.assertNotEqual(p1.secret, new_secret)
        tk1 = p1.make_token(user)
        # Tokens created with a different secret don't validate.
        self.assertFalse(p0.check_token(user, tk1))
        self.assertFalse(p1.check_token(user, tk0))
