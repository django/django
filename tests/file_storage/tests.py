import os
import shutil
import sys
import tempfile
import threading
import time
import unittest
from datetime import datetime, timedelta
from io import StringIO
from pathlib import Path
from urllib.request import urlopen

from django.core.cache import cache
from django.core.exceptions import SuspiciousFileOperation
from django.core.files.base import ContentFile, File
from django.core.files.storage import FileSystemStorage, get_storage_class
from django.core.files.uploadedfile import (
    InMemoryUploadedFile, SimpleUploadedFile, TemporaryUploadedFile,
)
from django.db.models.fields.files import FileDescriptor
from django.test import (
    LiveServerTestCase, SimpleTestCase, TestCase, override_settings,
)
from django.test.utils import requires_tz_support
from django.urls import NoReverseMatch, reverse_lazy
from django.utils import timezone

from .models import Storage, temp_storage, temp_storage_location

FILE_SUFFIX_REGEX = '[A-Za-z0-9]{7}'


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
        with self.assertRaisesMessage(ImportError, "No module named 'storage'"):
            get_storage_class('storage.NonexistentStorage')

    def test_get_nonexistent_storage_class(self):
        """
        get_storage_class raises an error if the requested class don't exist.
        """
        with self.assertRaises(ImportError):
            get_storage_class('django.core.files.storage.NonexistentStorage')

    def test_get_nonexistent_storage_module(self):
        """
        get_storage_class raises an error if the requested module don't exist.
        """
        with self.assertRaisesMessage(ImportError, "No module named 'django.core.files.nonexistent_storage'"):
            get_storage_class('django.core.files.nonexistent_storage.NonexistentStorage')


class FileSystemStorageTests(unittest.TestCase):

    def test_deconstruction(self):
        path, args, kwargs = temp_storage.deconstruct()
        self.assertEqual(path, "django.core.files.storage.FileSystemStorage")
        self.assertEqual(args, ())
        self.assertEqual(kwargs, {'location': temp_storage_location})

        kwargs_orig = {
            'location': temp_storage_location,
            'base_url': 'http://myfiles.example.com/'
        }
        storage = FileSystemStorage(**kwargs_orig)
        path, args, kwargs = storage.deconstruct()
        self.assertEqual(kwargs, kwargs_orig)

    def test_lazy_base_url_init(self):
        """
        FileSystemStorage.__init__() shouldn't evaluate base_url.
        """
        storage = FileSystemStorage(base_url=reverse_lazy('app:url'))
        with self.assertRaises(NoReverseMatch):
            storage.url(storage.base_url)


