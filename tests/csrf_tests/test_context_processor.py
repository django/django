import json

from django.http import HttpRequest
from django.template.context_processors import csrf
from django.test import SimpleTestCase
from django.utils.encoding import force_text


class TestContextProcessor(SimpleTestCase):

    def test_force_text_on_token(self):
        request = HttpRequest()
        request.META['CSRF_COOKIE'] = 'test-token'
        token = csrf(request).get('csrf_token')
        self.assertEqual(json.dumps(force_text(token)), '"test-token"')
