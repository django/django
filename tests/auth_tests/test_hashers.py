from unittest import mock, skipUnless

from django.conf.global_settings import PASSWORD_HASHERS
from django.contrib.auth.hashers import (
    UNUSABLE_PASSWORD_PREFIX,
    UNUSABLE_PASSWORD_SUFFIX_LENGTH,
    BasePasswordHasher,
    BCryptPasswordHasher,
    BCryptSHA256PasswordHasher,
    MD5PasswordHasher,
    PBKDF2PasswordHasher,
    PBKDF2SHA1PasswordHasher,
    ScryptPasswordHasher,
    check_password,
    get_hasher,
    identify_hasher,
    is_password_usable,
    make_password,
)
from django.test import SimpleTestCase, ignore_warnings
from django.test.utils import override_settings
from django.utils.deprecation import RemovedInDjango50Warning, RemovedInDjango51Warning

# RemovedInDjango50Warning.
try:
    import crypt
except ImportError:
    crypt = None
else:
    # On some platforms (e.g. OpenBSD), crypt.crypt() always return None.
    if crypt.crypt("") is None:
        crypt = None

try:
    import bcrypt
except ImportError:
    bcrypt = None

try:
    import argon2
except ImportError:
    argon2 = None

# scrypt requires OpenSSL 1.1+
try:
    import hashlib

    scrypt = hashlib.scrypt
except ImportError:
    scrypt = None


class PBKDF2SingleIterationHasher(PBKDF2PasswordHasher):
    iterations = 1


