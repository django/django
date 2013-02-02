# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf.global_settings import PASSWORD_HASHERS as default_hashers
from django.contrib.auth.hashers import (is_password_usable, 
    check_password, make_password, PBKDF2PasswordHasher, load_hashers,
    PBKDF2SHA1PasswordHasher, get_hasher, identify_hasher, UNUSABLE_PASSWORD)
from django.utils import unittest
from django.utils.unittest import skipUnless


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
        encoded = make_password('lètmein')
        self.assertTrue(encoded.startswith('pbkdf2_sha256$'))
        self.assertTrue(is_password_usable(encoded))
        self.assertTrue(check_password('lètmein', encoded))
        self.assertFalse(check_password('lètmeinz', encoded))

    def test_pkbdf2(self):
        encoded = make_password('lètmein', 'seasalt', 'pbkdf2_sha256')
        self.assertEqual(encoded,
            'pbkdf2_sha256$10000$seasalt$CWWFdHOWwPnki7HvkcqN9iA2T3KLW1cf2uZ5kvArtVY=')
        self.assertTrue(is_password_usable(encoded))
        self.assertTrue(check_password('lètmein', encoded))
        self.assertFalse(check_password('lètmeinz', encoded))
        self.assertEqual(identify_hasher(encoded).algorithm, "pbkdf2_sha256")

    def test_sha1(self):
        encoded = make_password('lètmein', 'seasalt', 'sha1')
        self.assertEqual(encoded,
            'sha1$seasalt$cff36ea83f5706ce9aa7454e63e431fc726b2dc8')
        self.assertTrue(is_password_usable(encoded))
        self.assertTrue(check_password('lètmein', encoded))
        self.assertFalse(check_password('lètmeinz', encoded))
        self.assertEqual(identify_hasher(encoded).algorithm, "sha1")

    def test_md5(self):
        encoded = make_password('lètmein', 'seasalt', 'md5')
        self.assertEqual(encoded, 
                         'md5$seasalt$3f86d0d3d465b7b458c231bf3555c0e3')
        self.assertTrue(is_password_usable(encoded))
        self.assertTrue(check_password('lètmein', encoded))
        self.assertFalse(check_password('lètmeinz', encoded))
        self.assertEqual(identify_hasher(encoded).algorithm, "md5")

    def test_unsalted_md5(self):
        encoded = make_password('lètmein', 'seasalt', 'unsalted_md5')
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

    @skipUnless(crypt, "no crypt module to generate password.")
    def test_crypt(self):
        encoded = make_password('lètmei', 'ab', 'crypt')
        self.assertEqual(encoded, 'crypt$$ab1Hv2Lg7ltQo')
        self.assertTrue(is_password_usable(encoded))
        self.assertTrue(check_password('lètmei', encoded))
        self.assertFalse(check_password('lètmeiz', encoded))
        self.assertEqual(identify_hasher(encoded).algorithm, "crypt")

    @skipUnless(bcrypt, "py-bcrypt not installed")
    def test_bcrypt(self):
        encoded = make_password('lètmein', hasher='bcrypt')
        self.assertTrue(is_password_usable(encoded))
        self.assertTrue(encoded.startswith('bcrypt$'))
        self.assertTrue(check_password('lètmein', encoded))
        self.assertFalse(check_password('lètmeinz', encoded))
        self.assertEqual(identify_hasher(encoded).algorithm, "bcrypt")

    def test_unusable(self):
        encoded = make_password(None)
        self.assertFalse(is_password_usable(encoded))
        self.assertFalse(check_password(None, encoded))
        self.assertFalse(check_password(UNUSABLE_PASSWORD, encoded))
        self.assertFalse(check_password('', encoded))
        self.assertFalse(check_password('lètmein', encoded))
        self.assertFalse(check_password('lètmeinz', encoded))
        self.assertRaises(ValueError, identify_hasher, encoded)

    def test_bad_algorithm(self):
        def doit():
            make_password('lètmein', hasher='lolcat')
        self.assertRaises(ValueError, doit)
        self.assertRaises(ValueError, identify_hasher, "lolcat$salt$hash")

    def test_bad_encoded(self):
        self.assertFalse(is_password_usable('lètmein_badencoded'))
        self.assertFalse(is_password_usable(''))

    def test_low_level_pkbdf2(self):
        hasher = PBKDF2PasswordHasher()
        encoded = hasher.encode('lètmein', 'seasalt')
        self.assertEqual(encoded,
            'pbkdf2_sha256$10000$seasalt$CWWFdHOWwPnki7HvkcqN9iA2T3KLW1cf2uZ5kvArtVY=')
        self.assertTrue(hasher.verify('lètmein', encoded))

    def test_low_level_pbkdf2_sha1(self):
        hasher = PBKDF2SHA1PasswordHasher()
        encoded = hasher.encode('lètmein', 'seasalt')
        self.assertEqual(encoded,
            'pbkdf2_sha1$10000$seasalt$oAfF6vgs95ncksAhGXOWf4Okq7o=')
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
