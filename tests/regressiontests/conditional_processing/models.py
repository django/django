# -*- coding:utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime

from django.test import TestCase


FULL_RESPONSE = 'Test conditional get response'
LAST_MODIFIED = datetime(2007, 10, 21, 23, 21, 47)
LAST_MODIFIED_STR = 'Sun, 21 Oct 2007 23:21:47 GMT'
LAST_MODIFIED_NEWER_STR = 'Mon, 18 Oct 2010 16:56:23 GMT'
LAST_MODIFIED_INVALID_STR = 'Mon, 32 Oct 2010 16:56:23 GMT'
EXPIRED_LAST_MODIFIED_STR = 'Sat, 20 Oct 2007 23:21:47 GMT'
ETAG = 'b4246ffc4f62314ca13147c9d4f76974'
EXPIRED_ETAG = '7fae4cd4b0f81e7d2914700043aa8ed6'

class ConditionalGet(TestCase):
    urls = 'regressiontests.conditional_processing.urls'

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

    def testWithoutConditions(self):
        response = self.client.get('/condition/')
        self.assertFullResponse(response)

    def testIfModifiedSince(self):
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

    def testIfNoneMatch(self):
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

    def testIfMatch(self):
        self.client.defaults['HTTP_IF_MATCH'] = '"%s"' % ETAG
        response = self.client.put('/condition/etag/')
        self.assertEqual(response.status_code, 200)
        self.client.defaults['HTTP_IF_MATCH'] = '"%s"' % EXPIRED_ETAG
        response = self.client.put('/condition/etag/')
        self.assertEqual(response.status_code, 412)

    def testBothHeaders(self):
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

    def testSingleCondition1(self):
        self.client.defaults['HTTP_IF_MODIFIED_SINCE'] = LAST_MODIFIED_STR
        response = self.client.get('/condition/last_modified/')
        self.assertNotModified(response)
        response = self.client.get('/condition/etag/')
        self.assertFullResponse(response, check_last_modified=False)

    def testSingleCondition2(self):
        self.client.defaults['HTTP_IF_NONE_MATCH'] = '"%s"' % ETAG
        response = self.client.get('/condition/etag/')
        self.assertNotModified(response)
        response = self.client.get('/condition/last_modified/')
        self.assertFullResponse(response, check_etag=False)

    def testSingleCondition3(self):
        self.client.defaults['HTTP_IF_MODIFIED_SINCE'] = EXPIRED_LAST_MODIFIED_STR
        response = self.client.get('/condition/last_modified/')
        self.assertFullResponse(response, check_etag=False)

    def testSingleCondition4(self):
        self.client.defaults['HTTP_IF_NONE_MATCH'] = '"%s"' % EXPIRED_ETAG
        response = self.client.get('/condition/etag/')
        self.assertFullResponse(response, check_last_modified=False)

    def testSingleCondition5(self):
        self.client.defaults['HTTP_IF_MODIFIED_SINCE'] = LAST_MODIFIED_STR
        response = self.client.get('/condition/last_modified2/')
        self.assertNotModified(response)
        response = self.client.get('/condition/etag2/')
        self.assertFullResponse(response, check_last_modified=False)

    def testSingleCondition6(self):
        self.client.defaults['HTTP_IF_NONE_MATCH'] = '"%s"' % ETAG
        response = self.client.get('/condition/etag2/')
        self.assertNotModified(response)
        response = self.client.get('/condition/last_modified2/')
        self.assertFullResponse(response, check_etag=False)

    def testInvalidETag(self):
        self.client.defaults['HTTP_IF_NONE_MATCH'] = r'"\"'
        response = self.client.get('/condition/etag/')
        self.assertFullResponse(response, check_last_modified=False)
