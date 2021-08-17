from django.http import HttpRequest
from django.template.context_processors import csrf
from django.test import SimpleTestCase

from .tests import CsrfFunctionTestMixin


class TestContextProcessor(CsrfFunctionTestMixin, SimpleTestCase):

    def test_force_token_to_string(self):
        request = HttpRequest()
        test_token = '1bcdefghij2bcdefghij3bcdefghij4bcdefghij5bcdefghij6bcdefghijABCD'
        request.META['CSRF_COOKIE'] = test_token
        token = csrf(request).get('csrf_token')
        self.assertMaskedSecretCorrect(token, 'lcccccccX2kcccccccY2jcccccccssIC')
