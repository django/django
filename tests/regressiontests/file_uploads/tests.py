#! -*- coding: utf-8 -*-
import errno
import os
import shutil
from StringIO import StringIO

from django.core.files import temp as tempfile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http.multipartparser import MultiPartParser
from django.test import TestCase, client
from django.utils import simplejson
from django.utils import unittest
from django.utils.hashcompat import sha_constructor

from models import FileModel, temp_storage, UPLOAD_TO
import uploadhandler


UNICODE_FILENAME = u'test-0123456789_中文_Orléans.jpg'

class FileUploadTests(TestCase):
    def test_simple_upload(self):
        post_data = {
            'name': 'Ringo',
            'file_field': open(__file__),
        }
        response = self.client.post('/file_uploads/upload/', post_data)
        self.assertEqual(response.status_code, 200)

    def test_large_upload(self):
        tdir = tempfile.gettempdir()

        file1 = tempfile.NamedTemporaryFile(suffix=".file1", dir=tdir)
        file1.write('a' * (2 ** 21))
        file1.seek(0)

        file2 = tempfile.NamedTemporaryFile(suffix=".file2", dir=tdir)
        file2.write('a' * (10 * 2 ** 20))
        file2.seek(0)

        post_data = {
            'name': 'Ringo',
            'file_field1': file1,
            'file_field2': file2,
            }

        for key in post_data.keys():
            try:
                post_data[key + '_hash'] = sha_constructor(post_data[key].read()).hexdigest()
                post_data[key].seek(0)
            except AttributeError:
                post_data[key + '_hash'] = sha_constructor(post_data[key]).hexdigest()

        response = self.client.post('/file_uploads/verify/', post_data)

        self.assertEqual(response.status_code, 200)

    def test_unicode_file_name(self):
        tdir = tempfile.gettempdir()

        # This file contains chinese symbols and an accented char in the name.
        file1 = open(os.path.join(tdir, UNICODE_FILENAME.encode('utf-8')), 'w+b')
        file1.write('b' * (2 ** 10))
        file1.seek(0)

        post_data = {
            'file_unicode': file1,
            }

        response = self.client.post('/file_uploads/unicode_name/', post_data)

        file1.close()
        try:
            os.unlink(file1.name)
        except:
            pass

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

        payload = []
        for i, name in enumerate(scary_file_names):
            payload.extend([
                '--' + client.BOUNDARY,
                'Content-Disposition: form-data; name="file%s"; filename="%s"' % (i, name),
                'Content-Type: application/octet-stream',
                '',
                'You got pwnd.'
            ])
        payload.extend([
            '--' + client.BOUNDARY + '--',
            '',
        ])

        payload = "\r\n".join(payload)
        r = {
            'CONTENT_LENGTH': len(payload),
            'CONTENT_TYPE':   client.MULTIPART_CONTENT,
            'PATH_INFO':      "/file_uploads/echo/",
            'REQUEST_METHOD': 'POST',
            'wsgi.input':     client.FakePayload(payload),
        }
        response = self.client.request(**r)

        # The filenames should have been sanitized by the time it got to the view.
        recieved = simplejson.loads(response.content)
        for i, name in enumerate(scary_file_names):
            got = recieved["file%s" % i]
            self.assertEqual(got, "hax0rd.txt")

    def test_filename_overflow(self):
        """File names over 256 characters (dangerous on some platforms) get fixed up."""
        name = "%s.txt" % ("f"*500)
        payload = "\r\n".join([
            '--' + client.BOUNDARY,
            'Content-Disposition: form-data; name="file"; filename="%s"' % name,
            'Content-Type: application/octet-stream',
            '',
            'Oops.'
            '--' + client.BOUNDARY + '--',
            '',
        ])
        r = {
            'CONTENT_LENGTH': len(payload),
            'CONTENT_TYPE':   client.MULTIPART_CONTENT,
            'PATH_INFO':      "/file_uploads/echo/",
            'REQUEST_METHOD': 'POST',
            'wsgi.input':     client.FakePayload(payload),
        }
        got = simplejson.loads(self.client.request(**r).content)
        self.assert_(len(got['file']) < 256, "Got a long file name (%s characters)." % len(got['file']))

    def test_custom_upload_handler(self):
        # A small file (under the 5M quota)
        smallfile = tempfile.NamedTemporaryFile()
        smallfile.write('a' * (2 ** 21))
        smallfile.seek(0)

        # A big file (over the quota)
        bigfile = tempfile.NamedTemporaryFile()
        bigfile.write('a' * (10 * 2 ** 20))
        bigfile.seek(0)

        # Small file posting should work.
        response = self.client.post('/file_uploads/quota/', {'f': smallfile})
        got = simplejson.loads(response.content)
        self.assert_('f' in got)

        # Large files don't go through.
        response = self.client.post("/file_uploads/quota/", {'f': bigfile})
        got = simplejson.loads(response.content)
        self.assert_('f' not in got)

    def test_broken_custom_upload_handler(self):
        f = tempfile.NamedTemporaryFile()
        f.write('a' * (2 ** 21))
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
        file1.write('a' * (2 ** 23))
        file1.seek(0)

        file2 = tempfile.NamedTemporaryFile()
        file2.write('a' * (2 * 2 ** 18))
        file2.seek(0)

        file2a = tempfile.NamedTemporaryFile()
        file2a.write('a' * (5 * 2 ** 20))
        file2a.seek(0)

        response = self.client.post('/file_uploads/getlist_count/', {
            'file1': file1,
            'field1': u'test',
            'field2': u'test3',
            'field3': u'test5',
            'field4': u'test6',
            'field5': u'test7',
            'file2': (file2, file2a)
        })
        got = simplejson.loads(response.content)

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

        post_data = {
            'name': 'Ringo',
            'file_field': open(__file__),
        }
        # Maybe this is a little more complicated that it needs to be; but if
        # the django.test.client.FakePayload.read() implementation changes then
        # this test would fail.  So we need to know exactly what kind of error
        # it raises when there is an attempt to read more than the available bytes:
        try:
            client.FakePayload('a').read(2)
        except Exception, reference_error:
            pass

        # install the custom handler that tries to access request.POST
        self.client.handler = POSTAccessingHandler()

        try:
            response = self.client.post('/file_uploads/upload_errors/', post_data)
        except reference_error.__class__, err:
            self.failIf(
                str(err) == str(reference_error),
                "Caught a repeated exception that'll cause an infinite loop in file uploads."
            )
        except Exception, err:
            # CustomUploadError is the error that should have been raised
            self.assertEqual(err.__class__, uploadhandler.CustomUploadError)

