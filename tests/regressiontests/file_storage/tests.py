# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import errno
import os
import shutil
import sys
import tempfile
import time
from datetime import datetime, timedelta
from io import BytesIO

try:
    import threading
except ImportError:
    import dummy_threading as threading

from django.conf import settings
from django.core.exceptions import SuspiciousOperation, ImproperlyConfigured
from django.core.files.base import File, ContentFile
from django.core.files.images import get_image_dimensions
from django.core.files.storage import FileSystemStorage, get_storage_class
from django.core.files.uploadedfile import UploadedFile
from django.test import SimpleTestCase
from django.utils import six
from django.utils import unittest
from django.utils._os import upath
from django.test.utils import override_settings
from ..servers.tests import LiveServerBase

# Try to import PIL in either of the two ways it can end up installed.
# Checking for the existence of Image is enough for CPython, but
# for PyPy, you need to check for the underlying modules
try:
    from PIL import Image, _imaging
except ImportError:
    try:
        import Image, _imaging
    except ImportError:
        Image = None


class GetStorageClassTests(SimpleTestCase):

    def test_get_filesystem_storage(self):
        """
        get_storage_class returns the class for a storage backend name/path.
        """
        self.assertEqual(
            get_storage_class('django.core.files.storage.FileSystemStorage'),
            FileSystemStorage)

    def test_get_invalid_storage_module(self):
        """
        get_storage_class raises an error if the requested import don't exist.
        """
        self.assertRaisesMessage(
            ImproperlyConfigured,
            "NonExistingStorage isn't a storage module.",
            get_storage_class,
            'NonExistingStorage')

    def test_get_nonexisting_storage_class(self):
        """
        get_storage_class raises an error if the requested class don't exist.
        """
        self.assertRaisesMessage(
            ImproperlyConfigured,
            'Storage module "django.core.files.storage" does not define a '\
                '"NonExistingStorage" class.',
            get_storage_class,
            'django.core.files.storage.NonExistingStorage')

    def test_get_nonexisting_storage_module(self):
        """
        get_storage_class raises an error if the requested module don't exist.
        """
        # Error message may or may not be the fully qualified path.
        six.assertRaisesRegex(self,
            ImproperlyConfigured,
            ('Error importing storage module django.core.files.non_existing_'
                'storage: "No module named .*non_existing_storage'),
            get_storage_class,
            'django.core.files.non_existing_storage.NonExistingStorage'
        )