class FileStorageTests(SimpleTestCase):
    storage_class = FileSystemStorage

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.storage = self.storage_class(location=self.temp_dir, base_url='/test_media_url/')
        # Set up a second temporary directory which is ensured to have a mixed
        # case name.
        self.temp_dir2 = tempfile.mkdtemp(suffix='aBc')

    def tearDown(self):
        shutil.rmtree(self.temp_dir)
        shutil.rmtree(self.temp_dir2)

    def test_empty_location(self):
        """
        Makes sure an exception is raised if the location is empty
        """
        storage = self.storage_class(location='')
        self.assertEqual(storage.base_location, '')
        self.assertEqual(storage.location, os.getcwd())

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

    def _test_file_time_getter(self, getter):
        # Check for correct behavior under both USE_TZ=True and USE_TZ=False.
        # The tests are similar since they both set up a situation where the
        # system time zone, Django's TIME_ZONE, and UTC are distinct.
        self._test_file_time_getter_tz_handling_on(getter)
        self._test_file_time_getter_tz_handling_off(getter)

    @override_settings(USE_TZ=True, TIME_ZONE='Africa/Algiers')
    def _test_file_time_getter_tz_handling_on(self, getter):
        # Django's TZ (and hence the system TZ) is set to Africa/Algiers which
        # is UTC+1 and has no DST change. We can set the Django TZ to something
        # else so that UTC, Django's TIME_ZONE, and the system timezone are all
        # different.
        now_in_algiers = timezone.make_aware(datetime.now())

        with timezone.override(timezone.get_fixed_timezone(-300)):
            # At this point the system TZ is +1 and the Django TZ
            # is -5. The following will be aware in UTC.
            now = timezone.now()
            self.assertFalse(self.storage.exists('test.file.tz.on'))

            f = ContentFile('custom contents')
            f_name = self.storage.save('test.file.tz.on', f)
            self.addCleanup(self.storage.delete, f_name)
            dt = getter(f_name)
            # dt should be aware, in UTC
            self.assertTrue(timezone.is_aware(dt))
            self.assertEqual(now.tzname(), dt.tzname())

            # The three timezones are indeed distinct.
            naive_now = datetime.now()
            algiers_offset = now_in_algiers.tzinfo.utcoffset(naive_now)
            django_offset = timezone.get_current_timezone().utcoffset(naive_now)
            utc_offset = timezone.utc.utcoffset(naive_now)
            self.assertGreater(algiers_offset, utc_offset)
            self.assertLess(django_offset, utc_offset)

            # dt and now should be the same effective time.
            self.assertLess(abs(dt - now), timedelta(seconds=2))

    @override_settings(USE_TZ=False, TIME_ZONE='Africa/Algiers')
    def _test_file_time_getter_tz_handling_off(self, getter):
        # Django's TZ (and hence the system TZ) is set to Africa/Algiers which
        # is UTC+1 and has no DST change. We can set the Django TZ to something
        # else so that UTC, Django's TIME_ZONE, and the system timezone are all
        # different.
        now_in_algiers = timezone.make_aware(datetime.now())

        with timezone.override(timezone.get_fixed_timezone(-300)):
            # At this point the system TZ is +1 and the Django TZ
            # is -5.
            self.assertFalse(self.storage.exists('test.file.tz.off'))

            f = ContentFile('custom contents')
            f_name = self.storage.save('test.file.tz.off', f)
            self.addCleanup(self.storage.delete, f_name)
            dt = getter(f_name)
            # dt should be naive, in system (+1) TZ
            self.assertTrue(timezone.is_naive(dt))

            # The three timezones are indeed distinct.
            naive_now = datetime.now()
            algiers_offset = now_in_algiers.tzinfo.utcoffset(naive_now)
            django_offset = timezone.get_current_timezone().utcoffset(naive_now)
            utc_offset = timezone.utc.utcoffset(naive_now)
            self.assertGreater(algiers_offset, utc_offset)
            self.assertLess(django_offset, utc_offset)

            # dt and naive_now should be the same effective time.
            self.assertLess(abs(dt - naive_now), timedelta(seconds=2))
            # If we convert dt to an aware object using the Algiers
            # timezone then it should be the same effective time to
            # now_in_algiers.
            _dt = timezone.make_aware(dt, now_in_algiers.tzinfo)
            self.assertLess(abs(_dt - now_in_algiers), timedelta(seconds=2))

    def test_file_get_accessed_time(self):
        """
        File storage returns a Datetime object for the last accessed time of
        a file.
        """
        self.assertFalse(self.storage.exists('test.file'))

        f = ContentFile('custom contents')
        f_name = self.storage.save('test.file', f)
        self.addCleanup(self.storage.delete, f_name)
        atime = self.storage.get_accessed_time(f_name)

        self.assertEqual(atime, datetime.fromtimestamp(os.path.getatime(self.storage.path(f_name))))
        self.assertLess(timezone.now() - self.storage.get_accessed_time(f_name), timedelta(seconds=2))

    @requires_tz_support
    def test_file_get_accessed_time_timezone(self):
        self._test_file_time_getter(self.storage.get_accessed_time)

    def test_file_get_created_time(self):
        """
        File storage returns a datetime for the creation time of a file.
        """
        self.assertFalse(self.storage.exists('test.file'))

        f = ContentFile('custom contents')
        f_name = self.storage.save('test.file', f)
        self.addCleanup(self.storage.delete, f_name)
        ctime = self.storage.get_created_time(f_name)

        self.assertEqual(ctime, datetime.fromtimestamp(os.path.getctime(self.storage.path(f_name))))
        self.assertLess(timezone.now() - self.storage.get_created_time(f_name), timedelta(seconds=2))

    @requires_tz_support
    def test_file_get_created_time_timezone(self):
        self._test_file_time_getter(self.storage.get_created_time)

    def test_file_get_modified_time(self):
        """
        File storage returns a datetime for the last modified time of a file.
        """
        self.assertFalse(self.storage.exists('test.file'))

        f = ContentFile('custom contents')
        f_name = self.storage.save('test.file', f)
        self.addCleanup(self.storage.delete, f_name)
        mtime = self.storage.get_modified_time(f_name)

        self.assertEqual(mtime, datetime.fromtimestamp(os.path.getmtime(self.storage.path(f_name))))
        self.assertLess(timezone.now() - self.storage.get_modified_time(f_name), timedelta(seconds=2))

    @requires_tz_support
    def test_file_get_modified_time_timezone(self):
        self._test_file_time_getter(self.storage.get_modified_time)

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
        self.storage.save('path/to/test.file', ContentFile('file saved with path'))

        self.assertTrue(self.storage.exists('path/to'))
        with self.storage.open('path/to/test.file') as f:
            self.assertEqual(f.read(), b'file saved with path')

        self.assertTrue(os.path.exists(
            os.path.join(self.temp_dir, 'path', 'to', 'test.file')))

        self.storage.delete('path/to/test.file')

    def test_save_doesnt_close(self):
        with TemporaryUploadedFile('test', 'text/plain', 1, 'utf8') as file:
            file.write(b'1')
            file.seek(0)
            self.assertFalse(file.closed)
            self.storage.save('path/to/test.file', file)
            self.assertFalse(file.closed)
            self.assertFalse(file.file.closed)

        file = InMemoryUploadedFile(StringIO('1'), '', 'test', 'text/plain', 1, 'utf8')
        with file:
            self.assertFalse(file.closed)
            self.storage.save('path/to/test.file', file)
            self.assertFalse(file.closed)
            self.assertFalse(file.file.closed)

    def test_file_path(self):
        """
        File storage returns the full path of a file
        """
        self.assertFalse(self.storage.exists('test.file'))

        f = ContentFile('custom contents')
        f_name = self.storage.save('test.file', f)

        self.assertEqual(self.storage.path(f_name), os.path.join(self.temp_dir, f_name))

        self.storage.delete(f_name)

    def test_file_url(self):
        """
        File storage returns a url to access a given file from the Web.
        """
        self.assertEqual(self.storage.url('test.file'), self.storage.base_url + 'test.file')

        # should encode special chars except ~!*()'
        # like encodeURIComponent() JavaScript function do
        self.assertEqual(
            self.storage.url(r"~!*()'@#$%^&*abc`+ =.file"),
            "/test_media_url/~!*()'%40%23%24%25%5E%26*abc%60%2B%20%3D.file"
        )
        self.assertEqual(self.storage.url("ab\0c"), "/test_media_url/ab%00c")

        # should translate os path separator(s) to the url path separator
        self.assertEqual(self.storage.url("""a/b\\c.file"""), "/test_media_url/a/b/c.file")

        # #25905: remove leading slashes from file names to prevent unsafe url output
        self.assertEqual(self.storage.url("/evil.com"), "/test_media_url/evil.com")
        self.assertEqual(self.storage.url(r"\evil.com"), "/test_media_url/evil.com")
        self.assertEqual(self.storage.url("///evil.com"), "/test_media_url/evil.com")
        self.assertEqual(self.storage.url(r"\\\evil.com"), "/test_media_url/evil.com")

        self.assertEqual(self.storage.url(None), "/test_media_url/")

    def test_base_url(self):
        """
        File storage returns a url even when its base_url is unset or modified.
        """
        self.storage.base_url = None
        with self.assertRaises(ValueError):
            self.storage.url('test.file')

        # #22717: missing ending slash in base_url should be auto-corrected
        storage = self.storage_class(location=self.temp_dir, base_url='/no_ending_slash')
        self.assertEqual(
            storage.url('test.file'),
            '%s%s' % (storage.base_url, 'test.file')
        )

    def test_listdir(self):
        """
        File storage returns a tuple containing directories and files.
        """
        self.assertFalse(self.storage.exists('storage_test_1'))
        self.assertFalse(self.storage.exists('storage_test_2'))
        self.assertFalse(self.storage.exists('storage_dir_1'))

        self.storage.save('storage_test_1', ContentFile('custom content'))
        self.storage.save('storage_test_2', ContentFile('custom content'))
        os.mkdir(os.path.join(self.temp_dir, 'storage_dir_1'))

        dirs, files = self.storage.listdir('')
        self.assertEqual(set(dirs), {'storage_dir_1'})
        self.assertEqual(set(files), {'storage_test_1', 'storage_test_2'})

        self.storage.delete('storage_test_1')
        self.storage.delete('storage_test_2')
        os.rmdir(os.path.join(self.temp_dir, 'storage_dir_1'))

    def test_file_storage_prevents_directory_traversal(self):
        """
        File storage prevents directory traversal (files can only be accessed if
        they're below the storage location).
        """
        with self.assertRaises(SuspiciousFileOperation):
            self.storage.exists('..')
        with self.assertRaises(SuspiciousFileOperation):
            self.storage.exists('/etc/passwd')

    def test_file_storage_preserves_filename_case(self):
        """The storage backend should preserve case of filenames."""
        # Create a storage backend associated with the mixed case name
        # directory.
        other_temp_storage = self.storage_class(location=self.temp_dir2)
        # Ask that storage backend to store a file with a mixed case filename.
        mixed_case = 'CaSe_SeNsItIvE'
        file = other_temp_storage.open(mixed_case, 'w')
        file.write('storage contents')
        file.close()
        self.assertEqual(os.path.join(self.temp_dir2, mixed_case), other_temp_storage.path(mixed_case))
        other_temp_storage.delete(mixed_case)

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
                raise FileExistsError()
            elif path == os.path.join(self.temp_dir, 'error'):
                raise PermissionError()
            else:
                self.fail('unexpected argument %r' % path)

        try:
            os.makedirs = fake_makedirs

            self.storage.save('normal/test.file', ContentFile('saved normally'))
            with self.storage.open('normal/test.file') as f:
                self.assertEqual(f.read(), b'saved normally')

            self.storage.save('raced/test.file', ContentFile('saved with race'))
            with self.storage.open('raced/test.file') as f:
                self.assertEqual(f.read(), b'saved with race')

            # Exceptions aside from FileExistsError are raised.
            with self.assertRaises(PermissionError):
                self.storage.save('error/test.file', ContentFile('not saved'))
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
                raise FileNotFoundError()
            elif path == os.path.join(self.temp_dir, 'error.file'):
                raise PermissionError()
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

            # Exceptions aside from FileNotFoundError are raised.
            self.storage.save('error.file', ContentFile('delete with error'))
            with self.assertRaises(PermissionError):
                self.storage.delete('error.file')
        finally:
            os.remove = real_remove

    def test_file_chunks_error(self):
        """
        Test behavior when file.chunks() is raising an error
        """
        f1 = ContentFile('chunks fails')

        def failing_chunks():
            raise IOError
        f1.chunks = failing_chunks
        with self.assertRaises(IOError):
            self.storage.save('error.file', f1)

    def test_delete_no_name(self):
        """
        Calling delete with an empty name should not try to remove the base
        storage directory, but fail loudly (#20660).
        """
        with self.assertRaises(AssertionError):
            self.storage.delete('')

    def test_delete_deletes_directories(self):
        tmp_dir = tempfile.mkdtemp(dir=self.storage.location)
        self.storage.delete(tmp_dir)
        self.assertFalse(os.path.exists(tmp_dir))

    @override_settings(
        MEDIA_ROOT='media_root',
        MEDIA_URL='media_url/',
        FILE_UPLOAD_PERMISSIONS=0o777,
        FILE_UPLOAD_DIRECTORY_PERMISSIONS=0o777,
    )
    def test_setting_changed(self):
        """
        Properties using settings values as defaults should be updated on
        referenced settings change while specified values should be unchanged.
        """
        storage = self.storage_class(
            location='explicit_location',
            base_url='explicit_base_url/',
            file_permissions_mode=0o666,
            directory_permissions_mode=0o666,
        )
        defaults_storage = self.storage_class()
        settings = {
            'MEDIA_ROOT': 'overriden_media_root',
            'MEDIA_URL': 'overriden_media_url/',
            'FILE_UPLOAD_PERMISSIONS': 0o333,
            'FILE_UPLOAD_DIRECTORY_PERMISSIONS': 0o333,
        }
        with self.settings(**settings):
            self.assertEqual(storage.base_location, 'explicit_location')
            self.assertIn('explicit_location', storage.location)
            self.assertEqual(storage.base_url, 'explicit_base_url/')
            self.assertEqual(storage.file_permissions_mode, 0o666)
            self.assertEqual(storage.directory_permissions_mode, 0o666)
            self.assertEqual(defaults_storage.base_location, settings['MEDIA_ROOT'])
            self.assertIn(settings['MEDIA_ROOT'], defaults_storage.location)
            self.assertEqual(defaults_storage.base_url, settings['MEDIA_URL'])
            self.assertEqual(defaults_storage.file_permissions_mode, settings['FILE_UPLOAD_PERMISSIONS'])
            self.assertEqual(
                defaults_storage.directory_permissions_mode, settings['FILE_UPLOAD_DIRECTORY_PERMISSIONS']
            )


