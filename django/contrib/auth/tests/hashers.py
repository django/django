from django.conf.global_settings import PASSWORD_HASHERS as default_hashers
from django.contrib.auth.hashers import (is_password_usable,
    check_password, make_password, PBKDF2PasswordHasher, load_hashers,
    PBKDF2SHA1PasswordHasher, get_hasher, UNUSABLE_PASSWORD,
    MAXIMUM_PASSWORD_LENGTH, password_max_length)
from django.utils import unittest
from django.utils.unittest import skipUnless
from django.test.utils import override_settings


try:
    import crypt
except ImportError:
    crypt = None

try:
    import bcrypt
except ImportError:
    bcrypt = None


class TestUtilsHashPass(unittest.TestCase):
    def setUp(self):
        load_hashers(password_hashers=default_hashers)

    def test_simple(self):
        encoded = make_password('letmein')
        self.assertTrue(encoded.startswith('pbkdf2_sha256$'))
        self.assertTrue(is_password_usable(encoded))
        self.assertTrue(check_password(u'letmein', encoded))
        self.assertFalse(check_password('letmeinz', encoded))
        # Long password
        self.assertRaises(
            ValueError,
            make_password,
            "1" * (MAXIMUM_PASSWORD_LENGTH + 1),
        )

    def test_pkbdf2(self):
        encoded = make_password('letmein', 'seasalt', 'pbkdf2_sha256')
        self.assertEqual(encoded,
'pbkdf2_sha256$10000$seasalt$FQCNpiZpTb0zub+HBsH6TOwyRxJ19FwvjbweatNmK/Y=')
        self.assertTrue(is_password_usable(encoded))
        self.assertTrue(check_password(u'letmein', encoded))
        self.assertFalse(check_password('letmeinz', encoded))
        # Long password
        self.assertRaises(
            ValueError,
            make_password,
            "1" * (MAXIMUM_PASSWORD_LENGTH + 1),
            "seasalt",
            "pbkdf2_sha256",
        )

    def test_sha1(self):
        encoded = make_password('letmein', 'seasalt', 'sha1')
        self.assertEqual(encoded,
'sha1$seasalt$fec3530984afba6bade3347b7140d1a7da7da8c7')
        self.assertTrue(is_password_usable(encoded))
        self.assertTrue(check_password(u'letmein', encoded))
        self.assertFalse(check_password('letmeinz', encoded))
        # Long password
        self.assertRaises(
            ValueError,
            make_password,
            "1" * (MAXIMUM_PASSWORD_LENGTH + 1),
            "seasalt",
            "sha1",
        )

    def test_md5(self):
        encoded = make_password('letmein', 'seasalt', 'md5')
        self.assertEqual(encoded,
                         'md5$seasalt$f5531bef9f3687d0ccf0f617f0e25573')
        self.assertTrue(is_password_usable(encoded))
        self.assertTrue(check_password(u'letmein', encoded))
        self.assertFalse(check_password('letmeinz', encoded))
        # Long password
        self.assertRaises(
            ValueError,
            make_password,
            "1" * (MAXIMUM_PASSWORD_LENGTH + 1),
            "seasalt",
            "md5",
        )

    def test_unsalted_md5(self):
        encoded = make_password('letmein', '', 'unsalted_md5')
        self.assertEqual(encoded, '0d107d09f5bbe40cade3de5c71e9e9b7')
        self.assertTrue(is_password_usable(encoded))
        self.assertTrue(check_password(u'letmein', encoded))
        self.assertFalse(check_password('letmeinz', encoded))
        # Alternate unsalted syntax
        alt_encoded = "md5$$%s" % encoded
        self.assertTrue(is_password_usable(alt_encoded))
        self.assertTrue(check_password(u'letmein', alt_encoded))
        self.assertFalse(check_password('letmeinz', alt_encoded))
        # Long password
        self.assertRaises(
            ValueError,
            make_password,
            "1" * (MAXIMUM_PASSWORD_LENGTH + 1),
            "",
            "unsalted_md5",
        )

    def test_unsalted_sha1(self):
        encoded = make_password('letmein', '', 'unsalted_sha1')
        self.assertEqual(encoded, 'sha1$$b7a875fc1ea228b9061041b7cec4bd3c52ab3ce3')
        self.assertTrue(is_password_usable(encoded))
        self.assertTrue(check_password('letmein', encoded))
        self.assertFalse(check_password('letmeinz', encoded))
        # Raw SHA1 isn't acceptable
        alt_encoded = encoded[6:]
        self.assertRaises(ValueError, check_password, 'letmein', alt_encoded)
        # Long password
        self.assertRaises(
            ValueError,
            make_password,
            "1" * (MAXIMUM_PASSWORD_LENGTH + 1),
            "",
            "unslated_sha1",
        )

    @skipUnless(crypt, "no crypt module to generate password.")
    def test_crypt(self):
        encoded = make_password('letmein', 'ab', 'crypt')
        self.assertEqual(encoded, 'crypt$$abN/qM.L/H8EQ')
        self.assertTrue(is_password_usable(encoded))
        self.assertTrue(check_password(u'letmein', encoded))
        self.assertFalse(check_password('letmeinz', encoded))
        # Long password
        self.assertRaises(
            ValueError,
            make_password,
            "1" * (MAXIMUM_PASSWORD_LENGTH + 1),
            "seasalt",
            "crypt",
        )

    @skipUnless(bcrypt, "py-bcrypt not installed")
    def test_bcrypt(self):
        encoded = make_password('letmein', hasher='bcrypt')
        self.assertTrue(is_password_usable(encoded))
        self.assertTrue(encoded.startswith('bcrypt$'))
        self.assertTrue(check_password(u'letmein', encoded))
        self.assertFalse(check_password('letmeinz', encoded))
        # Long password
        self.assertRaises(
            ValueError,
            make_password,
            "1" * (MAXIMUM_PASSWORD_LENGTH + 1),
            hasher="bcrypt",
        )

    def test_unusable(self):
        encoded = make_password(None)
        self.assertFalse(is_password_usable(encoded))
        self.assertFalse(check_password(None, encoded))
        self.assertFalse(check_password(UNUSABLE_PASSWORD, encoded))
        self.assertFalse(check_password('', encoded))
        self.assertFalse(check_password(u'letmein', encoded))
        self.assertFalse(check_password('letmeinz', encoded))

    def test_bad_algorithm(self):
        def doit():
            make_password('letmein', hasher='lolcat')
        self.assertRaises(ValueError, doit)

    def test_max_password_length_decorator(self):
        @password_max_length(10)
        def encode(s, password, salt):
            return True

        self.assertTrue(encode(None, "1234", "1234"))
        self.assertRaises(ValueError, encode, None, "1234567890A", "1234")

    def test_low_level_pkbdf2(self):
        hasher = PBKDF2PasswordHasher()
        encoded = hasher.encode('letmein', 'seasalt')
        self.assertEqual(encoded,
'pbkdf2_sha256$10000$seasalt$FQCNpiZpTb0zub+HBsH6TOwyRxJ19FwvjbweatNmK/Y=')
        self.assertTrue(hasher.verify('letmein', encoded))

    def test_low_level_pbkdf2_sha1(self):
        hasher = PBKDF2SHA1PasswordHasher()
        encoded = hasher.encode('letmein', 'seasalt')
        self.assertEqual(encoded,
'pbkdf2_sha1$10000$seasalt$91JiNKgwADC8j2j86Ije/cc4vfQ=')
        self.assertTrue(hasher.verify('letmein', encoded))

    def test_upgrade(self):
        self.assertEqual('pbkdf2_sha256', get_hasher('default').algorithm)
        for algo in ('sha1', 'md5'):
            encoded = make_password('letmein', hasher=algo)
            state = {'upgraded': False}
            def setter(password):
                state['upgraded'] = True
            self.assertTrue(check_password('letmein', encoded, setter))
            self.assertTrue(state['upgraded'])

    def test_no_upgrade(self):
        encoded = make_password('letmein')
        state = {'upgraded': False}
        def setter():
            state['upgraded'] = True
        self.assertFalse(check_password('WRONG', encoded, setter))
        self.assertFalse(state['upgraded'])

    def test_no_upgrade_on_incorrect_pass(self):
        self.assertEqual('pbkdf2_sha256', get_hasher('default').algorithm)
        for algo in ('sha1', 'md5'):
            encoded = make_password('letmein', hasher=algo)
            state = {'upgraded': False}
            def setter():
                state['upgraded'] = True
            self.assertFalse(check_password('WRONG', encoded, setter))
            self.assertFalse(state['upgraded'])
