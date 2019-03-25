from __future__ import division, absolute_import, print_function

import sys

import numpy as np
import pytest
try:
    import ctypes
except ImportError:
    ctypes = None

def check_dir(module, module_name=None):
    """Returns a mapping of all objects with the wrong __module__ attribute."""
    if module_name is None:
        module_name = module.__name__
    results = {}
    for name in dir(module):
        item = getattr(module, name)
        if (hasattr(item, '__module__') and hasattr(item, '__name__')
                and item.__module__ != module_name):
            results[name] = item.__module__ + '.' + item.__name__
    return results


@pytest.mark.skipif(
    sys.version_info[0] < 3,
    reason="NumPy exposes slightly different functions on Python 2")
def test_numpy_namespace():
    # None of these objects are publicly documented.
    undocumented = {
        'Tester': 'numpy.testing._private.nosetester.NoseTester',
        '_add_newdoc_ufunc': 'numpy.core._multiarray_umath._add_newdoc_ufunc',
        'add_docstring': 'numpy.core._multiarray_umath.add_docstring',
        'add_newdoc': 'numpy.core.function_base.add_newdoc',
        'add_newdoc_ufunc': 'numpy.core._multiarray_umath._add_newdoc_ufunc',
        'byte_bounds': 'numpy.lib.utils.byte_bounds',
        'compare_chararrays': 'numpy.core._multiarray_umath.compare_chararrays',
        'deprecate': 'numpy.lib.utils.deprecate',
        'deprecate_with_doc': 'numpy.lib.utils.<lambda>',
        'disp': 'numpy.lib.function_base.disp',
        'fastCopyAndTranspose': 'numpy.core._multiarray_umath._fastCopyAndTranspose',
        'get_array_wrap': 'numpy.lib.shape_base.get_array_wrap',
        'get_include': 'numpy.lib.utils.get_include',
        'int_asbuffer': 'numpy.core._multiarray_umath.int_asbuffer',
        'mafromtxt': 'numpy.lib.npyio.mafromtxt',
        'maximum_sctype': 'numpy.core.numerictypes.maximum_sctype',
        'ndfromtxt': 'numpy.lib.npyio.ndfromtxt',
        'recfromcsv': 'numpy.lib.npyio.recfromcsv',
        'recfromtxt': 'numpy.lib.npyio.recfromtxt',
        'safe_eval': 'numpy.lib.utils.safe_eval',
        'set_string_function': 'numpy.core.arrayprint.set_string_function',
        'show_config': 'numpy.__config__.show',
        'who': 'numpy.lib.utils.who',
    }
    # These built-in types are re-exported by numpy.
    builtins = {
        'bool': 'builtins.bool',
        'complex': 'builtins.complex',
        'float': 'builtins.float',
        'int': 'builtins.int',
        'long': 'builtins.int',
        'object': 'builtins.object',
        'str': 'builtins.str',
        'unicode': 'builtins.str',
    }
    whitelist = dict(undocumented, **builtins)
    bad_results = check_dir(np)
    # pytest gives better error messages with the builtin assert than with
    # assert_equal
    assert bad_results == whitelist


def test_numpy_linalg():
    bad_results = check_dir(np.linalg)
    assert bad_results == {}


def test_numpy_fft():
    bad_results = check_dir(np.fft)
    assert bad_results == {}

@pytest.mark.skipif(ctypes is None,
                    reason="ctypes not available in this python")
def test_NPY_NO_EXPORT():
    cdll = ctypes.CDLL(np.core._multiarray_tests.__file__)
    # Make sure an arbitrary NPY_NO_EXPORT function is actually hidden
    f = getattr(cdll, 'test_not_exported', None)
    assert f is None, ("'test_not_exported' is mistakenly exported, "
                      "NPY_NO_EXPORT does not work")
