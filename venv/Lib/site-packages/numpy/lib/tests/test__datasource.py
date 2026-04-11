import os
import urllib.request as urllib_request
from shutil import rmtree
from tempfile import NamedTemporaryFile, mkdtemp, mkstemp
from urllib.error import URLError
from urllib.parse import urlparse

import pytest

import numpy.lib._datasource as datasource
from numpy.testing import assert_, assert_equal, assert_raises


def urlopen_stub(url, data=None):
    '''Stub to replace urlopen for testing.'''
    if url == valid_httpurl():
        tmpfile = NamedTemporaryFile(prefix='urltmp_')
        return tmpfile
    else:
        raise URLError('Name or service not known')


# setup and teardown
old_urlopen = None


def setup_module():
    global old_urlopen

    old_urlopen = urllib_request.urlopen
    urllib_request.urlopen = urlopen_stub


def teardown_module():
    urllib_request.urlopen = old_urlopen


# A valid website for more robust testing
http_path = 'http://www.google.com/'
http_file = 'index.html'

http_fakepath = 'http://fake.abc.web/site/'
http_fakefile = 'fake.txt'

malicious_files = ['/etc/shadow', '../../shadow',
                   '..\\system.dat', 'c:\\windows\\system.dat']

magic_line = b'three is the magic number'


# Utility functions used by many tests
def valid_textfile(filedir):
    # Generate and return a valid temporary file.
    fd, path = mkstemp(suffix='.txt', prefix='dstmp_', dir=filedir, text=True)
    os.close(fd)
    return path


def invalid_textfile(filedir):
    # Generate and return an invalid filename.
    fd, path = mkstemp(suffix='.txt', prefix='dstmp_', dir=filedir)
    os.close(fd)
    os.remove(path)
    return path


def valid_httpurl():
    return http_path + http_file


def invalid_httpurl():
    return http_fakepath + http_fakefile


def valid_baseurl():
    return http_path


def invalid_baseurl():
    return http_fakepath


def valid_httpfile():
    return http_file


def invalid_httpfile():
    return http_fakefile


class TestDataSourceOpen:
    def test_ValidHTTP(self, tmp_path):
        ds = datasource.DataSource(tmp_path)
        fh = ds.open(valid_httpurl())
        assert_(fh)
        fh.close()

    def test_InvalidHTTP(self, tmp_path):
        ds = datasource.DataSource(tmp_path)
        url = invalid_httpurl()
        assert_raises(OSError, ds.open, url)
        try:
            ds.open(url)
        except OSError as e:
            # Regression test for bug fixed in r4342.
            assert_(e.errno is None)

    def test_InvalidHTTPCacheURLError(self, tmp_path):
        ds = datasource.DataSource(tmp_path)
        assert_raises(URLError, ds._cache, invalid_httpurl())

    def test_ValidFile(self, tmp_path):
        ds = datasource.DataSource(tmp_path)
        local_file = valid_textfile(tmp_path)
        fh = ds.open(local_file)
        assert_(fh)
        fh.close()

    def test_InvalidFile(self, tmp_path):
        ds = datasource.DataSource(tmp_path)
        invalid_file = invalid_textfile(tmp_path)
        assert_raises(OSError, ds.open, invalid_file)

    def test_ValidGzipFile(self, tmp_path):
        try:
            import gzip
        except ImportError:
            # We don't have the gzip capabilities to test.
            pytest.skip()
        # Test datasource's internal file_opener for Gzip files.
        ds = datasource.DataSource(tmp_path)
        filepath = os.path.join(tmp_path, 'foobar.txt.gz')
        fp = gzip.open(filepath, 'w')
        fp.write(magic_line)
        fp.close()
        fp = ds.open(filepath)
        result = fp.readline()
        fp.close()
        assert_equal(magic_line, result)

    def test_ValidBz2File(self, tmp_path):
        try:
            import bz2
        except ImportError:
            # We don't have the bz2 capabilities to test.
            pytest.skip()
        # Test datasource's internal file_opener for BZip2 files.
        ds = datasource.DataSource(tmp_path)
        filepath = os.path.join(tmp_path, 'foobar.txt.bz2')
        fp = bz2.BZ2File(filepath, 'w')
        fp.write(magic_line)
        fp.close()
        fp = ds.open(filepath)
        result = fp.readline()
        fp.close()
        assert_equal(magic_line, result)


class TestDataSourceExists:
    def test_ValidHTTP(self, tmp_path):
        ds = datasource.DataSource(tmp_path)
        assert_(ds.exists(valid_httpurl()))

    def test_InvalidHTTP(self, tmp_path):
        ds = datasource.DataSource(tmp_path)
        assert_equal(ds.exists(invalid_httpurl()), False)

    def test_ValidFile(self, tmp_path):
        # Test valid file in destpath
        ds = datasource.DataSource(tmp_path)
        tmpfile = valid_textfile(tmp_path)
        assert_(ds.exists(tmpfile))
        # Test valid local file not in destpath
        localdir = mkdtemp()
        tmpfile = valid_textfile(localdir)
        assert_(ds.exists(tmpfile))
        rmtree(localdir)

    def test_InvalidFile(self, tmp_path):
        ds = datasource.DataSource(tmp_path)
        tmpfile = invalid_textfile(tmp_path)
        assert_equal(ds.exists(tmpfile), False)


