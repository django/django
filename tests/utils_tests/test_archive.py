import os
import shutil
import tempfile
import unittest

from django.utils._os import upath
from django.utils.archive import Archive, extract

TEST_DIR = os.path.join(os.path.dirname(upath(__file__)), 'archives')


class ArchiveTester(object):
    archive = None

    def setUp(self):
        """
        Create temporary directory for testing extraction.
        """
        self.old_cwd = os.getcwd()
        self.tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmpdir)
        self.archive_path = os.path.join(TEST_DIR, self.archive)
        self.archive_lead_path = os.path.join(TEST_DIR, "leadpath_%s" % self.archive)
        # Always start off in TEST_DIR.
        os.chdir(TEST_DIR)

    def tearDown(self):
        os.chdir(self.old_cwd)

    def test_extract_method(self):
        with Archive(self.archive) as archive:
            archive.extract(self.tmpdir)
        self.check_files(self.tmpdir)

    def test_extract_method_no_to_path(self):
        os.chdir(self.tmpdir)
        with Archive(self.archive_path) as archive:
            archive.extract()
        self.check_files(self.tmpdir)

    def test_extract_function(self):
        extract(self.archive_path, self.tmpdir)
        self.check_files(self.tmpdir)

    def test_extract_function_with_leadpath(self):
        extract(self.archive_lead_path, self.tmpdir)
        self.check_files(self.tmpdir)

    def test_extract_function_no_to_path(self):
        os.chdir(self.tmpdir)
        extract(self.archive_path)
        self.check_files(self.tmpdir)

    def check_files(self, tmpdir):
        self.assertTrue(os.path.isfile(os.path.join(self.tmpdir, '1')))
        self.assertTrue(os.path.isfile(os.path.join(self.tmpdir, '2')))
        self.assertTrue(os.path.isfile(os.path.join(self.tmpdir, 'foo', '1')))
        self.assertTrue(os.path.isfile(os.path.join(self.tmpdir, 'foo', '2')))
        self.assertTrue(os.path.isfile(os.path.join(self.tmpdir, 'foo', 'bar', '1')))
        self.assertTrue(os.path.isfile(os.path.join(self.tmpdir, 'foo', 'bar', '2')))


class TestZip(ArchiveTester, unittest.TestCase):
    archive = 'foobar.zip'


class TestTar(ArchiveTester, unittest.TestCase):
    archive = 'foobar.tar'


class TestGzipTar(ArchiveTester, unittest.TestCase):
    archive = 'foobar.tar.gz'


class TestBzip2Tar(ArchiveTester, unittest.TestCase):
    archive = 'foobar.tar.bz2'
