import os
import sys
import time
import unittest

from django.core.files.base import ContentFile
from django.core.files.storage import InMemoryStorage
from django.core.files.uploadedfile import TemporaryUploadedFile
from django.test import SimpleTestCase, override_settings


class MemoryStorageIOTests(unittest.TestCase):
    def setUp(self):
        self.storage = InMemoryStorage()

    def test_write_string(self):
        with self.storage.open("file.txt", "w") as fd:
            fd.write("hello")
        with self.storage.open("file.txt", "r") as fd:
            self.assertEqual(fd.read(), "hello")
        with self.storage.open("file.dat", "wb") as fd:
            fd.write(b"hello")
        with self.storage.open("file.dat", "rb") as fd:
            self.assertEqual(fd.read(), b"hello")

    def test_convert_str_to_bytes_and_back(self):
        """InMemoryStorage handles conversion from str to bytes and back."""
        with self.storage.open("file.txt", "w") as fd:
            fd.write("hello")
        with self.storage.open("file.txt", "rb") as fd:
            self.assertEqual(fd.read(), b"hello")
        with self.storage.open("file.dat", "wb") as fd:
            fd.write(b"hello")
        with self.storage.open("file.dat", "r") as fd:
            self.assertEqual(fd.read(), "hello")

    def test_open_missing_file(self):
        self.assertRaises(FileNotFoundError, self.storage.open, "missing.txt")

    def test_open_dir_as_file(self):
        with self.storage.open("a/b/file.txt", "w") as fd:
            fd.write("hello")
        self.assertRaises(IsADirectoryError, self.storage.open, "a/b")

    def test_file_saving(self):
        self.storage.save("file.txt", ContentFile("test"))
        self.assertEqual(self.storage.open("file.txt", "r").read(), "test")

        self.storage.save("file.dat", ContentFile(b"test"))
        self.assertEqual(self.storage.open("file.dat", "rb").read(), b"test")

    @unittest.skipIf(
        sys.platform == "win32", "Windows doesn't support moving open files."
    )
    def test_removing_temporary_file_after_save(self):
        """A temporary file is removed when saved into storage."""
        with TemporaryUploadedFile("test", "text/plain", 1, "utf8") as file:
            self.storage.save("test.txt", file)
            self.assertFalse(os.path.exists(file.temporary_file_path()))

    def test_large_file_saving(self):
        large_file = ContentFile("A" * ContentFile.DEFAULT_CHUNK_SIZE * 3)
        self.storage.save("file.txt", large_file)

    def test_file_size(self):
        """
        File size is equal to the size of bytes-encoded version of the saved
        data.
        """
        self.storage.save("file.txt", ContentFile("test"))
        self.assertEqual(self.storage.size("file.txt"), 4)

        # A unicode char encoded to UTF-8 takes 2 bytes.
        self.storage.save("unicode_file.txt", ContentFile("è"))
        self.assertEqual(self.storage.size("unicode_file.txt"), 2)

        self.storage.save("file.dat", ContentFile(b"\xf1\xf1"))
        self.assertEqual(self.storage.size("file.dat"), 2)

    def test_listdir(self):
        self.assertEqual(self.storage.listdir(""), ([], []))

        self.storage.save("file_a.txt", ContentFile("test"))
        self.storage.save("file_b.txt", ContentFile("test"))
        self.storage.save("dir/file_c.txt", ContentFile("test"))

        dirs, files = self.storage.listdir("")
        self.assertEqual(sorted(files), ["file_a.txt", "file_b.txt"])
        self.assertEqual(dirs, ["dir"])

    def test_list_relative_path(self):
        self.storage.save("a/file.txt", ContentFile("test"))

        _dirs, files = self.storage.listdir("./a/./.")
        self.assertEqual(files, ["file.txt"])

    def test_exists(self):
        self.storage.save("dir/subdir/file.txt", ContentFile("test"))
        self.assertTrue(self.storage.exists("dir"))
        self.assertTrue(self.storage.exists("dir/subdir"))
        self.assertTrue(self.storage.exists("dir/subdir/file.txt"))

    def test_delete(self):
        """Deletion handles both files and directory trees."""
        self.storage.save("dir/subdir/file.txt", ContentFile("test"))
        self.storage.save("dir/subdir/other_file.txt", ContentFile("test"))
        self.assertTrue(self.storage.exists("dir/subdir/file.txt"))
        self.assertTrue(self.storage.exists("dir/subdir/other_file.txt"))

        self.storage.delete("dir/subdir/other_file.txt")
        self.assertFalse(self.storage.exists("dir/subdir/other_file.txt"))

        self.storage.delete("dir/subdir")
        self.assertFalse(self.storage.exists("dir/subdir/file.txt"))
        self.assertFalse(self.storage.exists("dir/subdir"))

    def test_delete_missing_file(self):
        self.storage.delete("missing_file.txt")
        self.storage.delete("missing_dir/missing_file.txt")

    def test_file_node_cannot_have_children(self):
        """Navigate to children of a file node raises FileExistsError."""
        self.storage.save("file.txt", ContentFile("test"))
        self.assertRaises(FileExistsError, self.storage.listdir, "file.txt/child_dir")
        self.assertRaises(
            FileExistsError,
            self.storage.save,
            "file.txt/child_file.txt",
            ContentFile("test"),
        )

    @override_settings(MEDIA_URL=None)
    def test_url(self):
        self.assertRaises(ValueError, self.storage.url, ("file.txt",))

        storage = InMemoryStorage(base_url="http://www.example.com")
        self.assertEqual(storage.url("file.txt"), "http://www.example.com/file.txt")

    def test_url_with_none_filename(self):
        storage = InMemoryStorage(base_url="/test_media_url/")
        self.assertEqual(storage.url(None), "/test_media_url/")


