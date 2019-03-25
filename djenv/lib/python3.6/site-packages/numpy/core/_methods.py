"""
Array methods which are called by both the C-code for the method
and the Python code for the NumPy-namespace function

"""
from __future__ import division, absolute_import, print_function

import warnings

from numpy.core import multiarray as mu
from numpy.core import umath as um
from numpy.core.numeric import asanyarray
from numpy.core import numerictypes as nt
from numpy._globals import _NoValue

# save those O(100) nanoseconds!
umr_maximum = um.maximum.reduce
umr_minimum = um.minimum.reduce
umr_sum = um.add.reduce
umr_prod = um.multiply.reduce
umr_any = um.logical_or.reduce
umr_all = um.logical_and.reduce

# avoid keyword arguments to speed up parsing, saves about 15%-20% for very
# small reductions
def _amax(a, axis=None, out=None, keepdims=False,
          initial=_NoValue):
    return umr_maximum(a, axis, None, out, keepdims, initial)

def _amin(a, axis=None, out=None, keepdims=False,
          initial=_NoValue):
    return umr_minimum(a, axis, None, out, keepdims, initial)

def _sum(a, axis=None, dtype=None, out=None, keepdims=False,
         initial=_NoValue):
    return umr_sum(a, axis, dtype, out, keepdims, initial)

def _prod(a, axis=None, dtype=None, out=None, keepdims=False,
          initial=_NoValue):
    return umr_prod(a, axis, dtype, out, keepdims, initial)

def _any(a, axis=None, dtype=None, out=None, keepdims=False):
    return umr_any(a, axis, dtype, out, keepdims)

def _all(a, axis=None, dtype=None, out=None, keepdims=False):
    return umr_all(a, axis, dtype, out, keepdims)

def _count_reduce_items(arr, axis):
    if axis is None:
        axis = tuple(range(arr.ndim))
    if not isinstance(axis, tuple):
        axis = (axis,)
    items = 1
    for ax in axis:
        items *= arr.shape[ax]
    return items

def _mean(a, axis=None, dtype=None, out=None, keepdims=False):
    arr = asanyarray(a)

    is_float16_result = False
    rcount = _count_reduce_items(arr, axis)
    # Make this warning show up first
    if rcount == 0:
        warnings.warn("Mean of empty slice.", RuntimeWarning, stacklevel=2)

    # Cast bool, unsigned int, and int to float64 by default
    if dtype is None:
        if issubclass(arr.dtype.type, (nt.integer, nt.bool_)):
            dtype = mu.dtype('f8')
        elif issubclass(arr.dtype.type, nt.float16):
            dtype = mu.dtype('f4')
            is_float16_result = True

    ret = umr_sum(arr, axis, dtype, out, keepdims)
    if isinstance(ret, mu.ndarray):
        ret = um.true_divide(
                ret, rcount, out=ret, casting='unsafe', subok=False)
        if is_float16_result and out is None:
            ret = arr.dtype.type(ret)
    elif hasattr(ret, 'dtype'):
        if is_float16_result:
            ret = arr.dtype.type(ret / rcount)
        else:
            ret = ret.dtype.type(ret / rcount)
    else:
        ret = ret / rcount

    return ret

def _var(a, axis=None, dtype=None, out=None, ddof=0, keepdims=False):
    arr = asanyarray(a)

    rcount = _count_reduce_items(arr, axis)
    # Make this warning show up on top.
    if ddof >= rcount:
        warnings.warn("Degrees of freedom <= 0 for slice", RuntimeWarning,
                      stacklevel=2)

    # Cast bool, unsigned int, and int to float64 by default
    if dtype is None and issubclass(arr.dtype.type, (nt.integer, nt.bool_)):
        dtype = mu.dtype('f8')

    # Compute the mean.
    # Note that if dtype is not of inexact type then arraymean will
    # not be either.
    arrmean = umr_sum(arr, axis, dtype, keepdims=True)
    if isinstance(arrmean, mu.ndarray):
        arrmean = um.true_divide(
                arrmean, rcount, out=arrmean, casting='unsafe', subok=False)
    else:
        arrmean = arrmean.dtype.type(arrmean / rcount)

    # Compute sum of squared deviations from mean
    # Note that x may not be inexact and that we need it to be an array,
    # not a scalar.
    x = asanyarray(arr - arrmean)
    if issubclass(arr.dtype.type, nt.complexfloating):
        x = um.multiply(x, um.conjugate(x), out=x).real
    else:
        x = um.multiply(x, x, out=x)
    ret = umr_sum(x, axis, dtype, out, keepdims)

    # Compute degrees of freedom and make sure it is not negative.
    rcount = max([rcount - ddof, 0])

    # divide by degrees of freedom
    if isinstance(ret, mu.ndarray):
        ret = um.true_divide(
                ret, rcount, out=ret, casting='unsafe', subok=False)
    elif hasattr(ret, 'dtype'):
        ret = ret.dtype.type(ret / rcount)
    else:
        ret = ret / rcount

    return ret

def _std(a, axis=None, dtype=None, out=None, ddof=0, keepdims=False):
    ret = _var(a, axis=axis, dtype=dtype, out=out, ddof=ddof,
               keepdims=keepdims)

    if isinstance(ret, mu.ndarray):
        ret = um.sqrt(ret, out=ret)
    elif hasattr(ret, 'dtype'):
        ret = ret.dtype.type(um.sqrt(ret))
    else:
        ret = um.sqrt(ret)

    return ret

def _ptp(a, axis=None, out=None, keepdims=False):
    return um.subtract(
        umr_maximum(a, axis, None, out, keepdims),
        umr_minimum(a, axis, None, None, keepdims),
        out
    )