class FileStorageTests(unittest.TestCase):
    storage_class = FileSystemStorage

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.storage = self.storage_class(location=self.temp_dir,
            base_url='/test_media_url/')
        # Set up a second temporary directory which is ensured to have a mixed
        # case name.
        self.temp_dir2 = tempfile.mkdtemp(suffix='aBc')

    def tearDown(self):
        shutil.rmtree(self.temp_dir)
        shutil.rmtree(self.temp_dir2)

    def test_emtpy_location(self):
        """
        Makes sure an exception is raised if the location is empty
        """
        storage = self.storage_class(location='')
        self.assertEqual(storage.base_location, '')
        self.assertEqual(storage.location, upath(os.getcwd()))

    def test_file_access_options(self):
        """
        Standard file access options are available, and work as expected.
        """
        self.assertFalse(self.storage.exists('storage_test'))
        f = self.storage.open('storage_test', 'w')
        f.write('storage contents')
        f.close()
        self.assertTrue(self.storage.exists('storage_test'))

        f = self.storage.open('storage_test', 'r')
        self.assertEqual(f.read(), 'storage contents')
        f.close()

        self.storage.delete('storage_test')
        self.assertFalse(self.storage.exists('storage_test'))

    def test_file_accessed_time(self):
        """
        File storage returns a Datetime object for the last accessed time of
        a file.
        """
        self.assertFalse(self.storage.exists('test.file'))

        f = ContentFile('custom contents')
        f_name = self.storage.save('test.file', f)
        atime = self.storage.accessed_time(f_name)

        self.assertEqual(atime, datetime.fromtimestamp(
            os.path.getatime(self.storage.path(f_name))))
        self.assertTrue(datetime.now() - self.storage.accessed_time(f_name) < timedelta(seconds=2))
        self.storage.delete(f_name)

    def test_file_created_time(self):
        """
        File storage returns a Datetime object for the creation time of
        a file.
        """
        self.assertFalse(self.storage.exists('test.file'))

        f = ContentFile('custom contents')
        f_name = self.storage.save('test.file', f)
        ctime = self.storage.created_time(f_name)

        self.assertEqual(ctime, datetime.fromtimestamp(
            os.path.getctime(self.storage.path(f_name))))
        self.assertTrue(datetime.now() - self.storage.created_time(f_name) < timedelta(seconds=2))

        self.storage.delete(f_name)

    def test_file_modified_time(self):
        """
        File storage returns a Datetime object for the last modified time of
        a file.
        """
        self.assertFalse(self.storage.exists('test.file'))

        f = ContentFile('custom contents')
        f_name = self.storage.save('test.file', f)
        mtime = self.storage.modified_time(f_name)

        self.assertEqual(mtime, datetime.fromtimestamp(
            os.path.getmtime(self.storage.path(f_name))))
        self.assertTrue(datetime.now() - self.storage.modified_time(f_name) < timedelta(seconds=2))

        self.storage.delete(f_name)

    def test_file_save_without_name(self):
        """
        File storage extracts the filename from the content object if no
        name is given explicitly.
        """
        self.assertFalse(self.storage.exists('test.file'))

        f = ContentFile('custom contents')
        f.name = 'test.file'

        storage_f_name = self.storage.save(None, f)

        self.assertEqual(storage_f_name, f.name)

        self.assertTrue(os.path.exists(os.path.join(self.temp_dir, f.name)))

        self.storage.delete(storage_f_name)

    def test_file_save_with_path(self):
        """
        Saving a pathname should create intermediate directories as necessary.
        """
        self.assertFalse(self.storage.exists('path/to'))
        self.storage.save('path/to/test.file',
            ContentFile('file saved with path'))

        self.assertTrue(self.storage.exists('path/to'))
        with self.storage.open('path/to/test.file') as f:
            self.assertEqual(f.read(), b'file saved with path')

        self.assertTrue(os.path.exists(
            os.path.join(self.temp_dir, 'path', 'to', 'test.file')))

        self.storage.delete('path/to/test.file')

    def test_file_path(self):
        """
        File storage returns the full path of a file
        """
        self.assertFalse(self.storage.exists('test.file'))

        f = ContentFile('custom contents')
        f_name = self.storage.save('test.file', f)

        self.assertEqual(self.storage.path(f_name),
            os.path.join(self.temp_dir, f_name))

        self.storage.delete(f_name)

    def test_file_url(self):
        """
        File storage returns a url to access a given file from the Web.
        """
        self.assertEqual(self.storage.url('test.file'),
            '%s%s' % (self.storage.base_url, 'test.file'))

        # should encode special chars except ~!*()'
        # like encodeURIComponent() JavaScript function do
        self.assertEqual(self.storage.url(r"""~!*()'@#$%^&*abc`+ =.file"""),
            """/test_media_url/~!*()'%40%23%24%25%5E%26*abc%60%2B%20%3D.file""")

        # should stanslate os path separator(s) to the url path separator
        self.assertEqual(self.storage.url("""a/b\\c.file"""),
            """/test_media_url/a/b/c.file""")

        self.storage.base_url = None
        self.assertRaises(ValueError, self.storage.url, 'test.file')

    def test_listdir(self):
        """
        File storage returns a tuple containing directories and files.
        """
        self.assertFalse(self.storage.exists('storage_test_1'))
        self.assertFalse(self.storage.exists('storage_test_2'))
        self.assertFalse(self.storage.exists('storage_dir_1'))

        f = self.storage.save('storage_test_1', ContentFile('custom content'))
        f = self.storage.save('storage_test_2', ContentFile('custom content'))
        os.mkdir(os.path.join(self.temp_dir, 'storage_dir_1'))

        dirs, files = self.storage.listdir('')
        self.assertEqual(set(dirs), set(['storage_dir_1']))
        self.assertEqual(set(files),
                         set(['storage_test_1', 'storage_test_2']))

        self.storage.delete('storage_test_1')
        self.storage.delete('storage_test_2')
        os.rmdir(os.path.join(self.temp_dir, 'storage_dir_1'))

    def test_file_storage_prevents_directory_traversal(self):
        """
        File storage prevents directory traversal (files can only be accessed if
        they're below the storage location).
        """
        self.assertRaises(SuspiciousOperation, self.storage.exists, '..')
        self.assertRaises(SuspiciousOperation, self.storage.exists, '/etc/passwd')

    def test_file_storage_preserves_filename_case(self):
        """The storage backend should preserve case of filenames."""
        # Create a storage backend associated with the mixed case name
        # directory.
        temp_storage = self.storage_class(location=self.temp_dir2)
        # Ask that storage backend to store a file with a mixed case filename.
        mixed_case = 'CaSe_SeNsItIvE'
        file = temp_storage.open(mixed_case, 'w')
        file.write('storage contents')
        file.close()
        self.assertEqual(os.path.join(self.temp_dir2, mixed_case),
                         temp_storage.path(mixed_case))
        temp_storage.delete(mixed_case)

    def test_makedirs_race_handling(self):
        """
        File storage should be robust against directory creation race conditions.
        """
        real_makedirs = os.makedirs

        # Monkey-patch os.makedirs, to simulate a normal call, a raced call,
        # and an error.
        def fake_makedirs(path):
            if path == os.path.join(self.temp_dir, 'normal'):
                real_makedirs(path)
            elif path == os.path.join(self.temp_dir, 'raced'):
                real_makedirs(path)
                raise OSError(errno.EEXIST, 'simulated EEXIST')
            elif path == os.path.join(self.temp_dir, 'error'):
                raise OSError(errno.EACCES, 'simulated EACCES')
            else:
                self.fail('unexpected argument %r' % path)

        try:
            os.makedirs = fake_makedirs

            self.storage.save('normal/test.file',
                ContentFile('saved normally'))
            with self.storage.open('normal/test.file') as f:
                self.assertEqual(f.read(), b'saved normally')

            self.storage.save('raced/test.file',
                ContentFile('saved with race'))
            with self.storage.open('raced/test.file') as f:
                self.assertEqual(f.read(), b'saved with race')

            # Check that OSErrors aside from EEXIST are still raised.
            self.assertRaises(OSError,
                self.storage.save, 'error/test.file', ContentFile('not saved'))
        finally:
            os.makedirs = real_makedirs

    def test_remove_race_handling(self):
        """
        File storage should be robust against file removal race conditions.
        """
        real_remove = os.remove

        # Monkey-patch os.remove, to simulate a normal call, a raced call,
        # and an error.
        def fake_remove(path):
            if path == os.path.join(self.temp_dir, 'normal.file'):
                real_remove(path)
            elif path == os.path.join(self.temp_dir, 'raced.file'):
                real_remove(path)
                raise OSError(errno.ENOENT, 'simulated ENOENT')
            elif path == os.path.join(self.temp_dir, 'error.file'):
                raise OSError(errno.EACCES, 'simulated EACCES')
            else:
                self.fail('unexpected argument %r' % path)

        try:
            os.remove = fake_remove

            self.storage.save('normal.file', ContentFile('delete normally'))
            self.storage.delete('normal.file')
            self.assertFalse(self.storage.exists('normal.file'))

            self.storage.save('raced.file', ContentFile('delete with race'))
            self.storage.delete('raced.file')
            self.assertFalse(self.storage.exists('normal.file'))

            # Check that OSErrors aside from ENOENT are still raised.
            self.storage.save('error.file', ContentFile('delete with error'))
            self.assertRaises(OSError, self.storage.delete, 'error.file')
        finally:
            os.remove = real_remove

    def test_file_chunks_error(self):
        """
        Test behaviour when file.chunks() is raising an error
        """
        f1 = ContentFile('chunks fails')
        def failing_chunks():
            raise IOError
        f1.chunks = failing_chunks
        with self.assertRaises(IOError):
            self.storage.save('error.file', f1)


