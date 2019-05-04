import os

from django.contrib.auth import validators
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import (
    CommonPasswordValidator, MinimumLengthValidator,
    NoAmbiguousCharactersValidator, NoRepeatSubstringsValidator,
    NoSequentialCharsValidator, NumericPasswordValidator,
    ShannonEntropyValidator, UserAttributeSimilarityValidator,
    get_default_password_validators, get_password_validators, password_changed,
    password_validators_help_text_html, password_validators_help_texts,
    validate_password,
)
from django.core.exceptions import ValidationError
from django.db import models
from django.test import SimpleTestCase, TestCase, override_settings
from django.test.utils import isolate_apps
from django.utils.html import conditional_escape


@override_settings(AUTH_PASSWORD_VALIDATORS=[
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {
        'min_length': 12,
    }},
])
class PasswordValidationTest(SimpleTestCase):
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

    def test_password_changed_with_custom_validator(self):
        class Validator:
            def password_changed(self, password, user):
                self.password = password
                self.user = user

        user = object()
        validator = Validator()
        password_changed('password', user=user, password_validators=(validator,))
        self.assertIs(validator.user, user)
        self.assertEqual(validator.password, 'password')

    def test_password_validators_help_texts(self):
        help_texts = password_validators_help_texts()
        self.assertEqual(len(help_texts), 2)
        self.assertIn('12 characters', help_texts[1])

        self.assertEqual(password_validators_help_texts(password_validators=[]), [])

    def test_password_validators_help_text_html(self):
        help_text = password_validators_help_text_html()
        self.assertEqual(help_text.count('<li>'), 2)
        self.assertIn('12 characters', help_text)

    def test_password_validators_help_text_html_escaping(self):
        class AmpersandValidator:
            def get_help_text(self):
                return 'Must contain &'
        help_text = password_validators_help_text_html([AmpersandValidator()])
        self.assertEqual(help_text, '<ul><li>Must contain &amp;</li></ul>')
        # help_text is marked safe and therefore unchanged by conditional_escape().
        self.assertEqual(help_text, conditional_escape(help_text))

    @override_settings(AUTH_PASSWORD_VALIDATORS=[])
    def test_empty_password_validator_help_text_html(self):
        self.assertEqual(password_validators_help_text_html(), '')


class MinimumLengthValidatorTest(SimpleTestCase):
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
        # max_similarity=1 doesn't allow passwords that are identical to the
        # attribute's value.
        with self.assertRaises(ValidationError) as cm:
            UserAttributeSimilarityValidator(
                user_attributes=['first_name'],
                max_similarity=1,
            ).validate(user.first_name, user=user)
        self.assertEqual(cm.exception.messages, [expected_error % "first name"])
        # max_similarity=0 rejects all passwords.
        with self.assertRaises(ValidationError) as cm:
            UserAttributeSimilarityValidator(
                user_attributes=['first_name'],
                max_similarity=0,
            ).validate('XXX', user=user)
        self.assertEqual(cm.exception.messages, [expected_error % "first name"])
        # Passes validation.
        self.assertIsNone(
            UserAttributeSimilarityValidator(user_attributes=['first_name']).validate('testclient', user=user)
        )

    @isolate_apps('auth_tests')
    def test_validate_property(self):
        class TestUser(models.Model):
            pass

            @property
            def username(self):
                return 'foobar'

        with self.assertRaises(ValidationError) as cm:
            UserAttributeSimilarityValidator().validate('foobar', user=TestUser()),
        self.assertEqual(cm.exception.messages, ['The password is too similar to the username.'])

    def test_help_text(self):
        self.assertEqual(
            UserAttributeSimilarityValidator().get_help_text(),
            "Your password can't be too similar to your other personal information."
        )


class CommonPasswordValidatorTest(SimpleTestCase):
    def test_validate(self):
        expected_error = "This password is too common."
        self.assertIsNone(CommonPasswordValidator().validate('a-safe-password'))

        with self.assertRaises(ValidationError) as cm:
            CommonPasswordValidator().validate('godzilla')
        self.assertEqual(cm.exception.messages, [expected_error])

    def test_validate_custom_list(self):
        path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'common-passwords-custom.txt')
        validator = CommonPasswordValidator(password_list_path=path)
        expected_error = "This password is too common."
        self.assertIsNone(validator.validate('a-safe-password'))

        with self.assertRaises(ValidationError) as cm:
            validator.validate('from-my-custom-list')
        self.assertEqual(cm.exception.messages, [expected_error])
        self.assertEqual(cm.exception.error_list[0].code, 'password_too_common')

    def test_validate_django_supplied_file(self):
        validator = CommonPasswordValidator()
        for password in validator.passwords:
            self.assertEqual(password, password.lower())

    def test_help_text(self):
        self.assertEqual(
            CommonPasswordValidator().get_help_text(),
            "Your password can't be a commonly used password."
        )