@override_settings(PASSWORD_HASHERS=PASSWORD_HASHERS)
class TestUtilsHashPass(SimpleTestCase):
    def test_simple(self):
        encoded = make_password("lètmein")
        self.assertTrue(encoded.startswith("pbkdf2_sha256$"))
        self.assertTrue(is_password_usable(encoded))
        self.assertTrue(check_password("lètmein", encoded))
        self.assertFalse(check_password("lètmeinz", encoded))
        # Blank passwords
        blank_encoded = make_password("")
        self.assertTrue(blank_encoded.startswith("pbkdf2_sha256$"))
        self.assertTrue(is_password_usable(blank_encoded))
        self.assertTrue(check_password("", blank_encoded))
        self.assertFalse(check_password(" ", blank_encoded))

    def test_bytes(self):
        encoded = make_password(b"bytes_password")
        self.assertTrue(encoded.startswith("pbkdf2_sha256$"))
        self.assertIs(is_password_usable(encoded), True)
        self.assertIs(check_password(b"bytes_password", encoded), True)

    def test_invalid_password(self):
        msg = "Password must be a string or bytes, got int."
        with self.assertRaisesMessage(TypeError, msg):
            make_password(1)

    def test_pbkdf2(self):
        encoded = make_password("lètmein", "seasalt", "pbkdf2_sha256")
        self.assertEqual(
            encoded,
            "pbkdf2_sha256$600000$seasalt$OAXyhAQ/4ZDA9V5RMExt3C1OwQdUpLZ99vm1McFlLRA=",
        )
        self.assertTrue(is_password_usable(encoded))
        self.assertTrue(check_password("lètmein", encoded))
        self.assertFalse(check_password("lètmeinz", encoded))
        self.assertEqual(identify_hasher(encoded).algorithm, "pbkdf2_sha256")
        # Blank passwords
        blank_encoded = make_password("", "seasalt", "pbkdf2_sha256")
        self.assertTrue(blank_encoded.startswith("pbkdf2_sha256$"))
        self.assertTrue(is_password_usable(blank_encoded))
        self.assertTrue(check_password("", blank_encoded))
        self.assertFalse(check_password(" ", blank_encoded))
        # Salt entropy check.
        hasher = get_hasher("pbkdf2_sha256")
        encoded_weak_salt = make_password("lètmein", "iodizedsalt", "pbkdf2_sha256")
        encoded_strong_salt = make_password("lètmein", hasher.salt(), "pbkdf2_sha256")
        self.assertIs(hasher.must_update(encoded_weak_salt), True)
        self.assertIs(hasher.must_update(encoded_strong_salt), False)

    @ignore_warnings(category=RemovedInDjango51Warning)
    @override_settings(
        PASSWORD_HASHERS=["django.contrib.auth.hashers.SHA1PasswordHasher"]
    )
    def test_sha1(self):
        encoded = make_password("lètmein", "seasalt", "sha1")
        self.assertEqual(
            encoded, "sha1$seasalt$cff36ea83f5706ce9aa7454e63e431fc726b2dc8"
        )
        self.assertTrue(is_password_usable(encoded))
        self.assertTrue(check_password("lètmein", encoded))
        self.assertFalse(check_password("lètmeinz", encoded))
        self.assertEqual(identify_hasher(encoded).algorithm, "sha1")
        # Blank passwords
        blank_encoded = make_password("", "seasalt", "sha1")
        self.assertTrue(blank_encoded.startswith("sha1$"))
        self.assertTrue(is_password_usable(blank_encoded))
        self.assertTrue(check_password("", blank_encoded))
        self.assertFalse(check_password(" ", blank_encoded))
        # Salt entropy check.
        hasher = get_hasher("sha1")
        encoded_weak_salt = make_password("lètmein", "iodizedsalt", "sha1")
        encoded_strong_salt = make_password("lètmein", hasher.salt(), "sha1")
        self.assertIs(hasher.must_update(encoded_weak_salt), True)
        self.assertIs(hasher.must_update(encoded_strong_salt), False)

    @override_settings(
        PASSWORD_HASHERS=["django.contrib.auth.hashers.SHA1PasswordHasher"]
    )
    def test_sha1_deprecation_warning(self):
        msg = "django.contrib.auth.hashers.SHA1PasswordHasher is deprecated."
        with self.assertRaisesMessage(RemovedInDjango51Warning, msg):
            get_hasher("sha1")

    @override_settings(
        PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"]
    )
    def test_md5(self):
        encoded = make_password("lètmein", "seasalt", "md5")
        self.assertEqual(encoded, "md5$seasalt$3f86d0d3d465b7b458c231bf3555c0e3")
        self.assertTrue(is_password_usable(encoded))
        self.assertTrue(check_password("lètmein", encoded))
        self.assertFalse(check_password("lètmeinz", encoded))
        self.assertEqual(identify_hasher(encoded).algorithm, "md5")
        # Blank passwords
        blank_encoded = make_password("", "seasalt", "md5")
        self.assertTrue(blank_encoded.startswith("md5$"))
        self.assertTrue(is_password_usable(blank_encoded))
        self.assertTrue(check_password("", blank_encoded))
        self.assertFalse(check_password(" ", blank_encoded))
        # Salt entropy check.
        hasher = get_hasher("md5")
        encoded_weak_salt = make_password("lètmein", "iodizedsalt", "md5")
        encoded_strong_salt = make_password("lètmein", hasher.salt(), "md5")
        self.assertIs(hasher.must_update(encoded_weak_salt), True)
        self.assertIs(hasher.must_update(encoded_strong_salt), False)

    @ignore_warnings(category=RemovedInDjango51Warning)
    @override_settings(
        PASSWORD_HASHERS=["django.contrib.auth.hashers.UnsaltedMD5PasswordHasher"]
    )
    def test_unsalted_md5(self):
        encoded = make_password("lètmein", "", "unsalted_md5")
        self.assertEqual(encoded, "88a434c88cca4e900f7874cd98123f43")
        self.assertTrue(is_password_usable(encoded))
        self.assertTrue(check_password("lètmein", encoded))
        self.assertFalse(check_password("lètmeinz", encoded))
        self.assertEqual(identify_hasher(encoded).algorithm, "unsalted_md5")
        # Alternate unsalted syntax
        alt_encoded = "md5$$%s" % encoded
        self.assertTrue(is_password_usable(alt_encoded))
        self.assertTrue(check_password("lètmein", alt_encoded))
        self.assertFalse(check_password("lètmeinz", alt_encoded))
        # Blank passwords
        blank_encoded = make_password("", "", "unsalted_md5")
        self.assertTrue(is_password_usable(blank_encoded))
        self.assertTrue(check_password("", blank_encoded))
        self.assertFalse(check_password(" ", blank_encoded))

    @ignore_warnings(category=RemovedInDjango51Warning)
    @override_settings(
        PASSWORD_HASHERS=["django.contrib.auth.hashers.UnsaltedMD5PasswordHasher"]
    )
    def test_unsalted_md5_encode_invalid_salt(self):
        hasher = get_hasher("unsalted_md5")
        msg = "salt must be empty."
        with self.assertRaisesMessage(ValueError, msg):
            hasher.encode("password", salt="salt")

    @override_settings(
        PASSWORD_HASHERS=["django.contrib.auth.hashers.UnsaltedMD5PasswordHasher"]
    )
    def test_unsalted_md5_deprecation_warning(self):
        msg = "django.contrib.auth.hashers.UnsaltedMD5PasswordHasher is deprecated."
        with self.assertRaisesMessage(RemovedInDjango51Warning, msg):
            get_hasher("unsalted_md5")

    @ignore_warnings(category=RemovedInDjango51Warning)
    @override_settings(
        PASSWORD_HASHERS=["django.contrib.auth.hashers.UnsaltedSHA1PasswordHasher"]
    )
    def test_unsalted_sha1(self):
        encoded = make_password("lètmein", "", "unsalted_sha1")
        self.assertEqual(encoded, "sha1$$6d138ca3ae545631b3abd71a4f076ce759c5700b")
        self.assertTrue(is_password_usable(encoded))
        self.assertTrue(check_password("lètmein", encoded))
        self.assertFalse(check_password("lètmeinz", encoded))
        self.assertEqual(identify_hasher(encoded).algorithm, "unsalted_sha1")
        # Raw SHA1 isn't acceptable
        alt_encoded = encoded[6:]
        self.assertFalse(check_password("lètmein", alt_encoded))
        # Blank passwords
        blank_encoded = make_password("", "", "unsalted_sha1")
        self.assertTrue(blank_encoded.startswith("sha1$"))
        self.assertTrue(is_password_usable(blank_encoded))
        self.assertTrue(check_password("", blank_encoded))
        self.assertFalse(check_password(" ", blank_encoded))

    @ignore_warnings(category=RemovedInDjango51Warning)
    @override_settings(
        PASSWORD_HASHERS=["django.contrib.auth.hashers.UnsaltedSHA1PasswordHasher"]
    )
    def test_unsalted_sha1_encode_invalid_salt(self):
        hasher = get_hasher("unsalted_sha1")
        msg = "salt must be empty."
        with self.assertRaisesMessage(ValueError, msg):
            hasher.encode("password", salt="salt")

    @override_settings(
        PASSWORD_HASHERS=["django.contrib.auth.hashers.UnsaltedSHA1PasswordHasher"]
    )
    def test_unsalted_sha1_deprecation_warning(self):
        msg = "django.contrib.auth.hashers.UnsaltedSHA1PasswordHasher is deprecated."
        with self.assertRaisesMessage(RemovedInDjango51Warning, msg):
            get_hasher("unsalted_sha1")

    @ignore_warnings(category=RemovedInDjango50Warning)
    @skipUnless(crypt, "no crypt module to generate password.")
    @override_settings(
        PASSWORD_HASHERS=["django.contrib.auth.hashers.CryptPasswordHasher"]
    )
    def test_crypt(self):
        encoded = make_password("lètmei", "ab", "crypt")
        self.assertEqual(encoded, "crypt$$ab1Hv2Lg7ltQo")
        self.assertTrue(is_password_usable(encoded))
        self.assertTrue(check_password("lètmei", encoded))
        self.assertFalse(check_password("lètmeiz", encoded))
        self.assertEqual(identify_hasher(encoded).algorithm, "crypt")
        # Blank passwords
        blank_encoded = make_password("", "ab", "crypt")
        self.assertTrue(blank_encoded.startswith("crypt$"))
        self.assertTrue(is_password_usable(blank_encoded))
        self.assertTrue(check_password("", blank_encoded))
        self.assertFalse(check_password(" ", blank_encoded))

    @ignore_warnings(category=RemovedInDjango50Warning)
    @skipUnless(crypt, "no crypt module to generate password.")
    @override_settings(
        PASSWORD_HASHERS=["django.contrib.auth.hashers.CryptPasswordHasher"]
    )
    def test_crypt_encode_invalid_salt(self):
        hasher = get_hasher("crypt")
        msg = "salt must be of length 2."
        with self.assertRaisesMessage(ValueError, msg):
            hasher.encode("password", salt="a")

    @ignore_warnings(category=RemovedInDjango50Warning)
    @skipUnless(crypt, "no crypt module to generate password.")
    @override_settings(
        PASSWORD_HASHERS=["django.contrib.auth.hashers.CryptPasswordHasher"]
    )
    def test_crypt_encode_invalid_hash(self):
        hasher = get_hasher("crypt")
        msg = "hash must be provided."
        with mock.patch("crypt.crypt", return_value=None):
            with self.assertRaisesMessage(TypeError, msg):
                hasher.encode("password", salt="ab")

    @skipUnless(crypt, "no crypt module to generate password.")
    @override_settings(
        PASSWORD_HASHERS=["django.contrib.auth.hashers.CryptPasswordHasher"]
    )
    def test_crypt_deprecation_warning(self):
        msg = "django.contrib.auth.hashers.CryptPasswordHasher is deprecated."
        with self.assertRaisesMessage(RemovedInDjango50Warning, msg):
            get_hasher("crypt")

    @skipUnless(bcrypt, "bcrypt not installed")
    def test_bcrypt_sha256(self):
        encoded = make_password("lètmein", hasher="bcrypt_sha256")
        self.assertTrue(is_password_usable(encoded))
        self.assertTrue(encoded.startswith("bcrypt_sha256$"))
        self.assertTrue(check_password("lètmein", encoded))
        self.assertFalse(check_password("lètmeinz", encoded))
        self.assertEqual(identify_hasher(encoded).algorithm, "bcrypt_sha256")

        # password truncation no longer works
        password = (
            "VSK0UYV6FFQVZ0KG88DYN9WADAADZO1CTSIVDJUNZSUML6IBX7LN7ZS3R5"
            "JGB3RGZ7VI7G7DJQ9NI8BQFSRPTG6UWTTVESA5ZPUN"
        )
        encoded = make_password(password, hasher="bcrypt_sha256")
        self.assertTrue(check_password(password, encoded))
        self.assertFalse(check_password(password[:72], encoded))
        # Blank passwords
        blank_encoded = make_password("", hasher="bcrypt_sha256")
        self.assertTrue(blank_encoded.startswith("bcrypt_sha256$"))
        self.assertTrue(is_password_usable(blank_encoded))
        self.assertTrue(check_password("", blank_encoded))
        self.assertFalse(check_password(" ", blank_encoded))

    @skipUnless(bcrypt, "bcrypt not installed")
    @override_settings(
        PASSWORD_HASHERS=["django.contrib.auth.hashers.BCryptPasswordHasher"]
    )
    def test_bcrypt(self):
        encoded = make_password("lètmein", hasher="bcrypt")
        self.assertTrue(is_password_usable(encoded))
        self.assertTrue(encoded.startswith("bcrypt$"))
        self.assertTrue(check_password("lètmein", encoded))
        self.assertFalse(check_password("lètmeinz", encoded))
        self.assertEqual(identify_hasher(encoded).algorithm, "bcrypt")
        # Blank passwords
        blank_encoded = make_password("", hasher="bcrypt")
        self.assertTrue(blank_encoded.startswith("bcrypt$"))
        self.assertTrue(is_password_usable(blank_encoded))
        self.assertTrue(check_password("", blank_encoded))
        self.assertFalse(check_password(" ", blank_encoded))

    @skipUnless(bcrypt, "bcrypt not installed")
    @override_settings(
        PASSWORD_HASHERS=["django.contrib.auth.hashers.BCryptPasswordHasher"]
    )
    def test_bcrypt_upgrade(self):
        hasher = get_hasher("bcrypt")
        self.assertEqual("bcrypt", hasher.algorithm)
        self.assertNotEqual(hasher.rounds, 4)

        old_rounds = hasher.rounds
        try:
            # Generate a password with 4 rounds.
            hasher.rounds = 4
            encoded = make_password("letmein", hasher="bcrypt")
            rounds = hasher.safe_summary(encoded)["work factor"]
            self.assertEqual(rounds, 4)

            state = {"upgraded": False}

            def setter(password):
                state["upgraded"] = True

            # No upgrade is triggered.
            self.assertTrue(check_password("letmein", encoded, setter, "bcrypt"))
            self.assertFalse(state["upgraded"])

            # Revert to the old rounds count and ...
            hasher.rounds = old_rounds

            # ... check if the password would get updated to the new count.
            self.assertTrue(check_password("letmein", encoded, setter, "bcrypt"))
            self.assertTrue(state["upgraded"])
        finally:
            hasher.rounds = old_rounds

    @skipUnless(bcrypt, "bcrypt not installed")
    @override_settings(
        PASSWORD_HASHERS=["django.contrib.auth.hashers.BCryptPasswordHasher"]
    )
    def test_bcrypt_harden_runtime(self):
        hasher = get_hasher("bcrypt")
        self.assertEqual("bcrypt", hasher.algorithm)

        with mock.patch.object(hasher, "rounds", 4):
            encoded = make_password("letmein", hasher="bcrypt")

        with mock.patch.object(hasher, "rounds", 6), mock.patch.object(
            hasher, "encode", side_effect=hasher.encode
        ):
            hasher.harden_runtime("wrong_password", encoded)

            # Increasing rounds from 4 to 6 means an increase of 4 in workload,
            # therefore hardening should run 3 times to make the timing the
            # same (the original encode() call already ran once).
            self.assertEqual(hasher.encode.call_count, 3)

            # Get the original salt (includes the original workload factor)
            algorithm, data = encoded.split("$", 1)
            expected_call = (("wrong_password", data[:29].encode()),)
            self.assertEqual(hasher.encode.call_args_list, [expected_call] * 3)

    def test_unusable(self):
        encoded = make_password(None)
        self.assertEqual(
            len(encoded),
            len(UNUSABLE_PASSWORD_PREFIX) + UNUSABLE_PASSWORD_SUFFIX_LENGTH,
        )
        self.assertFalse(is_password_usable(encoded))
        self.assertFalse(check_password(None, encoded))
        self.assertFalse(check_password(encoded, encoded))
        self.assertFalse(check_password(UNUSABLE_PASSWORD_PREFIX, encoded))
        self.assertFalse(check_password("", encoded))
        self.assertFalse(check_password("lètmein", encoded))
        self.assertFalse(check_password("lètmeinz", encoded))
        with self.assertRaisesMessage(ValueError, "Unknown password hashing algorith"):
            identify_hasher(encoded)
        # Assert that the unusable passwords actually contain a random part.
        # This might fail one day due to a hash collision.
        self.assertNotEqual(encoded, make_password(None), "Random password collision?")

    def test_unspecified_password(self):
        """
        Makes sure specifying no plain password with a valid encoded password
        returns `False`.
        """
        self.assertFalse(check_password(None, make_password("lètmein")))

    def test_bad_algorithm(self):
        msg = (
            "Unknown password hashing algorithm '%s'. Did you specify it in "
            "the PASSWORD_HASHERS setting?"
        )
        with self.assertRaisesMessage(ValueError, msg % "lolcat"):
            make_password("lètmein", hasher="lolcat")
        with self.assertRaisesMessage(ValueError, msg % "lolcat"):
            identify_hasher("lolcat$salt$hash")

    def test_is_password_usable(self):
        passwords = ("lètmein_badencoded", "", None)
        for password in passwords:
            with self.subTest(password=password):
                self.assertIs(is_password_usable(password), True)

    def test_low_level_pbkdf2(self):
        hasher = PBKDF2PasswordHasher()
        encoded = hasher.encode("lètmein", "seasalt2")
        self.assertEqual(
            encoded,
            "pbkdf2_sha256$600000$seasalt2$OSllgFdJjYQjb0RfMzrx8u0XYl4Fkt+wKpI1yq4lZlo"
            "=",
        )
        self.assertTrue(hasher.verify("lètmein", encoded))

    def test_low_level_pbkdf2_sha1(self):
        hasher = PBKDF2SHA1PasswordHasher()
        encoded = hasher.encode("lètmein", "seasalt2")
        self.assertEqual(
            encoded, "pbkdf2_sha1$600000$seasalt2$2CLsaL1MZhq6JOG6QOHtVbiopHE="
        )
        self.assertTrue(hasher.verify("lètmein", encoded))

    @skipUnless(bcrypt, "bcrypt not installed")
    def test_bcrypt_salt_check(self):
        hasher = BCryptPasswordHasher()
        encoded = hasher.encode("lètmein", hasher.salt())
        self.assertIs(hasher.must_update(encoded), False)

    @skipUnless(bcrypt, "bcrypt not installed")
    def test_bcryptsha256_salt_check(self):
        hasher = BCryptSHA256PasswordHasher()
        encoded = hasher.encode("lètmein", hasher.salt())
        self.assertIs(hasher.must_update(encoded), False)

    @override_settings(
        PASSWORD_HASHERS=[
            "django.contrib.auth.hashers.PBKDF2PasswordHasher",
            "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
            "django.contrib.auth.hashers.MD5PasswordHasher",
        ],
    )
    def test_upgrade(self):
        self.assertEqual("pbkdf2_sha256", get_hasher("default").algorithm)
        for algo in ("pbkdf2_sha1", "md5"):
            with self.subTest(algo=algo):
                encoded = make_password("lètmein", hasher=algo)
                state = {"upgraded": False}

                def setter(password):
                    state["upgraded"] = True

                self.assertTrue(check_password("lètmein", encoded, setter))
                self.assertTrue(state["upgraded"])

    def test_no_upgrade(self):
        encoded = make_password("lètmein")
        state = {"upgraded": False}

        def setter():
            state["upgraded"] = True

        self.assertFalse(check_password("WRONG", encoded, setter))
        self.assertFalse(state["upgraded"])

    @override_settings(
        PASSWORD_HASHERS=[
            "django.contrib.auth.hashers.PBKDF2PasswordHasher",
            "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
            "django.contrib.auth.hashers.MD5PasswordHasher",
        ],
    )
    def test_no_upgrade_on_incorrect_pass(self):
        self.assertEqual("pbkdf2_sha256", get_hasher("default").algorithm)
        for algo in ("pbkdf2_sha1", "md5"):
            with self.subTest(algo=algo):
                encoded = make_password("lètmein", hasher=algo)
                state = {"upgraded": False}

                def setter():
                    state["upgraded"] = True

                self.assertFalse(check_password("WRONG", encoded, setter))
                self.assertFalse(state["upgraded"])

    def test_pbkdf2_upgrade(self):
        hasher = get_hasher("default")
        self.assertEqual("pbkdf2_sha256", hasher.algorithm)
        self.assertNotEqual(hasher.iterations, 1)

        old_iterations = hasher.iterations
        try:
            # Generate a password with 1 iteration.
            hasher.iterations = 1
            encoded = make_password("letmein")
            algo, iterations, salt, hash = encoded.split("$", 3)
            self.assertEqual(iterations, "1")

            state = {"upgraded": False}

            def setter(password):
                state["upgraded"] = True

            # No upgrade is triggered
            self.assertTrue(check_password("letmein", encoded, setter))
            self.assertFalse(state["upgraded"])

            # Revert to the old iteration count and ...
            hasher.iterations = old_iterations

            # ... check if the password would get updated to the new iteration count.
            self.assertTrue(check_password("letmein", encoded, setter))
            self.assertTrue(state["upgraded"])
        finally:
            hasher.iterations = old_iterations

    def test_pbkdf2_harden_runtime(self):
        hasher = get_hasher("default")
        self.assertEqual("pbkdf2_sha256", hasher.algorithm)

        with mock.patch.object(hasher, "iterations", 1):
            encoded = make_password("letmein")

        with mock.patch.object(hasher, "iterations", 6), mock.patch.object(
            hasher, "encode", side_effect=hasher.encode
        ):
            hasher.harden_runtime("wrong_password", encoded)

            # Encode should get called once ...
            self.assertEqual(hasher.encode.call_count, 1)

            # ... with the original salt and 5 iterations.
            algorithm, iterations, salt, hash = encoded.split("$", 3)
            expected_call = (("wrong_password", salt, 5),)
            self.assertEqual(hasher.encode.call_args, expected_call)

    def test_pbkdf2_upgrade_new_hasher(self):
        hasher = get_hasher("default")
        self.assertEqual("pbkdf2_sha256", hasher.algorithm)
        self.assertNotEqual(hasher.iterations, 1)

        state = {"upgraded": False}

        def setter(password):
            state["upgraded"] = True

        with self.settings(
            PASSWORD_HASHERS=["auth_tests.test_hashers.PBKDF2SingleIterationHasher"]
        ):
            encoded = make_password("letmein")
            algo, iterations, salt, hash = encoded.split("$", 3)
            self.assertEqual(iterations, "1")

            # No upgrade is triggered
            self.assertTrue(check_password("letmein", encoded, setter))
            self.assertFalse(state["upgraded"])

        # Revert to the old iteration count and check if the password would get
        # updated to the new iteration count.
        with self.settings(
            PASSWORD_HASHERS=[
                "django.contrib.auth.hashers.PBKDF2PasswordHasher",
                "auth_tests.test_hashers.PBKDF2SingleIterationHasher",
            ]
        ):
            self.assertTrue(check_password("letmein", encoded, setter))
            self.assertTrue(state["upgraded"])

    def test_check_password_calls_harden_runtime(self):
        hasher = get_hasher("default")
        encoded = make_password("letmein")

        with mock.patch.object(hasher, "harden_runtime"), mock.patch.object(
            hasher, "must_update", return_value=True
        ):
            # Correct password supplied, no hardening needed
            check_password("letmein", encoded)
            self.assertEqual(hasher.harden_runtime.call_count, 0)

            # Wrong password supplied, hardening needed
            check_password("wrong_password", encoded)
            self.assertEqual(hasher.harden_runtime.call_count, 1)

    def test_check_password_calls_make_password_to_fake_runtime(self):
        hasher = get_hasher("default")
        cases = [
            (None, None, None),  # no plain text password provided
            ("foo", make_password(password=None), None),  # unusable encoded
            ("letmein", make_password(password="letmein"), ValueError),  # valid encoded
        ]
        for password, encoded, hasher_side_effect in cases:
            with (
                self.subTest(encoded=encoded),
                mock.patch(
                    "django.contrib.auth.hashers.identify_hasher",
                    side_effect=hasher_side_effect,
                ) as mock_identify_hasher,
                mock.patch(
                    "django.contrib.auth.hashers.make_password"
                ) as mock_make_password,
                mock.patch(
                    "django.contrib.auth.hashers.get_random_string",
                    side_effect=lambda size: "x" * size,
                ),
                mock.patch.object(hasher, "verify"),
            ):
                # Ensure make_password is called to standardize timing.
                check_password(password, encoded)
                self.assertEqual(hasher.verify.call_count, 0)
                self.assertEqual(mock_identify_hasher.mock_calls, [mock.call(encoded)])
                self.assertEqual(
                    mock_make_password.mock_calls,
                    [mock.call("x" * UNUSABLE_PASSWORD_SUFFIX_LENGTH)],
                )

    def test_encode_invalid_salt(self):
        hasher_classes = [
            MD5PasswordHasher,
            PBKDF2PasswordHasher,
            PBKDF2SHA1PasswordHasher,
            ScryptPasswordHasher,
        ]
        msg = "salt must be provided and cannot contain $."
        for hasher_class in hasher_classes:
            hasher = hasher_class()
            for salt in [None, "", "sea$salt"]:
                with self.subTest(hasher_class.__name__, salt=salt):
                    with self.assertRaisesMessage(ValueError, msg):
                        hasher.encode("password", salt)

    def test_encode_password_required(self):
        hasher_classes = [
            MD5PasswordHasher,
            PBKDF2PasswordHasher,
            PBKDF2SHA1PasswordHasher,
            ScryptPasswordHasher,
        ]
        msg = "password must be provided."
        for hasher_class in hasher_classes:
            hasher = hasher_class()
            with self.subTest(hasher_class.__name__):
                with self.assertRaisesMessage(TypeError, msg):
                    hasher.encode(None, "seasalt")


