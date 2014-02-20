from __future__ import absolute_import

from io import BytesIO
import os
import gzip
import shutil
import tempfile

from django.core.cache import cache
from django.core.files import File
from django.core.files.move import file_move_safe
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files.temp import NamedTemporaryFile
from django.test import TestCase
from django.utils import unittest
from django.utils.six import StringIO

from .models import Storage, temp_storage, temp_storage_location


class FileStorageTests(TestCase):
    def tearDown(self):
        shutil.rmtree(temp_storage_location)

    def test_files(self):
        temp_storage.save('tests/default.txt', ContentFile('default content'))
        # Attempting to access a FileField from the class raises a descriptive
        # error
        self.assertRaises(AttributeError, lambda: Storage.normal)

        # An object without a file has limited functionality.
        obj1 = Storage()
        self.assertEqual(obj1.normal.name, "")
        self.assertRaises(ValueError, lambda: obj1.normal.size)

        # Saving a file enables full functionality.
        obj1.normal.save("django_test.txt", ContentFile("content"))
        self.assertEqual(obj1.normal.name, "tests/django_test.txt")
        self.assertEqual(obj1.normal.size, 7)
        self.assertEqual(obj1.normal.read(), b"content")
        obj1.normal.close()

        # File objects can be assigned to FileField attributes, but shouldn't
        # get committed until the model it's attached to is saved.
        obj1.normal = SimpleUploadedFile("assignment.txt", b"content")
        dirs, files = temp_storage.listdir("tests")
        self.assertEqual(dirs, [])
        self.assertEqual(sorted(files), ["default.txt", "django_test.txt"])

        obj1.save()
        dirs, files = temp_storage.listdir("tests")
        self.assertEqual(
            sorted(files), ["assignment.txt", "default.txt", "django_test.txt"]
        )

        # Files can be read in a little at a time, if necessary.
        obj1.normal.open()
        self.assertEqual(obj1.normal.read(3), b"con")
        self.assertEqual(obj1.normal.read(), b"tent")
        self.assertEqual(list(obj1.normal.chunks(chunk_size=2)), [b"co", b"nt", b"en", b"t"])
        obj1.normal.close()

        # Save another file with the same name.
        obj2 = Storage()
        obj2.normal.save("django_test.txt", ContentFile("more content"))
        self.assertEqual(obj2.normal.name, "tests/django_test_1.txt")
        self.assertEqual(obj2.normal.size, 12)

        # Push the objects into the cache to make sure they pickle properly
        cache.set("obj1", obj1)
        cache.set("obj2", obj2)
        self.assertEqual(cache.get("obj2").normal.name, "tests/django_test_1.txt")

        # Deleting an object does not delete the file it uses.
        obj2.delete()
        obj2.normal.save("django_test.txt", ContentFile("more content"))
        self.assertEqual(obj2.normal.name, "tests/django_test_2.txt")

        # Multiple files with the same name get _N appended to them.
        objs = [Storage() for i in range(3)]
        for o in objs:
            o.normal.save("multiple_files.txt", ContentFile("Same Content"))
        self.assertEqual(
            [o.normal.name for o in objs],
            ["tests/multiple_files.txt", "tests/multiple_files_1.txt", "tests/multiple_files_2.txt"]
        )
        for o in objs:
            o.delete()

        # Default values allow an object to access a single file.
        obj3 = Storage.objects.create()
        self.assertEqual(obj3.default.name, "tests/default.txt")
        self.assertEqual(obj3.default.read(), b"default content")
        obj3.default.close()

        # But it shouldn't be deleted, even if there are no more objects using
        # it.
        obj3.delete()
        obj3 = Storage()
        self.assertEqual(obj3.default.read(), b"default content")
        obj3.default.close()

        # Verify the fix for #5655, making sure the directory is only
        # determined once.
        obj4 = Storage()
        obj4.random.save("random_file", ContentFile("random content"))
        self.assertTrue(obj4.random.name.endswith("/random_file"))

    def test_file_object(self):
        # Create sample file
        temp_storage.save('tests/example.txt', ContentFile('some content'))

        # Load it as python file object
        with open(temp_storage.path('tests/example.txt')) as file_obj:
            # Save it using storage and read its content
            temp_storage.save('tests/file_obj', file_obj)
        self.assertTrue(temp_storage.exists('tests/file_obj'))
        with temp_storage.open('tests/file_obj') as f:
            self.assertEqual(f.read(), b'some content')


    def test_stringio(self):
        # Test passing StringIO instance as content argument to save
        output = StringIO()
        output.write('content')
        output.seek(0)

        # Save it and read written file
        temp_storage.save('tests/stringio', output)
        self.assertTrue(temp_storage.exists('tests/stringio'))
        with temp_storage.open('tests/stringio') as f:
            self.assertEqual(f.read(), b'content')



class FileTests(unittest.TestCase):
    def test_context_manager(self):
        orig_file = tempfile.TemporaryFile()
        base_file = File(orig_file)
        with base_file as f:
            self.assertIs(base_file, f)
            self.assertFalse(f.closed)
        self.assertTrue(f.closed)
        self.assertTrue(orig_file.closed)

    def test_namedtemporaryfile_closes(self):
        """
        The symbol django.core.files.NamedTemporaryFile is assigned as
        a different class on different operating systems. In
        any case, the result should minimally mock some of the API of
        tempfile.NamedTemporaryFile from the Python standard library.
        """
        tempfile = NamedTemporaryFile()
        self.assertTrue(hasattr(tempfile, "closed"))
        self.assertFalse(tempfile.closed)

        tempfile.close()
        self.assertTrue(tempfile.closed)

    def test_file_mode(self):
        # Should not set mode to None if it is not present.
        # See #14681, stdlib gzip module crashes if mode is set to None
        file = SimpleUploadedFile("mode_test.txt", b"content")
        self.assertFalse(hasattr(file, 'mode'))
        g = gzip.GzipFile(fileobj=file)

    def test_file_iteration(self):
        """
        File objects should yield lines when iterated over.
        Refs #22107.
        """
        file = File(BytesIO(b'one\ntwo\nthree'))
        self.assertEqual(list(file), [b'one\n', b'two\n', b'three'])


class FileMoveSafeTests(unittest.TestCase):
    def test_file_move_overwrite(self):
        handle_a, self.file_a = tempfile.mkstemp(dir=os.environ['DJANGO_TEST_TEMP_DIR'])
        handle_b, self.file_b = tempfile.mkstemp(dir=os.environ['DJANGO_TEST_TEMP_DIR'])

        # file_move_safe should raise an IOError exception if destination file exists and allow_overwrite is False
        self.assertRaises(IOError, lambda: file_move_safe(self.file_a, self.file_b, allow_overwrite=False))

        # should allow it and continue on if allow_overwrite is True
        self.assertIsNone(file_move_safe(self.file_a, self.file_b, allow_overwrite=True))

        os.close(handle_a)
        os.close(handle_b)