class NumericPasswordValidatorTest(SimpleTestCase):
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


class UsernameValidatorsTests(SimpleTestCase):
    def test_unicode_validator(self):
        valid_usernames = ['joe', 'René', 'ᴮᴵᴳᴮᴵᴿᴰ', 'أحمد']
        invalid_usernames = [
            "o'connell", "عبد ال",
            "zerowidth\u200Bspace", "nonbreaking\u00A0space",
            "en\u2013dash", 'trailingnewline\u000A',
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
        valid_usernames = ['glenn', 'GLEnN', 'jean-marc']
        invalid_usernames = ["o'connell", 'Éric', 'jean marc', "أحمد", 'trailingnewline\n']
        v = validators.ASCIIUsernameValidator()
        for valid in valid_usernames:
            with self.subTest(valid=valid):
                v(valid)
        for invalid in invalid_usernames:
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValidationError):
                    v(invalid)


class NoAmbiguousCharactersValidatorTest(SimpleTestCase):
    def test_validate_default_ambiguous(self):
        self.assertIsNone(NoAmbiguousCharactersValidator().validate("abcdef"))
        self.assertIsNone(NoAmbiguousCharactersValidator().validate("234567"))

        for (ambig_pw, badmsg) in (
            (
                "aeiou",
                "This password contains the following ambiguous characters: 'i', 'o'.",
            ),
            (
                "c0rnhOle",
                "This password contains the following ambiguous characters: '0', 'O', 'l'.",
            ),
            (
                "carame|",
                "This password contains the following ambiguous character: '|'.",
            ),
        ):
            with self.subTest(ambig_pw=ambig_pw, badmsg=ambig_pw):
                with self.assertRaises(ValidationError) as cm:
                    NoAmbiguousCharactersValidator().validate(ambig_pw)
                self.assertEqual(cm.exception.messages, [badmsg])
                self.assertEqual(
                    cm.exception.error_list[0].code,
                    "password_has_ambiguous_characters",
                )

    def test_validate_custom_ambiguous(self):
        self.assertIsNone(
            NoAmbiguousCharactersValidator("efg").validate("abcd")
        )
        self.assertIsNone(
            NoAmbiguousCharactersValidator(set("efg")).validate("abcd")
        )

        for ambig_pw, badmsg in (
            (
                "hi_im_007",
                "This password contains the following ambiguous character: '0'.",
            ),
            (
                "bad_m0Od",
                "This password contains the following ambiguous characters: '0', 'O'.",
            ),
        ):
            with self.subTest(ambig_pw=ambig_pw, badmsg=ambig_pw):
                with self.assertRaises(ValidationError) as cm:
                    NoAmbiguousCharactersValidator(set("0O")).validate(ambig_pw)
                self.assertEqual(cm.exception.messages, [badmsg])
                self.assertEqual(
                    cm.exception.error_list[0].code,
                    "password_has_ambiguous_characters",
                )

    def test_get_help_text(self):
        self.assertEqual(
            NoAmbiguousCharactersValidator().get_help_text(),
            "Your password may not contain ambiguous characters '0', '1', 'I', 'O', 'i', 'l', 'o', '|'.",
        )
        self.assertEqual(
            NoAmbiguousCharactersValidator("aaaaa").get_help_text(),
            "Your password may not contain the ambiguous character 'a'.",
        )

    def test_requires_atleast_one_ambig(self):
        with self.assertRaises(ValueError) as cm:
            NoAmbiguousCharactersValidator(())
        self.assertEqual(
            cm.exception.args[0],
            "Must specify at least one ambiguous character.",
        )


