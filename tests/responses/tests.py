import io
import os
import sys
import tempfile
from unittest import skipIf

from django.conf import settings
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.http import FileResponse, HttpResponse
from django.http.response import HttpResponseBase
from django.test import SimpleTestCase

UTF8 = 'utf-8'
ISO88591 = 'iso-8859-1'


class HttpResponseBaseTests(SimpleTestCase):
    def test_closed(self):
        r = HttpResponseBase()
        self.assertIs(r.closed, False)

        r.close()
        self.assertIs(r.closed, True)

    def test_write(self):
        r = HttpResponseBase()
        self.assertIs(r.writable(), False)

        with self.assertRaisesMessage(IOError, 'This HttpResponseBase instance is not writable'):
            r.write('asdf')
        with self.assertRaisesMessage(IOError, 'This HttpResponseBase instance is not writable'):
            r.writelines(['asdf\n', 'qwer\n'])

    def test_tell(self):
        r = HttpResponseBase()
        with self.assertRaisesMessage(IOError, 'This HttpResponseBase instance cannot tell its position'):
            r.tell()

    def test_setdefault(self):
        """
        HttpResponseBase.setdefault() should not change an existing header
        and should be case insensitive.
        """
        r = HttpResponseBase()

        r['Header'] = 'Value'
        r.setdefault('header', 'changed')
        self.assertEqual(r['header'], 'Value')

        r.setdefault('x-header', 'DefaultValue')
        self.assertEqual(r['X-Header'], 'DefaultValue')


class HttpResponseTests(SimpleTestCase):
    def test_status_code(self):
        resp = HttpResponse(status=503)
        self.assertEqual(resp.status_code, 503)
        self.assertEqual(resp.reason_phrase, "Service Unavailable")

    def test_change_status_code(self):
        resp = HttpResponse()
        resp.status_code = 503
        self.assertEqual(resp.status_code, 503)
        self.assertEqual(resp.reason_phrase, "Service Unavailable")

    def test_valid_status_code_string(self):
        resp = HttpResponse(status='100')
        self.assertEqual(resp.status_code, 100)
        resp = HttpResponse(status='404')
        self.assertEqual(resp.status_code, 404)
        resp = HttpResponse(status='599')
        self.assertEqual(resp.status_code, 599)

    def test_invalid_status_code(self):
        must_be_integer = 'HTTP status code must be an integer.'
        must_be_integer_in_range = 'HTTP status code must be an integer from 100 to 599.'
        with self.assertRaisesMessage(TypeError, must_be_integer):
            HttpResponse(status=object())
        with self.assertRaisesMessage(TypeError, must_be_integer):
            HttpResponse(status="J'attendrai")
        with self.assertRaisesMessage(ValueError, must_be_integer_in_range):
            HttpResponse(status=99)
        with self.assertRaisesMessage(ValueError, must_be_integer_in_range):
            HttpResponse(status=600)

    def test_reason_phrase(self):
        reason = "I'm an anarchist coffee pot on crack."
        resp = HttpResponse(status=419, reason=reason)
        self.assertEqual(resp.status_code, 419)
        self.assertEqual(resp.reason_phrase, reason)

    def test_charset_detection(self):
        """ HttpResponse should parse charset from content_type."""
        response = HttpResponse('ok')
        self.assertEqual(response.charset, settings.DEFAULT_CHARSET)

        response = HttpResponse(charset=ISO88591)
        self.assertEqual(response.charset, ISO88591)
        self.assertEqual(response['Content-Type'], 'text/html; charset=%s' % ISO88591)

        response = HttpResponse(content_type='text/plain; charset=%s' % UTF8, charset=ISO88591)
        self.assertEqual(response.charset, ISO88591)

        response = HttpResponse(content_type='text/plain; charset=%s' % ISO88591)
        self.assertEqual(response.charset, ISO88591)

        response = HttpResponse(content_type='text/plain; charset="%s"' % ISO88591)
        self.assertEqual(response.charset, ISO88591)

        response = HttpResponse(content_type='text/plain; charset=')
        self.assertEqual(response.charset, settings.DEFAULT_CHARSET)

        response = HttpResponse(content_type='text/plain')
        self.assertEqual(response.charset, settings.DEFAULT_CHARSET)

    def test_response_content_charset(self):
        """HttpResponse should encode based on charset."""
        content = "Café :)"
        utf8_content = content.encode(UTF8)
        iso_content = content.encode(ISO88591)

        response = HttpResponse(utf8_content)
        self.assertContains(response, utf8_content)

        response = HttpResponse(iso_content, content_type='text/plain; charset=%s' % ISO88591)
        self.assertContains(response, iso_content)

        response = HttpResponse(iso_content)
        self.assertContains(response, iso_content)

        response = HttpResponse(iso_content, content_type='text/plain')
        self.assertContains(response, iso_content)

    def test_repr(self):
        response = HttpResponse(content="Café :)".encode(UTF8), status=201)
        expected = '<HttpResponse status_code=201, "text/html; charset=utf-8">'
        self.assertEqual(repr(response), expected)

    def test_repr_no_content_type(self):
        response = HttpResponse(status=204)
        del response['Content-Type']
        self.assertEqual(repr(response), '<HttpResponse status_code=204>')

    def test_wrap_textiowrapper(self):
        content = "Café :)"
        r = HttpResponse()
        with io.TextIOWrapper(r, UTF8) as buf:
            buf.write(content)
        self.assertEqual(r.content, content.encode(UTF8))

    def test_generator_cache(self):
        generator = ("{}".format(i) for i in range(10))
        response = HttpResponse(content=generator)
        self.assertEqual(response.content, b'0123456789')
        with self.assertRaises(StopIteration):
            next(generator)

        cache.set('my-response-key', response)
        response = cache.get('my-response-key')
        self.assertEqual(response.content, b'0123456789')