class MemoryStorageTimesTests(unittest.TestCase):
    def setUp(self):
        self.storage = InMemoryStorage()

    def test_file_modified_time(self):
        """
        File modified time should change after file changing
        """
        self.storage.save("file.txt", ContentFile("test"))
        modified_time = self.storage.get_modified_time("file.txt")

        time.sleep(0.1)

        with self.storage.open("file.txt", "w") as fd:
            fd.write("new content")

        new_modified_time = self.storage.get_modified_time("file.txt")
        self.assertTrue(new_modified_time > modified_time)

    def test_file_accessed_time(self):
        """File accessed time should change after consecutive opening."""
        self.storage.save("file.txt", ContentFile("test"))
        accessed_time = self.storage.get_accessed_time("file.txt")

        time.sleep(0.1)

        self.storage.open("file.txt", "r")
        new_accessed_time = self.storage.get_accessed_time("file.txt")
        self.assertGreater(new_accessed_time, accessed_time)

    def test_file_created_time(self):
        """File creation time should not change after I/O operations."""
        self.storage.save("file.txt", ContentFile("test"))
        created_time = self.storage.get_created_time("file.txt")

        time.sleep(0.1)

        # File opening doesn't change creation time.
        file = self.storage.open("file.txt", "r")
        after_open_created_time = self.storage.get_created_time("file.txt")
        self.assertEqual(after_open_created_time, created_time)
        # Writing to a file doesn't change its creation time.
        file.write("New test")
        self.storage.save("file.txt", file)
        after_write_created_time = self.storage.get_created_time("file.txt")
        self.assertEqual(after_write_created_time, created_time)

    def test_directory_times_changing_after_file_creation(self):
        """
        Directory modified and accessed time should change when a new file is
        created inside.
        """
        self.storage.save("dir/file1.txt", ContentFile("test"))
        created_time = self.storage.get_created_time("dir")
        modified_time = self.storage.get_modified_time("dir")
        accessed_time = self.storage.get_accessed_time("dir")

        time.sleep(0.1)

        self.storage.save("dir/file2.txt", ContentFile("test"))
        new_modified_time = self.storage.get_modified_time("dir")
        new_accessed_time = self.storage.get_accessed_time("dir")
        after_file_creation_created_time = self.storage.get_created_time("dir")
        self.assertGreater(new_modified_time, modified_time)
        self.assertGreater(new_accessed_time, accessed_time)
        self.assertEqual(created_time, after_file_creation_created_time)

    def test_directory_times_changing_after_file_deletion(self):
        """
        Directory modified and accessed time should change when a new file is
        deleted inside.
        """
        self.storage.save("dir/file.txt", ContentFile("test"))
        created_time = self.storage.get_created_time("dir")
        modified_time = self.storage.get_modified_time("dir")
        accessed_time = self.storage.get_accessed_time("dir")

        time.sleep(0.1)

        self.storage.delete("dir/file.txt")
        new_modified_time = self.storage.get_modified_time("dir")
        new_accessed_time = self.storage.get_accessed_time("dir")
        after_file_deletion_created_time = self.storage.get_created_time("dir")
        self.assertGreater(new_modified_time, modified_time)
        self.assertGreater(new_accessed_time, accessed_time)
        self.assertEqual(created_time, after_file_deletion_created_time)


