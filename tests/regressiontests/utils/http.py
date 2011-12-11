from django.utils import http
from django.utils import unittest
from django.http import HttpResponse, utils
from django.test import RequestFactory

class TestUtilsHttp(unittest.TestCase):

    def test_same_origin_true(self):
        # Identical
        self.assertTrue(http.same_origin('http://foo.com/', 'http://foo.com/'))
        # One with trailing slash - see #15617
        self.assertTrue(http.same_origin('http://foo.com', 'http://foo.com/'))
        self.assertTrue(http.same_origin('http://foo.com/', 'http://foo.com'))
        # With port
        self.assertTrue(http.same_origin('https://foo.com:8000', 'https://foo.com:8000/'))

    def test_same_origin_false(self):
        # Different scheme
        self.assertFalse(http.same_origin('http://foo.com', 'https://foo.com'))
        # Different host
        self.assertFalse(http.same_origin('http://foo.com', 'http://goo.com'))
        # Different host again
        self.assertFalse(http.same_origin('http://foo.com', 'http://foo.com.evil.com'))
        # Different port
        self.assertFalse(http.same_origin('http://foo.com:8000', 'http://foo.com:8001'))

    def test_fix_IE_for_vary(self):
        """
        Regression for #16632.

        `fix_IE_for_vary` shouldn't crash when there's no Content-Type header.
        """

        # functions to generate responses
        def response_with_unsafe_content_type():
            r = HttpResponse(content_type="text/unsafe")
            r['Vary'] = 'Cookie'
            return r

        def no_content_response_with_unsafe_content_type():
            # 'Content-Type' always defaulted, so delete it
            r = response_with_unsafe_content_type()
            del r['Content-Type']
            return r

        # request with & without IE user agent
        rf = RequestFactory()
        request = rf.get('/')
        ie_request = rf.get('/', HTTP_USER_AGENT='MSIE')

        # not IE, unsafe_content_type
        response = response_with_unsafe_content_type()
        utils.fix_IE_for_vary(request, response)
        self.assertTrue('Vary' in response)

        # IE, unsafe_content_type
        response = response_with_unsafe_content_type()
        utils.fix_IE_for_vary(ie_request, response)
        self.assertFalse('Vary' in response)

        # not IE, no_content
        response = no_content_response_with_unsafe_content_type()
        utils.fix_IE_for_vary(request, response)
        self.assertTrue('Vary' in response)

        # IE, no_content
        response = no_content_response_with_unsafe_content_type()
        utils.fix_IE_for_vary(ie_request, response)
        self.assertFalse('Vary' in response)