class CustomStorage(FileSystemStorage):
    def get_available_name(self, name, max_length=None):
        """
        Append numbers to duplicate files rather than underscores, like Trac.
        """
        basename, *ext = name.split('.')
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


class OverwritingStorage(FileSystemStorage):
    """
    Overwrite existing files instead of appending a suffix to generate an
    unused name.
    """
    # Mask out O_EXCL so os.open() doesn't raise OSError if the file exists.
    OS_OPEN_FLAGS = FileSystemStorage.OS_OPEN_FLAGS & ~os.O_EXCL

    def get_available_name(self, name, max_length=None):
        """Override the effort to find an used name."""
        return name


class OverwritingStorageTests(FileStorageTests):
    storage_class = OverwritingStorage

    def test_save_overwrite_behavior(self):
        """Saving to same file name twice overwrites the first file."""
        name = 'test.file'
        self.assertFalse(self.storage.exists(name))
        content_1 = b'content one'
        content_2 = b'second content'
        f_1 = ContentFile(content_1)
        f_2 = ContentFile(content_2)
        stored_name_1 = self.storage.save(name, f_1)
        try:
            self.assertEqual(stored_name_1, name)
            self.assertTrue(self.storage.exists(name))
            self.assertTrue(os.path.exists(os.path.join(self.temp_dir, name)))
            with self.storage.open(name) as fp:
                self.assertEqual(fp.read(), content_1)
            stored_name_2 = self.storage.save(name, f_2)
            self.assertEqual(stored_name_2, name)
            self.assertTrue(self.storage.exists(name))
            self.assertTrue(os.path.exists(os.path.join(self.temp_dir, name)))
            with self.storage.open(name) as fp:
                self.assertEqual(fp.read(), content_2)
        finally:
            self.storage.delete(name)


