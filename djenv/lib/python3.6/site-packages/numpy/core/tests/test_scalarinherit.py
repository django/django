# -*- coding: utf-8 -*-
""" Test printing of scalar types.

"""
from __future__ import division, absolute_import, print_function

import numpy as np
from numpy.testing import assert_


class A(object):
    pass
class B(A, np.float64):
    pass

class C(B):
    pass
class D(C, B):
    pass

class B0(np.float64, A):
    pass
class C0(B0):
    pass

class TestInherit(object):
    def test_init(self):
        x = B(1.0)
        assert_(str(x) == '1.0')
        y = C(2.0)
        assert_(str(y) == '2.0')
        z = D(3.0)
        assert_(str(z) == '3.0')

    def test_init2(self):
        x = B0(1.0)
        assert_(str(x) == '1.0')
        y = C0(2.0)
        assert_(str(y) == '2.0')


class TestCharacter(object):
    def test_char_radd(self):
        # GH issue 9620, reached gentype_add and raise TypeError
        np_s = np.string_('abc')
        np_u = np.unicode_('abc')
        s = b'def'
        u = u'def'
        assert_(np_s.__radd__(np_s) is NotImplemented)
        assert_(np_s.__radd__(np_u) is NotImplemented)
        assert_(np_s.__radd__(s) is NotImplemented)
        assert_(np_s.__radd__(u) is NotImplemented)
        assert_(np_u.__radd__(np_s) is NotImplemented)
        assert_(np_u.__radd__(np_u) is NotImplemented)
        assert_(np_u.__radd__(s) is NotImplemented)
        assert_(np_u.__radd__(u) is NotImplemented)
        assert_(s + np_s == b'defabc')
        assert_(u + np_u == u'defabc')


        class Mystr(str, np.generic):
            # would segfault
            pass

        ret = s + Mystr('abc')
        assert_(type(ret) is type(s))

    def test_char_repeat(self):
        np_s = np.string_('abc')
        np_u = np.unicode_('abc')
        np_i = np.int(5)
        res_s = b'abc' * 5
        res_u = u'abc' * 5
        assert_(np_s * np_i == res_s)
        assert_(np_u * np_i == res_u)
