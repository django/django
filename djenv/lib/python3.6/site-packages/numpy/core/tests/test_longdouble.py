from __future__ import division, absolute_import, print_function

import pytest

import numpy as np
from numpy.testing import (
    assert_, assert_equal, assert_raises, assert_array_equal, temppath,
    )
from numpy.core.tests._locales import CommaDecimalPointLocale

LD_INFO = np.finfo(np.longdouble)
longdouble_longer_than_double = (LD_INFO.eps < np.finfo(np.double).eps)


_o = 1 + LD_INFO.eps
string_to_longdouble_inaccurate = (_o != np.longdouble(repr(_o)))
del _o


def test_scalar_extraction():
    """Confirm that extracting a value doesn't convert to python float"""
    o = 1 + LD_INFO.eps
    a = np.array([o, o, o])
    assert_equal(a[1], o)


# Conversions string -> long double

# 0.1 not exactly representable in base 2 floating point.
repr_precision = len(repr(np.longdouble(0.1)))
# +2 from macro block starting around line 842 in scalartypes.c.src.
@pytest.mark.skipif(LD_INFO.precision + 2 >= repr_precision,
                    reason="repr precision not enough to show eps")
def test_repr_roundtrip():
    # We will only see eps in repr if within printing precision.
    o = 1 + LD_INFO.eps
    assert_equal(np.longdouble(repr(o)), o, "repr was %s" % repr(o))


def test_unicode():
    np.longdouble(u"1.2")


def test_string():
    np.longdouble("1.2")


def test_bytes():
    np.longdouble(b"1.2")


@pytest.mark.skipif(string_to_longdouble_inaccurate, reason="Need strtold_l")
def test_repr_roundtrip_bytes():
    o = 1 + LD_INFO.eps
    assert_equal(np.longdouble(repr(o).encode("ascii")), o)


def test_bogus_string():
    assert_raises(ValueError, np.longdouble, "spam")
    assert_raises(ValueError, np.longdouble, "1.0 flub")


@pytest.mark.skipif(string_to_longdouble_inaccurate, reason="Need strtold_l")
def test_fromstring():
    o = 1 + LD_INFO.eps
    s = (" " + repr(o))*5
    a = np.array([o]*5)
    assert_equal(np.fromstring(s, sep=" ", dtype=np.longdouble), a,
                 err_msg="reading '%s'" % s)


def test_fromstring_bogus():
    assert_equal(np.fromstring("1. 2. 3. flop 4.", dtype=float, sep=" "),
                 np.array([1., 2., 3.]))


def test_fromstring_empty():
    assert_equal(np.fromstring("xxxxx", sep="x"),
                 np.array([]))


def test_fromstring_missing():
    assert_equal(np.fromstring("1xx3x4x5x6", sep="x"),
                 np.array([1]))


class TestFileBased(object):

    ldbl = 1 + LD_INFO.eps
    tgt = np.array([ldbl]*5)
    out = ''.join([repr(t) + '\n' for t in tgt])

    def test_fromfile_bogus(self):
        with temppath() as path:
            with open(path, 'wt') as f:
                f.write("1. 2. 3. flop 4.\n")
            res = np.fromfile(path, dtype=float, sep=" ")
        assert_equal(res, np.array([1., 2., 3.]))

    @pytest.mark.skipif(string_to_longdouble_inaccurate,
                        reason="Need strtold_l")
    def test_fromfile(self):
        with temppath() as path:
            with open(path, 'wt') as f:
                f.write(self.out)
            res = np.fromfile(path, dtype=np.longdouble, sep="\n")
        assert_equal(res, self.tgt)

    @pytest.mark.skipif(string_to_longdouble_inaccurate,
                        reason="Need strtold_l")
    def test_genfromtxt(self):
        with temppath() as path:
            with open(path, 'wt') as f:
                f.write(self.out)
            res = np.genfromtxt(path, dtype=np.longdouble)
        assert_equal(res, self.tgt)

    @pytest.mark.skipif(string_to_longdouble_inaccurate,
                        reason="Need strtold_l")
    def test_loadtxt(self):
        with temppath() as path:
            with open(path, 'wt') as f:
                f.write(self.out)
            res = np.loadtxt(path, dtype=np.longdouble)
        assert_equal(res, self.tgt)

    @pytest.mark.skipif(string_to_longdouble_inaccurate,
                        reason="Need strtold_l")
    def test_tofile_roundtrip(self):
        with temppath() as path:
            self.tgt.tofile(path, sep=" ")
            res = np.fromfile(path, dtype=np.longdouble, sep=" ")
        assert_equal(res, self.tgt)


# Conversions long double -> string


def test_repr_exact():
    o = 1 + LD_INFO.eps
    assert_(repr(o) != '1')


@pytest.mark.skipif(longdouble_longer_than_double, reason="BUG #2376")
@pytest.mark.skipif(string_to_longdouble_inaccurate,
                    reason="Need strtold_l")
def test_format():
    o = 1 + LD_INFO.eps
    assert_("{0:.40g}".format(o) != '1')


@pytest.mark.skipif(longdouble_longer_than_double, reason="BUG #2376")
@pytest.mark.skipif(string_to_longdouble_inaccurate,
                    reason="Need strtold_l")
def test_percent():
    o = 1 + LD_INFO.eps
    assert_("%.40g" % o != '1')


@pytest.mark.skipif(longdouble_longer_than_double,
                    reason="array repr problem")
@pytest.mark.skipif(string_to_longdouble_inaccurate,
                    reason="Need strtold_l")
def test_array_repr():
    o = 1 + LD_INFO.eps
    a = np.array([o])
    b = np.array([1], dtype=np.longdouble)
    if not np.all(a != b):
        raise ValueError("precision loss creating arrays")
    assert_(repr(a) != repr(b))

#
# Locale tests: scalar types formatting should be independent of the locale
#

class TestCommaDecimalPointLocale(CommaDecimalPointLocale):

    def test_repr_roundtrip_foreign(self):
        o = 1.5
        assert_equal(o, np.longdouble(repr(o)))

    def test_fromstring_foreign_repr(self):
        f = 1.234
        a = np.fromstring(repr(f), dtype=float, sep=" ")
        assert_equal(a[0], f)

    def test_fromstring_best_effort_float(self):
        assert_equal(np.fromstring("1,234", dtype=float, sep=" "),
                     np.array([1.]))

    def test_fromstring_best_effort(self):
        assert_equal(np.fromstring("1,234", dtype=np.longdouble, sep=" "),
                     np.array([1.]))

    def test_fromstring_foreign(self):
        s = "1.234"
        a = np.fromstring(s, dtype=np.longdouble, sep=" ")
        assert_equal(a[0], np.longdouble(s))

    def test_fromstring_foreign_sep(self):
        a = np.array([1, 2, 3, 4])
        b = np.fromstring("1,2,3,4,", dtype=np.longdouble, sep=",")
        assert_array_equal(a, b)

    def test_fromstring_foreign_value(self):
        b = np.fromstring("1,234", dtype=np.longdouble, sep=" ")
        assert_array_equal(b[0], 1)