class CustomStorage(FileSystemStorage):
    def get_available_name(self, name):
        """
        Append numbers to duplicate files rather than underscores, like Trac.
        """
        parts = name.split('.')
        basename, ext = parts[0], parts[1:]
        number = 2
        while self.exists(name):
            name = '.'.join([basename, str(number)] + ext)
            number += 1

        return name

class CustomStorageTests(FileStorageTests):
    storage_class = CustomStorage

    def test_custom_get_available_name(self):
        first = self.storage.save('custom_storage', ContentFile('custom contents'))
        self.assertEqual(first, 'custom_storage')
        second = self.storage.save('custom_storage', ContentFile('more contents'))
        self.assertEqual(second, 'custom_storage.2')
        self.storage.delete(first)
        self.storage.delete(second)

class UnicodeFileNameTests(unittest.TestCase):
    def test_unicode_file_names(self):
        """
        Regression test for #8156: files with unicode names I can't quite figure
        out the encoding situation between doctest and this file, but the actual
        repr doesn't matter; it just shouldn't return a unicode object.
        """
        uf = UploadedFile(name='¿Cómo?',content_type='text')
        self.assertEqual(type(uf.__repr__()), str)

# Tests for a race condition on file saving (#4948).
# This is written in such a way that it'll always pass on platforms
# without threading.

