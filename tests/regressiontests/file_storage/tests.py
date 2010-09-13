# -*- coding: utf-8 -*-
import os
import shutil
import sys
import tempfile
import time
import unittest
from cStringIO import StringIO
from django.conf import settings
from django.core.exceptions import SuspiciousOperation
from django.core.files.base import ContentFile, File
from django.core.files.images import get_image_dimensions
from django.core.files.storage import FileSystemStorage, get_storage_class
from django.core.files.uploadedfile import UploadedFile
from django.core.exceptions import ImproperlyConfigured
from unittest import TestCase
try:
    import threading
except ImportError:
    import dummy_threading as threading

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

class GetStorageClassTests(unittest.TestCase):
    def assertRaisesErrorWithMessage(self, error, message, callable,
        *args, **kwargs):
        self.assertRaises(error, callable, *args, **kwargs)
        try:
            callable(*args, **kwargs)
        except error, e:
            self.assertEqual(message, str(e))

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
        self.assertRaisesErrorWithMessage(
            ImproperlyConfigured,
            "NonExistingStorage isn't a storage module.",
            get_storage_class,
            'NonExistingStorage')

    def test_get_nonexisting_storage_class(self):
        """
        get_storage_class raises an error if the requested class don't exist.
        """
        self.assertRaisesErrorWithMessage(
            ImproperlyConfigured,
            'Storage module "django.core.files.storage" does not define a '\
                '"NonExistingStorage" class.',
            get_storage_class,
            'django.core.files.storage.NonExistingStorage')

    def test_get_nonexisting_storage_module(self):
        """
        get_storage_class raises an error if the requested module don't exist.
        """
        self.assertRaisesErrorWithMessage(
            ImproperlyConfigured,
            'Error importing storage module django.core.files.non_existing_'\
                'storage: "No module named non_existing_storage"',
            get_storage_class,
            'django.core.files.non_existing_storage.NonExistingStorage')

class FileStorageTests(unittest.TestCase):
    storage_class = FileSystemStorage
    
    def setUp(self):
        self.temp_dir = tempfile.mktemp()
        os.makedirs(self.temp_dir)
        self.storage = self.storage_class(location=self.temp_dir,
            base_url='/test_media_url/')
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir)
        
    def test_file_access_options(self):
        """
        Standard file access options are available, and work as expected.
        """
        self.failIf(self.storage.exists('storage_test'))
        f = self.storage.open('storage_test', 'w')
        f.write('storage contents')
        f.close()
        self.assert_(self.storage.exists('storage_test'))

        f = self.storage.open('storage_test', 'r')
        self.assertEqual(f.read(), 'storage contents')
        f.close()
        
        self.storage.delete('storage_test')
        self.failIf(self.storage.exists('storage_test'))

    def test_file_save_without_name(self):
        """
        File storage extracts the filename from the content object if no
        name is given explicitly.
        """
        self.failIf(self.storage.exists('test.file'))

        f = ContentFile('custom contents')
        f.name = 'test.file'

        storage_f_name = self.storage.save(None, f)

        self.assertEqual(storage_f_name, f.name)

        self.assert_(os.path.exists(os.path.join(self.temp_dir, f.name)))

        self.storage.delete(storage_f_name)

    def test_file_path(self):
        """
        File storage returns the full path of a file
        """
        self.failIf(self.storage.exists('test.file'))

        f = ContentFile('custom contents')
        f_name = self.storage.save('test.file', f)

        self.assertEqual(self.storage.path(f_name),
            os.path.join(self.temp_dir, f_name))

        self.storage.delete(f_name)

    def test_file_url(self):
        """
        File storage returns a url to access a given file from the web.
        """
        self.assertEqual(self.storage.url('test.file'),
            '%s%s' % (self.storage.base_url, 'test.file'))

        self.storage.base_url = None
        self.assertRaises(ValueError, self.storage.url, 'test.file')

    def test_file_with_mixin(self):
        """
        File storage can get a mixin to extend the functionality of the
        returned file.
        """
        self.failIf(self.storage.exists('test.file'))

        class TestFileMixin(object):
            mixed_in = True

        f = ContentFile('custom contents')
        f_name = self.storage.save('test.file', f)

        self.assert_(isinstance(
            self.storage.open('test.file', mixin=TestFileMixin),
            TestFileMixin
        ))

        self.storage.delete('test.file')

    def test_listdir(self):
        """
        File storage returns a tuple containing directories and files.
        """
        self.failIf(self.storage.exists('storage_test_1'))
        self.failIf(self.storage.exists('storage_test_2'))
        self.failIf(self.storage.exists('storage_dir_1'))

        f = self.storage.save('storage_test_1', ContentFile('custom content'))
        f = self.storage.save('storage_test_2', ContentFile('custom content'))
        os.mkdir(os.path.join(self.temp_dir, 'storage_dir_1'))

        dirs, files = self.storage.listdir('')
        self.assertEqual(set(dirs), set([u'storage_dir_1']))
        self.assertEqual(set(files),
                         set([u'storage_test_1', u'storage_test_2']))

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
        uf = UploadedFile(name=u'¿Cómo?',content_type='text')
        self.assertEqual(type(uf.__repr__()), str)

