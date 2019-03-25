"""
Test the scalar constructors, which also do type-coercion
"""
from __future__ import division, absolute_import, print_function

import sys
import platform
import pytest

import numpy as np
from numpy.testing import (
    assert_equal, assert_almost_equal, assert_raises, assert_warns,
    )

class TestFromString(object):
    def test_floating(self):
        # Ticket #640, floats from string
        fsingle = np.single('1.234')
        fdouble = np.double('1.234')
        flongdouble = np.longdouble('1.234')
        assert_almost_equal(fsingle, 1.234)
        assert_almost_equal(fdouble, 1.234)
        assert_almost_equal(flongdouble, 1.234)

    def test_floating_overflow(self):
        """ Strings containing an unrepresentable float overflow """
        fhalf = np.half('1e10000')
        assert_equal(fhalf, np.inf)
        fsingle = np.single('1e10000')
        assert_equal(fsingle, np.inf)
        fdouble = np.double('1e10000')
        assert_equal(fdouble, np.inf)
        flongdouble = assert_warns(RuntimeWarning, np.longdouble, '1e10000')
        assert_equal(flongdouble, np.inf)

        fhalf = np.half('-1e10000')
        assert_equal(fhalf, -np.inf)
        fsingle = np.single('-1e10000')
        assert_equal(fsingle, -np.inf)
        fdouble = np.double('-1e10000')
        assert_equal(fdouble, -np.inf)
        flongdouble = assert_warns(RuntimeWarning, np.longdouble, '-1e10000')
        assert_equal(flongdouble, -np.inf)

    @pytest.mark.skipif((sys.version_info[0] >= 3)
                        or (sys.platform == "win32"
                            and platform.architecture()[0] == "64bit"),
                        reason="numpy.intp('0xff', 16) not supported on Py3 "
                               "or 64 bit Windows")
    def test_intp(self):
        # Ticket #99
        i_width = np.int_(0).nbytes*2 - 1
        np.intp('0x' + 'f'*i_width, 16)
        assert_raises(OverflowError, np.intp, '0x' + 'f'*(i_width+1), 16)
        assert_raises(ValueError, np.intp, '0x1', 32)
        assert_equal(255, np.intp('0xFF', 16))


class TestFromInt(object):
    def test_intp(self):
        # Ticket #99
        assert_equal(1024, np.intp(1024))

    def test_uint64_from_negative(self):
        assert_equal(np.uint64(-2), np.uint64(18446744073709551614))