class NoSequentialCharsValidatorTest(SimpleTestCase):
    def test_get_help_text(self):
        self.assertEqual(
            NoSequentialCharsValidator(1).get_help_text(),
            "Your password must contain no more than 1 repeat of the same "
            "character in a row.",
        )
        self.assertEqual(
            NoSequentialCharsValidator(99).get_help_text(),
            "Your password must contain no more than 99 repeats of the same "
            "character in a row.",
        )

    def test_max_sequential_chars_param(self):
        with self.assertRaises(ValueError):
            NoSequentialCharsValidator(0)

    def test_validate(self):
        self.assertIsNone(NoSequentialCharsValidator(2).validate("abcda"))
        self.assertIsNone(NoSequentialCharsValidator(4).validate("abcabc"))

        with self.assertRaises(ValidationError) as cm:
            NoSequentialCharsValidator(2).validate("rrpeaterrr")
        self.assertEqual(
            cm.exception.messages,
            [
                "This password contains 3 sequential characters.  "
                "Your password should contain no more than 2 sequential"
                " characters."
            ],
        )
        self.assertEqual(
            cm.exception.error_list[0].code, "password_has_sequential_chars"
        )

        with self.assertRaises(ValidationError) as cm:
            NoSequentialCharsValidator(3).validate("paaaassword1!")
        self.assertEqual(
            cm.exception.messages,
            [
                "This password contains 4 sequential characters.  "
                "Your password should contain no more than 3 sequential"
                " characters."
            ],
        )
        self.assertEqual(
            cm.exception.error_list[0].code, "password_has_sequential_chars"
        )


class ShannonEntropyValidatorTest(SimpleTestCase):
    def setUp(self):
        self.entropy = ShannonEntropyValidator._shannon_entropy

    def test_shannon_entropy(self):
        self.assertGreater(self.entropy("abcd"), self.entropy("abc"))
        self.assertGreater(self.entropy("abcd"), self.entropy("abca"))
        self.assertGreater(
            self.entropy('U*&y=PYZH:*rfuL~h=":|&CmecPK4.'),
            self.entropy('U*&y=PYZH:*UUUUUUUUU|&CmecPK4.'),
        )
        self.assertAlmostEqual(self.entropy("AAAAABBCDE"), 1.9609640474436814)
        self.assertAlmostEqual(self.entropy("({ucdC(Rp7kG"), 3.418295834054489)

    def test_validate(self):
        weak = "banana$"  # ~1.84
        self.assertIsNone(ShannonEntropyValidator(1.8).validate(weak))
        with self.assertRaises(ValidationError) as cm:
            ShannonEntropyValidator(2.0).validate(weak)

        self.assertEqual(
            cm.exception.messages,
            ['This password does not meet the required complexity score of '
             '2.00; it scores a 1.84.  Increase the length of the password'
             ' and avoid repeating characters.']
        )
        self.assertEqual(
            cm.exception.error_list[0].code, "password_not_complex_enough"
        )

    def test_get_help_text(self):
        self.assertEqual(
            ShannonEntropyValidator().get_help_text(),
            "Your password should meet an overall complexity score. "
            "This score is based on the length of the password and variety "
            "of unique characters used.",
        )


class NoRepeatSubstringsValidatorTest(SimpleTestCase):
    def test_validate(self):
        with self.assertRaises(ValueError):
            NoRepeatSubstringsValidator(0)
        self.assertIsNone(NoRepeatSubstringsValidator(1).validate("aba"))
        self.assertIsNone(NoRepeatSubstringsValidator(2).validate("abba"))
        self.assertIsNone(NoRepeatSubstringsValidator(3).validate("abaccc"))
        for n in (1, 2, 3):
            with self.subTest(n=n):
                self.assertIsNone(NoRepeatSubstringsValidator(n).validate("myfirstname"))

        with self.assertRaises(ValidationError) as cm:
            NoRepeatSubstringsValidator(3).validate("passpassword")
        self.assertEqual(
            cm.exception.messages,
            ["This password contains a repeated substring longer than 3 characters: 'pass'."]
        )
        self.assertEqual(
            cm.exception.error_list[0].code, "password_found_repeat_substring"
        )

    def test_get_help_text(self):
        self.assertEqual(
            NoRepeatSubstringsValidator(1).get_help_text(),
            "Your password should not contain a repeated substring longer than 1 character."
        )
        self.assertEqual(
            NoRepeatSubstringsValidator(3).get_help_text(),
            "Your password should not contain a repeated substring longer than 3 characters."
        )
