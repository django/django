import hashlib
import unittest

from django.test import SimpleTestCase, ignore_warnings
from django.utils.crypto import (
    InvalidAlgorithm, constant_time_compare, get_random_string, pbkdf2,
    salted_hmac,
)
from django.utils.deprecation import RemovedInDjango40Warning


class TestUtilsCryptoMisc(SimpleTestCase):

    def test_constant_time_compare(self):
        # It's hard to test for constant time, just test the result.
        self.assertTrue(constant_time_compare(b'spam', b'spam'))
        self.assertFalse(constant_time_compare(b'spam', b'eggs'))
        self.assertTrue(constant_time_compare('spam', 'spam'))
        self.assertFalse(constant_time_compare('spam', 'eggs'))

    def test_salted_hmac(self):
        tests = [
            ((b'salt', b'value'), {}, 'b51a2e619c43b1ca4f91d15c57455521d71d61eb'),
            (('salt', 'value'), {}, 'b51a2e619c43b1ca4f91d15c57455521d71d61eb'),
            (
                ('salt', 'value'),
                {'secret': 'abcdefg'},
                '8bbee04ccddfa24772d1423a0ba43bd0c0e24b76',
            ),
            (
                ('salt', 'value'),
                {'secret': 'x' * hashlib.sha1().block_size},
                'bd3749347b412b1b0a9ea65220e55767ac8e96b0',
            ),
            (
                ('salt', 'value'),
                {'algorithm': 'sha256'},
                'ee0bf789e4e009371a5372c90f73fcf17695a8439c9108b0480f14e347b3f9ec',
            ),
            (
                ('salt', 'value'),
                {
                    'algorithm': 'blake2b',
                    'secret': 'x' * hashlib.blake2b().block_size,
                },
                'fc6b9800a584d40732a07fa33fb69c35211269441823bca431a143853c32f'
                'e836cf19ab881689528ede647dac412170cd5d3407b44c6d0f44630690c54'
                'ad3d58',
            ),
        ]
        for args, kwargs, digest in tests:
            with self.subTest(args=args, kwargs=kwargs):
                self.assertEqual(salted_hmac(*args, **kwargs).hexdigest(), digest)

    def test_invalid_algorithm(self):
        msg = "'whatever' is not an algorithm accepted by the hashlib module."
        with self.assertRaisesMessage(InvalidAlgorithm, msg):
            salted_hmac('salt', 'value', algorithm='whatever')


class TestUtilsCryptoPBKDF2(unittest.TestCase):

    # http://tools.ietf.org/html/draft-josefsson-pbkdf2-test-vectors-06
    rfc_vectors = [
        {
            "args": {
                "password": "password",
                "salt": "salt",
                "iterations": 1,
                "dklen": 20,
                "digest": hashlib.sha1,
            },
            "result": "0c60c80f961f0e71f3a9b524af6012062fe037a6",
        },
        {
            "args": {
                "password": "password",
                "salt": "salt",
                "iterations": 2,
                "dklen": 20,
                "digest": hashlib.sha1,
            },
            "result": "ea6c014dc72d6f8ccd1ed92ace1d41f0d8de8957",
        },
        {
            "args": {
                "password": "password",
                "salt": "salt",
                "iterations": 4096,
                "dklen": 20,
                "digest": hashlib.sha1,
            },
            "result": "4b007901b765489abead49d926f721d065a429c1",
        },
        # # this takes way too long :(
        # {
        #     "args": {
        #         "password": "password",
        #         "salt": "salt",
        #         "iterations": 16777216,
        #         "dklen": 20,
        #         "digest": hashlib.sha1,
        #     },
        #     "result": "eefe3d61cd4da4e4e9945b3d6ba2158c2634e984",
        # },
        {
            "args": {
                "password": "passwordPASSWORDpassword",
                "salt": "saltSALTsaltSALTsaltSALTsaltSALTsalt",
                "iterations": 4096,
                "dklen": 25,
                "digest": hashlib.sha1,
            },
            "result": "3d2eec4fe41c849b80c8d83662c0e44a8b291a964cf2f07038",
        },
        {
            "args": {
                "password": "pass\0word",
                "salt": "sa\0lt",
                "iterations": 4096,
                "dklen": 16,
                "digest": hashlib.sha1,
            },
            "result": "56fa6aa75548099dcc37d7f03425e0c3",
        },
    ]

    regression_vectors = [
        {
            "args": {
                "password": "password",
                "salt": "salt",
                "iterations": 1,
                "dklen": 20,
                "digest": hashlib.sha256,
            },
            "result": "120fb6cffcf8b32c43e7225256c4f837a86548c9",
        },
        {
            "args": {
                "password": "password",
                "salt": "salt",
                "iterations": 1,
                "dklen": 20,
                "digest": hashlib.sha512,
            },
            "result": "867f70cf1ade02cff3752599a3a53dc4af34c7a6",
        },
        {
            "args": {
                "password": "password",
                "salt": "salt",
                "iterations": 1000,
                "dklen": 0,
                "digest": hashlib.sha512,
            },
            "result": ("afe6c5530785b6cc6b1c6453384731bd5ee432ee"
                       "549fd42fb6695779ad8a1c5bf59de69c48f774ef"
                       "c4007d5298f9033c0241d5ab69305e7b64eceeb8d"
                       "834cfec"),
        },
        # Check leading zeros are not stripped (#17481)
        {
            "args": {
                "password": b'\xba',
                "salt": "salt",
                "iterations": 1,
                "dklen": 20,
                "digest": hashlib.sha1,
            },
            "result": '0053d3b91a7f1e54effebd6d68771e8a6e0b2c5b',
        },
    ]

    def test_public_vectors(self):
        for vector in self.rfc_vectors:
            result = pbkdf2(**vector['args'])
            self.assertEqual(result.hex(), vector['result'])

    def test_regression_vectors(self):
        for vector in self.regression_vectors:
            result = pbkdf2(**vector['args'])
            self.assertEqual(result.hex(), vector['result'])

    def test_default_hmac_alg(self):
        kwargs = {'password': b'password', 'salt': b'salt', 'iterations': 1, 'dklen': 20}
        self.assertEqual(pbkdf2(**kwargs), hashlib.pbkdf2_hmac(hash_name=hashlib.sha256().name, **kwargs))


class DeprecationTests(SimpleTestCase):
    @ignore_warnings(category=RemovedInDjango40Warning)
    def test_get_random_string(self):
        self.assertEqual(len(get_random_string()), 12)

    def test_get_random_string_warning(self):
        msg = 'Not providing a length argument is deprecated.'
        with self.assertRaisesMessage(RemovedInDjango40Warning, msg):
            get_random_string()
