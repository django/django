import random
import shutil
import os

from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files.base import ContentFile
from django.core.cache import cache

from models import Storage, temp_storage, temp_storage_location

def make_obj():
    obj = Storage()
    obj.normal.save('django_test.txt', ContentFile('content'))
    return obj

class CustomFileStorageTestCase(TestCase):
    def setUp(self):
        #recreate our temp dir if necessary
        if not os.path.exists(temp_storage_location):
            os.mkdir(temp_storage_location)
        # Write out a file to be used as default content
        temp_storage.save('tests/default.txt', ContentFile('default content'))

    def tearDown(self):
        #remove the temp dir after each test
        shutil.rmtree(temp_storage_location)

    def test_access_from_class(self):
        # Attempting to access a FileField from the class raises a
        # descriptive error
        self.assertRaises(AttributeError,
                          getattr,
                          Storage, 'normal')

    def test_object_without_file(self):
        # An object without a file has limited functionality.
        obj = Storage()
        self.assertEqual(repr(obj.normal), '<FieldFile: None>')
        self.assertRaises(ValueError,
                          getattr,
                          obj.normal, 'size') 

    def test_basic_saved_file(self):
        # Saving a file enables full functionality.
        obj = Storage()
        obj.normal.save('django_test.txt', ContentFile('content'))
        self.assertEqual(repr(obj.normal), '<FieldFile: tests/django_test.txt>')
        self.assertEqual(obj.normal.size, 7)
        self.assertEqual(obj.normal.read(), 'content') 


    def test_attribute_assignment(self):
        # File objects can be assigned to FileField attributes, but
        # shouldn't get committed until the model it's attached to is
        # saved.
        obj = Storage()
        obj.normal = SimpleUploadedFile('assignment.txt', 'content')
        dirs, files = temp_storage.listdir('tests')
        self.assertEqual(len(dirs), 0)
        self.assertEqual(files, ['default.txt'])
        obj.save()
        dirs, files = temp_storage.listdir('tests')
        files.sort()
        self.assertEqual(files, ['assignment.txt', 'default.txt'])

    def test_file_read(self):
        # Files can be read in a little at a time, if necessary.
        obj = make_obj()
        obj.normal.open()
        self.assertEqual(obj.normal.read(3), 'con')
        self.assertEqual(obj.normal.read(), 'tent')
        self.assertEqual('-'.join(obj.normal.chunks(chunk_size=2)),
                         'co-nt-en-t')

    def test_file_duplicate_name(self):
        # Save another file with the same name.
        obj = make_obj()
        obj2 = Storage()
        obj2.normal.save('django_test.txt', ContentFile('more content'))
        self.assertEqual(repr(obj2.normal), 
                         "<FieldFile: tests/django_test_1.txt>")
        self.assertEqual(obj2.normal.size, 12)

    def test_object_pickling(self):
        # Push the objects into the cache to make sure they pickle properly
        obj = make_obj()
        cache.set('obj', obj)
        self.assertEqual(repr(cache.get('obj').normal),
                         "<FieldFile: tests/django_test.txt>")

    def test_delete(self):
        # Deleting an object deletes the file it uses, if there are no
        # other objects still using that file.
        obj = make_obj()
        obj.delete()
        obj.normal.save('django_test.txt', ContentFile('more content'))
        self.assertEqual(repr(obj.normal),
                         "<FieldFile: tests/django_test.txt>")

    def test_duplicate_file_name_differentiation(self):
        # Multiple files with the same name get _N appended to them.
        objs = [Storage() for i in range(3)]
        for o in objs:
            o.normal.save('multiple_files.txt', ContentFile('Same Content'))
        self.assertEqual(repr([o.normal for o in objs]),
                         "[<FieldFile: tests/multiple_files.txt>, <FieldFile: tests/multiple_files_1.txt>, <FieldFile: tests/multiple_files_2.txt>]")

    def test_default_values(self):
        # Default values allow an object to access a single file.
        obj = Storage.objects.create()
        self.assertEqual(repr(obj.default), "<FieldFile: tests/default.txt>")
        self.assertEqual(obj.default.read(), 'default content')

        # But it shouldn't be deleted, even if there are no more
        # objects using it.
        obj.delete()
        obj = Storage()
        self.assertEqual(obj.default.read(), 'default content')

    def test_directory_determined_once(self):
        # Verify the fix for #5655, making sure the directory is only
        # determined once.
        obj = Storage()
        obj.random.save('random_file', ContentFile('random content'))
        self.assertEqual(obj.random.read(), 'random content')
