import os
import stat
import sys
import tempfile
import unittest
from unittest.mock import Mock

from django.core.exceptions import SuspiciousOperation
from django.test import SimpleTestCase
from django.utils import archive
from django.utils.archive import BaseArchive, TarArchive, UnrecognizedArchiveFormat

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
        self.testdir = os.path.join(os.path.dirname(__file__), "archives")
        self.old_cwd = os.getcwd()
        os.chdir(self.testdir)

    def tearDown(self):
        os.chdir(self.old_cwd)

    def test_extract_function(self):
        with os.scandir(self.testdir) as entries:
            for entry in entries:
                with self.subTest(entry.name), tempfile.TemporaryDirectory() as tmpdir:
                    if (entry.name.endswith(".bz2") and not HAS_BZ2) or (
                        entry.name.endswith((".lzma", ".xz")) and not HAS_LZMA
                    ):
                        continue
                    archive.extract(entry.path, tmpdir)
                    self.assertTrue(os.path.isfile(os.path.join(tmpdir, "1")))
                    self.assertTrue(os.path.isfile(os.path.join(tmpdir, "2")))
                    self.assertTrue(os.path.isfile(os.path.join(tmpdir, "foo", "1")))
                    self.assertTrue(os.path.isfile(os.path.join(tmpdir, "foo", "2")))
                    self.assertTrue(
                        os.path.isfile(os.path.join(tmpdir, "foo", "bar", "1"))
                    )
                    self.assertTrue(
                        os.path.isfile(os.path.join(tmpdir, "foo", "bar", "2"))
                    )

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
                    archive.extract(entry.path, tmpdir)
                    # An executable file in the archive has executable
                    # permissions.
                    filepath = os.path.join(tmpdir, "executable")
                    self.assertEqual(os.stat(filepath).st_mode & mask, 0o775)
                    # A file is readable even if permission data is missing.
                    filepath = os.path.join(tmpdir, "no_permissions")
                    self.assertEqual(os.stat(filepath).st_mode & mask, 0o666 & ~umask)

    def test_extract_not_supported_format(self):
        test_file_path = os.path.join(
            os.path.dirname(__file__), "files", "archive_unsupported.txt"
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            with self.assertRaises(UnrecognizedArchiveFormat) as context:
                archive.extract(test_file_path, tmpdir)
            self.assertEqual(
                "Path not a recognized archive format: %s" % test_file_path,
                str(context.exception),
            )

    def test_extract_supported_extension_followed_by_unsupported_extension(self):
        test_file_path = os.path.join(
            os.path.dirname(__file__), "files", "archive_weird_extension.zip.txt"
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            archive.extract(test_file_path, tmpdir)
            self.assertTrue(os.path.isfile(os.path.join(tmpdir, "1")))
            self.assertTrue(os.path.isfile(os.path.join(tmpdir, "2")))
            self.assertTrue(os.path.isfile(os.path.join(tmpdir, "foo", "1")))
            self.assertTrue(os.path.isfile(os.path.join(tmpdir, "foo", "2")))
            self.assertTrue(os.path.isfile(os.path.join(tmpdir, "foo", "bar", "1")))
            self.assertTrue(os.path.isfile(os.path.join(tmpdir, "foo", "bar", "2")))

    def test_extract_function_with_unsupported_instance(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with self.assertRaises(UnrecognizedArchiveFormat) as context:
                # Accessing any attribute not in the spec will raise AttributeError.
                file = Mock(spec=[])
                archive.extract(file, tmpdir)
            self.assertEqual(
                "File object not a recognized archive format.",
                str(context.exception),
            )

    def test_extract_function_with_file_instance(self):
        test_file_path = os.path.join(
            os.path.dirname(__file__), "archives", "foobar.tar"
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            archive.extract(test_file_path, tmpdir)
            self.assertTrue(os.path.isfile(os.path.join(tmpdir, "1")))
            self.assertTrue(os.path.isfile(os.path.join(tmpdir, "2")))
            self.assertTrue(os.path.isfile(os.path.join(tmpdir, "foo", "1")))
            self.assertTrue(os.path.isfile(os.path.join(tmpdir, "foo", "2")))
            self.assertTrue(os.path.isfile(os.path.join(tmpdir, "foo", "bar", "1")))
            self.assertTrue(os.path.isfile(os.path.join(tmpdir, "foo", "bar", "2")))


class TestArchiveInvalid(SimpleTestCase):
    def test_extract_function_traversal(self):
        archives_dir = os.path.join(os.path.dirname(__file__), "traversal_archives")
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
                    archive.extract(os.path.join(archives_dir, entry), tmpdir)


class TestBaseArchive(unittest.TestCase):
    def test_split_leading_dir_windows_style(self):
        self.assertEqual(
            ["C:", "Documents\\Newsletters\\Summer2018.pdf"],
            BaseArchive().split_leading_dir(
                "C:\\Documents\\Newsletters\\Summer2018.pdf"
            ),
        )
        self.assertEqual(
            ["Documents", "Newsletters\\Summer2018.pdf"],
            BaseArchive().split_leading_dir("\\Documents\\Newsletters\\Summer2018.pdf"),
        )
        self.assertEqual(
            ["C:Documents", "Newsletters\\Summer2018.pdf"],
            BaseArchive().split_leading_dir("C:Documents\\Newsletters\\Summer2018.pdf"),
        )
        self.assertEqual(
            ["..", "Publications\\TravelBrochure.pdf"],
            BaseArchive().split_leading_dir("..\\Publications\\TravelBrochure.pdf"),
        )
        self.assertEqual(
            ["Publications", "TravelBrochure.pdf"],
            BaseArchive().split_leading_dir("Publications\\TravelBrochure.pdf"),
        )

    def test_has_leading_dir_has_no_prefix(self):
        self.assertFalse(BaseArchive().has_leading_dir(["/\\/foo.pdf"]))

    def test_extract(self):
        with self.assertRaises(NotImplementedError) as context:
            BaseArchive().extract()

        self.assertEqual(
            "subclasses of BaseArchive must provide an extract() method",
            str(context.exception),
        )

    def test_list(self):
        with self.assertRaises(NotImplementedError) as context:
            BaseArchive().list()

        self.assertEqual(
            "subclasses of BaseArchive must provide a list() method",
            str(context.exception),
        )


class TestTarArchive(unittest.TestCase):
    def test_extract_with_corrupt_file(self):
        test_file_path = os.path.join(
            os.path.dirname(__file__), "archives", "foobar.tar"
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            tar_archive = TarArchive(test_file_path)

            tar_archive._archive.extractfile = Mock(side_effect=KeyError())
            with self.assertRaises(
                UnboundLocalError
            ):  # this is possible bug, need to be changed when fixed
                tar_archive.extract(tmpdir)

            tar_archive._archive.extractfile = Mock(side_effect=AttributeError())
            with self.assertRaises(
                UnboundLocalError
            ):  # this is possible bug, need to be changed when fixed
                tar_archive.extract(tmpdir)

            tar_archive.close()
