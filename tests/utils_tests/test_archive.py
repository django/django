import os
import stat
import sys
import tempfile
import unittest

from django.core.exceptions import SuspiciousOperation
from django.test import SimpleTestCase
from django.utils import archive


class TestArchive(unittest.TestCase):

    def setUp(self):
        self.testdir = os.path.join(os.path.dirname(__file__), 'archives')
        self.old_cwd = os.getcwd()
        os.chdir(self.testdir)

    def tearDown(self):
        os.chdir(self.old_cwd)

    def test_extract_function(self):
        for entry in os.scandir(self.testdir):
            with self.subTest(entry.name), tempfile.TemporaryDirectory() as tmpdir:
                archive.extract(entry.path, tmpdir)
                self.assertTrue(os.path.isfile(os.path.join(tmpdir, '1')))
                self.assertTrue(os.path.isfile(os.path.join(tmpdir, '2')))
                self.assertTrue(os.path.isfile(os.path.join(tmpdir, 'foo', '1')))
                self.assertTrue(os.path.isfile(os.path.join(tmpdir, 'foo', '2')))
                self.assertTrue(os.path.isfile(os.path.join(tmpdir, 'foo', 'bar', '1')))
                self.assertTrue(os.path.isfile(os.path.join(tmpdir, 'foo', 'bar', '2')))

    @unittest.skipIf(sys.platform == 'win32', 'Python on Windows has a limited os.chmod().')
    def test_extract_file_permissions(self):
        """archive.extract() preserves file permissions."""
        mask = stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO
        umask = os.umask(0)
        os.umask(umask)  # Restore the original umask.
        for entry in os.scandir(self.testdir):
            if entry.name.startswith('leadpath_'):
                continue
            with self.subTest(entry.name), tempfile.TemporaryDirectory() as tmpdir:
                archive.extract(entry.path, tmpdir)
                # An executable file in the archive has executable permissions.
                filepath = os.path.join(tmpdir, 'executable')
                self.assertEqual(os.stat(filepath).st_mode & mask, 0o775)
                # A file is readable even if permission data is missing.
                filepath = os.path.join(tmpdir, 'no_permissions')
                self.assertEqual(os.stat(filepath).st_mode & mask, 0o666 & ~umask)


class TestArchiveInvalid(SimpleTestCase):
    def test_extract_function_traversal(self):
        archives_dir = os.path.join(os.path.dirname(__file__), 'traversal_archives')
        tests = [
            ('traversal.tar', '..'),
            ('traversal_absolute.tar', '/tmp/evil.py'),
        ]
        if sys.platform == 'win32':
            tests += [
                ('traversal_disk_win.tar', 'd:evil.py'),
                ('traversal_disk_win.zip', 'd:evil.py'),
            ]
        msg = "Archive contains invalid path: '%s'"
        for entry, invalid_path in tests:
            with self.subTest(entry), tempfile.TemporaryDirectory() as tmpdir:
                with self.assertRaisesMessage(SuspiciousOperation, msg % invalid_path):
                    archive.extract(os.path.join(archives_dir, entry), tmpdir)
