
import math
import timeit
import hashlib

from django.utils import unittest
from django.utils.crypto import pbkdf2


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
                "password": chr(186), 
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
            self.assertEqual(result.encode('hex'), vector['result'])

    def test_regression_vectors(self):
        for vector in self.regression_vectors:
            result = pbkdf2(**vector['args'])
            self.assertEqual(result.encode('hex'), vector['result'])

    def test_performance_scalability(self):
        """
        Theory: If you run with 100 iterations, it should take 100
        times as long as running with 1 iteration.
        """
        # These values are chosen as a reasonable tradeoff between time
        # to run the test suite and false positives caused by imprecise
        # measurement.
        n1, n2 = 200000, 800000
        elapsed = lambda f: timeit.Timer(f, 
                    'from django.utils.crypto import pbkdf2').timeit(number=1)
        t1 = elapsed('pbkdf2("password", "salt", iterations=%d)' % n1)
        t2 = elapsed('pbkdf2("password", "salt", iterations=%d)' % n2)
        measured_scale_exponent = math.log(t2 / t1, n2 / n1)
        # This should be less than 1. We allow up to 1.2 so that tests don't 
        # fail nondeterministically too often.
        self.assertLess(measured_scale_exponent, 1.2)