class DiscardingFalseContentStorage(FileSystemStorage):
    def _save(self, name, content):
        if content:
            return super()._save(name, content)
        return ''


class DiscardingFalseContentStorageTests(FileStorageTests):
    storage_class = DiscardingFalseContentStorage

    def test_custom_storage_discarding_empty_content(self):
        """
        When Storage.save() wraps a file-like object in File, it should include
        the name argument so that bool(file) evaluates to True (#26495).
        """
        output = StringIO('content')
        self.storage.save('tests/stringio', output)
        self.assertTrue(self.storage.exists('tests/stringio'))

        with self.storage.open('tests/stringio') as f:
            self.assertEqual(f.read(), b'content')


class FileFieldStorageTests(TestCase):
    def tearDown(self):
        shutil.rmtree(temp_storage_location)

    def _storage_max_filename_length(self, storage):
        """
        Query filesystem for maximum filename length (e.g. AUFS has 242).
        """
        dir_to_test = storage.location
        while not os.path.exists(dir_to_test):
            dir_to_test = os.path.dirname(dir_to_test)
        try:
            return os.pathconf(dir_to_test, 'PC_NAME_MAX')
        except Exception:
            return 255  # Should be safe on most backends

    def test_files(self):
        self.assertIsInstance(Storage.normal, FileDescriptor)

        # An object without a file has limited functionality.
        obj1 = Storage()
        self.assertEqual(obj1.normal.name, "")
        with self.assertRaises(ValueError):
            obj1.normal.size

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
        self.assertNotIn("assignment.txt", files)

        obj1.save()
        dirs, files = temp_storage.listdir("tests")
        self.assertEqual(sorted(files), ["assignment.txt", "django_test.txt"])

        # Save another file with the same name.
        obj2 = Storage()
        obj2.normal.save("django_test.txt", ContentFile("more content"))
        obj2_name = obj2.normal.name
        self.assertRegex(obj2_name, "tests/django_test_%s.txt" % FILE_SUFFIX_REGEX)
        self.assertEqual(obj2.normal.size, 12)
        obj2.normal.close()

        # Deleting an object does not delete the file it uses.
        obj2.delete()
        obj2.normal.save("django_test.txt", ContentFile("more content"))
        self.assertNotEqual(obj2_name, obj2.normal.name)
        self.assertRegex(obj2.normal.name, "tests/django_test_%s.txt" % FILE_SUFFIX_REGEX)
        obj2.normal.close()

    def test_filefield_read(self):
        # Files can be read in a little at a time, if necessary.
        obj = Storage.objects.create(
            normal=SimpleUploadedFile("assignment.txt", b"content"))
        obj.normal.open()
        self.assertEqual(obj.normal.read(3), b"con")
        self.assertEqual(obj.normal.read(), b"tent")
        self.assertEqual(list(obj.normal.chunks(chunk_size=2)), [b"co", b"nt", b"en", b"t"])
        obj.normal.close()

    def test_filefield_write(self):
        # Files can be written to.
        obj = Storage.objects.create(normal=SimpleUploadedFile('rewritten.txt', b'content'))
        with obj.normal as normal:
            normal.open('wb')
            normal.write(b'updated')
        obj.refresh_from_db()
        self.assertEqual(obj.normal.read(), b'updated')
        obj.normal.close()

    def test_filefield_reopen(self):
        obj = Storage.objects.create(normal=SimpleUploadedFile('reopen.txt', b'content'))
        with obj.normal as normal:
            normal.open()
        obj.normal.open()
        obj.normal.file.seek(0)
        obj.normal.close()

    def test_duplicate_filename(self):
        # Multiple files with the same name get _(7 random chars) appended to them.
        objs = [Storage() for i in range(2)]
        for o in objs:
            o.normal.save("multiple_files.txt", ContentFile("Same Content"))
        try:
            names = [o.normal.name for o in objs]
            self.assertEqual(names[0], "tests/multiple_files.txt")
            self.assertRegex(names[1], "tests/multiple_files_%s.txt" % FILE_SUFFIX_REGEX)
        finally:
            for o in objs:
                o.delete()

    def test_file_truncation(self):
        # Given the max_length is limited, when multiple files get uploaded
        # under the same name, then the filename get truncated in order to fit
        # in _(7 random chars). When most of the max_length is taken by
        # dirname + extension and there are not enough  characters in the
        # filename to truncate, an exception should be raised.
        objs = [Storage() for i in range(2)]
        filename = 'filename.ext'

        for o in objs:
            o.limited_length.save(filename, ContentFile('Same Content'))
        try:
            # Testing truncation.
            names = [o.limited_length.name for o in objs]
            self.assertEqual(names[0], 'tests/%s' % filename)
            self.assertRegex(names[1], 'tests/fi_%s.ext' % FILE_SUFFIX_REGEX)

            # Testing exception is raised when filename is too short to truncate.
            filename = 'short.longext'
            objs[0].limited_length.save(filename, ContentFile('Same Content'))
            with self.assertRaisesMessage(SuspiciousFileOperation, 'Storage can not find an available filename'):
                objs[1].limited_length.save(*(filename, ContentFile('Same Content')))
        finally:
            for o in objs:
                o.delete()

    @unittest.skipIf(
        sys.platform.startswith('win'),
        "Windows supports at most 260 characters in a path.",
    )
    def test_extended_length_storage(self):
        # Testing FileField with max_length > 255. Most systems have filename
        # length limitation of 255. Path takes extra chars.
        filename = (self._storage_max_filename_length(temp_storage) - 4) * 'a'  # 4 chars for extension.
        obj = Storage()
        obj.extended_length.save('%s.txt' % filename, ContentFile('Same Content'))
        self.assertEqual(obj.extended_length.name, 'tests/%s.txt' % filename)
        self.assertEqual(obj.extended_length.read(), b'Same Content')
        obj.extended_length.close()

    def test_filefield_default(self):
        # Default values allow an object to access a single file.
        temp_storage.save('tests/default.txt', ContentFile('default content'))
        obj = Storage.objects.create()
        self.assertEqual(obj.default.name, "tests/default.txt")
        self.assertEqual(obj.default.read(), b"default content")
        obj.default.close()

        # But it shouldn't be deleted, even if there are no more objects using
        # it.
        obj.delete()
        obj = Storage()
        self.assertEqual(obj.default.read(), b"default content")
        obj.default.close()

    def test_empty_upload_to(self):
        # upload_to can be empty, meaning it does not use subdirectory.
        obj = Storage()
        obj.empty.save('django_test.txt', ContentFile('more content'))
        self.assertEqual(obj.empty.name, "django_test.txt")
        self.assertEqual(obj.empty.read(), b"more content")
        obj.empty.close()

    def test_random_upload_to(self):
        # Verify the fix for #5655, making sure the directory is only
        # determined once.
        obj = Storage()
        obj.random.save("random_file", ContentFile("random content"))
        self.assertTrue(obj.random.name.endswith("/random_file"))
        obj.random.close()

    def test_custom_valid_name_callable_upload_to(self):
        """
        Storage.get_valid_name() should be called when upload_to is a callable.
        """
        obj = Storage()
        obj.custom_valid_name.save("random_file", ContentFile("random content"))
        # CustomValidNameStorage.get_valid_name() appends '_valid' to the name
        self.assertTrue(obj.custom_valid_name.name.endswith("/random_file_valid"))
        obj.custom_valid_name.close()

    def test_filefield_pickling(self):
        # Push an object into the cache to make sure it pickles properly
        obj = Storage()
        obj.normal.save("django_test.txt", ContentFile("more content"))
        obj.normal.close()
        cache.set("obj", obj)
        self.assertEqual(cache.get("obj").normal.name, "tests/django_test.txt")

    def test_file_object(self):
        # Create sample file
        temp_storage.save('tests/example.txt', ContentFile('some content'))

        # Load it as Python file object
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


