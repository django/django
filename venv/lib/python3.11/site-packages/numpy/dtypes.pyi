import numpy as np


__all__: list[str]

# Boolean:
BoolDType = np.dtype[np.bool_]
# Sized integers:
Int8DType = np.dtype[np.int8]
UInt8DType = np.dtype[np.uint8]
Int16DType = np.dtype[np.int16]
UInt16DType = np.dtype[np.uint16]
Int32DType = np.dtype[np.int32]
UInt32DType = np.dtype[np.uint32]
Int64DType = np.dtype[np.int64]
UInt64DType = np.dtype[np.uint64]
# Standard C-named version/alias:
ByteDType = np.dtype[np.byte]
UByteDType = np.dtype[np.ubyte]
ShortDType = np.dtype[np.short]
UShortDType = np.dtype[np.ushort]
IntDType = np.dtype[np.intc]
UIntDType = np.dtype[np.uintc]
LongDType = np.dtype[np.int_]  # Unfortunately, the correct scalar
ULongDType = np.dtype[np.uint]  # Unfortunately, the correct scalar
LongLongDType = np.dtype[np.longlong]
ULongLongDType = np.dtype[np.ulonglong]
# Floats
Float16DType = np.dtype[np.float16]
Float32DType = np.dtype[np.float32]
Float64DType = np.dtype[np.float64]
LongDoubleDType = np.dtype[np.longdouble]
# Complex:
Complex64DType = np.dtype[np.complex64]
Complex128DType = np.dtype[np.complex128]
CLongDoubleDType = np.dtype[np.clongdouble]
# Others:
ObjectDType = np.dtype[np.object_]
BytesDType = np.dtype[np.bytes_]
StrDType = np.dtype[np.str_]
VoidDType = np.dtype[np.void]
DateTime64DType = np.dtype[np.datetime64]
TimeDelta64DType = np.dtype[np.timedelta64]
