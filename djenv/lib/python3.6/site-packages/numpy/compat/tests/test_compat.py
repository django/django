from __future__ import division, absolute_import, print_function

from os.path import join

from numpy.compat import isfileobj, os_fspath
from numpy.testing import assert_
from numpy.testing import tempdir


def test_isfileobj():
    with tempdir(prefix="numpy_test_compat_") as folder:
        filename = join(folder, 'a.bin')

        with open(filename, 'wb') as f:
            assert_(isfileobj(f))

        with open(filename, 'ab') as f:
            assert_(isfileobj(f))

        with open(filename, 'rb') as f:
            assert_(isfileobj(f))


def test_os_fspath_strings():
    for string_path in (b'/a/b/c.d', u'/a/b/c.d'):
        assert_(os_fspath(string_path) == string_path)
