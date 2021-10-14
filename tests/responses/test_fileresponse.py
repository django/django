import io
import itertools
import os
import sys
import tempfile
from unittest import skipIf

from django.core.files.base import ContentFile
from django.http import FileResponse
from django.test import SimpleTestCase


class UnseekableBytesIO(io.BytesIO):
    def seekable(self):
        return False


class FileResponseTests(SimpleTestCase):
    def test_content_length_file(self):
        response = FileResponse(open(__file__, 'rb'))
        self.assertEqual(response.headers['Content-Length'], str(os.path.getsize(__file__)))
        response.close()

    def test_content_length_buffer(self):
        response = FileResponse(io.BytesIO(b'binary content'))
        self.assertEqual(response.headers['Content-Length'], '14')

    def test_content_type_file(self):
        response = FileResponse(open(__file__, 'rb'))
        self.assertIn(response.headers['Content-Type'], ['text/x-python', 'text/plain'])
        response.close()

    def test_content_type_buffer(self):
        response = FileResponse(io.BytesIO(b'binary content'))
        self.assertEqual(response.headers['Content-Type'], 'application/octet-stream')

    def test_content_type_buffer_explicit(self):
        response = FileResponse(io.BytesIO(b'binary content'), content_type='video/webm')
        self.assertEqual(response.headers['Content-Type'], 'video/webm')

    def test_content_type_buffer_named(self):
        test_tuples = (
            ('test_fileresponse.py', ['text/x-python', 'text/plain']),
            ('test_fileresponse.pynosuchfile', ['application/octet-stream']),
        )
        for filename, content_types in test_tuples:
            with self.subTest(filename=filename):
                buffer = io.BytesIO(b'binary content')
                buffer.name = filename
                response = FileResponse(buffer)
                self.assertIn(response.headers['Content-Type'], content_types)

    def test_content_disposition_file(self):
        filenames = (
            ('', 'test_fileresponse.py'),
            ('custom_name.py', 'custom_name.py'),
        )
        dispositions = (
            (False, 'inline'),
            (True, 'attachment'),
        )
        for (filename, header_filename), (as_attachment, header_disposition)\
                in itertools.product(filenames, dispositions):
            with self.subTest(filename=filename, disposition=header_disposition):
                response = FileResponse(open(__file__, 'rb'), filename=filename, as_attachment=as_attachment)
                self.assertEqual(
                    response.headers['Content-Disposition'],
                    '%s; filename="%s"' % (header_disposition, header_filename),
                )
                response.close()

    def test_content_disposition_buffer(self):
        response = FileResponse(io.BytesIO(b'binary content'))
        self.assertFalse(response.has_header('Content-Disposition'))

    def test_content_disposition_buffer_attachment(self):
        response = FileResponse(io.BytesIO(b'binary content'), as_attachment=True)
        self.assertEqual(response.headers['Content-Disposition'], 'attachment')

    def test_content_disposition_buffer_explicit_filename(self):
        dispositions = (
            (False, 'inline'),
            (True, 'attachment'),
        )
        for as_attachment, header_disposition in dispositions:
            response = FileResponse(
                io.BytesIO(b'binary content'),
                as_attachment=as_attachment,
                filename='custom_name.py',
            )
            self.assertEqual(
                response.headers['Content-Disposition'], '%s; filename="custom_name.py"' % header_disposition
            )

    def test_response_buffer(self):
        response = FileResponse(io.BytesIO(b'binary content'))
        self.assertEqual(list(response), [b'binary content'])

    def test_response_nonzero_starting_position(self):
        test_tuples = (
            ('BytesIO', io.BytesIO),
            ('UnseekableBytesIO', UnseekableBytesIO),
        )
        for buffer_class_name, BufferClass in test_tuples:
            with self.subTest(buffer_class_name=buffer_class_name):
                buffer = BufferClass(b'binary content')
                buffer.seek(10)
                response = FileResponse(buffer)
                self.assertEqual(list(response), [b'tent'])

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
            response.close()
            self.assertFalse(response.has_header('Content-Length'))

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
                self.assertEqual(response.headers['Content-Type'], mimetype)
                self.assertFalse(response.has_header('Content-Encoding'))

    def test_unicode_attachment(self):
        response = FileResponse(
            ContentFile(b'binary content', name="祝您平安.odt"), as_attachment=True,
            content_type='application/vnd.oasis.opendocument.text',
        )
        self.assertEqual(
            response.headers['Content-Type'],
            'application/vnd.oasis.opendocument.text',
        )
        self.assertEqual(
            response.headers['Content-Disposition'],
            "attachment; filename*=utf-8''%E7%A5%9D%E6%82%A8%E5%B9%B3%E5%AE%89.odt",
        )

    def test_repr(self):
        response = FileResponse(io.BytesIO(b'binary content'))
        self.assertEqual(
            repr(response),
            '<FileResponse status_code=200, "application/octet-stream">',
        )