class SlowFile(ContentFile):
    def chunks(self):
        time.sleep(1)
        return super(ContentFile, self).chunks()

class FileSaveRaceConditionTest(unittest.TestCase):
    def setUp(self):
        self.storage_dir = tempfile.mkdtemp()
        self.storage = FileSystemStorage(self.storage_dir)
        self.thread = threading.Thread(target=self.save_file, args=['conflict'])

    def tearDown(self):
        shutil.rmtree(self.storage_dir)

    def save_file(self, name):
        name = self.storage.save(name, SlowFile(b"Data"))

    def test_race_condition(self):
        self.thread.start()
        name = self.save_file('conflict')
        self.thread.join()
        self.assertTrue(self.storage.exists('conflict'))
        self.assertTrue(self.storage.exists('conflict_1'))
        self.storage.delete('conflict')
        self.storage.delete('conflict_1')

@unittest.skipIf(sys.platform.startswith('win'), "Windows only partially supports umasks and chmod.")
class FileStoragePermissions(unittest.TestCase):
    def setUp(self):
        self.umask = 0o027
        self.old_umask = os.umask(self.umask)
        self.storage_dir = tempfile.mkdtemp()
        self.storage = FileSystemStorage(self.storage_dir)

    def tearDown(self):
        shutil.rmtree(self.storage_dir)
        os.umask(self.old_umask)

    @override_settings(FILE_UPLOAD_PERMISSIONS=0o654)
    def test_file_upload_permissions(self):
        name = self.storage.save("the_file", ContentFile("data"))
        actual_mode = os.stat(self.storage.path(name))[0] & 0o777
        self.assertEqual(actual_mode, 0o654)

    @override_settings(FILE_UPLOAD_PERMISSIONS=None)
    def test_file_upload_default_permissions(self):
        fname = self.storage.save("some_file", ContentFile("data"))
        mode = os.stat(self.storage.path(fname))[0] & 0o777
        self.assertEqual(mode, 0o666 & ~self.umask)

class FileStoragePathParsing(unittest.TestCase):
    def setUp(self):
        self.storage_dir = tempfile.mkdtemp()
        self.storage = FileSystemStorage(self.storage_dir)

    def tearDown(self):
        shutil.rmtree(self.storage_dir)

    def test_directory_with_dot(self):
        """Regression test for #9610.

        If the directory name contains a dot and the file name doesn't, make
        sure we still mangle the file name instead of the directory name.
        """

        self.storage.save('dotted.path/test', ContentFile("1"))
        self.storage.save('dotted.path/test', ContentFile("2"))

        self.assertFalse(os.path.exists(os.path.join(self.storage_dir, 'dotted_.path')))
        self.assertTrue(os.path.exists(os.path.join(self.storage_dir, 'dotted.path/test')))
        self.assertTrue(os.path.exists(os.path.join(self.storage_dir, 'dotted.path/test_1')))

    def test_first_character_dot(self):
        """
        File names with a dot as their first character don't have an extension,
        and the underscore should get added to the end.
        """
        self.storage.save('dotted.path/.test', ContentFile("1"))
        self.storage.save('dotted.path/.test', ContentFile("2"))

        self.assertTrue(os.path.exists(os.path.join(self.storage_dir, 'dotted.path/.test')))
        self.assertTrue(os.path.exists(os.path.join(self.storage_dir, 'dotted.path/.test_1')))