class InMemoryStorageTests(SimpleTestCase):
    def test_deconstruction(self):
        storage = InMemoryStorage()
        path, args, kwargs = storage.deconstruct()
        self.assertEqual(path, "django.core.files.storage.InMemoryStorage")
        self.assertEqual(args, ())
        self.assertEqual(kwargs, {})

        kwargs_orig = {
            "location": "/custom_path",
            "base_url": "http://myfiles.example.com/",
            "file_permissions_mode": "0o755",
            "directory_permissions_mode": "0o600",
        }
        storage = InMemoryStorage(**kwargs_orig)
        path, args, kwargs = storage.deconstruct()
        self.assertEqual(kwargs, kwargs_orig)

    @override_settings(
        MEDIA_ROOT="media_root",
        MEDIA_URL="media_url/",
        FILE_UPLOAD_PERMISSIONS=0o777,
        FILE_UPLOAD_DIRECTORY_PERMISSIONS=0o777,
    )
    def test_setting_changed(self):
        """
        Properties using settings values as defaults should be updated on
        referenced settings change while specified values should be unchanged.
        """
        storage = InMemoryStorage(
            location="explicit_location",
            base_url="explicit_base_url/",
            file_permissions_mode=0o666,
            directory_permissions_mode=0o666,
        )
        defaults_storage = InMemoryStorage()
        settings = {
            "MEDIA_ROOT": "overridden_media_root",
            "MEDIA_URL": "/overridden_media_url/",
            "FILE_UPLOAD_PERMISSIONS": 0o333,
            "FILE_UPLOAD_DIRECTORY_PERMISSIONS": 0o333,
        }
        with self.settings(**settings):
            self.assertEqual(storage.base_location, "explicit_location")
            self.assertIn("explicit_location", storage.location)
            self.assertEqual(storage.base_url, "explicit_base_url/")
            self.assertEqual(storage.file_permissions_mode, 0o666)
            self.assertEqual(storage.directory_permissions_mode, 0o666)
            self.assertEqual(defaults_storage.base_location, settings["MEDIA_ROOT"])
            self.assertIn(settings["MEDIA_ROOT"], defaults_storage.location)
            self.assertEqual(defaults_storage.base_url, settings["MEDIA_URL"])
            self.assertEqual(
                defaults_storage.file_permissions_mode,
                settings["FILE_UPLOAD_PERMISSIONS"],
            )
            self.assertEqual(
                defaults_storage.directory_permissions_mode,
                settings["FILE_UPLOAD_DIRECTORY_PERMISSIONS"],
            )