class BasePasswordHasherTests(SimpleTestCase):
    not_implemented_msg = "subclasses of BasePasswordHasher must provide %s() method"

    def setUp(self):
        self.hasher = BasePasswordHasher()

    def test_load_library_no_algorithm(self):
        msg = "Hasher 'BasePasswordHasher' doesn't specify a library attribute"
        with self.assertRaisesMessage(ValueError, msg):
            self.hasher._load_library()

    def test_load_library_importerror(self):
        PlainHasher = type(
            "PlainHasher",
            (BasePasswordHasher,),
            {"algorithm": "plain", "library": "plain"},
        )
        msg = "Couldn't load 'PlainHasher' algorithm library: No module named 'plain'"
        with self.assertRaisesMessage(ValueError, msg):
            PlainHasher()._load_library()

    def test_attributes(self):
        self.assertIsNone(self.hasher.algorithm)
        self.assertIsNone(self.hasher.library)

    def test_encode(self):
        msg = self.not_implemented_msg % "an encode"
        with self.assertRaisesMessage(NotImplementedError, msg):
            self.hasher.encode("password", "salt")

    def test_decode(self):
        msg = self.not_implemented_msg % "a decode"
        with self.assertRaisesMessage(NotImplementedError, msg):
            self.hasher.decode("encoded")

    def test_harden_runtime(self):
        msg = (
            "subclasses of BasePasswordHasher should provide a harden_runtime() method"
        )
        with self.assertWarnsMessage(Warning, msg):
            self.hasher.harden_runtime("password", "encoded")

    def test_must_update(self):
        self.assertIs(self.hasher.must_update("encoded"), False)

    def test_safe_summary(self):
        msg = self.not_implemented_msg % "a safe_summary"
        with self.assertRaisesMessage(NotImplementedError, msg):
            self.hasher.safe_summary("encoded")

    def test_verify(self):
        msg = self.not_implemented_msg % "a verify"
        with self.assertRaisesMessage(NotImplementedError, msg):
            self.hasher.verify("password", "encoded")


