# -*- coding:utf-8 -*-
from datetime import datetime

from django.test import TestCase
from django.utils import unittest
from django.utils.http import parse_etags, quote_etag, parse_http_date

FULL_RESPONSE = 'Test conditional get response'
LAST_MODIFIED = datetime(2007, 10, 21, 23, 21, 47)
LAST_MODIFIED_STR = 'Sun, 21 Oct 2007 23:21:47 GMT'
LAST_MODIFIED_NEWER_STR = 'Mon, 18 Oct 2010 16:56:23 GMT'
LAST_MODIFIED_INVALID_STR = 'Mon, 32 Oct 2010 16:56:23 GMT'
EXPIRED_LAST_MODIFIED_STR = 'Sat, 20 Oct 2007 23:21:47 GMT'
ETAG = 'b4246ffc4f62314ca13147c9d4f76974'
EXPIRED_ETAG = '7fae4cd4b0f81e7d2914700043aa8ed6'


class ConditionalGet(TestCase):
    def assertFullResponse(self, response, check_last_modified=True, check_etag=True):
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.content, FULL_RESPONSE)
        if check_last_modified:
            self.assertEquals(response['Last-Modified'], LAST_MODIFIED_STR)
        if check_etag:
            self.assertEquals(response['ETag'], '"%s"' % ETAG)

    def assertNotModified(self, response):
        self.assertEquals(response.status_code, 304)
        self.assertEquals(response.content, '')

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
        response = self.client.put('/condition/etag/', {'data': ''})
        self.assertEquals(response.status_code, 200)
        self.client.defaults['HTTP_IF_MATCH'] = '"%s"' % EXPIRED_ETAG
        response = self.client.put('/condition/etag/', {'data': ''})
        self.assertEquals(response.status_code, 412)

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


class ETagProcessing(unittest.TestCase):
    def testParsing(self):
        etags = parse_etags(r'"", "etag", "e\"t\"ag", "e\\tag", W/"weak"')
        self.assertEquals(etags, ['', 'etag', 'e"t"ag', r'e\tag', 'weak'])

    def testQuoting(self):
        quoted_etag = quote_etag(r'e\t"ag')
        self.assertEquals(quoted_etag, r'"e\\t\"ag"')


class HttpDateProcessing(unittest.TestCase):
    def testParsingRfc1123(self):
        parsed = parse_http_date('Sun, 06 Nov 1994 08:49:37 GMT')
        self.assertEqual(datetime.utcfromtimestamp(parsed),
                         datetime(1994, 11, 06, 8, 49, 37))

    def testParsingRfc850(self):
        parsed = parse_http_date('Sunday, 06-Nov-94 08:49:37 GMT')
        self.assertEqual(datetime.utcfromtimestamp(parsed),
                         datetime(1994, 11, 06, 8, 49, 37))

    def testParsingAsctime(self):
        parsed = parse_http_date('Sun Nov  6 08:49:37 1994')
        self.assertEqual(datetime.utcfromtimestamp(parsed),
                         datetime(1994, 11, 06, 8, 49, 37))
