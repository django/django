""" Test functions for limits module.

"""
import types
import warnings

import pytest

import numpy as np
from numpy import double, half, longdouble, single
from numpy._core import finfo, iinfo
from numpy.testing import assert_, assert_equal, assert_raises

##################################################

class TestPythonFloat:
    def test_singleton(self):
        ftype = finfo(float)
        ftype2 = finfo(float)
        assert_equal(id(ftype), id(ftype2))

class TestHalf:
    def test_singleton(self):
        ftype = finfo(half)
        ftype2 = finfo(half)
        assert_equal(id(ftype), id(ftype2))

class TestSingle:
    def test_singleton(self):
        ftype = finfo(single)
        ftype2 = finfo(single)
        assert_equal(id(ftype), id(ftype2))

class TestDouble:
    def test_singleton(self):
        ftype = finfo(double)
        ftype2 = finfo(double)
        assert_equal(id(ftype), id(ftype2))

class TestLongdouble:
    def test_singleton(self):
        ftype = finfo(longdouble)
        ftype2 = finfo(longdouble)
        assert_equal(id(ftype), id(ftype2))

def assert_finfo_equal(f1, f2):
    # assert two finfo instances have the same attributes
    for attr in ('bits', 'eps', 'epsneg', 'iexp', 'machep',
                 'max', 'maxexp', 'min', 'minexp', 'negep', 'nexp',
                 'nmant', 'precision', 'resolution', 'tiny',
                 'smallest_normal', 'smallest_subnormal'):
        assert_equal(getattr(f1, attr), getattr(f2, attr),
                     f'finfo instances {f1} and {f2} differ on {attr}')

def assert_iinfo_equal(i1, i2):
    # assert two iinfo instances have the same attributes
    for attr in ('bits', 'min', 'max'):
        assert_equal(getattr(i1, attr), getattr(i2, attr),
                     f'iinfo instances {i1} and {i2} differ on {attr}')

class TestFinfo:
    def test_basic(self):
        dts = list(zip(['f2', 'f4', 'f8', 'c8', 'c16'],
                       [np.float16, np.float32, np.float64, np.complex64,
                        np.complex128]))
        for dt1, dt2 in dts:
            assert_finfo_equal(finfo(dt1), finfo(dt2))

        assert_raises(ValueError, finfo, 'i4')

    def test_regression_gh23108(self):
        # np.float32(1.0) and np.float64(1.0) have the same hash and are
        # equal under the == operator
        f1 = np.finfo(np.float32(1.0))
        f2 = np.finfo(np.float64(1.0))
        assert f1 != f2

    def test_regression_gh23867(self):
        class NonHashableWithDtype:
            __hash__ = None
            dtype = np.dtype('float32')

        x = NonHashableWithDtype()
        assert np.finfo(x) == np.finfo(x.dtype)


class TestIinfo:
    def test_basic(self):
        dts = list(zip(['i1', 'i2', 'i4', 'i8',
                   'u1', 'u2', 'u4', 'u8'],
                  [np.int8, np.int16, np.int32, np.int64,
                   np.uint8, np.uint16, np.uint32, np.uint64]))
        for dt1, dt2 in dts:
            assert_iinfo_equal(iinfo(dt1), iinfo(dt2))

        assert_raises(ValueError, iinfo, 'f4')

    def test_unsigned_max(self):
        types = np._core.sctypes['uint']
        for T in types:
            with np.errstate(over="ignore"):
                max_calculated = T(0) - T(1)
            assert_equal(iinfo(T).max, max_calculated)

class TestRepr:
    def test_iinfo_repr(self):
        expected = "iinfo(min=-32768, max=32767, dtype=int16)"
        assert_equal(repr(np.iinfo(np.int16)), expected)

    def test_finfo_repr(self):
        expected = "finfo(resolution=1e-06, min=-3.4028235e+38,"\
                   " max=3.4028235e+38, dtype=float32)"
        assert_equal(repr(np.finfo(np.float32)), expected)


def test_instances():
    # Test the finfo and iinfo results on numeric instances agree with
    # the results on the corresponding types

    for c in [int, np.int16, np.int32, np.int64]:
        class_iinfo = iinfo(c)
        instance_iinfo = iinfo(c(12))

        assert_iinfo_equal(class_iinfo, instance_iinfo)

    for c in [float, np.float16, np.float32, np.float64]:
        class_finfo = finfo(c)
        instance_finfo = finfo(c(1.2))
        assert_finfo_equal(class_finfo, instance_finfo)

    with pytest.raises(ValueError):
        iinfo(10.)

    with pytest.raises(ValueError):
        iinfo('hi')

    with pytest.raises(ValueError):
        finfo(np.int64(1))


def test_subnormal_warning():
    """Test that the subnormal is zero warning is not being raised."""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter('always')
        # Test for common float types
        for dtype in [np.float16, np.float32, np.float64]:
            f = finfo(dtype)
            _ = f.smallest_subnormal
        # Also test longdouble
        with np.errstate(all='ignore'):
            fld = finfo(np.longdouble)
            _ = fld.smallest_subnormal
        # Check no warnings were raised
        assert len(w) == 0


def test_plausible_finfo():
    # Assert that finfo returns reasonable results for all types
    for ftype in np._core.sctypes['float'] + np._core.sctypes['complex']:
        info = np.finfo(ftype)
        assert_(info.nmant > 1)
        assert_(info.minexp < -1)
        assert_(info.maxexp > 1)


class TestRuntimeSubscriptable:
    def test_finfo_generic(self):
        assert isinstance(np.finfo[np.float64], types.GenericAlias)

    def test_iinfo_generic(self):
        assert isinstance(np.iinfo[np.int_], types.GenericAlias)
