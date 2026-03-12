import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path

from django.core.exceptions import SuspiciousFileOperation
from django.utils._os import safe_join, safe_makedirs, to_path


class SafeMakeDirsTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.base = tmp.name
        self.addCleanup(tmp.cleanup)

    def assertDirMode(self, path, expected):
        self.assertIs(os.path.isdir(path), True)
        if sys.platform == "win32":
            # Windows partially supports chmod: dirs always end up with 0o777.
            expected = 0o777

        # These tests assume a typical process umask (0o022 or similar): they
        # create directories with modes like 0o755 and 0o700, which don't have
        # group/world write bits, so a typical umask doesn't change the final
        # permissions. On unexpected failures, check whether umask has changed.
        self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), expected)

    def test_creates_directory_hierarchy_with_permissions(self):
        path = os.path.join(self.base, "a", "b", "c")
        safe_makedirs(path, mode=0o755)

        self.assertDirMode(os.path.join(self.base, "a"), 0o755)
        self.assertDirMode(os.path.join(self.base, "a", "b"), 0o755)
        self.assertDirMode(path, 0o755)

    def test_existing_directory_exist_ok(self):
        path = os.path.join(self.base, "a")
        os.mkdir(path, 0o700)

        safe_makedirs(path, mode=0o755, exist_ok=True)

        self.assertDirMode(path, 0o700)

    def test_existing_directory_exist_ok_false_raises(self):
        path = os.path.join(self.base, "a")
        os.mkdir(path)

        with self.assertRaises(FileExistsError):
            safe_makedirs(path, mode=0o755, exist_ok=False)

    def test_existing_file_at_target_raises(self):
        path = os.path.join(self.base, "a")
        with open(path, "w") as f:
            f.write("x")

        with self.assertRaises(FileExistsError):
            safe_makedirs(path, mode=0o755, exist_ok=False)

        with self.assertRaises(FileExistsError):
            safe_makedirs(path, mode=0o755, exist_ok=True)

    def test_file_in_intermediate_path_raises(self):
        file_path = os.path.join(self.base, "a")
        with open(file_path, "w") as f:
            f.write("x")

        path = os.path.join(file_path, "b")

        expected = FileNotFoundError if sys.platform == "win32" else NotADirectoryError

        with self.assertRaises(expected):
            safe_makedirs(path, mode=0o755, exist_ok=False)

        with self.assertRaises(expected):
            safe_makedirs(path, mode=0o755, exist_ok=True)

    def test_existing_parent_preserves_permissions(self):
        a = os.path.join(self.base, "a")
        b = os.path.join(a, "b")

        os.mkdir(a, 0o700)

        safe_makedirs(b, mode=0o755, exist_ok=False)

        self.assertDirMode(a, 0o700)
        self.assertDirMode(b, 0o755)

        c = os.path.join(a, "c")
        safe_makedirs(c, mode=0o750, exist_ok=True)

        self.assertDirMode(a, 0o700)
        self.assertDirMode(c, 0o750)

    def test_path_is_normalized(self):
        path = os.path.join(self.base, "a", "b", "..", "c")
        safe_makedirs(path, mode=0o755)

        self.assertDirMode(os.path.normpath(path), 0o755)
        self.assertIs(os.path.isdir(os.path.join(self.base, "a", "c")), True)

    def test_permissions_unaffected_by_process_umask(self):
        path = os.path.join(self.base, "a", "b", "c")
        # `umask()` returns the current mask, so it'll be restored on cleanup.
        self.addCleanup(os.umask, os.umask(0o077))

        safe_makedirs(path, mode=0o755)

        self.assertDirMode(os.path.join(self.base, "a"), 0o755)
        self.assertDirMode(os.path.join(self.base, "a", "b"), 0o755)
        self.assertDirMode(path, 0o755)

    def test_permissions_correct_despite_concurrent_umask_change(self):
        path = os.path.join(self.base, "a", "b", "c")
        original_mkdir = os.mkdir
        # `umask()` returns the current mask, so it'll be restored on cleanup.
        self.addCleanup(os.umask, os.umask(0o000))

        def mkdir_changing_umask(p, mode):
            # Simulate a concurrent thread changing the process umask.
            os.umask(0o077)
            original_mkdir(p, mode)

        with unittest.mock.patch("os.mkdir", side_effect=mkdir_changing_umask):
            safe_makedirs(path, mode=0o755)

        self.assertDirMode(os.path.join(self.base, "a"), 0o755)
        self.assertDirMode(os.path.join(self.base, "a", "b"), 0o755)
        self.assertDirMode(path, 0o755)

    def test_race_condition_exist_ok_false(self):
        path = os.path.join(self.base, "a", "b")

        original_mkdir = os.mkdir
        call_count = [0]

        # `safe_makedirs()` calls `os.mkdir()` for each level in the path.
        # For path "a/b", mkdir is called twice: once for "a", once for "b".
        def mkdir_with_race(p, mode):
            call_count[0] += 1
            if call_count[0] == 1:
                original_mkdir(p, mode)
            else:
                raise FileExistsError(f"Directory exists: '{p}'")

        with unittest.mock.patch("os.mkdir", side_effect=mkdir_with_race):
            with self.assertRaises(FileExistsError):
                safe_makedirs(path, mode=0o755, exist_ok=False)

    def test_race_condition_exist_ok_true(self):
        path = os.path.join(self.base, "a", "b")

        original_mkdir = os.mkdir
        call_count = [0]

        def mkdir_with_race(p, mode):
            call_count[0] += 1
            if call_count[0] == 1:
                original_mkdir(p, mode)
            else:
                # Simulate other thread creating the directory during the race.
                # The directory needs to exist for `exist_ok=True` to succeed.
                original_mkdir(p, mode)
                raise FileExistsError(f"Directory exists: '{p}'")

        with unittest.mock.patch("os.mkdir", side_effect=mkdir_with_race):
            safe_makedirs(path, mode=0o755, exist_ok=True)

        self.assertIs(os.path.isdir(path), True)


class SafeJoinTests(unittest.TestCase):
    def test_base_path_ends_with_sep(self):
        drive, path = os.path.splitdrive(safe_join("/abc/", "abc"))
        self.assertEqual(path, "{0}abc{0}abc".format(os.path.sep))

    def test_root_path(self):
        drive, path = os.path.splitdrive(safe_join("/", "path"))
        self.assertEqual(
            path,
            "{}path".format(os.path.sep),
        )

        drive, path = os.path.splitdrive(safe_join("/", ""))
        self.assertEqual(
            path,
            os.path.sep,
        )

    def test_parent_path(self):
        with self.assertRaises(SuspiciousFileOperation):
            safe_join("/abc/", "../def")


class ToPathTests(unittest.TestCase):
    def test_to_path(self):
        for path in ("/tmp/some_file.txt", Path("/tmp/some_file.txt")):
            with self.subTest(path):
                self.assertEqual(to_path(path), Path("/tmp/some_file.txt"))

    def test_to_path_invalid_value(self):
        with self.assertRaises(TypeError):
            to_path(42)
