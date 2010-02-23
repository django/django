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
from django.core.files.base import ContentFile
from django.core.files.images import get_image_dimensions
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import UploadedFile
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

class FileStorageTests(unittest.TestCase):
    storage_class = FileSystemStorage
    
    def setUp(self):
        self.temp_dir = tempfile.mktemp()
        os.makedirs(self.temp_dir)
        self.storage = self.storage_class(location=self.temp_dir)
    
    def tearDown(self):
        os.rmdir(self.temp_dir)
        
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
            self.assert_(os.path.exists(os.path.join(self.storage_dir, 'dotted.path/_.test')))
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
