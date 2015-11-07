from django.http import HttpRequest
from django.middleware.csrf import _compare_salted_tokens as equivalent_tokens
from django.template.context_processors import csrf
from django.test import SimpleTestCase
from django.utils.encoding import force_text


class TestContextProcessor(SimpleTestCase):

    def test_force_text_on_token(self):
        request = HttpRequest()
        test_token = '1bcdefghij2bcdefghij3bcdefghij4bcdefghij5bcdefghij6bcdefghijABCD'
        request.META['CSRF_COOKIE'] = test_token
        token = csrf(request).get('csrf_token')
        self.assertTrue(equivalent_tokens(force_text(token), test_token))
