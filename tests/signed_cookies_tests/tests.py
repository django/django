from __future__ import unicode_literals

import time

from django.core import signing
from django.http import HttpRequest, HttpResponse
from django.test import TestCase


class SignedCookieTest(TestCase):

    def test_can_set_and_read_signed_cookies(self):
        response = HttpResponse()
        response.set_signed_cookie('c', 'hello')
        self.assertIn('c', response.cookies)
        self.assertTrue(response.cookies['c'].value.startswith('hello:'))
        request = HttpRequest()
        request.COOKIES['c'] = response.cookies['c'].value
        value = request.get_signed_cookie('c')
        self.assertEqual(value, 'hello')

    def test_can_use_salt(self):
        response = HttpResponse()
        response.set_signed_cookie('a', 'hello', salt='one')
        request = HttpRequest()
        request.COOKIES['a'] = response.cookies['a'].value
        value = request.get_signed_cookie('a', salt='one')
        self.assertEqual(value, 'hello')
        self.assertRaises(signing.BadSignature,
            request.get_signed_cookie, 'a', salt='two')

    def test_detects_tampering(self):
        response = HttpResponse()
        response.set_signed_cookie('c', 'hello')
        request = HttpRequest()
        request.COOKIES['c'] = response.cookies['c'].value[:-2] + '$$'
        self.assertRaises(signing.BadSignature,
            request.get_signed_cookie, 'c')

    def test_default_argument_supresses_exceptions(self):
        response = HttpResponse()
        response.set_signed_cookie('c', 'hello')
        request = HttpRequest()
        request.COOKIES['c'] = response.cookies['c'].value[:-2] + '$$'
        self.assertEqual(request.get_signed_cookie('c', default=None), None)

    def test_max_age_argument(self):
        value = 'hello'
        _time = time.time
        time.time = lambda: 123456789
        try:
            response = HttpResponse()
            response.set_signed_cookie('c', value)
            request = HttpRequest()
            request.COOKIES['c'] = response.cookies['c'].value
            self.assertEqual(request.get_signed_cookie('c'), value)

            time.time = lambda: 123456800
            self.assertEqual(request.get_signed_cookie('c', max_age=12), value)
            self.assertEqual(request.get_signed_cookie('c', max_age=11), value)
            self.assertRaises(signing.SignatureExpired,
                request.get_signed_cookie, 'c', max_age = 10)
        finally:
            time.time = _time