@skipUnless(argon2, "argon2-cffi not installed")
@override_settings(PASSWORD_HASHERS=PASSWORD_HASHERS)
class TestUtilsHashPassArgon2(SimpleTestCase):
    def test_argon2(self):
        encoded = make_password("lètmein", hasher="argon2")
        self.assertTrue(is_password_usable(encoded))
        self.assertTrue(encoded.startswith("argon2$argon2id$"))
        self.assertTrue(check_password("lètmein", encoded))
        self.assertFalse(check_password("lètmeinz", encoded))
        self.assertEqual(identify_hasher(encoded).algorithm, "argon2")
        # Blank passwords
        blank_encoded = make_password("", hasher="argon2")
        self.assertTrue(blank_encoded.startswith("argon2$argon2id$"))
        self.assertTrue(is_password_usable(blank_encoded))
        self.assertTrue(check_password("", blank_encoded))
        self.assertFalse(check_password(" ", blank_encoded))
        # Old hashes without version attribute
        encoded = (
            "argon2$argon2i$m=8,t=1,p=1$c29tZXNhbHQ$gwQOXSNhxiOxPOA0+PY10P9QFO"
            "4NAYysnqRt1GSQLE55m+2GYDt9FEjPMHhP2Cuf0nOEXXMocVrsJAtNSsKyfg"
        )
        self.assertTrue(check_password("secret", encoded))
        self.assertFalse(check_password("wrong", encoded))
        # Old hashes with version attribute.
        encoded = "argon2$argon2i$v=19$m=8,t=1,p=1$c2FsdHNhbHQ$YC9+jJCrQhs5R6db7LlN8Q"
        self.assertIs(check_password("secret", encoded), True)
        self.assertIs(check_password("wrong", encoded), False)
        # Salt entropy check.
        hasher = get_hasher("argon2")
        encoded_weak_salt = make_password("lètmein", "iodizedsalt", "argon2")
        encoded_strong_salt = make_password("lètmein", hasher.salt(), "argon2")
        self.assertIs(hasher.must_update(encoded_weak_salt), True)
        self.assertIs(hasher.must_update(encoded_strong_salt), False)

    def test_argon2_decode(self):
        salt = "abcdefghijk"
        encoded = make_password("lètmein", salt=salt, hasher="argon2")
        hasher = get_hasher("argon2")
        decoded = hasher.decode(encoded)
        self.assertEqual(decoded["memory_cost"], hasher.memory_cost)
        self.assertEqual(decoded["parallelism"], hasher.parallelism)
        self.assertEqual(decoded["salt"], salt)
        self.assertEqual(decoded["time_cost"], hasher.time_cost)

    def test_argon2_upgrade(self):
        self._test_argon2_upgrade("time_cost", "time cost", 1)
        self._test_argon2_upgrade("memory_cost", "memory cost", 64)
        self._test_argon2_upgrade("parallelism", "parallelism", 1)

    def test_argon2_version_upgrade(self):
        hasher = get_hasher("argon2")
        state = {"upgraded": False}
        encoded = (
            "argon2$argon2id$v=19$m=102400,t=2,p=8$Y041dExhNkljRUUy$TMa6A8fPJh"
            "CAUXRhJXCXdw"
        )

        def setter(password):
            state["upgraded"] = True

        old_m = hasher.memory_cost
        old_t = hasher.time_cost
        old_p = hasher.parallelism
        try:
            hasher.memory_cost = 8
            hasher.time_cost = 1
            hasher.parallelism = 1
            self.assertTrue(check_password("secret", encoded, setter, "argon2"))
            self.assertTrue(state["upgraded"])
        finally:
            hasher.memory_cost = old_m
            hasher.time_cost = old_t
            hasher.parallelism = old_p

    def _test_argon2_upgrade(self, attr, summary_key, new_value):
        hasher = get_hasher("argon2")
        self.assertEqual("argon2", hasher.algorithm)
        self.assertNotEqual(getattr(hasher, attr), new_value)

        old_value = getattr(hasher, attr)
        try:
            # Generate hash with attr set to 1
            setattr(hasher, attr, new_value)
            encoded = make_password("letmein", hasher="argon2")
            attr_value = hasher.safe_summary(encoded)[summary_key]
            self.assertEqual(attr_value, new_value)

            state = {"upgraded": False}

            def setter(password):
                state["upgraded"] = True

            # No upgrade is triggered.
            self.assertTrue(check_password("letmein", encoded, setter, "argon2"))
            self.assertFalse(state["upgraded"])

            # Revert to the old rounds count and ...
            setattr(hasher, attr, old_value)

            # ... check if the password would get updated to the new count.
            self.assertTrue(check_password("letmein", encoded, setter, "argon2"))
            self.assertTrue(state["upgraded"])
        finally:
            setattr(hasher, attr, old_value)


