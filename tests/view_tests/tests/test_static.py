from __future__ import absolute_import

import mimetypes
from os import path
import unittest

from django.conf.urls.static import static
from django.http import HttpResponseNotModified
from django.test import TestCase
from django.test.utils import override_settings
from django.utils.http import http_date
from django.views.static import was_modified_since

from .. import urls
from ..urls import media_dir


@override_settings(DEBUG=True)
class StaticTests(TestCase):
    """Tests django views in django/views/static.py"""

    prefix = 'site_media'

    def test_serve(self):
        "The static view can serve static media"
        media_files = ['file.txt', 'file.txt.gz']
        for filename in media_files:
            response = self.client.get('/views/%s/%s' % (self.prefix, filename))
            response_content = b''.join(response)
            file_path = path.join(media_dir, filename)
            with open(file_path, 'rb') as fp:
                self.assertEqual(fp.read(), response_content)
            self.assertEqual(len(response_content), int(response['Content-Length']))
            self.assertEqual(mimetypes.guess_type(file_path)[1], response.get('Content-Encoding', None))

    def test_unknown_mime_type(self):
        response = self.client.get('/views/%s/file.unknown' % self.prefix)
        self.assertEqual('application/octet-stream', response['Content-Type'])

    def test_copes_with_empty_path_component(self):
        file_name = 'file.txt'
        response = self.client.get('/views/%s//%s' % (self.prefix, file_name))
        response_content = b''.join(response)
        with open(path.join(media_dir, file_name), 'rb') as fp:
            self.assertEqual(fp.read(), response_content)

    def test_is_modified_since(self):
        file_name = 'file.txt'
        response = self.client.get('/views/%s/%s' % (self.prefix, file_name),
            HTTP_IF_MODIFIED_SINCE='Thu, 1 Jan 1970 00:00:00 GMT')
        response_content = b''.join(response)
        with open(path.join(media_dir, file_name), 'rb') as fp:
            self.assertEqual(fp.read(), response_content)

    def test_not_modified_since(self):
        file_name = 'file.txt'
        response = self.client.get(
            '/views/%s/%s' % (self.prefix, file_name),
            HTTP_IF_MODIFIED_SINCE='Mon, 18 Jan 2038 05:14:07 GMT'
            # This is 24h before max Unix time. Remember to fix Django and
            # update this test well before 2038 :)
            )
        self.assertIsInstance(response, HttpResponseNotModified)

    def test_invalid_if_modified_since(self):
        """Handle bogus If-Modified-Since values gracefully

        Assume that a file is modified since an invalid timestamp as per RFC
        2616, section 14.25.
        """
        file_name = 'file.txt'
        invalid_date = 'Mon, 28 May 999999999999 28:25:26 GMT'
        response = self.client.get('/views/%s/%s' % (self.prefix, file_name),
                                   HTTP_IF_MODIFIED_SINCE=invalid_date)
        response_content = b''.join(response)
        with open(path.join(media_dir, file_name), 'rb') as fp:
            self.assertEqual(fp.read(), response_content)
        self.assertEqual(len(response_content),
                          int(response['Content-Length']))

    def test_invalid_if_modified_since2(self):
        """Handle even more bogus If-Modified-Since values gracefully

        Assume that a file is modified since an invalid timestamp as per RFC
        2616, section 14.25.
        """
        file_name = 'file.txt'
        invalid_date = ': 1291108438, Wed, 20 Oct 2010 14:05:00 GMT'
        response = self.client.get('/views/%s/%s' % (self.prefix, file_name),
                                   HTTP_IF_MODIFIED_SINCE=invalid_date)
        response_content = b''.join(response)
        with open(path.join(media_dir, file_name), 'rb') as fp:
            self.assertEqual(fp.read(), response_content)
        self.assertEqual(len(response_content),
                          int(response['Content-Length']))


class StaticHelperTest(StaticTests):
    """
    Test case to make sure the static URL pattern helper works as expected
    """
    def setUp(self):
        super(StaticHelperTest, self).setUp()
        self._old_views_urlpatterns = urls.urlpatterns[:]
        urls.urlpatterns += static('/media/', document_root=media_dir)

    def tearDown(self):
        super(StaticHelperTest, self).tearDown()
        urls.urlpatterns = self._old_views_urlpatterns


class StaticUtilsTests(unittest.TestCase):
    def test_was_modified_since_fp(self):
        """
        Test that a floating point mtime does not disturb was_modified_since.
        (#18675)
        """
        mtime = 1343416141.107817
        header = http_date(mtime)
        self.assertFalse(was_modified_since(header, mtime))
