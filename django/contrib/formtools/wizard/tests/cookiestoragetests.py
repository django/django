from django.test import TestCase
from django.core import signing
from django.core.exceptions import SuspiciousOperation
from django.http import HttpResponse

from django.contrib.formtools.wizard.storage.cookie import CookieStorage
from django.contrib.formtools.wizard.tests.storagetests import get_request, TestStorage

class TestCookieStorage(TestStorage, TestCase):
    def get_storage(self):
        return CookieStorage

    def test_manipulated_cookie(self):
        request = get_request()
        storage = self.get_storage()('wizard1', request, None)

        cookie_signer = signing.get_cookie_signer(storage.prefix)

        storage.request.COOKIES[storage.prefix] = cookie_signer.sign(
            storage.encoder.encode({'key1': 'value1'}))

        self.assertEqual(storage.load_data(), {'key1': 'value1'})

        storage.request.COOKIES[storage.prefix] = 'i_am_manipulated'
        self.assertRaises(SuspiciousOperation, storage.load_data)

    def test_reset_cookie(self):
        from django.core.signing import SignatureExpired
        request = get_request()
        storage = self.get_storage()('wizard1', request, None)

        storage.data = {'key1': 'value1'}

        response = HttpResponse()
        storage.update_response(response)

        cookie_signer = signing.get_cookie_signer(storage.prefix)
        signed_cookie_data = cookie_signer.sign(storage.encoder.encode(storage.data))

        # signing with different timestamps generates different signatures
        self.assertNotEqual(response.cookies[storage.prefix].value, signed_cookie_data)
        self.assertEqual(cookie_signer.unsign(response.cookies[storage.prefix].value),
                         cookie_signer.unsign(signed_cookie_data))
        self.assertRaises(SignatureExpired,
                          lambda: cookie_signer.unsign(value=response.cookies[storage.prefix].value, max_age=0))
        self.assertEqual(cookie_signer.unsign(value=response.cookies[storage.prefix].value, max_age=10),
                         cookie_signer.unsign(signed_cookie_data))

        storage.init_data()
        storage.update_response(response)
        unsigned_cookie_data = cookie_signer.unsign(response.cookies[storage.prefix].value)
        self.assertEqual(unsigned_cookie_data, '{"step_files":{},"step":null,"extra_data":{},"step_data":{}}')
