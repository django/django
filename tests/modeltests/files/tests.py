from __future__ import with_statement, absolute_import

import shutil
import tempfile

from django.core.cache import cache
from django.core.files import File
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import six

from .models import Storage, temp_storage, temp_storage_location


FILE_SUFFIX_REGEX = '[A-Za-z0-9]{7}'


class FileTests(TestCase):
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
        self.assertEqual(obj1.normal.read(), "content")
        obj1.normal.close()

        # File objects can be assigned to FileField attributes, but shouldn't
        # get committed until the model it's attached to is saved.
        obj1.normal = SimpleUploadedFile("assignment.txt", "content")
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
        self.assertEqual(obj1.normal.read(3), "con")
        self.assertEqual(obj1.normal.read(), "tent")
        self.assertEqual(list(obj1.normal.chunks(chunk_size=2)), ["co", "nt", "en", "t"])
        obj1.normal.close()

        # Save another file with the same name.
        obj2 = Storage()
        obj2.normal.save("django_test.txt", ContentFile("more content"))
        obj2_name = obj2.normal.name
        six.assertRegex(self, obj2_name, "tests/django_test_%s.txt" % FILE_SUFFIX_REGEX)
        self.assertEqual(obj2.normal.size, 12)

        # Push the objects into the cache to make sure they pickle properly
        cache.set("obj1", obj1)
        cache.set("obj2", obj2)
        six.assertRegex(self, cache.get("obj2").normal.name, "tests/django_test_%s.txt" % FILE_SUFFIX_REGEX)

        # Deleting an object does not delete the file it uses.
        obj2.delete()
        obj2.normal.save("django_test.txt", ContentFile("more content"))
        self.assertNotEqual(obj2_name, obj2.normal.name)
        six.assertRegex(self, obj2.normal.name, "tests/django_test_%s.txt" % FILE_SUFFIX_REGEX)

        # Multiple files with the same name get _N appended to them.
        objs = [Storage() for i in range(2)]
        for o in objs:
            o.normal.save("multiple_files.txt", ContentFile("Same Content"))
        names = [o.normal.name for o in objs]
        self.assertEqual(names[0], "tests/multiple_files.txt")
        six.assertRegex(self, names[1], "tests/multiple_files_%s.txt" % FILE_SUFFIX_REGEX)
        for o in objs:
            o.delete()

        # Default values allow an object to access a single file.
        obj3 = Storage.objects.create()
        self.assertEqual(obj3.default.name, "tests/default.txt")
        self.assertEqual(obj3.default.read(), "default content")
        obj3.default.close()

        # But it shouldn't be deleted, even if there are no more objects using
        # it.
        obj3.delete()
        obj3 = Storage()
        self.assertEqual(obj3.default.read(), "default content")
        obj3.default.close()

        # Verify the fix for #5655, making sure the directory is only
        # determined once.
        obj4 = Storage()
        obj4.random.save("random_file", ContentFile("random content"))
        self.assertTrue(obj4.random.name.endswith("/random_file"))

        # Clean up the temporary files and dir.
        obj1.normal.delete()
        obj2.normal.delete()
        obj3.default.delete()
        obj4.random.delete()

    def test_context_manager(self):
        orig_file = tempfile.TemporaryFile()
        base_file = File(orig_file)
        with base_file as f:
            self.assertIs(base_file, f)
            self.assertFalse(f.closed)
        self.assertTrue(f.closed)
        self.assertTrue(orig_file.closed)