class DirectoryCreationTests(unittest.TestCase):
    """
    Tests for error handling during directory creation
    via _save_FIELD_file (ticket #6450)
    """
    def setUp(self):
        self.obj = FileModel()
        if not os.path.isdir(temp_storage.location):
            os.makedirs(temp_storage.location)
        if os.path.isdir(UPLOAD_TO):
            os.chmod(UPLOAD_TO, 0700)
            shutil.rmtree(UPLOAD_TO)

    def tearDown(self):
        os.chmod(temp_storage.location, 0700)
        shutil.rmtree(temp_storage.location)

    def test_readonly_root(self):
        """Permission errors are not swallowed"""
        os.chmod(temp_storage.location, 0500)
        try:
            self.obj.testfile.save('foo.txt', SimpleUploadedFile('foo.txt', 'x'))
        except OSError, err:
            self.assertEquals(err.errno, errno.EACCES)
        except Exception, err:
            self.fail("OSError [Errno %s] not raised." % errno.EACCES)

    def test_not_a_directory(self):
        """The correct IOError is raised when the upload directory name exists but isn't a directory"""
        # Create a file with the upload directory name
        fd = open(UPLOAD_TO, 'w')
        fd.close()
        try:
            self.obj.testfile.save('foo.txt', SimpleUploadedFile('foo.txt', 'x'))
        except IOError, err:
            # The test needs to be done on a specific string as IOError
            # is raised even without the patch (just not early enough)
            self.assertEquals(err.args[0],
                              "%s exists and is not a directory." % UPLOAD_TO)
        except:
            self.fail("IOError not raised")

class MultiParserTests(unittest.TestCase):

    def test_empty_upload_handlers(self):
        # We're not actually parsing here; just checking if the parser properly
        # instantiates with empty upload handlers.
        parser = MultiPartParser({
            'CONTENT_TYPE':     'multipart/form-data; boundary=_foo',
            'CONTENT_LENGTH':   '1'
        }, StringIO('x'), [], 'utf-8')
