# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from unittest import skipUnless

from django.conf.global_settings import PASSWORD_HASHERS
from django.contrib.auth.hashers import (
    UNUSABLE_PASSWORD_PREFIX, UNUSABLE_PASSWORD_SUFFIX_LENGTH,
    BasePasswordHasher, PBKDF2PasswordHasher, PBKDF2SHA1PasswordHasher,
    check_password, get_hasher, identify_hasher, is_password_usable,
    make_password,
)
from django.test import SimpleTestCase
from django.test.utils import override_settings
from django.utils import six

try:
    import crypt
except ImportError:
    crypt = None

try:
    import bcrypt
except ImportError:
    bcrypt = None


class PBKDF2SingleIterationHasher(PBKDF2PasswordHasher):
    iterations = 1


@override_settings(PASSWORD_HASHERS=PASSWORD_HASHERS)
class TestUtilsHashPass(SimpleTestCase):

    def test_simple(self):
        encoded = make_password('lètmein')
        self.assertTrue(encoded.startswith('pbkdf2_sha256$'))
        self.assertTrue(is_password_usable(encoded))
        self.assertTrue(check_password('lètmein', encoded))
        self.assertFalse(check_password('lètmeinz', encoded))
        # Blank passwords
        blank_encoded = make_password('')
        self.assertTrue(blank_encoded.startswith('pbkdf2_sha256$'))
        self.assertTrue(is_password_usable(blank_encoded))
        self.assertTrue(check_password('', blank_encoded))
        self.assertFalse(check_password(' ', blank_encoded))

    def test_pkbdf2(self):
        encoded = make_password('lètmein', 'seasalt', 'pbkdf2_sha256')
        self.assertEqual(encoded,
            'pbkdf2_sha256$20000$seasalt$oBSd886ysm3AqYun62DOdin8YcfbU1z9cksZSuLP9r0=')
        self.assertTrue(is_password_usable(encoded))
        self.assertTrue(check_password('lètmein', encoded))
        self.assertFalse(check_password('lètmeinz', encoded))
        self.assertEqual(identify_hasher(encoded).algorithm, "pbkdf2_sha256")
        # Blank passwords
        blank_encoded = make_password('', 'seasalt', 'pbkdf2_sha256')
        self.assertTrue(blank_encoded.startswith('pbkdf2_sha256$'))
        self.assertTrue(is_password_usable(blank_encoded))
        self.assertTrue(check_password('', blank_encoded))
        self.assertFalse(check_password(' ', blank_encoded))

    def test_sha1(self):
        encoded = make_password('lètmein', 'seasalt', 'sha1')
        self.assertEqual(encoded,
            'sha1$seasalt$cff36ea83f5706ce9aa7454e63e431fc726b2dc8')
        self.assertTrue(is_password_usable(encoded))
        self.assertTrue(check_password('lètmein', encoded))
        self.assertFalse(check_password('lètmeinz', encoded))
        self.assertEqual(identify_hasher(encoded).algorithm, "sha1")
        # Blank passwords
        blank_encoded = make_password('', 'seasalt', 'sha1')
        self.assertTrue(blank_encoded.startswith('sha1$'))
        self.assertTrue(is_password_usable(blank_encoded))
        self.assertTrue(check_password('', blank_encoded))
        self.assertFalse(check_password(' ', blank_encoded))

    def test_md5(self):
        encoded = make_password('lètmein', 'seasalt', 'md5')
        self.assertEqual(encoded,
                         'md5$seasalt$3f86d0d3d465b7b458c231bf3555c0e3')
        self.assertTrue(is_password_usable(encoded))
        self.assertTrue(check_password('lètmein', encoded))
        self.assertFalse(check_password('lètmeinz', encoded))
        self.assertEqual(identify_hasher(encoded).algorithm, "md5")
        # Blank passwords
        blank_encoded = make_password('', 'seasalt', 'md5')
        self.assertTrue(blank_encoded.startswith('md5$'))
        self.assertTrue(is_password_usable(blank_encoded))
        self.assertTrue(check_password('', blank_encoded))
        self.assertFalse(check_password(' ', blank_encoded))

    def test_unsalted_md5(self):
        encoded = make_password('lètmein', '', 'unsalted_md5')
        self.assertEqual(encoded, '88a434c88cca4e900f7874cd98123f43')
        self.assertTrue(is_password_usable(encoded))
        self.assertTrue(check_password('lètmein', encoded))
        self.assertFalse(check_password('lètmeinz', encoded))
        self.assertEqual(identify_hasher(encoded).algorithm, "unsalted_md5")
        # Alternate unsalted syntax
        alt_encoded = "md5$$%s" % encoded
        self.assertTrue(is_password_usable(alt_encoded))
        self.assertTrue(check_password('lètmein', alt_encoded))
        self.assertFalse(check_password('lètmeinz', alt_encoded))
        # Blank passwords
        blank_encoded = make_password('', '', 'unsalted_md5')
        self.assertTrue(is_password_usable(blank_encoded))
        self.assertTrue(check_password('', blank_encoded))
        self.assertFalse(check_password(' ', blank_encoded))

    def test_unsalted_sha1(self):
        encoded = make_password('lètmein', '', 'unsalted_sha1')
        self.assertEqual(encoded, 'sha1$$6d138ca3ae545631b3abd71a4f076ce759c5700b')
        self.assertTrue(is_password_usable(encoded))
        self.assertTrue(check_password('lètmein', encoded))
        self.assertFalse(check_password('lètmeinz', encoded))
        self.assertEqual(identify_hasher(encoded).algorithm, "unsalted_sha1")
        # Raw SHA1 isn't acceptable
        alt_encoded = encoded[6:]
        self.assertFalse(check_password('lètmein', alt_encoded))
        # Blank passwords
        blank_encoded = make_password('', '', 'unsalted_sha1')
        self.assertTrue(blank_encoded.startswith('sha1$'))
        self.assertTrue(is_password_usable(blank_encoded))
        self.assertTrue(check_password('', blank_encoded))
        self.assertFalse(check_password(' ', blank_encoded))

    @skipUnless(crypt, "no crypt module to generate password.")
    def test_crypt(self):
        encoded = make_password('lètmei', 'ab', 'crypt')
        self.assertEqual(encoded, 'crypt$$ab1Hv2Lg7ltQo')
        self.assertTrue(is_password_usable(encoded))
        self.assertTrue(check_password('lètmei', encoded))
        self.assertFalse(check_password('lètmeiz', encoded))
        self.assertEqual(identify_hasher(encoded).algorithm, "crypt")
        # Blank passwords
        blank_encoded = make_password('', 'ab', 'crypt')
        self.assertTrue(blank_encoded.startswith('crypt$'))
        self.assertTrue(is_password_usable(blank_encoded))
        self.assertTrue(check_password('', blank_encoded))
        self.assertFalse(check_password(' ', blank_encoded))

    @skipUnless(bcrypt, "bcrypt not installed")
    def test_bcrypt_sha256(self):
        encoded = make_password('lètmein', hasher='bcrypt_sha256')
        self.assertTrue(is_password_usable(encoded))
        self.assertTrue(encoded.startswith('bcrypt_sha256$'))
        self.assertTrue(check_password('lètmein', encoded))
        self.assertFalse(check_password('lètmeinz', encoded))
        self.assertEqual(identify_hasher(encoded).algorithm, "bcrypt_sha256")

        # Verify that password truncation no longer works
        password = ('VSK0UYV6FFQVZ0KG88DYN9WADAADZO1CTSIVDJUNZSUML6IBX7LN7ZS3R5'
                    'JGB3RGZ7VI7G7DJQ9NI8BQFSRPTG6UWTTVESA5ZPUN')
        encoded = make_password(password, hasher='bcrypt_sha256')
        self.assertTrue(check_password(password, encoded))
        self.assertFalse(check_password(password[:72], encoded))
        # Blank passwords
        blank_encoded = make_password('', hasher='bcrypt_sha256')
        self.assertTrue(blank_encoded.startswith('bcrypt_sha256$'))
        self.assertTrue(is_password_usable(blank_encoded))
        self.assertTrue(check_password('', blank_encoded))
        self.assertFalse(check_password(' ', blank_encoded))

    @skipUnless(bcrypt, "bcrypt not installed")
    def test_bcrypt(self):
        encoded = make_password('lètmein', hasher='bcrypt')
        self.assertTrue(is_password_usable(encoded))
        self.assertTrue(encoded.startswith('bcrypt$'))
        self.assertTrue(check_password('lètmein', encoded))
        self.assertFalse(check_password('lètmeinz', encoded))
        self.assertEqual(identify_hasher(encoded).algorithm, "bcrypt")
        # Blank passwords
        blank_encoded = make_password('', hasher='bcrypt')
        self.assertTrue(blank_encoded.startswith('bcrypt$'))
        self.assertTrue(is_password_usable(blank_encoded))
        self.assertTrue(check_password('', blank_encoded))
        self.assertFalse(check_password(' ', blank_encoded))

    def test_unusable(self):
        encoded = make_password(None)
        self.assertEqual(len(encoded), len(UNUSABLE_PASSWORD_PREFIX) + UNUSABLE_PASSWORD_SUFFIX_LENGTH)
        self.assertFalse(is_password_usable(encoded))
        self.assertFalse(check_password(None, encoded))
        self.assertFalse(check_password(encoded, encoded))
        self.assertFalse(check_password(UNUSABLE_PASSWORD_PREFIX, encoded))
        self.assertFalse(check_password('', encoded))
        self.assertFalse(check_password('lètmein', encoded))
        self.assertFalse(check_password('lètmeinz', encoded))
        self.assertRaises(ValueError, identify_hasher, encoded)
        # Assert that the unusable passwords actually contain a random part.
        # This might fail one day due to a hash collision.
        self.assertNotEqual(encoded, make_password(None), "Random password collision?")

    def test_unspecified_password(self):
        """
        Makes sure specifying no plain password with a valid encoded password
        returns `False`.
        """
        self.assertFalse(check_password(None, make_password('lètmein')))

    def test_bad_algorithm(self):
        with self.assertRaises(ValueError):
            make_password('lètmein', hasher='lolcat')
        self.assertRaises(ValueError, identify_hasher, "lolcat$salt$hash")

    def test_bad_encoded(self):
        self.assertFalse(is_password_usable('lètmein_badencoded'))
        self.assertFalse(is_password_usable(''))

    def test_low_level_pkbdf2(self):
        hasher = PBKDF2PasswordHasher()
        encoded = hasher.encode('lètmein', 'seasalt2')
        self.assertEqual(encoded,
            'pbkdf2_sha256$20000$seasalt2$Flpve/uAcyo6+IFI6YAhjeABGPVbRQjzHDxRhqxewgw=')
        self.assertTrue(hasher.verify('lètmein', encoded))

    def test_low_level_pbkdf2_sha1(self):
        hasher = PBKDF2SHA1PasswordHasher()
        encoded = hasher.encode('lètmein', 'seasalt2')
        self.assertEqual(encoded,
            'pbkdf2_sha1$20000$seasalt2$pJt86NmjAweBY1StBvxCu7l1o9o=')
        self.assertTrue(hasher.verify('lètmein', encoded))

    def test_upgrade(self):
        self.assertEqual('pbkdf2_sha256', get_hasher('default').algorithm)
        for algo in ('sha1', 'md5'):
            encoded = make_password('lètmein', hasher=algo)
            state = {'upgraded': False}

            def setter(password):
                state['upgraded'] = True
            self.assertTrue(check_password('lètmein', encoded, setter))
            self.assertTrue(state['upgraded'])

    def test_no_upgrade(self):
        encoded = make_password('lètmein')
        state = {'upgraded': False}

        def setter():
            state['upgraded'] = True
        self.assertFalse(check_password('WRONG', encoded, setter))
        self.assertFalse(state['upgraded'])

    def test_no_upgrade_on_incorrect_pass(self):
        self.assertEqual('pbkdf2_sha256', get_hasher('default').algorithm)
        for algo in ('sha1', 'md5'):
            encoded = make_password('lètmein', hasher=algo)
            state = {'upgraded': False}

            def setter():
                state['upgraded'] = True
            self.assertFalse(check_password('WRONG', encoded, setter))
            self.assertFalse(state['upgraded'])

    def test_pbkdf2_upgrade(self):
        hasher = get_hasher('default')
        self.assertEqual('pbkdf2_sha256', hasher.algorithm)
        self.assertNotEqual(hasher.iterations, 1)

        old_iterations = hasher.iterations
        try:
            # Generate a password with 1 iteration.
            hasher.iterations = 1
            encoded = make_password('letmein')
            algo, iterations, salt, hash = encoded.split('$', 3)
            self.assertEqual(iterations, '1')

            state = {'upgraded': False}

            def setter(password):
                state['upgraded'] = True

            # Check that no upgrade is triggered
            self.assertTrue(check_password('letmein', encoded, setter))
            self.assertFalse(state['upgraded'])

            # Revert to the old iteration count and ...
            hasher.iterations = old_iterations

            # ... check if the password would get updated to the new iteration count.
            self.assertTrue(check_password('letmein', encoded, setter))
            self.assertTrue(state['upgraded'])
        finally:
            hasher.iterations = old_iterations

    def test_pbkdf2_upgrade_new_hasher(self):
        hasher = get_hasher('default')
        self.assertEqual('pbkdf2_sha256', hasher.algorithm)
        self.assertNotEqual(hasher.iterations, 1)

        state = {'upgraded': False}

        def setter(password):
            state['upgraded'] = True

        with self.settings(PASSWORD_HASHERS=[
                'auth_tests.test_hashers.PBKDF2SingleIterationHasher']):
            encoded = make_password('letmein')
            algo, iterations, salt, hash = encoded.split('$', 3)
            self.assertEqual(iterations, '1')

            # Check that no upgrade is triggered
            self.assertTrue(check_password('letmein', encoded, setter))
            self.assertFalse(state['upgraded'])

        # Revert to the old iteration count and check if the password would get
        # updated to the new iteration count.
        with self.settings(PASSWORD_HASHERS=[
                'django.contrib.auth.hashers.PBKDF2PasswordHasher',
                'auth_tests.test_hashers.PBKDF2SingleIterationHasher']):
            self.assertTrue(check_password('letmein', encoded, setter))
            self.assertTrue(state['upgraded'])

    def test_load_library_no_algorithm(self):
        with self.assertRaises(ValueError) as e:
            BasePasswordHasher()._load_library()
        self.assertEqual("Hasher 'BasePasswordHasher' doesn't specify a "
                         "library attribute", str(e.exception))

    def test_load_library_importerror(self):
        PlainHasher = type(str('PlainHasher'), (BasePasswordHasher,),
                           {'algorithm': 'plain', 'library': 'plain'})
        # Python 3.3 adds quotes around module name
        with six.assertRaisesRegex(self, ValueError,
                "Couldn't load 'PlainHasher' algorithm library: No module named '?plain'?"):
            PlainHasher()._load_library()
