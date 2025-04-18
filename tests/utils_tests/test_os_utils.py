import os
import unittest
from pathlib import Path
from unittest.mock import Mock

from django.core.exceptions import SuspiciousFileOperation
from django.utils._os import safe_join, symlinks_supported, to_path


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


class SymlinksSupportedTests(unittest.TestCase):
    def test_supported(self):
        os.symlink = Mock()
        self.assertTrue(symlinks_supported())

    def test_os_error(self):
        os.symlink = Mock(side_effect=OSError("os_failed"))
        self.assertFalse(symlinks_supported())

    def test_not_implemented_error(self):
        os.symlink = Mock(side_effect=NotImplementedError("not_implemented"))
        self.assertFalse(symlinks_supported())
