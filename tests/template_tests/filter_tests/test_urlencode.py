from django.test import SimpleTestCase

from ..utils import render, setup


class UrlencodeTests(SimpleTestCase):

    @setup({'urlencode01': '{{ url|urlencode }}'})
    def test_urlencode01(self):
        output = render('urlencode01', {'url': '/test&"/me?/'})
        self.assertEqual(output, '/test%26%22/me%3F/')

    @setup({'urlencode02': '/test/{{ urlbit|urlencode:"" }}/'})
    def test_urlencode02(self):
        output = render('urlencode02', {'urlbit': 'escape/slash'})
        self.assertEqual(output, '/test/escape%2Fslash/')
