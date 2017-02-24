import mimetypes
import unittest
from os import path

from django.conf.urls.static import static
from django.core.exceptions import ImproperlyConfigured
from django.http import FileResponse, HttpResponseNotModified
from django.test import SimpleTestCase, override_settings
from django.utils.http import http_date
from django.views.static import was_modified_since

from .. import urls
from ..urls import media_dir


@override_settings(DEBUG=True, ROOT_URLCONF='view_tests.urls')
class StaticTests(SimpleTestCase):
    """Tests django views in django/views/static.py"""

    prefix = 'site_media'

    def test_serve(self):
        "The static view can serve static media"
        media_files = ['file.txt', 'file.txt.gz']
        for filename in media_files:
            response = self.client.get('/%s/%s' % (self.prefix, filename))
            response_content = b''.join(response)
            file_path = path.join(media_dir, filename)
            with open(file_path, 'rb') as fp:
                self.assertEqual(fp.read(), response_content)
            self.assertEqual(len(response_content), int(response['Content-Length']))
            self.assertEqual(mimetypes.guess_type(file_path)[1], response.get('Content-Encoding', None))

    def test_chunked(self):
        "The static view should stream files in chunks to avoid large memory usage"
        response = self.client.get('/%s/%s' % (self.prefix, 'long-line.txt'))
        first_chunk = next(response.streaming_content)
        self.assertEqual(len(first_chunk), FileResponse.block_size)
        second_chunk = next(response.streaming_content)
        response.close()
        # strip() to prevent OS line endings from causing differences
        self.assertEqual(len(second_chunk.strip()), 1449)

    def test_unknown_mime_type(self):
        response = self.client.get('/%s/file.unknown' % self.prefix)
        self.assertEqual('application/octet-stream', response['Content-Type'])
        response.close()

    def test_copes_with_empty_path_component(self):
        file_name = 'file.txt'
        response = self.client.get('/%s//%s' % (self.prefix, file_name))
        response_content = b''.join(response)
        with open(path.join(media_dir, file_name), 'rb') as fp:
            self.assertEqual(fp.read(), response_content)

    def test_is_modified_since(self):
        file_name = 'file.txt'
        response = self.client.get(
            '/%s/%s' % (self.prefix, file_name),
            HTTP_IF_MODIFIED_SINCE='Thu, 1 Jan 1970 00:00:00 GMT'
        )
        response_content = b''.join(response)
        with open(path.join(media_dir, file_name), 'rb') as fp:
            self.assertEqual(fp.read(), response_content)

    def test_not_modified_since(self):
        file_name = 'file.txt'
        response = self.client.get(
            '/%s/%s' % (self.prefix, file_name),
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
        response = self.client.get('/%s/%s' % (self.prefix, file_name),
                                   HTTP_IF_MODIFIED_SINCE=invalid_date)
        response_content = b''.join(response)
        with open(path.join(media_dir, file_name), 'rb') as fp:
            self.assertEqual(fp.read(), response_content)
        self.assertEqual(len(response_content), int(response['Content-Length']))

    def test_invalid_if_modified_since2(self):
        """Handle even more bogus If-Modified-Since values gracefully

        Assume that a file is modified since an invalid timestamp as per RFC
        2616, section 14.25.
        """
        file_name = 'file.txt'
        invalid_date = ': 1291108438, Wed, 20 Oct 2010 14:05:00 GMT'
        response = self.client.get('/%s/%s' % (self.prefix, file_name),
                                   HTTP_IF_MODIFIED_SINCE=invalid_date)
        response_content = b''.join(response)
        with open(path.join(media_dir, file_name), 'rb') as fp:
            self.assertEqual(fp.read(), response_content)
        self.assertEqual(len(response_content), int(response['Content-Length']))

    def test_404(self):
        response = self.client.get('/%s/nonexistent_resource' % self.prefix)
        self.assertEqual(404, response.status_code)

    def test_index(self):
        response = self.client.get('/%s/' % self.prefix)
        self.assertContains(response, 'Index of /')


class StaticHelperTest(StaticTests):
    """
    Test case to make sure the static URL pattern helper works as expected
    """
    def setUp(self):
        super().setUp()
        self._old_views_urlpatterns = urls.urlpatterns[:]
        urls.urlpatterns += static('/media/', document_root=media_dir)

    def tearDown(self):
        super().tearDown()
        urls.urlpatterns = self._old_views_urlpatterns

    def test_prefix(self):
        self.assertEqual(static('test')[0].regex.pattern, '^test(?P<path>.*)$')

    @override_settings(DEBUG=False)
    def test_debug_off(self):
        """No URLs are served if DEBUG=False."""
        self.assertEqual(static('test'), [])

    def test_empty_prefix(self):
        with self.assertRaisesMessage(ImproperlyConfigured, 'Empty static prefix not permitted'):
            static('')

    def test_special_prefix(self):
        """No URLs are served if prefix contains '://'."""
        self.assertEqual(static('http://'), [])


class StaticUtilsTests(unittest.TestCase):
    def test_was_modified_since_fp(self):
        """
        A floating point mtime does not disturb was_modified_since (#18675).
        """
        mtime = 1343416141.107817
        header = http_date(mtime)
        self.assertFalse(was_modified_since(header, mtime))