@skipUnless(scrypt, "scrypt not available")
@override_settings(PASSWORD_HASHERS=PASSWORD_HASHERS)
class TestUtilsHashPassScrypt(SimpleTestCase):
    def test_scrypt(self):
        encoded = make_password("lètmein", "seasalt", "scrypt")
        self.assertEqual(
            encoded,
            "scrypt$16384$seasalt$8$1$Qj3+9PPyRjSJIebHnG81TMjsqtaIGxNQG/aEB/NY"
            "afTJ7tibgfYz71m0ldQESkXFRkdVCBhhY8mx7rQwite/Pw==",
        )
        self.assertIs(is_password_usable(encoded), True)
        self.assertIs(check_password("lètmein", encoded), True)
        self.assertIs(check_password("lètmeinz", encoded), False)
        self.assertEqual(identify_hasher(encoded).algorithm, "scrypt")
        # Blank passwords.
        blank_encoded = make_password("", "seasalt", "scrypt")
        self.assertIs(blank_encoded.startswith("scrypt$"), True)
        self.assertIs(is_password_usable(blank_encoded), True)
        self.assertIs(check_password("", blank_encoded), True)
        self.assertIs(check_password(" ", blank_encoded), False)

    def test_scrypt_decode(self):
        encoded = make_password("lètmein", "seasalt", "scrypt")
        hasher = get_hasher("scrypt")
        decoded = hasher.decode(encoded)
        tests = [
            ("block_size", hasher.block_size),
            ("parallelism", hasher.parallelism),
            ("salt", "seasalt"),
            ("work_factor", hasher.work_factor),
        ]
        for key, excepted in tests:
            with self.subTest(key=key):
                self.assertEqual(decoded[key], excepted)

    def _test_scrypt_upgrade(self, attr, summary_key, new_value):
        hasher = get_hasher("scrypt")
        self.assertEqual(hasher.algorithm, "scrypt")
        self.assertNotEqual(getattr(hasher, attr), new_value)

        old_value = getattr(hasher, attr)
        try:
            # Generate hash with attr set to the new value.
            setattr(hasher, attr, new_value)
            encoded = make_password("lètmein", "seasalt", "scrypt")
            attr_value = hasher.safe_summary(encoded)[summary_key]
            self.assertEqual(attr_value, new_value)

            state = {"upgraded": False}

            def setter(password):
                state["upgraded"] = True

            # No update is triggered.
            self.assertIs(check_password("lètmein", encoded, setter, "scrypt"), True)
            self.assertIs(state["upgraded"], False)
            # Revert to the old value.
            setattr(hasher, attr, old_value)
            # Password is updated.
            self.assertIs(check_password("lètmein", encoded, setter, "scrypt"), True)
            self.assertIs(state["upgraded"], True)
        finally:
            setattr(hasher, attr, old_value)

    def test_scrypt_upgrade(self):
        tests = [
            ("work_factor", "work factor", 2**11),
            ("block_size", "block size", 10),
            ("parallelism", "parallelism", 2),
        ]
        for attr, summary_key, new_value in tests:
            with self.subTest(attr=attr):
                self._test_scrypt_upgrade(attr, summary_key, new_value)
