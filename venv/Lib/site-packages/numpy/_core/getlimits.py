"""Machine limits for Float32 and Float64 and (long double) if available...

"""
__all__ = ['finfo', 'iinfo']

import math
import types
import warnings
from functools import cached_property

from numpy._utils import set_module

from . import numeric, numerictypes as ntypes
from ._multiarray_umath import _populate_finfo_constants


def _fr0(a):
    """fix rank-0 --> rank-1"""
    if a.ndim == 0:
        a = a.copy()
        a.shape = (1,)
    return a


def _fr1(a):
    """fix rank > 0 --> rank-0"""
    if a.size == 1:
        a = a.copy()
        a.shape = ()
    return a


_convert_to_float = {
    ntypes.csingle: ntypes.single,
    ntypes.complex128: ntypes.float64,
    ntypes.clongdouble: ntypes.longdouble
    }

# Parameters for creating MachAr / MachAr-like objects
_title_fmt = 'numpy {} precision floating point number'
_MACHAR_PARAMS = {
    ntypes.double: {
        'itype': ntypes.int64,
        'fmt': '%24.16e',
        'title': _title_fmt.format('double')},
    ntypes.single: {
        'itype': ntypes.int32,
        'fmt': '%15.7e',
        'title': _title_fmt.format('single')},
    ntypes.longdouble: {
        'itype': ntypes.longlong,
        'fmt': '%s',
        'title': _title_fmt.format('long double')},
    ntypes.half: {
        'itype': ntypes.int16,
        'fmt': '%12.5e',
        'title': _title_fmt.format('half')}}