# Tests for a race condition on file saving (#4948).
# This is written in such a way that it'll always pass on platforms
# without threading.

class SlowFile(ContentFile):
    def chunks(self):
        time.sleep(1)
        return super().chunks()


class FileSaveRaceConditionTest(SimpleTestCase):
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
        self.save_file('conflict')
        self.thread.join()
        files = sorted(os.listdir(self.storage_dir))
        self.assertEqual(files[0], 'conflict')
        self.assertRegex(files[1], 'conflict_%s' % FILE_SUFFIX_REGEX)


@unittest.skipIf(sys.platform.startswith('win'), "Windows only partially supports umasks and chmod.")
class FileStoragePermissions(unittest.TestCase):
    def setUp(self):
        self.umask = 0o027
        self.old_umask = os.umask(self.umask)
        self.storage_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.storage_dir)
        os.umask(self.old_umask)

    @override_settings(FILE_UPLOAD_PERMISSIONS=0o654)
    def test_file_upload_permissions(self):
        self.storage = FileSystemStorage(self.storage_dir)
        name = self.storage.save("the_file", ContentFile("data"))
        actual_mode = os.stat(self.storage.path(name))[0] & 0o777
        self.assertEqual(actual_mode, 0o654)

    @override_settings(FILE_UPLOAD_PERMISSIONS=None)
    def test_file_upload_default_permissions(self):
        self.storage = FileSystemStorage(self.storage_dir)
        fname = self.storage.save("some_file", ContentFile("data"))
        mode = os.stat(self.storage.path(fname))[0] & 0o777
        self.assertEqual(mode, 0o666 & ~self.umask)

    @override_settings(FILE_UPLOAD_DIRECTORY_PERMISSIONS=0o765)
    def test_file_upload_directory_permissions(self):
        self.storage = FileSystemStorage(self.storage_dir)
        name = self.storage.save('the_directory/subdir/the_file', ContentFile('data'))
        file_path = Path(self.storage.path(name))
        self.assertEqual(file_path.parent.stat().st_mode & 0o777, 0o765)
        self.assertEqual(file_path.parent.parent.stat().st_mode & 0o777, 0o765)

    @override_settings(FILE_UPLOAD_DIRECTORY_PERMISSIONS=None)
    def test_file_upload_directory_default_permissions(self):
        self.storage = FileSystemStorage(self.storage_dir)
        name = self.storage.save('the_directory/subdir/the_file', ContentFile('data'))
        file_path = Path(self.storage.path(name))
        expected_mode = 0o777 & ~self.umask
        self.assertEqual(file_path.parent.stat().st_mode & 0o777, expected_mode)
        self.assertEqual(file_path.parent.parent.stat().st_mode & 0o777, expected_mode)


