import os

from django.core.exceptions import SuspiciousFileOperation
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage, Storage
from django.db.models import FileField
from django.test import SimpleTestCase


class AWSS3Storage(Storage):
    """
    Simulate an AWS S3 storage which uses Unix-like paths and allows any
    characters in file names but where there aren't actual folders but just
    keys.
    """
    prefix = 'mys3folder/'

    def _save(self, name, content):
        """
        This method is important to test that Storage.save() doesn't replace
        '\' with '/' (rather FileSystemStorage.save() does).
        """
        return name

    def get_valid_name(self, name):
        return name

    def get_available_name(self, name, max_length=None):
        return name

    def generate_filename(self, filename):
        """
        This is the method that's important to override when using S3 so that
        os.path() isn't called, which would break S3 keys.
        """
        return self.prefix + self.get_valid_name(filename)


class GenerateFilenameStorageTests(SimpleTestCase):
    def test_storage_dangerous_paths(self):
        candidates = [
            ('/tmp/..', '..'),
            ('/tmp/.', '.'),
            ('', ''),
        ]
        s = FileSystemStorage()
        msg = "Could not derive file name from '%s'"
        for file_name, base_name in candidates:
            with self.subTest(file_name=file_name):
                with self.assertRaisesMessage(SuspiciousFileOperation, msg % base_name):
                    s.get_available_name(file_name)
                with self.assertRaisesMessage(SuspiciousFileOperation, msg % base_name):
                    s.generate_filename(file_name)

    def test_storage_dangerous_paths_dir_name(self):
        candidates = [
            ('tmp/../path', 'tmp/..'),
            ('tmp\\..\\path', 'tmp/..'),
            ('/tmp/../path', '/tmp/..'),
            ('\\tmp\\..\\path', '/tmp/..'),
        ]
        s = FileSystemStorage()
        for file_name, path in candidates:
            msg = "Detected path traversal attempt in '%s'" % path
            with self.subTest(file_name=file_name):
                with self.assertRaisesMessage(SuspiciousFileOperation, msg):
                    s.get_available_name(file_name)
                with self.assertRaisesMessage(SuspiciousFileOperation, msg):
                    s.generate_filename(file_name)

    def test_filefield_dangerous_filename(self):
        candidates = [
            ('..', 'some/folder/..'),
            ('.', 'some/folder/.'),
            ('', 'some/folder/'),
            ('???', '???'),
            ('$.$.$', '$.$.$'),
        ]
        f = FileField(upload_to='some/folder/')
        for file_name, msg_file_name in candidates:
            msg = "Could not derive file name from '%s'" % msg_file_name
            with self.subTest(file_name=file_name):
                with self.assertRaisesMessage(SuspiciousFileOperation, msg):
                    f.generate_filename(None, file_name)

    def test_filefield_dangerous_filename_dot_segments(self):
        f = FileField(upload_to='some/folder/')
        msg = "Detected path traversal attempt in 'some/folder/../path'"
        with self.assertRaisesMessage(SuspiciousFileOperation, msg):
            f.generate_filename(None, '../path')

    def test_filefield_generate_filename_absolute_path(self):
        f = FileField(upload_to='some/folder/')
        candidates = [
            '/tmp/path',
            '/tmp/../path',
        ]
        for file_name in candidates:
            msg = "Detected path traversal attempt in '%s'" % file_name
            with self.subTest(file_name=file_name):
                with self.assertRaisesMessage(SuspiciousFileOperation, msg):
                    f.generate_filename(None, file_name)

    def test_filefield_generate_filename(self):
        f = FileField(upload_to='some/folder/')
        self.assertEqual(
            f.generate_filename(None, 'test with space.txt'),
            os.path.normpath('some/folder/test_with_space.txt')
        )

    def test_filefield_generate_filename_with_upload_to(self):
        def upload_to(instance, filename):
            return 'some/folder/' + filename

        f = FileField(upload_to=upload_to)
        self.assertEqual(
            f.generate_filename(None, 'test with space.txt'),
            os.path.normpath('some/folder/test_with_space.txt')
        )

    def test_filefield_generate_filename_upload_to_overrides_dangerous_filename(self):
        def upload_to(instance, filename):
            return 'test.txt'

        f = FileField(upload_to=upload_to)
        candidates = [
            '/tmp/.',
            '/tmp/..',
            '/tmp/../path',
            '/tmp/path',
            'some/folder/',
            'some/folder/.',
            'some/folder/..',
            'some/folder/???',
            'some/folder/$.$.$',
            'some/../test.txt',
            '',
        ]
        for file_name in candidates:
            with self.subTest(file_name=file_name):
                self.assertEqual(f.generate_filename(None, file_name), 'test.txt')

    def test_filefield_generate_filename_upload_to_absolute_path(self):
        def upload_to(instance, filename):
            return '/tmp/' + filename

        f = FileField(upload_to=upload_to)
        candidates = [
            'path',
            '../path',
            '???',
            '$.$.$',
        ]
        for file_name in candidates:
            msg = "Detected path traversal attempt in '/tmp/%s'" % file_name
            with self.subTest(file_name=file_name):
                with self.assertRaisesMessage(SuspiciousFileOperation, msg):
                    f.generate_filename(None, file_name)

    def test_filefield_generate_filename_upload_to_dangerous_filename(self):
        def upload_to(instance, filename):
            return '/tmp/' + filename

        f = FileField(upload_to=upload_to)
        candidates = ['..', '.', '']
        for file_name in candidates:
            msg = "Could not derive file name from '/tmp/%s'" % file_name
            with self.subTest(file_name=file_name):
                with self.assertRaisesMessage(SuspiciousFileOperation, msg):
                    f.generate_filename(None, file_name)

    def test_filefield_awss3_storage(self):
        """
        Simulate a FileField with an S3 storage which uses keys rather than
        folders and names. FileField and Storage shouldn't have any os.path()
        calls that break the key.
        """
        storage = AWSS3Storage()
        folder = 'not/a/folder/'

        f = FileField(upload_to=folder, storage=storage)
        key = 'my-file-key\\with odd characters'
        data = ContentFile('test')
        expected_key = AWSS3Storage.prefix + folder + key

        # Simulate call to f.save()
        result_key = f.generate_filename(None, key)
        self.assertEqual(result_key, expected_key)

        result_key = storage.save(result_key, data)
        self.assertEqual(result_key, expected_key)

        # Repeat test with a callable.
        def upload_to(instance, filename):
            # Return a non-normalized path on purpose.
            return folder + filename

        f = FileField(upload_to=upload_to, storage=storage)

        # Simulate call to f.save()
        result_key = f.generate_filename(None, key)
        self.assertEqual(result_key, expected_key)

        result_key = storage.save(result_key, data)
        self.assertEqual(result_key, expected_key)
