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
from django.test import SimpleTestCase, mock
from django.test.utils import override_settings
from django.utils import six
from django.utils.encoding import force_bytes

try:
    import crypt
except ImportError:
    crypt = None
else:
    # On some platforms (e.g. OpenBSD), crypt.crypt() always return None.
    if crypt.crypt('', '') is None:
        crypt = None

try:
    import bcrypt
except ImportError:
    bcrypt = None

try:
    import argon2
except ImportError:
    argon2 = None


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

    def test_pbkdf2(self):
        encoded = make_password('lètmein', 'seasalt', 'pbkdf2_sha256')
        self.assertEqual(encoded, 'pbkdf2_sha256$30000$seasalt$VrX+V8drCGo68wlvy6rfu8i1d1pfkdeXA4LJkRGJodY=')
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

    @override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.SHA1PasswordHasher'])
    def test_sha1(self):
        encoded = make_password('lètmein', 'seasalt', 'sha1')
        self.assertEqual(encoded, 'sha1$seasalt$cff36ea83f5706ce9aa7454e63e431fc726b2dc8')
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

    @override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
    def test_md5(self):
        encoded = make_password('lètmein', 'seasalt', 'md5')
        self.assertEqual(encoded, 'md5$seasalt$3f86d0d3d465b7b458c231bf3555c0e3')
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

    @override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.UnsaltedMD5PasswordHasher'])
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

    @override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.UnsaltedSHA1PasswordHasher'])
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
    @override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.CryptPasswordHasher'])
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
        password = (
            'VSK0UYV6FFQVZ0KG88DYN9WADAADZO1CTSIVDJUNZSUML6IBX7LN7ZS3R5'
            'JGB3RGZ7VI7G7DJQ9NI8BQFSRPTG6UWTTVESA5ZPUN'
        )
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

    @skipUnless(bcrypt, "bcrypt not installed")
    def test_bcrypt_upgrade(self):
        hasher = get_hasher('bcrypt')
        self.assertEqual('bcrypt', hasher.algorithm)
        self.assertNotEqual(hasher.rounds, 4)

        old_rounds = hasher.rounds
        try:
            # Generate a password with 4 rounds.
            hasher.rounds = 4
            encoded = make_password('letmein', hasher='bcrypt')
            rounds = hasher.safe_summary(encoded)['work factor']
            self.assertEqual(rounds, '04')

            state = {'upgraded': False}

            def setter(password):
                state['upgraded'] = True

            # Check that no upgrade is triggered.
            self.assertTrue(check_password('letmein', encoded, setter, 'bcrypt'))
            self.assertFalse(state['upgraded'])

            # Revert to the old rounds count and ...
            hasher.rounds = old_rounds

            # ... check if the password would get updated to the new count.
            self.assertTrue(check_password('letmein', encoded, setter, 'bcrypt'))
            self.assertTrue(state['upgraded'])
        finally:
            hasher.rounds = old_rounds

    @skipUnless(bcrypt, "bcrypt not installed")
    def test_bcrypt_harden_runtime(self):
        hasher = get_hasher('bcrypt')
        self.assertEqual('bcrypt', hasher.algorithm)

        with mock.patch.object(hasher, 'rounds', 4):
            encoded = make_password('letmein', hasher='bcrypt')

        with mock.patch.object(hasher, 'rounds', 6), \
                mock.patch.object(hasher, 'encode', side_effect=hasher.encode):
            hasher.harden_runtime('wrong_password', encoded)

            # Increasing rounds from 4 to 6 means an increase of 4 in workload,
            # therefore hardening should run 3 times to make the timing the
            # same (the original encode() call already ran once).
            self.assertEqual(hasher.encode.call_count, 3)

            # Get the original salt (includes the original workload factor)
            algorithm, data = encoded.split('$', 1)
            expected_call = (('wrong_password', force_bytes(data[:29])),)
            self.assertEqual(hasher.encode.call_args_list, [expected_call] * 3)

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
        with self.assertRaises(ValueError):
            identify_hasher(encoded)
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
        with self.assertRaises(ValueError):
            identify_hasher('lolcat$salt$hash')

    def test_bad_encoded(self):
        self.assertFalse(is_password_usable('lètmein_badencoded'))
        self.assertFalse(is_password_usable(''))

    def test_low_level_pbkdf2(self):
        hasher = PBKDF2PasswordHasher()
        encoded = hasher.encode('lètmein', 'seasalt2')
        self.assertEqual(encoded, 'pbkdf2_sha256$30000$seasalt2$a75qzbogeVhNFeMqhdgyyoqGKpIzYUo651sq57RERew=')
        self.assertTrue(hasher.verify('lètmein', encoded))

    def test_low_level_pbkdf2_sha1(self):
        hasher = PBKDF2SHA1PasswordHasher()
        encoded = hasher.encode('lètmein', 'seasalt2')
        self.assertEqual(encoded, 'pbkdf2_sha1$30000$seasalt2$pMzU1zNPcydf6wjnJFbiVKwgULc=')
        self.assertTrue(hasher.verify('lètmein', encoded))

    @override_settings(
        PASSWORD_HASHERS=[
            'django.contrib.auth.hashers.PBKDF2PasswordHasher',
            'django.contrib.auth.hashers.SHA1PasswordHasher',
            'django.contrib.auth.hashers.MD5PasswordHasher',
        ],
    )
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

    @override_settings(
        PASSWORD_HASHERS=[
            'django.contrib.auth.hashers.PBKDF2PasswordHasher',
            'django.contrib.auth.hashers.SHA1PasswordHasher',
            'django.contrib.auth.hashers.MD5PasswordHasher',
        ],
    )
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

    def test_pbkdf2_harden_runtime(self):
        hasher = get_hasher('default')
        self.assertEqual('pbkdf2_sha256', hasher.algorithm)

        with mock.patch.object(hasher, 'iterations', 1):
            encoded = make_password('letmein')

        with mock.patch.object(hasher, 'iterations', 6), \
                mock.patch.object(hasher, 'encode', side_effect=hasher.encode):
            hasher.harden_runtime('wrong_password', encoded)

            # Encode should get called once ...
            self.assertEqual(hasher.encode.call_count, 1)

            # ... with the original salt and 5 iterations.
            algorithm, iterations, salt, hash = encoded.split('$', 3)
            expected_call = (('wrong_password', salt, 5),)
            self.assertEqual(hasher.encode.call_args, expected_call)

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

    def test_check_password_calls_harden_runtime(self):
        hasher = get_hasher('default')
        encoded = make_password('letmein')

        with mock.patch.object(hasher, 'harden_runtime'), \
                mock.patch.object(hasher, 'must_update', return_value=True):
            # Correct password supplied, no hardening needed
            check_password('letmein', encoded)
            self.assertEqual(hasher.harden_runtime.call_count, 0)

            # Wrong password supplied, hardening needed
            check_password('wrong_password', encoded)
            self.assertEqual(hasher.harden_runtime.call_count, 1)

    def test_load_library_no_algorithm(self):
        with self.assertRaises(ValueError) as e:
            BasePasswordHasher()._load_library()
        self.assertEqual("Hasher 'BasePasswordHasher' doesn't specify a library attribute", str(e.exception))

    def test_load_library_importerror(self):
        PlainHasher = type(str('PlainHasher'), (BasePasswordHasher,), {'algorithm': 'plain', 'library': 'plain'})
        # Python 3 adds quotes around module name
        msg = "Couldn't load 'PlainHasher' algorithm library: No module named '?plain'?"
        with six.assertRaisesRegex(self, ValueError, msg):
            PlainHasher()._load_library()