@set_module('numpy')
class finfo:
    """
    finfo(dtype)

    Machine limits for floating point types.

    Attributes
    ----------
    bits : int
        The number of bits occupied by the type.
    dtype : dtype
        Returns the dtype for which `finfo` returns information. For complex
        input, the returned dtype is the associated ``float*`` dtype for its
        real and complex components.
    eps : float
        The difference between 1.0 and the next smallest representable float
        larger than 1.0. For example, for 64-bit binary floats in the IEEE-754
        standard, ``eps = 2**-52``, approximately 2.22e-16.
    epsneg : float
        The difference between 1.0 and the next smallest representable float
        less than 1.0. For example, for 64-bit binary floats in the IEEE-754
        standard, ``epsneg = 2**-53``, approximately 1.11e-16.
    iexp : int
        The number of bits in the exponent portion of the floating point
        representation.
    machep : int
        The exponent that yields `eps`.
    max : floating point number of the appropriate type
        The largest representable number.
    maxexp : int
        The smallest positive power of the base (2) that causes overflow.
        Corresponds to the C standard MAX_EXP.
    min : floating point number of the appropriate type
        The smallest representable number, typically ``-max``.
    minexp : int
        The most negative power of the base (2) consistent with there
        being no leading 0's in the mantissa. Corresponds to the C
        standard MIN_EXP - 1.
    negep : int
        The exponent that yields `epsneg`.
    nexp : int
        The number of bits in the exponent including its sign and bias.
    nmant : int
        The number of explicit bits in the mantissa (excluding the implicit
        leading bit for normalized numbers).
    precision : int
        The approximate number of decimal digits to which this kind of
        float is precise.
    resolution : floating point number of the appropriate type
        The approximate decimal resolution of this type, i.e.,
        ``10**-precision``.
    tiny : float
        An alias for `smallest_normal`, kept for backwards compatibility.
    smallest_normal : float
        The smallest positive floating point number with 1 as leading bit in
        the mantissa following IEEE-754 (see Notes).
    smallest_subnormal : float
        The smallest positive floating point number with 0 as leading bit in
        the mantissa following IEEE-754.

    Parameters
    ----------
    dtype : float, dtype, or instance
        Kind of floating point or complex floating point
        data-type about which to get information.

    See Also
    --------
    iinfo : The equivalent for integer data types.
    spacing : The distance between a value and the nearest adjacent number
    nextafter : The next floating point value after x1 towards x2

    Notes
    -----
    For developers of NumPy: do not instantiate this at the module level.
    The initial calculation of these parameters is expensive and negatively
    impacts import times.  These objects are cached, so calling ``finfo()``
    repeatedly inside your functions is not a problem.

    Note that ``smallest_normal`` is not actually the smallest positive
    representable value in a NumPy floating point type. As in the IEEE-754
    standard [1]_, NumPy floating point types make use of subnormal numbers to
    fill the gap between 0 and ``smallest_normal``. However, subnormal numbers
    may have significantly reduced precision [2]_.

    For ``longdouble``, the representation varies across platforms. On most
    platforms it is IEEE 754 binary128 (quad precision) or binary64-extended
    (80-bit extended precision). On PowerPC systems, it may use the IBM
    double-double format (a pair of float64 values), which has special
    characteristics for precision and range.

    This function can also be used for complex data types as well. If used,
    the output will be the same as the corresponding real float type
    (e.g. numpy.finfo(numpy.csingle) is the same as numpy.finfo(numpy.single)).
    However, the output is true for the real and imaginary components.

    References
    ----------
    .. [1] IEEE Standard for Floating-Point Arithmetic, IEEE Std 754-2008,
           pp.1-70, 2008, https://doi.org/10.1109/IEEESTD.2008.4610935
    .. [2] Wikipedia, "Denormal Numbers",
           https://en.wikipedia.org/wiki/Denormal_number

    Examples
    --------
    >>> import numpy as np
    >>> np.finfo(np.float64).dtype
    dtype('float64')
    >>> np.finfo(np.complex64).dtype
    dtype('float32')

    """

    _finfo_cache = {}

    __class_getitem__ = classmethod(types.GenericAlias)

    def __new__(cls, dtype):
        try:
            obj = cls._finfo_cache.get(dtype)  # most common path
            if obj is not None:
                return obj
        except TypeError:
            pass

        if dtype is None:
            # Deprecated in NumPy 1.25, 2023-01-16
            warnings.warn(
                "finfo() dtype cannot be None. This behavior will "
                "raise an error in the future. (Deprecated in NumPy 1.25)",
                DeprecationWarning,
                stacklevel=2
            )

        try:
            dtype = numeric.dtype(dtype)
        except TypeError:
            # In case a float instance was given
            dtype = numeric.dtype(type(dtype))

        obj = cls._finfo_cache.get(dtype)
        if obj is not None:
            return obj
        dtypes = [dtype]
        newdtype = ntypes.obj2sctype(dtype)
        if newdtype is not dtype:
            dtypes.append(newdtype)
            dtype = newdtype
        if not issubclass(dtype, numeric.inexact):
            raise ValueError(f"data type {dtype!r} not inexact")
        obj = cls._finfo_cache.get(dtype)
        if obj is not None:
            return obj
        if not issubclass(dtype, numeric.floating):
            newdtype = _convert_to_float[dtype]
            if newdtype is not dtype:
                # dtype changed, for example from complex128 to float64
                dtypes.append(newdtype)
                dtype = newdtype

                obj = cls._finfo_cache.get(dtype, None)
                if obj is not None:
                    # the original dtype was not in the cache, but the new
                    # dtype is in the cache. we add the original dtypes to
                    # the cache and return the result
                    for dt in dtypes:
                        cls._finfo_cache[dt] = obj
                    return obj
        obj = object.__new__(cls)._init(dtype)
        for dt in dtypes:
            cls._finfo_cache[dt] = obj
        return obj

    def _init(self, dtype):
        self.dtype = numeric.dtype(dtype)
        self.bits = self.dtype.itemsize * 8
        self._fmt = None
        self._repr = None
        _populate_finfo_constants(self, self.dtype)
        return self

    @cached_property
    def epsneg(self):
        # Assume typical floating point logic.  Could also use nextafter.
        return self.eps / self._radix

    @cached_property
    def resolution(self):
        return self.dtype.type(10)**-self.precision

    @cached_property
    def machep(self):
        return int(math.log2(self.eps))

    @cached_property
    def negep(self):
        return int(math.log2(self.epsneg))

    @cached_property
    def nexp(self):
        # considering all ones (inf/nan) and all zeros (subnormal/zero)
        return math.ceil(math.log2(self.maxexp - self.minexp + 2))

    @cached_property
    def iexp(self):
        # Calculate exponent bits from it's range:
        return math.ceil(math.log2(self.maxexp - self.minexp))

    def __str__(self):
        if (fmt := getattr(self, "_fmt", None)) is not None:
            return fmt

        def get_str(name, pad=None):
            if (val := getattr(self, name, None)) is None:
                return "<undefined>"
            if pad is not None:
                s = str(val).ljust(pad)
            return str(val)

        precision = get_str("precision", 3)
        machep = get_str("machep", 6)
        negep = get_str("negep", 6)
        minexp = get_str("minexp", 6)
        maxexp = get_str("maxexp", 6)
        resolution = get_str("resolution")
        eps = get_str("eps")
        epsneg = get_str("epsneg")
        tiny = get_str("tiny")
        smallest_normal = get_str("smallest_normal")
        smallest_subnormal = get_str("smallest_subnormal")
        nexp = get_str("nexp", 6)
        max_ = get_str("max")
        if hasattr(self, "min") and hasattr(self, "max") and -self.min == self.max:
            min_ = "-max"
        else:
            min_ = get_str("min")

        fmt = (
            f'Machine parameters for {self.dtype}\n'
            f'---------------------------------------------------------------\n'
            f'precision = {precision}   resolution = {resolution}\n'
            f'machep = {machep}   eps =        {eps}\n'
            f'negep =  {negep}   epsneg =     {epsneg}\n'
            f'minexp = {minexp}   tiny =       {tiny}\n'
            f'maxexp = {maxexp}   max =        {max_}\n'
            f'nexp =   {nexp}   min =        {min_}\n'
            f'smallest_normal = {smallest_normal}   '
            f'smallest_subnormal = {smallest_subnormal}\n'
            f'---------------------------------------------------------------\n'
        )
        self._fmt = fmt
        return fmt

    def __repr__(self):
        if (repr_str := getattr(self, "_repr", None)) is not None:
            return repr_str

        c = self.__class__.__name__

        # Use precision+1 digits in exponential notation
        fmt_str = _MACHAR_PARAMS.get(self.dtype.type, {}).get('fmt', '%s')
        if fmt_str != '%s' and hasattr(self, 'max') and hasattr(self, 'min'):
            max_str = (fmt_str % self.max).strip()
            min_str = (fmt_str % self.min).strip()
        else:
            max_str = str(self.max)
            min_str = str(self.min)

        resolution_str = str(self.resolution)

        repr_str = (f"{c}(resolution={resolution_str}, min={min_str},"
                    f" max={max_str}, dtype={self.dtype})")
        self._repr = repr_str
        return repr_str

    @cached_property
    def tiny(self):
        """Return the value for tiny, alias of smallest_normal.

        Returns
        -------
        tiny : float
            Value for the smallest normal, alias of smallest_normal.

        Warns
        -----
        UserWarning
            If the calculated value for the smallest normal is requested for
            double-double.
        """
        return self.smallest_normal


