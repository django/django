"""
DType classes and utility (:mod:`numpy.dtypes`)
===============================================

This module is home to specific dtypes related functionality and their classes.
For more general information about dtypes, also see `numpy.dtype` and
:ref:`arrays.dtypes`.

Similar to the builtin ``types`` module, this submodule defines types (classes)
that are not widely used directly.

.. versionadded:: NumPy 1.25

    The dtypes module is new in NumPy 1.25.  Previously DType classes were
    only accessible indirectly.


DType classes
-------------

The following are the classes of the corresponding NumPy dtype instances and
NumPy scalar types.  The classes can be used in ``isinstance`` checks and can
also be instantiated or used directly.  Direct use of these classes is not
typical, since their scalar counterparts (e.g. ``np.float64``) or strings
like ``"float64"`` can be used.

.. list-table::
    :header-rows: 1

    * - Group
      - DType class

    * - Boolean
      - ``BoolDType``

    * - Bit-sized integers
      - ``Int8DType``, ``UInt8DType``, ``Int16DType``, ``UInt16DType``,
        ``Int32DType``, ``UInt32DType``, ``Int64DType``, ``UInt64DType``

    * - C-named integers (may be aliases)
      - ``ByteDType``, ``UByteDType``, ``ShortDType``, ``UShortDType``,
        ``IntDType``, ``UIntDType``, ``LongDType``, ``ULongDType``,
        ``LongLongDType``, ``ULongLongDType``

    * - Floating point
      - ``Float16DType``, ``Float32DType``, ``Float64DType``,
        ``LongDoubleDType``

    * - Complex
      - ``Complex64DType``, ``Complex128DType``, ``CLongDoubleDType``

    * - Strings
      - ``BytesDType``, ``BytesDType``

    * - Times
      - ``DateTime64DType``, ``TimeDelta64DType``

    * - Others
      - ``ObjectDType``, ``VoidDType``

"""

__all__ = []


def _add_dtype_helper(DType, alias):
    # Function to add DTypes a bit more conveniently without channeling them
    # through `numpy.core._multiarray_umath` namespace or similar.
    from numpy import dtypes

    setattr(dtypes, DType.__name__, DType)
    __all__.append(DType.__name__)

    if alias:
        alias = alias.removeprefix("numpy.dtypes.")
        setattr(dtypes, alias, DType)
        __all__.append(alias)