@skipUnless(argon2, "argon2-cffi not installed")
@override_settings(PASSWORD_HASHERS=PASSWORD_HASHERS)
class TestUtilsHashPassArgon2(SimpleTestCase):

    def test_argon2(self):
        encoded = make_password('lètmein', hasher='argon2')
        self.assertTrue(is_password_usable(encoded))
        self.assertTrue(encoded.startswith('argon2$'))
        self.assertTrue(check_password('lètmein', encoded))
        self.assertFalse(check_password('lètmeinz', encoded))
        self.assertEqual(identify_hasher(encoded).algorithm, 'argon2')
        # Blank passwords
        blank_encoded = make_password('', hasher='argon2')
        self.assertTrue(blank_encoded.startswith('argon2$'))
        self.assertTrue(is_password_usable(blank_encoded))
        self.assertTrue(check_password('', blank_encoded))
        self.assertFalse(check_password(' ', blank_encoded))
        # Old hashes without version attribute
        encoded = (
            'argon2$argon2i$m=8,t=1,p=1$c29tZXNhbHQ$gwQOXSNhxiOxPOA0+PY10P9QFO'
            '4NAYysnqRt1GSQLE55m+2GYDt9FEjPMHhP2Cuf0nOEXXMocVrsJAtNSsKyfg'
        )
        self.assertTrue(check_password('secret', encoded))
        self.assertFalse(check_password('wrong', encoded))

    def test_argon2_upgrade(self):
        self._test_argon2_upgrade('time_cost', 'time cost', 1)
        self._test_argon2_upgrade('memory_cost', 'memory cost', 16)
        self._test_argon2_upgrade('parallelism', 'parallelism', 1)

    def test_argon2_version_upgrade(self):
        hasher = get_hasher('argon2')
        state = {'upgraded': False}
        encoded = (
            'argon2$argon2i$m=8,t=1,p=1$c29tZXNhbHQ$gwQOXSNhxiOxPOA0+PY10P9QFO'
            '4NAYysnqRt1GSQLE55m+2GYDt9FEjPMHhP2Cuf0nOEXXMocVrsJAtNSsKyfg'
        )

        def setter(password):
            state['upgraded'] = True

        old_m = hasher.memory_cost
        old_t = hasher.time_cost
        old_p = hasher.parallelism
        try:
            hasher.memory_cost = 8
            hasher.time_cost = 1
            hasher.parallelism = 1
            self.assertTrue(check_password('secret', encoded, setter, 'argon2'))
            self.assertTrue(state['upgraded'])
        finally:
            hasher.memory_cost = old_m
            hasher.time_cost = old_t
            hasher.parallelism = old_p

    def _test_argon2_upgrade(self, attr, summary_key, new_value):
        hasher = get_hasher('argon2')
        self.assertEqual('argon2', hasher.algorithm)
        self.assertNotEqual(getattr(hasher, attr), new_value)

        old_value = getattr(hasher, attr)
        try:
            # Generate hash with attr set to 1
            setattr(hasher, attr, new_value)
            encoded = make_password('letmein', hasher='argon2')
            attr_value = hasher.safe_summary(encoded)[summary_key]
            self.assertEqual(attr_value, new_value)

            state = {'upgraded': False}

            def setter(password):
                state['upgraded'] = True

            # Check that no upgrade is triggered.
            self.assertTrue(check_password('letmein', encoded, setter, 'argon2'))
            self.assertFalse(state['upgraded'])

            # Revert to the old rounds count and ...
            setattr(hasher, attr, old_value)

            # ... check if the password would get updated to the new count.
            self.assertTrue(check_password('letmein', encoded, setter, 'argon2'))
            self.assertTrue(state['upgraded'])
        finally:
            setattr(hasher, attr, old_value)
