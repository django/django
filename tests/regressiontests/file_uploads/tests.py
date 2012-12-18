#! -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import base64
import errno
import hashlib
import json
import os
import shutil
import tempfile as sys_tempfile

from django.core.files import temp as tempfile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http.multipartparser import MultiPartParser
from django.test import TestCase, client
from django.test.utils import override_settings
from django.utils.encoding import force_bytes
from django.utils.six import StringIO
from django.utils import unittest

from . import uploadhandler
from .models import FileModel


UNICODE_FILENAME = 'test-0123456789_中文_Orléans.jpg'
MEDIA_ROOT = sys_tempfile.mkdtemp()
UPLOAD_TO = os.path.join(MEDIA_ROOT, 'test_upload')

@override_settings(MEDIA_ROOT=MEDIA_ROOT)
class FileUploadTests(TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.path.isdir(MEDIA_ROOT):
            os.makedirs(MEDIA_ROOT)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(MEDIA_ROOT)

    def test_simple_upload(self):
        with open(__file__, 'rb') as fp:
            post_data = {
                'name': 'Ringo',
                'file_field': fp,
            }
            response = self.client.post('/file_uploads/upload/', post_data)
        self.assertEqual(response.status_code, 200)

    def test_large_upload(self):
        tdir = tempfile.gettempdir()

        file1 = tempfile.NamedTemporaryFile(suffix=".file1", dir=tdir)
        file1.write(b'a' * (2 ** 21))
        file1.seek(0)

        file2 = tempfile.NamedTemporaryFile(suffix=".file2", dir=tdir)
        file2.write(b'a' * (10 * 2 ** 20))
        file2.seek(0)

        post_data = {
            'name': 'Ringo',
            'file_field1': file1,
            'file_field2': file2,
            }

        for key in list(post_data):
            try:
                post_data[key + '_hash'] = hashlib.sha1(post_data[key].read()).hexdigest()
                post_data[key].seek(0)
            except AttributeError:
                post_data[key + '_hash'] = hashlib.sha1(force_bytes(post_data[key])).hexdigest()

        response = self.client.post('/file_uploads/verify/', post_data)

        self.assertEqual(response.status_code, 200)

    def _test_base64_upload(self, content):
        payload = client.FakePayload("\r\n".join([
            '--' + client.BOUNDARY,
            'Content-Disposition: form-data; name="file"; filename="test.txt"',
            'Content-Type: application/octet-stream',
            'Content-Transfer-Encoding: base64',
            '',]))
        payload.write(b"\r\n" + base64.b64encode(force_bytes(content)) + b"\r\n")
        payload.write('--' + client.BOUNDARY + '--\r\n')
        r = {
            'CONTENT_LENGTH': len(payload),
            'CONTENT_TYPE':   client.MULTIPART_CONTENT,
            'PATH_INFO':      "/file_uploads/echo_content/",
            'REQUEST_METHOD': 'POST',
            'wsgi.input':     payload,
        }
        response = self.client.request(**r)
        received = json.loads(response.content.decode('utf-8'))

        self.assertEqual(received['file'], content)

    def test_base64_upload(self):
        self._test_base64_upload("This data will be transmitted base64-encoded.")

    def test_big_base64_upload(self):
        self._test_base64_upload("Big data" * 68000)  # > 512Kb

    def test_unicode_file_name(self):
        tdir = sys_tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tdir, True)

        # This file contains chinese symbols and an accented char in the name.
        with open(os.path.join(tdir, UNICODE_FILENAME), 'w+b') as file1:
            file1.write(b'b' * (2 ** 10))
            file1.seek(0)

            post_data = {
                'file_unicode': file1,
                }

            response = self.client.post('/file_uploads/unicode_name/', post_data)

        self.assertEqual(response.status_code, 200)

    def test_dangerous_file_names(self):
        """Uploaded file names should be sanitized before ever reaching the view."""
        # This test simulates possible directory traversal attacks by a
        # malicious uploader We have to do some monkeybusiness here to construct
        # a malicious payload with an invalid file name (containing os.sep or
        # os.pardir). This similar to what an attacker would need to do when
        # trying such an attack.
        scary_file_names = [
            "/tmp/hax0rd.txt",          # Absolute path, *nix-style.
            "C:\\Windows\\hax0rd.txt",  # Absolute path, win-syle.
            "C:/Windows/hax0rd.txt",    # Absolute path, broken-style.
            "\\tmp\\hax0rd.txt",        # Absolute path, broken in a different way.
            "/tmp\\hax0rd.txt",         # Absolute path, broken by mixing.
            "subdir/hax0rd.txt",        # Descendant path, *nix-style.
            "subdir\\hax0rd.txt",       # Descendant path, win-style.
            "sub/dir\\hax0rd.txt",      # Descendant path, mixed.
            "../../hax0rd.txt",         # Relative path, *nix-style.
            "..\\..\\hax0rd.txt",       # Relative path, win-style.
            "../..\\hax0rd.txt"         # Relative path, mixed.
        ]

        payload = client.FakePayload()
        for i, name in enumerate(scary_file_names):
            payload.write('\r\n'.join([
                '--' + client.BOUNDARY,
                'Content-Disposition: form-data; name="file%s"; filename="%s"' % (i, name),
                'Content-Type: application/octet-stream',
                '',
                'You got pwnd.\r\n'
            ]))
        payload.write('\r\n--' + client.BOUNDARY + '--\r\n')

        r = {
            'CONTENT_LENGTH': len(payload),
            'CONTENT_TYPE':   client.MULTIPART_CONTENT,
            'PATH_INFO':      "/file_uploads/echo/",
            'REQUEST_METHOD': 'POST',
            'wsgi.input':     payload,
        }
        response = self.client.request(**r)

        # The filenames should have been sanitized by the time it got to the view.
        recieved = json.loads(response.content.decode('utf-8'))
        for i, name in enumerate(scary_file_names):
            got = recieved["file%s" % i]
            self.assertEqual(got, "hax0rd.txt")

    def test_filename_overflow(self):
        """File names over 256 characters (dangerous on some platforms) get fixed up."""
        name = "%s.txt" % ("f"*500)
        payload = client.FakePayload("\r\n".join([
            '--' + client.BOUNDARY,
            'Content-Disposition: form-data; name="file"; filename="%s"' % name,
            'Content-Type: application/octet-stream',
            '',
            'Oops.'
            '--' + client.BOUNDARY + '--',
            '',
        ]))
        r = {
            'CONTENT_LENGTH': len(payload),
            'CONTENT_TYPE':   client.MULTIPART_CONTENT,
            'PATH_INFO':      "/file_uploads/echo/",
            'REQUEST_METHOD': 'POST',
            'wsgi.input':     payload,
        }
        got = json.loads(self.client.request(**r).content.decode('utf-8'))
        self.assertTrue(len(got['file']) < 256, "Got a long file name (%s characters)." % len(got['file']))

    def test_truncated_multipart_handled_gracefully(self):
        """
        If passed an incomplete multipart message, MultiPartParser does not
        attempt to read beyond the end of the stream, and simply will handle
        the part that can be parsed gracefully.
        """
        payload_str = "\r\n".join([
            '--' + client.BOUNDARY,
            'Content-Disposition: form-data; name="file"; filename="foo.txt"',
            'Content-Type: application/octet-stream',
            '',
            'file contents'
            '--' + client.BOUNDARY + '--',
            '',
        ])
        payload = client.FakePayload(payload_str[:-10])
        r = {
            'CONTENT_LENGTH': len(payload),
            'CONTENT_TYPE': client.MULTIPART_CONTENT,
            'PATH_INFO': '/file_uploads/echo/',
            'REQUEST_METHOD': 'POST',
            'wsgi.input': payload,
        }
        got = json.loads(self.client.request(**r).content.decode('utf-8'))
        self.assertEqual(got, {})

    def test_empty_multipart_handled_gracefully(self):
        """
        If passed an empty multipart message, MultiPartParser will return
        an empty QueryDict.
        """
        r = {
            'CONTENT_LENGTH': 0,
            'CONTENT_TYPE': client.MULTIPART_CONTENT,
            'PATH_INFO': '/file_uploads/echo/',
            'REQUEST_METHOD': 'POST',
            'wsgi.input': client.FakePayload(b''),
        }
        got = json.loads(self.client.request(**r).content.decode('utf-8'))
        self.assertEqual(got, {})

    def test_custom_upload_handler(self):
        # A small file (under the 5M quota)
        smallfile = tempfile.NamedTemporaryFile()
        smallfile.write(b'a' * (2 ** 21))
        smallfile.seek(0)

        # A big file (over the quota)
        bigfile = tempfile.NamedTemporaryFile()
        bigfile.write(b'a' * (10 * 2 ** 20))
        bigfile.seek(0)

        # Small file posting should work.
        response = self.client.post('/file_uploads/quota/', {'f': smallfile})
        got = json.loads(response.content.decode('utf-8'))
        self.assertTrue('f' in got)

        # Large files don't go through.
        response = self.client.post("/file_uploads/quota/", {'f': bigfile})
        got = json.loads(response.content.decode('utf-8'))
        self.assertTrue('f' not in got)

    def test_broken_custom_upload_handler(self):
        f = tempfile.NamedTemporaryFile()
        f.write(b'a' * (2 ** 21))
        f.seek(0)

        # AttributeError: You cannot alter upload handlers after the upload has been processed.
        self.assertRaises(
            AttributeError,
            self.client.post,
            '/file_uploads/quota/broken/',
            {'f': f}
        )

    def test_fileupload_getlist(self):
        file1 = tempfile.NamedTemporaryFile()
        file1.write(b'a' * (2 ** 23))
        file1.seek(0)

        file2 = tempfile.NamedTemporaryFile()
        file2.write(b'a' * (2 * 2 ** 18))
        file2.seek(0)

        file2a = tempfile.NamedTemporaryFile()
        file2a.write(b'a' * (5 * 2 ** 20))
        file2a.seek(0)

        response = self.client.post('/file_uploads/getlist_count/', {
            'file1': file1,
            'field1': 'test',
            'field2': 'test3',
            'field3': 'test5',
            'field4': 'test6',
            'field5': 'test7',
            'file2': (file2, file2a)
        })
        got = json.loads(response.content.decode('utf-8'))

        self.assertEqual(got.get('file1'), 1)
        self.assertEqual(got.get('file2'), 2)

    def test_file_error_blocking(self):
        """
        The server should not block when there are upload errors (bug #8622).
        This can happen if something -- i.e. an exception handler -- tries to
        access POST while handling an error in parsing POST. This shouldn't
        cause an infinite loop!
        """
        class POSTAccessingHandler(client.ClientHandler):
            """A handler that'll access POST during an exception."""
            def handle_uncaught_exception(self, request, resolver, exc_info):
                ret = super(POSTAccessingHandler, self).handle_uncaught_exception(request, resolver, exc_info)
                p = request.POST
                return ret

        # Maybe this is a little more complicated that it needs to be; but if
        # the django.test.client.FakePayload.read() implementation changes then
        # this test would fail.  So we need to know exactly what kind of error
        # it raises when there is an attempt to read more than the available bytes:
        try:
            client.FakePayload(b'a').read(2)
        except Exception as err:
            reference_error = err

        # install the custom handler that tries to access request.POST
        self.client.handler = POSTAccessingHandler()

        with open(__file__, 'rb') as fp:
            post_data = {
                'name': 'Ringo',
                'file_field': fp,
            }
            try:
                response = self.client.post('/file_uploads/upload_errors/', post_data)
            except reference_error.__class__ as err:
                self.assertFalse(
                    str(err) == str(reference_error),
                    "Caught a repeated exception that'll cause an infinite loop in file uploads."
                )
            except Exception as err:
                # CustomUploadError is the error that should have been raised
                self.assertEqual(err.__class__, uploadhandler.CustomUploadError)

    def test_filename_case_preservation(self):
        """
        The storage backend shouldn't mess with the case of the filenames
        uploaded.
        """
        # Synthesize the contents of a file upload with a mixed case filename
        # so we don't have to carry such a file in the Django tests source code
        # tree.
        vars = {'boundary': 'oUrBoUnDaRyStRiNg'}
        post_data = [
            '--%(boundary)s',
            'Content-Disposition: form-data; name="file_field"; '
                'filename="MiXeD_cAsE.txt"',
            'Content-Type: application/octet-stream',
            '',
            'file contents\n'
            '',
            '--%(boundary)s--\r\n',
        ]
        response = self.client.post(
            '/file_uploads/filename_case/',
            '\r\n'.join(post_data) % vars,
            'multipart/form-data; boundary=%(boundary)s' % vars
        )
        self.assertEqual(response.status_code, 200)
        id = int(response.content)
        obj = FileModel.objects.get(pk=id)
        # The name of the file uploaded and the file stored in the server-side
        # shouldn't differ.
        self.assertEqual(os.path.basename(obj.testfile.path), 'MiXeD_cAsE.txt')