class FileResponseTests(SimpleTestCase):
    def test_file_from_disk_response(self):
        response = FileResponse(open(__file__, 'rb'))
        self.assertEqual(response['Content-Length'], str(os.path.getsize(__file__)))
        self.assertIn(response['Content-Type'], ['text/x-python', 'text/plain'])

    def test_file_from_buffer_response(self):
        response = FileResponse(io.BytesIO(b'binary content'))
        self.assertEqual(response['Content-Length'], '14')
        self.assertEqual(response['Content-Type'], 'application/octet-stream')
        self.assertEqual(list(response), [b'binary content'])

    @skipIf(sys.platform == 'win32', "Named pipes are Unix-only.")
    def test_file_from_named_pipe_response(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            pipe_file = os.path.join(temp_dir, 'named_pipe')
            os.mkfifo(pipe_file)
            pipe_for_read = os.open(pipe_file, os.O_RDONLY | os.O_NONBLOCK)
            with open(pipe_file, 'wb') as pipe_for_write:
                pipe_for_write.write(b'binary content')

            response = FileResponse(os.fdopen(pipe_for_read, mode='rb'))
            self.assertEqual(list(response), [b'binary content'])
            self.assertFalse(response.has_header('Ĉontent-Length'))

    def test_file_from_disk_as_attachment(self):
        response = FileResponse(open(__file__, 'rb'), as_attachment=True)
        self.assertEqual(response['Content-Length'], str(os.path.getsize(__file__)))
        self.assertIn(response['Content-Type'], ['text/x-python', 'text/plain'])
        self.assertEqual(response['Content-Disposition'], 'attachment; filename="tests.py"')

    def test_compressed_response(self):
        """
        If compressed responses are served with the uncompressed Content-Type
        and a compression Content-Encoding, browsers might automatically
        uncompress the file, which is most probably not wanted.
        """
        test_tuples = (
            ('.tar.gz', 'application/gzip'),
            ('.tar.bz2', 'application/x-bzip'),
            ('.tar.xz', 'application/x-xz'),
        )
        for extension, mimetype in test_tuples:
            with self.subTest(ext=extension):
                with tempfile.NamedTemporaryFile(suffix=extension) as tmp:
                    response = FileResponse(tmp)
                self.assertEqual(response['Content-Type'], mimetype)
                self.assertFalse(response.has_header('Content-Encoding'))

    def test_unicode_attachment(self):
        response = FileResponse(
            ContentFile(b'binary content', name="祝您平安.odt"), as_attachment=True,
            content_type='application/vnd.oasis.opendocument.text',
        )
        self.assertEqual(response['Content-Type'], 'application/vnd.oasis.opendocument.text')
        self.assertEqual(
            response['Content-Disposition'],
            "attachment; filename*=utf-8''%E7%A5%9D%E6%82%A8%E5%B9%B3%E5%AE%89.odt"
        )