class DimensionClosingBug(unittest.TestCase):
    """
    Test that get_image_dimensions() properly closes files (#8817)
    """
    @unittest.skipUnless(Image, "PIL not installed")
    def test_not_closing_of_files(self):
        """
        Open files passed into get_image_dimensions() should stay opened.
        """
        empty_io = BytesIO()
        try:
            get_image_dimensions(empty_io)
        finally:
            self.assertTrue(not empty_io.closed)

    @unittest.skipUnless(Image, "PIL not installed")
    def test_closing_of_filenames(self):
        """
        get_image_dimensions() called with a filename should closed the file.
        """
        # We need to inject a modified open() builtin into the images module
        # that checks if the file was closed properly if the function is
        # called with a filename instead of an file object.
        # get_image_dimensions will call our catching_open instead of the
        # regular builtin one.

        class FileWrapper(object):
            _closed = []
            def __init__(self, f):
                self.f = f
            def __getattr__(self, name):
                return getattr(self.f, name)
            def close(self):
                self._closed.append(True)
                self.f.close()

        def catching_open(*args):
            return FileWrapper(open(*args))

        from django.core.files import images
        images.open = catching_open
        try:
            get_image_dimensions(os.path.join(os.path.dirname(upath(__file__)), "test1.png"))
        finally:
            del images.open
        self.assertTrue(FileWrapper._closed)

class InconsistentGetImageDimensionsBug(unittest.TestCase):
    """
    Test that get_image_dimensions() works properly after various calls
    using a file handler (#11158)
    """
    @unittest.skipUnless(Image, "PIL not installed")
    def test_multiple_calls(self):
        """
        Multiple calls of get_image_dimensions() should return the same size.
        """
        from django.core.files.images import ImageFile

        img_path = os.path.join(os.path.dirname(upath(__file__)), "test.png")
        image = ImageFile(open(img_path, 'rb'))
        image_pil = Image.open(img_path)
        size_1, size_2 = get_image_dimensions(image), get_image_dimensions(image)
        self.assertEqual(image_pil.size, size_1)
        self.assertEqual(size_1, size_2)

class ContentFileTestCase(unittest.TestCase):

    def setUp(self):
        self.storage_dir = tempfile.mkdtemp()
        self.storage = FileSystemStorage(self.storage_dir)

    def tearDown(self):
        shutil.rmtree(self.storage_dir)

    def test_content_file_default_name(self):
        self.assertEqual(ContentFile(b"content").name, None)

    def test_content_file_custom_name(self):
        """
        Test that the constructor of ContentFile accepts 'name' (#16590).
        """
        name = "I can have a name too!"
        self.assertEqual(ContentFile(b"content", name=name).name, name)

    def test_content_file_input_type(self):
        """
        Test that ContentFile can accept both bytes and unicode and that the
        retrieved content is of the same type.
        """
        self.assertTrue(isinstance(ContentFile(b"content").read(), bytes))
        if six.PY3:
            self.assertTrue(isinstance(ContentFile("español").read(), six.text_type))
        else:
            self.assertTrue(isinstance(ContentFile("español").read(), bytes))

    def test_content_saving(self):
        """
        Test that ContentFile can be saved correctly with the filesystem storage,
        both if it was initialized with string or unicode content"""
        self.storage.save('bytes.txt', ContentFile(b"content"))
        self.storage.save('unicode.txt', ContentFile("español"))


class NoNameFileTestCase(unittest.TestCase):
    """
    Other examples of unnamed files may be tempfile.SpooledTemporaryFile or
    urllib.urlopen()
    """
    def test_noname_file_default_name(self):
        self.assertEqual(File(BytesIO(b'A file with no name')).name, None)

    def test_noname_file_get_size(self):
        self.assertEqual(File(BytesIO(b'A file with no name')).size, 19)

class FileLikeObjectTestCase(LiveServerBase):
    """
    Test file-like objects (#15644).
    """
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.storage = FileSystemStorage(location=self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_urllib2_urlopen(self):
        """
        Test the File storage API with a file like object coming from urllib2.urlopen()
        """

        file_like_object = self.urlopen('/example_view/')
        f = File(file_like_object)
        stored_filename = self.storage.save("remote_file.html", f)

        stored_file = self.storage.open(stored_filename)
        remote_file = self.urlopen('/example_view/')

        self.assertEqual(stored_file.read(), remote_file.read())
