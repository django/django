from datetime import datetime, timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase
from django.test.utils import override_settings

from .models import CustomEmailField


class MockedPasswordResetTokenGenerator(PasswordResetTokenGenerator):
    def __init__(self, now):
        self._now_val = now
        super().__init__()

    def _now(self):
        return self._now_val


class TokenGeneratorTest(TestCase):
    def test_make_token(self):
        user = User.objects.create_user("tokentestuser", "test2@example.com", "testpw")
        p0 = PasswordResetTokenGenerator()
        tk1 = p0.make_token(user)
        self.assertIs(p0.check_token(user, tk1), True)

    def test_10265(self):
        """
        The token generated for a user created in the same request
        will work correctly.
        """
        user = User.objects.create_user("comebackkid", "test3@example.com", "testpw")
        user_reload = User.objects.get(username="comebackkid")
        p0 = MockedPasswordResetTokenGenerator(datetime.now())
        tk1 = p0.make_token(user)
        tk2 = p0.make_token(user_reload)
        self.assertEqual(tk1, tk2)

    def test_token_with_different_email(self):
        """Updating the user email address invalidates the token."""
        tests = [
            (CustomEmailField, None),
            (CustomEmailField, "test4@example.com"),
            (User, "test4@example.com"),
        ]
        for model, email in tests:
            with self.subTest(model=model.__qualname__, email=email):
                user = model.objects.create_user(
                    "changeemailuser",
                    email=email,
                    password="testpw",
                )
                p0 = PasswordResetTokenGenerator()
                tk1 = p0.make_token(user)
                self.assertIs(p0.check_token(user, tk1), True)
                setattr(user, user.get_email_field_name(), "test4new@example.com")
                user.save()
                self.assertIs(p0.check_token(user, tk1), False)

    def test_timeout(self):
        """The token is valid after n seconds, but no greater."""
        # Uses a mocked version of PasswordResetTokenGenerator so we can change
        # the value of 'now'.
        user = User.objects.create_user("tokentestuser", "test2@example.com", "testpw")
        now = datetime.now()
        p0 = MockedPasswordResetTokenGenerator(now)
        tk1 = p0.make_token(user)
        p1 = MockedPasswordResetTokenGenerator(
            now + timedelta(seconds=settings.PASSWORD_RESET_TIMEOUT)
        )
        self.assertIs(p1.check_token(user, tk1), True)
        p2 = MockedPasswordResetTokenGenerator(
            now + timedelta(seconds=(settings.PASSWORD_RESET_TIMEOUT + 1))
        )
        self.assertIs(p2.check_token(user, tk1), False)
        with self.settings(PASSWORD_RESET_TIMEOUT=60 * 60):
            p3 = MockedPasswordResetTokenGenerator(
                now + timedelta(seconds=settings.PASSWORD_RESET_TIMEOUT)
            )
            self.assertIs(p3.check_token(user, tk1), True)
            p4 = MockedPasswordResetTokenGenerator(
                now + timedelta(seconds=(settings.PASSWORD_RESET_TIMEOUT + 1))
            )
            self.assertIs(p4.check_token(user, tk1), False)

    def test_check_token_with_nonexistent_token_and_user(self):
        user = User.objects.create_user("tokentestuser", "test2@example.com", "testpw")
        p0 = PasswordResetTokenGenerator()
        tk1 = p0.make_token(user)
        self.assertIs(p0.check_token(None, tk1), False)
        self.assertIs(p0.check_token(user, None), False)

    def test_token_with_different_secret(self):
        """
        A valid token can be created with a secret other than SECRET_KEY by
        using the PasswordResetTokenGenerator.secret attribute.
        """
        user = User.objects.create_user("tokentestuser", "test2@example.com", "testpw")
        new_secret = "abcdefghijkl"
        # Create and check a token with a different secret.
        p0 = PasswordResetTokenGenerator()
        p0.secret = new_secret
        tk0 = p0.make_token(user)
        self.assertIs(p0.check_token(user, tk0), True)
        # Create and check a token with the default secret.
        p1 = PasswordResetTokenGenerator()
        self.assertEqual(p1.secret, settings.SECRET_KEY)
        self.assertNotEqual(p1.secret, new_secret)
        tk1 = p1.make_token(user)
        # Tokens created with a different secret don't validate.
        self.assertIs(p0.check_token(user, tk1), False)
        self.assertIs(p1.check_token(user, tk0), False)

    def test_token_with_different_secret_subclass(self):
        class CustomPasswordResetTokenGenerator(PasswordResetTokenGenerator):
            secret = "test-secret"

        user = User.objects.create_user("tokentestuser", "test2@example.com", "testpw")
        custom_password_generator = CustomPasswordResetTokenGenerator()
        tk_custom = custom_password_generator.make_token(user)
        self.assertIs(custom_password_generator.check_token(user, tk_custom), True)

        default_password_generator = PasswordResetTokenGenerator()
        self.assertNotEqual(
            custom_password_generator.secret,
            default_password_generator.secret,
        )
        self.assertEqual(default_password_generator.secret, settings.SECRET_KEY)
        # Tokens created with a different secret don't validate.
        tk_default = default_password_generator.make_token(user)
        self.assertIs(custom_password_generator.check_token(user, tk_default), False)
        self.assertIs(default_password_generator.check_token(user, tk_custom), False)

    @override_settings(SECRET_KEY="")
    def test_secret_lazy_validation(self):
        default_token_generator = PasswordResetTokenGenerator()
        msg = "The SECRET_KEY setting must not be empty."
        with self.assertRaisesMessage(ImproperlyConfigured, msg):
            default_token_generator.secret

    def test_check_token_secret_fallbacks(self):
        user = User.objects.create_user("tokentestuser", "test2@example.com", "testpw")
        p1 = PasswordResetTokenGenerator()
        p1.secret = "secret"
        tk = p1.make_token(user)
        p2 = PasswordResetTokenGenerator()
        p2.secret = "newsecret"
        p2.secret_fallbacks = ["secret"]
        self.assertIs(p1.check_token(user, tk), True)
        self.assertIs(p2.check_token(user, tk), True)

    @override_settings(
        SECRET_KEY="secret",
        SECRET_KEY_FALLBACKS=["oldsecret"],
    )
    def test_check_token_secret_key_fallbacks(self):
        user = User.objects.create_user("tokentestuser", "test2@example.com", "testpw")
        p1 = PasswordResetTokenGenerator()
        p1.secret = "oldsecret"
        tk = p1.make_token(user)
        p2 = PasswordResetTokenGenerator()
        self.assertIs(p2.check_token(user, tk), True)

    @override_settings(
        SECRET_KEY="secret",
        SECRET_KEY_FALLBACKS=["oldsecret"],
    )
    def test_check_token_secret_key_fallbacks_override(self):
        user = User.objects.create_user("tokentestuser", "test2@example.com", "testpw")
        p1 = PasswordResetTokenGenerator()
        p1.secret = "oldsecret"
        tk = p1.make_token(user)
        p2 = PasswordResetTokenGenerator()
        p2.secret_fallbacks = []
        self.assertIs(p2.check_token(user, tk), False)
