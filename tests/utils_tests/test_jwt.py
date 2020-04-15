from datetime import datetime, timedelta
from unittest import TestCase

from django.utils.jwt import ExpiredToken, JWTFactory


class TestJWT(TestCase):

    def test_secret_param(self):
        default = JWTFactory()
        with_secret = JWTFactory(secret='thisIsASecretKey')
        self.assertNotEqual(
            default.make_token({'iss': 'Django test suite'}),
            with_secret.make_token({'iss': 'Django test suite'})
        )

    def test_token(self):
        default = JWTFactory()
        token = default.make_token({'iss': 'Django test suite'})
        self.assertEqual(token.count('.'), 2)
        decoded = default.decode_token(token)
        self.assertIsInstance(decoded['iat'], int)
        self.assertEqual(decoded['iss'], 'Django test suite')

    def test_bad_payload(self):
        default = JWTFactory()
        with self.assertRaises(TypeError):
            default.make_token('Should not be a string')

    def test_token_validity(self):
        default = JWTFactory()
        token = default.make_token({'iss': 'Django test suite'}, valid_for=timedelta(days=2))
        decoded = default.decode_token(token)
        self.assertEqual(decoded['iss'], 'Django test suite')
        # If token has expired, decode_token raises an ExpiredToken exception.
        token = default.make_token(
            {'iat': int(datetime(2018, 1, 1, 10, 30).timestamp())},
            valid_for=timedelta(days=2)
        )
        with self.assertRaises(ExpiredToken):
            default.decode_token(token)