class FileStoragePathParsing(SimpleTestCase):
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

        files = sorted(os.listdir(os.path.join(self.storage_dir, 'dotted.path')))
        self.assertFalse(os.path.exists(os.path.join(self.storage_dir, 'dotted_.path')))
        self.assertEqual(files[0], 'test')
        self.assertRegex(files[1], 'test_%s' % FILE_SUFFIX_REGEX)

    def test_first_character_dot(self):
        """
        File names with a dot as their first character don't have an extension,
        and the underscore should get added to the end.
        """
        self.storage.save('dotted.path/.test', ContentFile("1"))
        self.storage.save('dotted.path/.test', ContentFile("2"))

        files = sorted(os.listdir(os.path.join(self.storage_dir, 'dotted.path')))
        self.assertFalse(os.path.exists(os.path.join(self.storage_dir, 'dotted_.path')))
        self.assertEqual(files[0], '.test')
        self.assertRegex(files[1], '.test_%s' % FILE_SUFFIX_REGEX)


class ContentFileStorageTestCase(unittest.TestCase):

    def setUp(self):
        self.storage_dir = tempfile.mkdtemp()
        self.storage = FileSystemStorage(self.storage_dir)

    def tearDown(self):
        shutil.rmtree(self.storage_dir)

    def test_content_saving(self):
        """
        ContentFile can be saved correctly with the filesystem storage,
        if it was initialized with either bytes or unicode content.
        """
        self.storage.save('bytes.txt', ContentFile(b"content"))
        self.storage.save('unicode.txt', ContentFile("español"))


@override_settings(ROOT_URLCONF='file_storage.urls')
class FileLikeObjectTestCase(LiveServerTestCase):
    """
    Test file-like objects (#15644).
    """

    available_apps = []

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.storage = FileSystemStorage(location=self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_urllib_request_urlopen(self):
        """
        Test the File storage API with a file-like object coming from
        urllib.request.urlopen().
        """
        file_like_object = urlopen(self.live_server_url + '/')
        f = File(file_like_object)
        stored_filename = self.storage.save("remote_file.html", f)

        remote_file = urlopen(self.live_server_url + '/')
        with self.storage.open(stored_filename) as stored_file:
            self.assertEqual(stored_file.read(), remote_file.read())