@override_settings(MEDIA_ROOT=MEDIA_ROOT)
class DirectoryCreationTests(TestCase):
    """
    Tests for error handling during directory creation
    via _save_FIELD_file (ticket #6450)
    """
    @classmethod
    def setUpClass(cls):
        if not os.path.isdir(MEDIA_ROOT):
            os.makedirs(MEDIA_ROOT)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(MEDIA_ROOT)

    def setUp(self):
        self.obj = FileModel()

    def test_readonly_root(self):
        """Permission errors are not swallowed"""
        os.chmod(MEDIA_ROOT, 0o500)
        self.addCleanup(os.chmod, MEDIA_ROOT, 0o700)
        try:
            self.obj.testfile.save('foo.txt', SimpleUploadedFile('foo.txt', b'x'))
        except OSError as err:
            self.assertEqual(err.errno, errno.EACCES)
        except Exception:
            self.fail("OSError [Errno %s] not raised." % errno.EACCES)

    def test_not_a_directory(self):
        """The correct IOError is raised when the upload directory name exists but isn't a directory"""
        # Create a file with the upload directory name
        open(UPLOAD_TO, 'wb').close()
        self.addCleanup(os.remove, UPLOAD_TO)
        with self.assertRaises(IOError) as exc_info:
            self.obj.testfile.save('foo.txt', SimpleUploadedFile('foo.txt', b'x'))
        # The test needs to be done on a specific string as IOError
        # is raised even without the patch (just not early enough)
        self.assertEqual(exc_info.exception.args[0],
                          "%s exists and is not a directory." % UPLOAD_TO)


class MultiParserTests(unittest.TestCase):

    def test_empty_upload_handlers(self):
        # We're not actually parsing here; just checking if the parser properly
        # instantiates with empty upload handlers.
        parser = MultiPartParser({
            'CONTENT_TYPE':     'multipart/form-data; boundary=_foo',
            'CONTENT_LENGTH':   '1'
        }, StringIO('x'), [], 'utf-8')