class TestDataSourceAbspath:
    def test_ValidHTTP(self, tmp_path):
        ds = datasource.DataSource(tmp_path)
        _, netloc, upath, _, _, _ = urlparse(valid_httpurl())
        local_path = os.path.join(tmp_path, netloc,
                                  upath.strip(os.sep).strip('/'))
        assert_equal(local_path, ds.abspath(valid_httpurl()))

    def test_ValidFile(self, tmp_path):
        ds = datasource.DataSource(tmp_path)
        tmpfile = valid_textfile(tmp_path)
        tmpfilename = os.path.split(tmpfile)[-1]
        # Test with filename only
        assert_equal(tmpfile, ds.abspath(tmpfilename))
        # Test filename with complete path
        assert_equal(tmpfile, ds.abspath(tmpfile))

    def test_InvalidHTTP(self, tmp_path):
        ds = datasource.DataSource(tmp_path)
        _, netloc, upath, _, _, _ = urlparse(invalid_httpurl())
        invalidhttp = os.path.join(tmp_path, netloc,
                                   upath.strip(os.sep).strip('/'))
        assert_(invalidhttp != ds.abspath(valid_httpurl()))

    def test_InvalidFile(self, tmp_path):
        ds = datasource.DataSource(tmp_path)
        invalidfile = valid_textfile(tmp_path)
        tmpfile = valid_textfile(tmp_path)
        tmpfilename = os.path.split(tmpfile)[-1]
        # Test with filename only
        assert_(invalidfile != ds.abspath(tmpfilename))
        # Test filename with complete path
        assert_(invalidfile != ds.abspath(tmpfile))

    def test_sandboxing(self, tmp_path):
        ds = datasource.DataSource(tmp_path)
        tmpfile = valid_textfile(tmp_path)
        tmpfilename = os.path.split(tmpfile)[-1]

        path = lambda x: os.path.abspath(ds.abspath(x))

        assert_(path(valid_httpurl()).startswith(str(tmp_path)))
        assert_(path(invalid_httpurl()).startswith(str(tmp_path)))
        assert_(path(tmpfile).startswith(str(tmp_path)))
        assert_(path(tmpfilename).startswith(str(tmp_path)))
        for fn in malicious_files:
            assert_(path(http_path + fn).startswith(str(tmp_path)))
            assert_(path(fn).startswith(str(tmp_path)))

    def test_windows_os_sep(self, tmp_path):
        orig_os_sep = os.sep
        try:
            os.sep = '\\'
            self.test_ValidHTTP(tmp_path)
            self.test_ValidFile(tmp_path)
            self.test_InvalidHTTP(tmp_path)
            self.test_InvalidFile(tmp_path)
            self.test_sandboxing(tmp_path)
        finally:
            os.sep = orig_os_sep


class TestRepositoryAbspath:
    def test_ValidHTTP(self, tmp_path):
        repos = datasource.Repository(valid_baseurl(), tmp_path)
        _, netloc, upath, _, _, _ = urlparse(valid_httpurl())
        local_path = os.path.join(repos._destpath, netloc,
                                  upath.strip(os.sep).strip('/'))
        filepath = repos.abspath(valid_httpfile())
        assert_equal(local_path, filepath)

    def test_sandboxing(self, tmp_path):
        repos = datasource.Repository(valid_baseurl(), tmp_path)
        path = lambda x: os.path.abspath(repos.abspath(x))
        assert_(path(valid_httpfile()).startswith(str(tmp_path)))
        for fn in malicious_files:
            assert_(path(http_path + fn).startswith(str(tmp_path)))
            assert_(path(fn).startswith(str(tmp_path)))

    def test_windows_os_sep(self, tmp_path):
        orig_os_sep = os.sep
        try:
            os.sep = '\\'
            self.test_ValidHTTP(tmp_path)
            self.test_sandboxing(tmp_path)
        finally:
            os.sep = orig_os_sep


class TestRepositoryExists:
    def test_ValidFile(self, tmp_path):
        # Create local temp file
        repos = datasource.Repository(valid_baseurl(), tmp_path)
        tmpfile = valid_textfile(tmp_path)
        assert_(repos.exists(tmpfile))

    def test_InvalidFile(self, tmp_path):
        repos = datasource.Repository(valid_baseurl(), tmp_path)
        tmpfile = invalid_textfile(tmp_path)
        assert_equal(repos.exists(tmpfile), False)

    def test_RemoveHTTPFile(self, tmp_path):
        repos = datasource.Repository(valid_baseurl(), tmp_path)
        assert_(repos.exists(valid_httpurl()))

    def test_CachedHTTPFile(self, tmp_path):
        localfile = valid_httpurl()
        # Create a locally cached temp file with an URL based
        # directory structure.  This is similar to what Repository.open
        # would do.
        repos = datasource.Repository(valid_baseurl(), tmp_path)
        _, netloc, _, _, _, _ = urlparse(localfile)
        local_path = os.path.join(repos._destpath, netloc)
        os.mkdir(local_path, 0o0700)
        tmpfile = valid_textfile(local_path)
        assert_(repos.exists(tmpfile))


class TestOpenFunc:
    def test_DataSourceOpen(self, tmp_path):
        local_file = valid_textfile(tmp_path)
        # Test case where destpath is passed in
        fp = datasource.open(local_file, destpath=tmp_path)
        assert_(fp)
        fp.close()
        # Test case where default destpath is used
        fp = datasource.open(local_file)
        assert_(fp)
        fp.close()

def test_del_attr_handling():
    # DataSource __del__ can be called
    # even if __init__ fails when the
    # Exception object is caught by the
    # caller as happens in refguide_check
    # is_deprecated() function

    ds = datasource.DataSource()
    # simulate failed __init__ by removing key attribute
    # produced within __init__ and expected by __del__
    del ds._istmpdest
    # should not raise an AttributeError if __del__
    # gracefully handles failed __init__:
    ds.__del__()
