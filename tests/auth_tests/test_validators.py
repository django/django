import os
from unittest import mock

from django.contrib.auth import validators
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import (
    CommonPasswordValidator,
    MinimumLengthValidator,
    NumericPasswordValidator,
    UserAttributeSimilarityValidator,
    get_default_password_validators,
    get_password_validators,
    password_changed,
    password_validators_help_text_html,
    password_validators_help_texts,
    validate_password,
)
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.db import models
from django.test import SimpleTestCase, TestCase, override_settings
from django.test.utils import isolate_apps
from django.utils.html import conditional_escape


@override_settings(
    AUTH_PASSWORD_VALIDATORS=[
        {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
        {
            "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
            "OPTIONS": {
                "min_length": 12,
            },
        },
    ]
)
class PasswordValidationTest(SimpleTestCase):
    def test_get_default_password_validators(self):
        validators = get_default_password_validators()
        self.assertEqual(len(validators), 2)
        self.assertEqual(validators[0].__class__.__name__, "CommonPasswordValidator")
        self.assertEqual(validators[1].__class__.__name__, "MinimumLengthValidator")
        self.assertEqual(validators[1].min_length, 12)

    def test_get_password_validators_custom(self):
        validator_config = [
            {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"}
        ]
        validators = get_password_validators(validator_config)
        self.assertEqual(len(validators), 1)
        self.assertEqual(validators[0].__class__.__name__, "CommonPasswordValidator")

        self.assertEqual(get_password_validators([]), [])

    def test_get_password_validators_custom_invalid(self):
        validator_config = [{"NAME": "json.tool"}]
        msg = (
            "The module in NAME could not be imported: json.tool. "
            "Check your AUTH_PASSWORD_VALIDATORS setting."
        )
        with self.assertRaisesMessage(ImproperlyConfigured, msg):
            get_password_validators(validator_config)

    def test_validate_password(self):
        self.assertIsNone(validate_password("sufficiently-long"))
        msg_too_short = (
            "This password is too short. It must contain at least 12 characters."
        )

        with self.assertRaises(ValidationError) as cm:
            validate_password("django4242")
        self.assertEqual(cm.exception.messages, [msg_too_short])
        self.assertEqual(cm.exception.error_list[0].code, "password_too_short")

        with self.assertRaises(ValidationError) as cm:
            validate_password("password")
        self.assertEqual(
            cm.exception.messages, ["This password is too common.", msg_too_short]
        )
        self.assertEqual(cm.exception.error_list[0].code, "password_too_common")

        self.assertIsNone(validate_password("password", password_validators=[]))

    def test_password_changed(self):
        self.assertIsNone(password_changed("password"))

    def test_password_changed_with_custom_validator(self):
        class Validator:
            def password_changed(self, password, user):
                self.password = password
                self.user = user

        user = object()
        validator = Validator()
        password_changed("password", user=user, password_validators=(validator,))
        self.assertIs(validator.user, user)
        self.assertEqual(validator.password, "password")

    def test_password_validators_help_texts(self):
        help_texts = password_validators_help_texts()
        self.assertEqual(len(help_texts), 2)
        self.assertIn("12 characters", help_texts[1])

        self.assertEqual(password_validators_help_texts(password_validators=[]), [])

    def test_password_validators_help_text_html(self):
        help_text = password_validators_help_text_html()
        self.assertEqual(help_text.count("<li>"), 2)
        self.assertIn("12 characters", help_text)

    def test_password_validators_help_text_html_escaping(self):
        class AmpersandValidator:
            def get_help_text(self):
                return "Must contain &"

        help_text = password_validators_help_text_html([AmpersandValidator()])
        self.assertEqual(help_text, "<ul><li>Must contain &amp;</li></ul>")
        # help_text is marked safe and therefore unchanged by conditional_escape().
        self.assertEqual(help_text, conditional_escape(help_text))

    @override_settings(AUTH_PASSWORD_VALIDATORS=[])
    def test_empty_password_validator_help_text_html(self):
        self.assertEqual(password_validators_help_text_html(), "")


class MinimumLengthValidatorTest(SimpleTestCase):
    def test_validate(self):
        expected_error = (
            "This password is too short. It must contain at least %d characters."
        )
        self.assertIsNone(MinimumLengthValidator().validate("12345678"))
        self.assertIsNone(MinimumLengthValidator(min_length=3).validate("123"))

        with self.assertRaises(ValidationError) as cm:
            MinimumLengthValidator().validate("1234567")
        self.assertEqual(cm.exception.messages, [expected_error % 8])
        error = cm.exception.error_list[0]
        self.assertEqual(error.code, "password_too_short")
        self.assertEqual(error.params, {"min_length": 8})

        with self.assertRaises(ValidationError) as cm:
            MinimumLengthValidator(min_length=3).validate("12")
        self.assertEqual(cm.exception.messages, [expected_error % 3])
        error = cm.exception.error_list[0]
        self.assertEqual(error.code, "password_too_short")
        self.assertEqual(error.params, {"min_length": 3})

    def test_help_text(self):
        self.assertEqual(
            MinimumLengthValidator().get_help_text(),
            "Your password must contain at least 8 characters.",
        )

    @mock.patch("django.contrib.auth.password_validation.ngettext")
    def test_l10n(self, mock_ngettext):
        with self.subTest("get_error_message"):
            MinimumLengthValidator().get_error_message()
            mock_ngettext.assert_called_with(
                "This password is too short. It must contain at least %d character.",
                "This password is too short. It must contain at least %d characters.",
                8,
            )
        mock_ngettext.reset()
        with self.subTest("get_help_text"):
            MinimumLengthValidator().get_help_text()
            mock_ngettext.assert_called_with(
                "Your password must contain at least %(min_length)d " "character.",
                "Your password must contain at least %(min_length)d " "characters.",
                8,
            )

    def test_custom_error(self):
        class CustomMinimumLengthValidator(MinimumLengthValidator):
            def get_error_message(self):
                return "Your password must be %d characters long" % self.min_length

        expected_error = "Your password must be %d characters long"

        with self.assertRaisesMessage(ValidationError, expected_error % 8) as cm:
            CustomMinimumLengthValidator().validate("1234567")
        self.assertEqual(cm.exception.error_list[0].code, "password_too_short")

        with self.assertRaisesMessage(ValidationError, expected_error % 3) as cm:
            CustomMinimumLengthValidator(min_length=3).validate("12")


class UserAttributeSimilarityValidatorTest(TestCase):
    def test_validate(self):
        user = User.objects.create_user(
            username="testclient",
            password="password",
            email="testclient@example.com",
            first_name="Test",
            last_name="Client",
        )
        expected_error = "The password is too similar to the %s."

        self.assertIsNone(UserAttributeSimilarityValidator().validate("testclient"))

        with self.assertRaises(ValidationError) as cm:
            UserAttributeSimilarityValidator().validate("testclient", user=user)
        self.assertEqual(cm.exception.messages, [expected_error % "username"])
        self.assertEqual(cm.exception.error_list[0].code, "password_too_similar")

        with self.assertRaises(ValidationError) as cm:
            UserAttributeSimilarityValidator().validate("example.com", user=user)
        self.assertEqual(cm.exception.messages, [expected_error % "email address"])

        with self.assertRaises(ValidationError) as cm:
            UserAttributeSimilarityValidator(
                user_attributes=["first_name"],
                max_similarity=0.3,
            ).validate("testclient", user=user)
        self.assertEqual(cm.exception.messages, [expected_error % "first name"])
        # max_similarity=1 doesn't allow passwords that are identical to the
        # attribute's value.
        with self.assertRaises(ValidationError) as cm:
            UserAttributeSimilarityValidator(
                user_attributes=["first_name"],
                max_similarity=1,
            ).validate(user.first_name, user=user)
        self.assertEqual(cm.exception.messages, [expected_error % "first name"])
        # Very low max_similarity is rejected.
        msg = "max_similarity must be at least 0.1"
        with self.assertRaisesMessage(ValueError, msg):
            UserAttributeSimilarityValidator(max_similarity=0.09)
        # Passes validation.
        self.assertIsNone(
            UserAttributeSimilarityValidator(user_attributes=["first_name"]).validate(
                "testclient", user=user
            )
        )

    @isolate_apps("auth_tests")
    def test_validate_property(self):
        class TestUser(models.Model):
            pass

            @property
            def username(self):
                return "foobar"

        with self.assertRaises(ValidationError) as cm:
            UserAttributeSimilarityValidator().validate("foobar", user=TestUser())
        self.assertEqual(
            cm.exception.messages, ["The password is too similar to the username."]
        )

    def test_help_text(self):
        self.assertEqual(
            UserAttributeSimilarityValidator().get_help_text(),
            "Your password can’t be too similar to your other personal information.",
        )

    def test_custom_error(self):
        class CustomUserAttributeSimilarityValidator(UserAttributeSimilarityValidator):
            def get_error_message(self):
                return "The password is too close to the %(verbose_name)s."

        user = User.objects.create_user(
            username="testclient",
            password="password",
            email="testclient@example.com",
            first_name="Test",
            last_name="Client",
        )

        expected_error = "The password is too close to the %s."

        with self.assertRaisesMessage(ValidationError, expected_error % "username"):
            CustomUserAttributeSimilarityValidator().validate("testclient", user=user)

    def test_custom_error_verbose_name_not_used(self):
        class CustomUserAttributeSimilarityValidator(UserAttributeSimilarityValidator):
            def get_error_message(self):
                return "The password is too close to a user attribute."

        user = User.objects.create_user(
            username="testclient",
            password="password",
            email="testclient@example.com",
            first_name="Test",
            last_name="Client",
        )

        expected_error = "The password is too close to a user attribute."

        with self.assertRaisesMessage(ValidationError, expected_error):
            CustomUserAttributeSimilarityValidator().validate("testclient", user=user)


class CommonPasswordValidatorTest(SimpleTestCase):
    def test_validate(self):
        expected_error = "This password is too common."
        self.assertIsNone(CommonPasswordValidator().validate("a-safe-password"))

        with self.assertRaises(ValidationError) as cm:
            CommonPasswordValidator().validate("godzilla")
        self.assertEqual(cm.exception.messages, [expected_error])

    def test_common_hexed_codes(self):
        expected_error = "This password is too common."
        common_hexed_passwords = ["asdfjkl:", "&#2336:"]
        for password in common_hexed_passwords:
            with self.subTest(password=password):
                with self.assertRaises(ValidationError) as cm:
                    CommonPasswordValidator().validate(password)
                self.assertEqual(cm.exception.messages, [expected_error])

    def test_validate_custom_list(self):
        path = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "common-passwords-custom.txt"
        )
        validator = CommonPasswordValidator(password_list_path=path)
        expected_error = "This password is too common."
        self.assertIsNone(validator.validate("a-safe-password"))

        with self.assertRaises(ValidationError) as cm:
            validator.validate("from-my-custom-list")
        self.assertEqual(cm.exception.messages, [expected_error])
        self.assertEqual(cm.exception.error_list[0].code, "password_too_common")

    def test_validate_django_supplied_file(self):
        validator = CommonPasswordValidator()
        for password in validator.passwords:
            self.assertEqual(password, password.lower())

    def test_help_text(self):
        self.assertEqual(
            CommonPasswordValidator().get_help_text(),
            "Your password can’t be a commonly used password.",
        )

    def test_custom_error(self):
        class CustomCommonPasswordValidator(CommonPasswordValidator):
            def get_error_message(self):
                return "This password has been used too much."

        expected_error = "This password has been used too much."

        with self.assertRaisesMessage(ValidationError, expected_error):
            CustomCommonPasswordValidator().validate("godzilla")


class NumericPasswordValidatorTest(SimpleTestCase):
    def test_validate(self):
        expected_error = "This password is entirely numeric."
        self.assertIsNone(NumericPasswordValidator().validate("a-safe-password"))

        with self.assertRaises(ValidationError) as cm:
            NumericPasswordValidator().validate("42424242")
        self.assertEqual(cm.exception.messages, [expected_error])
        self.assertEqual(cm.exception.error_list[0].code, "password_entirely_numeric")

    def test_help_text(self):
        self.assertEqual(
            NumericPasswordValidator().get_help_text(),
            "Your password can’t be entirely numeric.",
        )

    def test_custom_error(self):
        class CustomNumericPasswordValidator(NumericPasswordValidator):
            def get_error_message(self):
                return "This password is all digits."

        expected_error = "This password is all digits."

        with self.assertRaisesMessage(ValidationError, expected_error):
            CustomNumericPasswordValidator().validate("42424242")


class UsernameValidatorsTests(SimpleTestCase):
    def test_unicode_validator(self):
        valid_usernames = ["joe", "René", "ᴮᴵᴳᴮᴵᴿᴰ", "أحمد"]
        invalid_usernames = [
            "o'connell",
            "عبد ال",
            "zerowidth\u200bspace",
            "nonbreaking\u00a0space",
            "en\u2013dash",
            "trailingnewline\u000a",
        ]
        v = validators.UnicodeUsernameValidator()
        for valid in valid_usernames:
            with self.subTest(valid=valid):
                v(valid)
        for invalid in invalid_usernames:
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValidationError):
                    v(invalid)

    def test_ascii_validator(self):
        valid_usernames = ["glenn", "GLEnN", "jean-marc"]
        invalid_usernames = [
            "o'connell",
            "Éric",
            "jean marc",
            "أحمد",
            "trailingnewline\n",
        ]
        v = validators.ASCIIUsernameValidator()
        for valid in valid_usernames:
            with self.subTest(valid=valid):
                v(valid)
        for invalid in invalid_usernames:
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValidationError):
                    v(invalid)
