# -*- coding: utf-8 -*-
"""
Helper for testing a C++ exception throw aborts the process.

Takes one argument, the name of the function in :mod:`_test_extension_cpp` to call.
"""
import sys
import greenlet
from greenlet.tests import _test_extension_cpp
print('fail_cpp_exception is running')

def run_unhandled_exception_in_greenlet_aborts():
    def _():
        _test_extension_cpp.test_exception_switch_and_do_in_g2(
            _test_extension_cpp.test_exception_throw_nonstd
        )
    g1 = greenlet.greenlet(_)
    g1.switch()


func_name = sys.argv[1]
try:
    func = getattr(_test_extension_cpp, func_name)
except AttributeError:
    if func_name == run_unhandled_exception_in_greenlet_aborts.__name__:
        func = run_unhandled_exception_in_greenlet_aborts
    elif func_name == 'run_as_greenlet_target':
        g = greenlet.greenlet(_test_extension_cpp.test_exception_throw_std)
        func = g.switch
    else:
        raise
print('raising', func, flush=True)
func()