# Tests for a race condition on file saving (#4948).
# This is written in such a way that it'll always pass on platforms
# without threading.

class SlowFile(ContentFile):
    def chunks(self):
        time.sleep(1)
        return super(ContentFile, self).chunks()

class FileSaveRaceConditionTest(TestCase):
    def setUp(self):
        self.storage_dir = tempfile.mkdtemp()
        self.storage = FileSystemStorage(self.storage_dir)
        self.thread = threading.Thread(target=self.save_file, args=['conflict'])

    def tearDown(self):
        shutil.rmtree(self.storage_dir)

    def save_file(self, name):
        name = self.storage.save(name, SlowFile("Data"))

    def test_race_condition(self):
        self.thread.start()
        name = self.save_file('conflict')
        self.thread.join()
        self.assert_(self.storage.exists('conflict'))
        self.assert_(self.storage.exists('conflict_1'))
        self.storage.delete('conflict')
        self.storage.delete('conflict_1')

class FileStoragePermissions(TestCase):
    def setUp(self):
        self.old_perms = settings.FILE_UPLOAD_PERMISSIONS
        settings.FILE_UPLOAD_PERMISSIONS = 0666
        self.storage_dir = tempfile.mkdtemp()
        self.storage = FileSystemStorage(self.storage_dir)

    def tearDown(self):
        settings.FILE_UPLOAD_PERMISSIONS = self.old_perms
        shutil.rmtree(self.storage_dir)

    def test_file_upload_permissions(self):
        name = self.storage.save("the_file", ContentFile("data"))
        actual_mode = os.stat(self.storage.path(name))[0] & 0777
        self.assertEqual(actual_mode, 0666)


class FileStoragePathParsing(TestCase):
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

        self.failIf(os.path.exists(os.path.join(self.storage_dir, 'dotted_.path')))
        self.assert_(os.path.exists(os.path.join(self.storage_dir, 'dotted.path/test')))
        self.assert_(os.path.exists(os.path.join(self.storage_dir, 'dotted.path/test_1')))

    def test_first_character_dot(self):
        """
        File names with a dot as their first character don't have an extension,
        and the underscore should get added to the end.
        """
        self.storage.save('dotted.path/.test', ContentFile("1"))
        self.storage.save('dotted.path/.test', ContentFile("2"))

        self.assert_(os.path.exists(os.path.join(self.storage_dir, 'dotted.path/.test')))
        # Before 2.6, a leading dot was treated as an extension, and so
        # underscore gets added to beginning instead of end.
        if sys.version_info < (2, 6):
            self.assert_(os.path.exists(os.path.join(self.storage_dir, 'dotted.path/_1.test')))
        else:
            self.assert_(os.path.exists(os.path.join(self.storage_dir, 'dotted.path/.test_1')))

if Image is not None:
    class DimensionClosingBug(TestCase):
        """
        Test that get_image_dimensions() properly closes files (#8817)
        """
        def test_not_closing_of_files(self):
            """
            Open files passed into get_image_dimensions() should stay opened.
            """
            empty_io = StringIO()
            try:
                get_image_dimensions(empty_io)
            finally:
                self.assert_(not empty_io.closed)

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
                get_image_dimensions(os.path.join(os.path.dirname(__file__), "test1.png"))
            finally:
                del images.open
            self.assert_(FileWrapper._closed)

    class InconsistentGetImageDimensionsBug(TestCase):
        """
        Test that get_image_dimensions() works properly after various calls using a file handler (#11158)
        """
        def test_multiple_calls(self):
            """
            Multiple calls of get_image_dimensions() should return the same size.
            """
            from django.core.files.images import ImageFile
            img_path = os.path.join(os.path.dirname(__file__), "test.png")
            image = ImageFile(open(img_path))
            image_pil = Image.open(img_path)
            size_1, size_2 = get_image_dimensions(image), get_image_dimensions(image)
            self.assertEqual(image_pil.size, size_1)
            self.assertEqual(size_1, size_2)