@set_module('numpy')
class iinfo:
    """
    iinfo(type)

    Machine limits for integer types.

    Attributes
    ----------
    bits : int
        The number of bits occupied by the type.
    dtype : dtype
        Returns the dtype for which `iinfo` returns information.
    min : int
        The smallest integer expressible by the type.
    max : int
        The largest integer expressible by the type.

    Parameters
    ----------
    int_type : integer type, dtype, or instance
        The kind of integer data type to get information about.

    See Also
    --------
    finfo : The equivalent for floating point data types.

    Examples
    --------
    With types:

    >>> import numpy as np
    >>> ii16 = np.iinfo(np.int16)
    >>> ii16.min
    -32768
    >>> ii16.max
    32767
    >>> ii32 = np.iinfo(np.int32)
    >>> ii32.min
    -2147483648
    >>> ii32.max
    2147483647

    With instances:

    >>> ii32 = np.iinfo(np.int32(10))
    >>> ii32.min
    -2147483648
    >>> ii32.max
    2147483647

    """

    _min_vals = {}
    _max_vals = {}

    __class_getitem__ = classmethod(types.GenericAlias)

    def __init__(self, int_type):
        try:
            self.dtype = numeric.dtype(int_type)
        except TypeError:
            self.dtype = numeric.dtype(type(int_type))
        self.kind = self.dtype.kind
        self.bits = self.dtype.itemsize * 8
        self.key = "%s%d" % (self.kind, self.bits)
        if self.kind not in 'iu':
            raise ValueError(f"Invalid integer data type {self.kind!r}.")

    @property
    def min(self):
        """Minimum value of given dtype."""
        if self.kind == 'u':
            return 0
        else:
            try:
                val = iinfo._min_vals[self.key]
            except KeyError:
                val = int(-(1 << (self.bits - 1)))
                iinfo._min_vals[self.key] = val
            return val

    @property
    def max(self):
        """Maximum value of given dtype."""
        try:
            val = iinfo._max_vals[self.key]
        except KeyError:
            if self.kind == 'u':
                val = int((1 << self.bits) - 1)
            else:
                val = int((1 << (self.bits - 1)) - 1)
            iinfo._max_vals[self.key] = val
        return val

    def __str__(self):
        """String representation."""
        fmt = (
            'Machine parameters for %(dtype)s\n'
            '---------------------------------------------------------------\n'
            'min = %(min)s\n'
            'max = %(max)s\n'
            '---------------------------------------------------------------\n'
            )
        return fmt % {'dtype': self.dtype, 'min': self.min, 'max': self.max}

    def __repr__(self):
        return "%s(min=%s, max=%s, dtype=%s)" % (self.__class__.__name__,
                                    self.min, self.max, self.dtype)
