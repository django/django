# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os

from django.contrib.auth import validators
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import (
    CommonPasswordValidator, MinimumLengthValidator, NumericPasswordValidator,
    UserAttributeSimilarityValidator, get_default_password_validators,
    get_password_validators, password_changed,
    password_validators_help_text_html, password_validators_help_texts,
    validate_password,
)
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.utils._os import upath


@override_settings(AUTH_PASSWORD_VALIDATORS=[
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {
        'min_length': 12,
    }},
])
class PasswordValidationTest(TestCase):
    def test_get_default_password_validators(self):
        validators = get_default_password_validators()
        self.assertEqual(len(validators), 2)
        self.assertEqual(validators[0].__class__.__name__, 'CommonPasswordValidator')
        self.assertEqual(validators[1].__class__.__name__, 'MinimumLengthValidator')
        self.assertEqual(validators[1].min_length, 12)

    def test_get_password_validators_custom(self):
        validator_config = [{'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'}]
        validators = get_password_validators(validator_config)
        self.assertEqual(len(validators), 1)
        self.assertEqual(validators[0].__class__.__name__, 'CommonPasswordValidator')

        self.assertEqual(get_password_validators([]), [])

    def test_validate_password(self):
        self.assertIsNone(validate_password('sufficiently-long'))
        msg_too_short = 'This password is too short. It must contain at least 12 characters.'

        with self.assertRaises(ValidationError) as cm:
            validate_password('django4242')
        self.assertEqual(cm.exception.messages, [msg_too_short])
        self.assertEqual(cm.exception.error_list[0].code, 'password_too_short')

        with self.assertRaises(ValidationError) as cm:
            validate_password('password')
        self.assertEqual(cm.exception.messages, ['This password is too common.', msg_too_short])
        self.assertEqual(cm.exception.error_list[0].code, 'password_too_common')

        self.assertIsNone(validate_password('password', password_validators=[]))

    def test_password_changed(self):
        self.assertIsNone(password_changed('password'))

    def test_password_validators_help_texts(self):
        help_texts = password_validators_help_texts()
        self.assertEqual(len(help_texts), 2)
        self.assertIn('12 characters', help_texts[1])

        self.assertEqual(password_validators_help_texts(password_validators=[]), [])

    def test_password_validators_help_text_html(self):
        help_text = password_validators_help_text_html()
        self.assertEqual(help_text.count('<li>'), 2)
        self.assertIn('12 characters', help_text)

    @override_settings(AUTH_PASSWORD_VALIDATORS=[])
    def test_empty_password_validator_help_text_html(self):
        self.assertEqual(password_validators_help_text_html(), '')


class MinimumLengthValidatorTest(TestCase):
    def test_validate(self):
        expected_error = "This password is too short. It must contain at least %d characters."
        self.assertIsNone(MinimumLengthValidator().validate('12345678'))
        self.assertIsNone(MinimumLengthValidator(min_length=3).validate('123'))

        with self.assertRaises(ValidationError) as cm:
            MinimumLengthValidator().validate('1234567')
        self.assertEqual(cm.exception.messages, [expected_error % 8])
        self.assertEqual(cm.exception.error_list[0].code, 'password_too_short')

        with self.assertRaises(ValidationError) as cm:
            MinimumLengthValidator(min_length=3).validate('12')
        self.assertEqual(cm.exception.messages, [expected_error % 3])

    def test_help_text(self):
        self.assertEqual(
            MinimumLengthValidator().get_help_text(),
            "Your password must contain at least 8 characters."
        )


class UserAttributeSimilarityValidatorTest(TestCase):
    def test_validate(self):
        user = User.objects.create_user(
            username='testclient', password='password', email='testclient@example.com',
            first_name='Test', last_name='Client',
        )
        expected_error = "The password is too similar to the %s."

        self.assertIsNone(UserAttributeSimilarityValidator().validate('testclient'))

        with self.assertRaises(ValidationError) as cm:
            UserAttributeSimilarityValidator().validate('testclient', user=user),
        self.assertEqual(cm.exception.messages, [expected_error % "username"])
        self.assertEqual(cm.exception.error_list[0].code, 'password_too_similar')

        with self.assertRaises(ValidationError) as cm:
            UserAttributeSimilarityValidator().validate('example.com', user=user),
        self.assertEqual(cm.exception.messages, [expected_error % "email address"])

        with self.assertRaises(ValidationError) as cm:
            UserAttributeSimilarityValidator(
                user_attributes=['first_name'],
                max_similarity=0.3,
            ).validate('testclient', user=user)
        self.assertEqual(cm.exception.messages, [expected_error % "first name"])

        self.assertIsNone(
            UserAttributeSimilarityValidator(user_attributes=['first_name']).validate('testclient', user=user)
        )

    def test_help_text(self):
        self.assertEqual(
            UserAttributeSimilarityValidator().get_help_text(),
            "Your password can't be too similar to your other personal information."
        )


class CommonPasswordValidatorTest(TestCase):
    def test_validate(self):
        expected_error = "This password is too common."
        self.assertIsNone(CommonPasswordValidator().validate('a-safe-password'))

        with self.assertRaises(ValidationError) as cm:
            CommonPasswordValidator().validate('godzilla')
        self.assertEqual(cm.exception.messages, [expected_error])

    def test_validate_custom_list(self):
        path = os.path.join(os.path.dirname(os.path.realpath(upath(__file__))), 'common-passwords-custom.txt')
        validator = CommonPasswordValidator(password_list_path=path)
        expected_error = "This password is too common."
        self.assertIsNone(validator.validate('a-safe-password'))

        with self.assertRaises(ValidationError) as cm:
            validator.validate('from-my-custom-list')
        self.assertEqual(cm.exception.messages, [expected_error])
        self.assertEqual(cm.exception.error_list[0].code, 'password_too_common')

    def test_help_text(self):
        self.assertEqual(
            CommonPasswordValidator().get_help_text(),
            "Your password can't be a commonly used password."
        )


class NumericPasswordValidatorTest(TestCase):
    def test_validate(self):
        expected_error = "This password is entirely numeric."
        self.assertIsNone(NumericPasswordValidator().validate('a-safe-password'))

        with self.assertRaises(ValidationError) as cm:
            NumericPasswordValidator().validate('42424242')
        self.assertEqual(cm.exception.messages, [expected_error])
        self.assertEqual(cm.exception.error_list[0].code, 'password_entirely_numeric')

    def test_help_text(self):
        self.assertEqual(
            NumericPasswordValidator().get_help_text(),
            "Your password can't be entirely numeric."
        )


class UsernameValidatorsTests(TestCase):
    def test_unicode_validator(self):
        valid_usernames = ['joe', 'René', 'ᴮᴵᴳᴮᴵᴿᴰ', 'أحمد']
        invalid_usernames = [
            "o'connell", "عبد ال",
            "zerowidth\u200Bspace", "nonbreaking\u00A0space",
            "en\u2013dash",
        ]
        v = validators.UnicodeUsernameValidator()
        for valid in valid_usernames:
            v(valid)
        for invalid in invalid_usernames:
            with self.assertRaises(ValidationError):
                v(invalid)

    def test_ascii_validator(self):
        valid_usernames = ['glenn', 'GLEnN', 'jean-marc']
        invalid_usernames = ["o'connell", 'Éric', 'jean marc', "أحمد"]
        v = validators.ASCIIUsernameValidator()
        for valid in valid_usernames:
            v(valid)
        for invalid in invalid_usernames:
            with self.assertRaises(ValidationError):
                v(invalid)
