import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path

from django.core.exceptions import SuspiciousOperation
from django.test import SimpleTestCase
from django.utils import archive

try:
    import bz2  # NOQA

    HAS_BZ2 = True
except ImportError:
    HAS_BZ2 = False

try:
    import lzma  # NOQA

    HAS_LZMA = True
except ImportError:
    HAS_LZMA = False


class TestArchive(unittest.TestCase):
    def setUp(self):
        self.testdir = Path(__file__).parent / "archives"
        self.old_cwd = Path.cwd()
        os.chdir(self.testdir)

    def tearDown(self):
        os.chdir(self.old_cwd)

    def test_extract_function(self):
        with os.scandir(self.testdir) as entries:
            for entry in entries:
                with self.subTest(entry.name), tempfile.TemporaryDirectory() as tmpdir:
                    tmpdir = Path(tmpdir)
                    if (entry.name.endswith(".bz2") and not HAS_BZ2) or (
                        entry.name.endswith((".lzma", ".xz")) and not HAS_LZMA
                    ):
                        continue
                    archive.extract(entry.path, tmpdir)
                    self.assertTrue(tmpdir.joinpath("1").is_file())
                    self.assertTrue(tmpdir.joinpath("2").is_file())
                    self.assertTrue(tmpdir.joinpath("foo", "1").is_file())
                    self.assertTrue(tmpdir.joinpath("foo", "2").is_file())
                    self.assertTrue(tmpdir.joinpath("foo", "bar", "1").is_file())
                    self.assertTrue(tmpdir.joinpath("foo", "bar", "2").is_file())

    @unittest.skipIf(
        sys.platform == "win32", "Python on Windows has a limited os.chmod()."
    )
    def test_extract_file_permissions(self):
        """archive.extract() preserves file permissions."""
        mask = stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO
        umask = os.umask(0)
        os.umask(umask)  # Restore the original umask.
        with os.scandir(self.testdir) as entries:
            for entry in entries:
                if (
                    entry.name.startswith("leadpath_")
                    or (entry.name.endswith(".bz2") and not HAS_BZ2)
                    or (entry.name.endswith((".lzma", ".xz")) and not HAS_LZMA)
                ):
                    continue
                with self.subTest(entry.name), tempfile.TemporaryDirectory() as tmpdir:
                    tmpdir = Path(tmpdir)
                    archive.extract(entry.path, tmpdir)
                    # An executable file in the archive has executable
                    # permissions.
                    filepath = tmpdir / "executable"
                    self.assertEqual(filepath.stat().st_mode & mask, 0o775)
                    # A file is readable even if permission data is missing.
                    filepath = tmpdir / "no_permissions"
                    self.assertEqual(filepath.stat().st_mode & mask, 0o666 & ~umask)


class TestArchiveInvalid(SimpleTestCase):
    def test_extract_function_traversal(self):
        archives_dir = Path(__file__).parent / "traversal_archives"
        tests = [
            ("traversal.tar", ".."),
            ("traversal_absolute.tar", "/tmp/evil.py"),
        ]
        if sys.platform == "win32":
            tests += [
                ("traversal_disk_win.tar", "d:evil.py"),
                ("traversal_disk_win.zip", "d:evil.py"),
            ]
        msg = "Archive contains invalid path: '%s'"
        for entry, invalid_path in tests:
            with self.subTest(entry), tempfile.TemporaryDirectory() as tmpdir:
                with self.assertRaisesMessage(SuspiciousOperation, msg % invalid_path):
                    archive.extract(archives_dir / entry, tmpdir)
