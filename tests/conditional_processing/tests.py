# -*- coding:utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime

from django.test import SimpleTestCase, override_settings

FULL_RESPONSE = 'Test conditional get response'
LAST_MODIFIED = datetime(2007, 10, 21, 23, 21, 47)
LAST_MODIFIED_STR = 'Sun, 21 Oct 2007 23:21:47 GMT'
LAST_MODIFIED_NEWER_STR = 'Mon, 18 Oct 2010 16:56:23 GMT'
LAST_MODIFIED_INVALID_STR = 'Mon, 32 Oct 2010 16:56:23 GMT'
EXPIRED_LAST_MODIFIED_STR = 'Sat, 20 Oct 2007 23:21:47 GMT'
ETAG = '"b4246ffc4f62314ca13147c9d4f76974"'
WEAK_ETAG = 'W/"b4246ffc4f62314ca13147c9d4f76974"'  # weak match to ETAG
EXPIRED_ETAG = '"7fae4cd4b0f81e7d2914700043aa8ed6"'


@override_settings(ROOT_URLCONF='conditional_processing.urls')
class ConditionalGet(SimpleTestCase):

    def assertFullResponse(self, response, check_last_modified=True, check_etag=True):
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, FULL_RESPONSE.encode())
        if check_last_modified:
            self.assertEqual(response['Last-Modified'], LAST_MODIFIED_STR)
        if check_etag:
            self.assertEqual(response['ETag'], ETAG)

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
        response = self.client.put('/condition/')
        self.assertFullResponse(response)
        self.client.defaults['HTTP_IF_MODIFIED_SINCE'] = LAST_MODIFIED_NEWER_STR
        response = self.client.get('/condition/')
        self.assertNotModified(response)
        response = self.client.put('/condition/')
        self.assertFullResponse(response)
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
        self.client.defaults['HTTP_IF_NONE_MATCH'] = ETAG
        response = self.client.get('/condition/')
        self.assertNotModified(response)
        response = self.client.put('/condition/')
        self.assertEqual(response.status_code, 412)
        self.client.defaults['HTTP_IF_NONE_MATCH'] = EXPIRED_ETAG
        response = self.client.get('/condition/')
        self.assertFullResponse(response)

        # Several etags in If-None-Match is a bit exotic but why not?
        self.client.defaults['HTTP_IF_NONE_MATCH'] = '%s, %s' % (ETAG, EXPIRED_ETAG)
        response = self.client.get('/condition/')
        self.assertNotModified(response)

    def test_weak_if_none_match(self):
        """
        If-None-Match comparisons use weak matching, so weak and strong ETags
        with the same value result in a 304 response.
        """
        self.client.defaults['HTTP_IF_NONE_MATCH'] = ETAG
        response = self.client.get('/condition/weak_etag/')
        self.assertNotModified(response)
        response = self.client.put('/condition/weak_etag/')
        self.assertEqual(response.status_code, 412)

        self.client.defaults['HTTP_IF_NONE_MATCH'] = WEAK_ETAG
        response = self.client.get('/condition/weak_etag/')
        self.assertNotModified(response)
        response = self.client.put('/condition/weak_etag/')
        self.assertEqual(response.status_code, 412)
        response = self.client.get('/condition/')
        self.assertNotModified(response)
        response = self.client.put('/condition/')
        self.assertEqual(response.status_code, 412)

    def test_all_if_none_match(self):
        self.client.defaults['HTTP_IF_NONE_MATCH'] = '*'
        response = self.client.get('/condition/')
        self.assertNotModified(response)
        response = self.client.put('/condition/')
        self.assertEqual(response.status_code, 412)
        response = self.client.get('/condition/no_etag/')
        self.assertFullResponse(response, check_last_modified=False, check_etag=False)

    def test_if_match(self):
        self.client.defaults['HTTP_IF_MATCH'] = ETAG
        response = self.client.put('/condition/')
        self.assertFullResponse(response)
        self.client.defaults['HTTP_IF_MATCH'] = EXPIRED_ETAG
        response = self.client.put('/condition/')
        self.assertEqual(response.status_code, 412)

    def test_weak_if_match(self):
        """
        If-Match comparisons use strong matching, so any comparison involving
        a weak ETag return a 412 response.
        """
        self.client.defaults['HTTP_IF_MATCH'] = ETAG
        response = self.client.get('/condition/weak_etag/')
        self.assertEqual(response.status_code, 412)

        self.client.defaults['HTTP_IF_MATCH'] = WEAK_ETAG
        response = self.client.get('/condition/weak_etag/')
        self.assertEqual(response.status_code, 412)
        response = self.client.get('/condition/')
        self.assertEqual(response.status_code, 412)

    def test_all_if_match(self):
        self.client.defaults['HTTP_IF_MATCH'] = '*'
        response = self.client.get('/condition/')
        self.assertFullResponse(response)
        response = self.client.get('/condition/no_etag/')
        self.assertEqual(response.status_code, 412)

    def test_both_headers(self):
        # see https://tools.ietf.org/html/rfc7232#section-6
        self.client.defaults['HTTP_IF_MODIFIED_SINCE'] = LAST_MODIFIED_STR
        self.client.defaults['HTTP_IF_NONE_MATCH'] = ETAG
        response = self.client.get('/condition/')
        self.assertNotModified(response)

        self.client.defaults['HTTP_IF_MODIFIED_SINCE'] = EXPIRED_LAST_MODIFIED_STR
        self.client.defaults['HTTP_IF_NONE_MATCH'] = ETAG
        response = self.client.get('/condition/')
        self.assertNotModified(response)

        self.client.defaults['HTTP_IF_MODIFIED_SINCE'] = LAST_MODIFIED_STR
        self.client.defaults['HTTP_IF_NONE_MATCH'] = EXPIRED_ETAG
        response = self.client.get('/condition/')
        self.assertFullResponse(response)

        self.client.defaults['HTTP_IF_MODIFIED_SINCE'] = EXPIRED_LAST_MODIFIED_STR
        self.client.defaults['HTTP_IF_NONE_MATCH'] = EXPIRED_ETAG
        response = self.client.get('/condition/')
        self.assertFullResponse(response)

    def test_both_headers_2(self):
        self.client.defaults['HTTP_IF_UNMODIFIED_SINCE'] = LAST_MODIFIED_STR
        self.client.defaults['HTTP_IF_MATCH'] = ETAG
        response = self.client.get('/condition/')
        self.assertFullResponse(response)

        self.client.defaults['HTTP_IF_UNMODIFIED_SINCE'] = EXPIRED_LAST_MODIFIED_STR
        self.client.defaults['HTTP_IF_MATCH'] = ETAG
        response = self.client.get('/condition/')
        self.assertFullResponse(response)

        self.client.defaults['HTTP_IF_UNMODIFIED_SINCE'] = EXPIRED_LAST_MODIFIED_STR
        self.client.defaults['HTTP_IF_MATCH'] = EXPIRED_ETAG
        response = self.client.get('/condition/')
        self.assertEqual(response.status_code, 412)

        self.client.defaults['HTTP_IF_UNMODIFIED_SINCE'] = LAST_MODIFIED_STR
        self.client.defaults['HTTP_IF_MATCH'] = EXPIRED_ETAG
        response = self.client.get('/condition/')
        self.assertEqual(response.status_code, 412)

    def test_single_condition_1(self):
        self.client.defaults['HTTP_IF_MODIFIED_SINCE'] = LAST_MODIFIED_STR
        response = self.client.get('/condition/last_modified/')
        self.assertNotModified(response)
        response = self.client.get('/condition/etag/')
        self.assertFullResponse(response, check_last_modified=False)

    def test_single_condition_2(self):
        self.client.defaults['HTTP_IF_NONE_MATCH'] = ETAG
        response = self.client.get('/condition/etag/')
        self.assertNotModified(response)
        response = self.client.get('/condition/last_modified/')
        self.assertFullResponse(response, check_etag=False)

    def test_single_condition_3(self):
        self.client.defaults['HTTP_IF_MODIFIED_SINCE'] = EXPIRED_LAST_MODIFIED_STR
        response = self.client.get('/condition/last_modified/')
        self.assertFullResponse(response, check_etag=False)

    def test_single_condition_4(self):
        self.client.defaults['HTTP_IF_NONE_MATCH'] = EXPIRED_ETAG
        response = self.client.get('/condition/etag/')
        self.assertFullResponse(response, check_last_modified=False)

    def test_single_condition_5(self):
        self.client.defaults['HTTP_IF_MODIFIED_SINCE'] = LAST_MODIFIED_STR
        response = self.client.get('/condition/last_modified2/')
        self.assertNotModified(response)
        response = self.client.get('/condition/etag2/')
        self.assertFullResponse(response, check_last_modified=False)

    def test_single_condition_6(self):
        self.client.defaults['HTTP_IF_NONE_MATCH'] = ETAG
        response = self.client.get('/condition/etag2/')
        self.assertNotModified(response)
        response = self.client.get('/condition/last_modified2/')
        self.assertFullResponse(response, check_etag=False)

    def test_single_condition_7(self):
        self.client.defaults['HTTP_IF_UNMODIFIED_SINCE'] = EXPIRED_LAST_MODIFIED_STR
        response = self.client.get('/condition/last_modified/')
        self.assertEqual(response.status_code, 412)
        response = self.client.get('/condition/etag/')
        self.assertEqual(response.status_code, 412)

    def test_single_condition_8(self):
        self.client.defaults['HTTP_IF_UNMODIFIED_SINCE'] = LAST_MODIFIED_STR
        response = self.client.get('/condition/last_modified/')
        self.assertFullResponse(response, check_etag=False)

    def test_single_condition_9(self):
        self.client.defaults['HTTP_IF_UNMODIFIED_SINCE'] = EXPIRED_LAST_MODIFIED_STR
        response = self.client.get('/condition/last_modified2/')
        self.assertEqual(response.status_code, 412)
        response = self.client.get('/condition/etag2/')
        self.assertEqual(response.status_code, 412)

    def test_single_condition_head(self):
        self.client.defaults['HTTP_IF_MODIFIED_SINCE'] = LAST_MODIFIED_STR
        response = self.client.head('/condition/')
        self.assertNotModified(response)

    def test_unquoted(self):
        """
        The same quoted ETag should be set on the header regardless of whether
        etag_func() in condition() returns a quoted or an unquoted ETag.
        """
        response_quoted = self.client.get('/condition/etag/')
        response_unquoted = self.client.get('/condition/unquoted_etag/')
        self.assertEqual(response_quoted['ETag'], response_unquoted['ETag'])

    # It's possible that the matching algorithm could use the wrong value even
    # if the ETag header is set correctly correctly (as tested by
    # test_unquoted()), so check that the unquoted value is matched.
    def test_unquoted_if_none_match(self):
        self.client.defaults['HTTP_IF_NONE_MATCH'] = ETAG
        response = self.client.get('/condition/unquoted_etag/')
        self.assertNotModified(response)
        response = self.client.put('/condition/unquoted_etag/')
        self.assertEqual(response.status_code, 412)
        self.client.defaults['HTTP_IF_NONE_MATCH'] = EXPIRED_ETAG
        response = self.client.get('/condition/unquoted_etag/')
        self.assertFullResponse(response, check_last_modified=False)

    def test_invalid_etag(self):
        self.client.defaults['HTTP_IF_NONE_MATCH'] = '"""'
        response = self.client.get('/condition/etag/')
        self.assertFullResponse(response, check_last_modified=False)
