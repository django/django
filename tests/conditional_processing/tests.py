# -*- coding:utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime

from django.test import TestCase, override_settings

FULL_RESPONSE = 'Test conditional get response'
LAST_MODIFIED = datetime(2007, 10, 21, 23, 21, 47)
LAST_MODIFIED_STR = 'Sun, 21 Oct 2007 23:21:47 GMT'
LAST_MODIFIED_NEWER_STR = 'Mon, 18 Oct 2010 16:56:23 GMT'
LAST_MODIFIED_INVALID_STR = 'Mon, 32 Oct 2010 16:56:23 GMT'
EXPIRED_LAST_MODIFIED_STR = 'Sat, 20 Oct 2007 23:21:47 GMT'
ETAG = 'b4246ffc4f62314ca13147c9d4f76974'
EXPIRED_ETAG = '7fae4cd4b0f81e7d2914700043aa8ed6'


@override_settings(ROOT_URLCONF='conditional_processing.urls')
class ConditionalGet(TestCase):

    def assertFullResponse(self, response, check_last_modified=True, check_etag=True):
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, FULL_RESPONSE.encode())
        if check_last_modified:
            self.assertEqual(response['Last-Modified'], LAST_MODIFIED_STR)
        if check_etag:
            self.assertEqual(response['ETag'], '"%s"' % ETAG)

    def assertNotModified(self, response):
        self.assertEqual(response.status_code, 304)
        self.assertEqual(response.content, b'')

    def test_without_conditions(self):
        response = self.client.get('/condition/')
        self.assertFullResponse(response)

    def test_if_modified_since(self):
        self.client.defaults['HTTP_IF_MODIFIED_SINCE'] = LAST_MODIFIED_STR
        response = self.client.get('/condition/')
        self.assertNotModified(response)
        self.client.defaults['HTTP_IF_MODIFIED_SINCE'] = LAST_MODIFIED_NEWER_STR
        response = self.client.get('/condition/')
        self.assertNotModified(response)
        self.client.defaults['HTTP_IF_MODIFIED_SINCE'] = LAST_MODIFIED_INVALID_STR
        response = self.client.get('/condition/')
        self.assertFullResponse(response)
        self.client.defaults['HTTP_IF_MODIFIED_SINCE'] = EXPIRED_LAST_MODIFIED_STR
        response = self.client.get('/condition/')
        self.assertFullResponse(response)

    def test_if_unmodified_since(self):
        self.client.defaults['HTTP_IF_UNMODIFIED_SINCE'] = LAST_MODIFIED_STR
        response = self.client.get('/condition/')
        self.assertFullResponse(response)
        self.client.defaults['HTTP_IF_UNMODIFIED_SINCE'] = LAST_MODIFIED_NEWER_STR
        response = self.client.get('/condition/')
        self.assertFullResponse(response)
        self.client.defaults['HTTP_IF_UNMODIFIED_SINCE'] = LAST_MODIFIED_INVALID_STR
        response = self.client.get('/condition/')
        self.assertFullResponse(response)
        self.client.defaults['HTTP_IF_UNMODIFIED_SINCE'] = EXPIRED_LAST_MODIFIED_STR
        response = self.client.get('/condition/')
        self.assertEqual(response.status_code, 412)

    def test_if_none_match(self):
        self.client.defaults['HTTP_IF_NONE_MATCH'] = '"%s"' % ETAG
        response = self.client.get('/condition/')
        self.assertNotModified(response)
        self.client.defaults['HTTP_IF_NONE_MATCH'] = '"%s"' % EXPIRED_ETAG
        response = self.client.get('/condition/')
        self.assertFullResponse(response)

        # Several etags in If-None-Match is a bit exotic but why not?
        self.client.defaults['HTTP_IF_NONE_MATCH'] = '"%s", "%s"' % (ETAG, EXPIRED_ETAG)
        response = self.client.get('/condition/')
        self.assertNotModified(response)

    def test_if_match(self):
        self.client.defaults['HTTP_IF_MATCH'] = '"%s"' % ETAG
        response = self.client.put('/condition/etag/')
        self.assertEqual(response.status_code, 200)
        self.client.defaults['HTTP_IF_MATCH'] = '"%s"' % EXPIRED_ETAG
        response = self.client.put('/condition/etag/')
        self.assertEqual(response.status_code, 412)

    def test_both_headers(self):
        # see http://www.w3.org/Protocols/rfc2616/rfc2616-sec13.html#sec13.3.4
        self.client.defaults['HTTP_IF_MODIFIED_SINCE'] = LAST_MODIFIED_STR
        self.client.defaults['HTTP_IF_NONE_MATCH'] = '"%s"' % ETAG
        response = self.client.get('/condition/')
        self.assertNotModified(response)

        self.client.defaults['HTTP_IF_MODIFIED_SINCE'] = EXPIRED_LAST_MODIFIED_STR
        self.client.defaults['HTTP_IF_NONE_MATCH'] = '"%s"' % ETAG
        response = self.client.get('/condition/')
        self.assertFullResponse(response)

        self.client.defaults['HTTP_IF_MODIFIED_SINCE'] = LAST_MODIFIED_STR
        self.client.defaults['HTTP_IF_NONE_MATCH'] = '"%s"' % EXPIRED_ETAG
        response = self.client.get('/condition/')
        self.assertFullResponse(response)

        self.client.defaults['HTTP_IF_MODIFIED_SINCE'] = EXPIRED_LAST_MODIFIED_STR
        self.client.defaults['HTTP_IF_NONE_MATCH'] = '"%s"' % EXPIRED_ETAG
        response = self.client.get('/condition/')
        self.assertFullResponse(response)

    def test_both_headers_2(self):
        self.client.defaults['HTTP_IF_UNMODIFIED_SINCE'] = LAST_MODIFIED_STR
        self.client.defaults['HTTP_IF_MATCH'] = '"%s"' % ETAG
        response = self.client.get('/condition/')
        self.assertFullResponse(response)

        self.client.defaults['HTTP_IF_UNMODIFIED_SINCE'] = EXPIRED_LAST_MODIFIED_STR
        self.client.defaults['HTTP_IF_MATCH'] = '"%s"' % EXPIRED_ETAG
        response = self.client.get('/condition/')
        self.assertEqual(response.status_code, 412)

        self.client.defaults['HTTP_IF_UNMODIFIED_SINCE'] = LAST_MODIFIED_STR
        self.client.defaults['HTTP_IF_MATCH'] = '"%s"' % EXPIRED_ETAG
        response = self.client.get('/condition/')
        self.assertEqual(response.status_code, 412)

        self.client.defaults['HTTP_IF_UNMODIFIED_SINCE'] = EXPIRED_LAST_MODIFIED_STR
        self.client.defaults['HTTP_IF_MATCH'] = '"%s"' % ETAG
        response = self.client.get('/condition/')
        self.assertEqual(response.status_code, 412)

    def test_single_condition_1(self):
        self.client.defaults['HTTP_IF_MODIFIED_SINCE'] = LAST_MODIFIED_STR
        response = self.client.get('/condition/last_modified/')
        self.assertNotModified(response)
        response = self.client.get('/condition/etag/')
        self.assertFullResponse(response, check_last_modified=False)

    def test_single_condition_2(self):
        self.client.defaults['HTTP_IF_NONE_MATCH'] = '"%s"' % ETAG
        response = self.client.get('/condition/etag/')
        self.assertNotModified(response)
        response = self.client.get('/condition/last_modified/')
        self.assertFullResponse(response, check_etag=False)

    def test_single_condition_3(self):
        self.client.defaults['HTTP_IF_MODIFIED_SINCE'] = EXPIRED_LAST_MODIFIED_STR
        response = self.client.get('/condition/last_modified/')
        self.assertFullResponse(response, check_etag=False)

    def test_single_condition_4(self):
        self.client.defaults['HTTP_IF_NONE_MATCH'] = '"%s"' % EXPIRED_ETAG
        response = self.client.get('/condition/etag/')
        self.assertFullResponse(response, check_last_modified=False)

    def test_single_condition_5(self):
        self.client.defaults['HTTP_IF_MODIFIED_SINCE'] = LAST_MODIFIED_STR
        response = self.client.get('/condition/last_modified2/')
        self.assertNotModified(response)
        response = self.client.get('/condition/etag2/')
        self.assertFullResponse(response, check_last_modified=False)

    def test_single_condition_6(self):
        self.client.defaults['HTTP_IF_NONE_MATCH'] = '"%s"' % ETAG
        response = self.client.get('/condition/etag2/')
        self.assertNotModified(response)
        response = self.client.get('/condition/last_modified2/')
        self.assertFullResponse(response, check_etag=False)

    def test_single_condition_7(self):
        self.client.defaults['HTTP_IF_UNMODIFIED_SINCE'] = EXPIRED_LAST_MODIFIED_STR
        response = self.client.get('/condition/last_modified/')
        self.assertEqual(response.status_code, 412)
        response = self.client.get('/condition/etag/')
        self.assertFullResponse(response, check_last_modified=False)

    def test_single_condition_8(self):
        self.client.defaults['HTTP_IF_UNMODIFIED_SINCE'] = LAST_MODIFIED_STR
        response = self.client.get('/condition/last_modified/')
        self.assertFullResponse(response, check_etag=False)

    def test_single_condition_9(self):
        self.client.defaults['HTTP_IF_UNMODIFIED_SINCE'] = EXPIRED_LAST_MODIFIED_STR
        response = self.client.get('/condition/last_modified2/')
        self.assertEqual(response.status_code, 412)
        response = self.client.get('/condition/etag2/')
        self.assertFullResponse(response, check_last_modified=False)

    def test_single_condition_head(self):
        self.client.defaults['HTTP_IF_MODIFIED_SINCE'] = LAST_MODIFIED_STR
        response = self.client.head('/condition/')
        self.assertNotModified(response)

    def test_invalid_etag(self):
        self.client.defaults['HTTP_IF_NONE_MATCH'] = r'"\"'
        response = self.client.get('/condition/etag/')
        self.assertFullResponse(response, check_last_modified=False)
