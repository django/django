# coding: utf-8
"""
Tests for the file storage mechanism

>>> import tempfile
>>> from django.core.files.storage import FileSystemStorage
>>> from django.core.files.base import ContentFile

# Set up a unique temporary directory
>>> import os
>>> temp_dir = tempfile.mktemp()
>>> os.makedirs(temp_dir)

>>> temp_storage = FileSystemStorage(location=temp_dir)

# Standard file access options are available, and work as expected.

>>> temp_storage.exists('storage_test')
False
>>> file = temp_storage.open('storage_test', 'w')
>>> file.write('storage contents')
>>> file.close()

>>> temp_storage.exists('storage_test')
True
>>> file = temp_storage.open('storage_test', 'r')
>>> file.read()
'storage contents'
>>> file.close()

>>> temp_storage.delete('storage_test')
>>> temp_storage.exists('storage_test')
False

# Files can only be accessed if they're below the specified location.

>>> temp_storage.exists('..')
Traceback (most recent call last):
...
SuspiciousOperation: Attempted access to '..' denied.
>>> temp_storage.open('/etc/passwd')
Traceback (most recent call last):
  ...
SuspiciousOperation: Attempted access to '/etc/passwd' denied.

# Custom storage systems can be created to customize behavior

>>> class CustomStorage(FileSystemStorage):
...     def get_available_name(self, name):
...         # Append numbers to duplicate files rather than underscores, like Trac
...
...         parts = name.split('.')
...         basename, ext = parts[0], parts[1:]
...         number = 2
...
...         while self.exists(name):
...             name = '.'.join([basename, str(number)] + ext)
...             number += 1
...
...         return name
>>> custom_storage = CustomStorage(temp_dir)

>>> first = custom_storage.save('custom_storage', ContentFile('custom contents'))
>>> first
u'custom_storage'
>>> second = custom_storage.save('custom_storage', ContentFile('more contents'))
>>> second
u'custom_storage.2'

>>> custom_storage.delete(first)
>>> custom_storage.delete(second)

# Cleanup the temp dir
>>> os.rmdir(temp_dir)


# Regression test for #8156: files with unicode names I can't quite figure out the
# encoding situation between doctest and this file, but the actual repr doesn't
# matter; it just shouldn't return a unicode object.
>>> from django.core.files.uploadedfile import UploadedFile
>>> uf = UploadedFile(name=u'¿Cómo?',content_type='text')
>>> uf.__repr__()
'<UploadedFile: ... (text)>'
"""

# Tests for a race condition on file saving (#4948).
# This is written in such a way that it'll always pass on platforms
# without threading.
import os
import time
import shutil
import sys
import tempfile
from unittest import TestCase
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
try:
    import threading
except ImportError:
    import dummy_threading as threading

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
        self.assert_(self.storage.exists('conflict_'))
        self.storage.delete('conflict')
        self.storage.delete('conflict_')

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

        self.assertFalse(os.path.exists(os.path.join(self.storage_dir, 'dotted_.path')))
        self.assertTrue(os.path.exists(os.path.join(self.storage_dir, 'dotted.path/test')))
        self.assertTrue(os.path.exists(os.path.join(self.storage_dir, 'dotted.path/test_')))

    def test_first_character_dot(self):
        """
        File names with a dot as their first character don't have an extension,
        and the underscore should get added to the end.
        """
        self.storage.save('dotted.path/.test', ContentFile("1"))
        self.storage.save('dotted.path/.test', ContentFile("2"))

        self.assertTrue(os.path.exists(os.path.join(self.storage_dir, 'dotted.path/.test')))
        # Before 2.6, a leading dot was treated as an extension, and so
        # underscore gets added to beginning instead of end.
        if sys.version_info < (2, 6):
            self.assertTrue(os.path.exists(os.path.join(self.storage_dir, 'dotted.path/_.test')))
        else:
            self.assertTrue(os.path.exists(os.path.join(self.storage_dir, 'dotted.path/.test_')))
