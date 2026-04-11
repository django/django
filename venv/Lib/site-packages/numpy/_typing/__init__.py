"""Private counterpart of ``numpy.typing``."""

import sys

from ._array_like import (
    NDArray as NDArray,
    _ArrayLike as _ArrayLike,
    _ArrayLikeAnyString_co as _ArrayLikeAnyString_co,
    _ArrayLikeBool_co as _ArrayLikeBool_co,
    _ArrayLikeBytes_co as _ArrayLikeBytes_co,
    _ArrayLikeComplex128_co as _ArrayLikeComplex128_co,
    _ArrayLikeComplex_co as _ArrayLikeComplex_co,
    _ArrayLikeDT64_co as _ArrayLikeDT64_co,
    _ArrayLikeFloat64_co as _ArrayLikeFloat64_co,
    _ArrayLikeFloat_co as _ArrayLikeFloat_co,
    _ArrayLikeInt as _ArrayLikeInt,
    _ArrayLikeInt_co as _ArrayLikeInt_co,
    _ArrayLikeNumber_co as _ArrayLikeNumber_co,
    _ArrayLikeObject_co as _ArrayLikeObject_co,
    _ArrayLikeStr_co as _ArrayLikeStr_co,
    _ArrayLikeString_co as _ArrayLikeString_co,
    _ArrayLikeTD64_co as _ArrayLikeTD64_co,
    _ArrayLikeUInt_co as _ArrayLikeUInt_co,
    _ArrayLikeVoid_co as _ArrayLikeVoid_co,
    _FiniteNestedSequence as _FiniteNestedSequence,
    _SupportsArray as _SupportsArray,
    _SupportsArrayFunc as _SupportsArrayFunc,
)

#
from ._char_codes import (
    _BoolCodes as _BoolCodes,
    _ByteCodes as _ByteCodes,
    _BytesCodes as _BytesCodes,
    _CDoubleCodes as _CDoubleCodes,
    _CharacterCodes as _CharacterCodes,
    _CLongDoubleCodes as _CLongDoubleCodes,
    _Complex64Codes as _Complex64Codes,
    _Complex128Codes as _Complex128Codes,
    _ComplexFloatingCodes as _ComplexFloatingCodes,
    _CSingleCodes as _CSingleCodes,
    _DoubleCodes as _DoubleCodes,
    _DT64Codes as _DT64Codes,
    _FlexibleCodes as _FlexibleCodes,
    _Float16Codes as _Float16Codes,
    _Float32Codes as _Float32Codes,
    _Float64Codes as _Float64Codes,
    _FloatingCodes as _FloatingCodes,
    _GenericCodes as _GenericCodes,
    _HalfCodes as _HalfCodes,
    _InexactCodes as _InexactCodes,
    _Int8Codes as _Int8Codes,
    _Int16Codes as _Int16Codes,
    _Int32Codes as _Int32Codes,
    _Int64Codes as _Int64Codes,
    _IntCCodes as _IntCCodes,
    _IntCodes as _IntCodes,
    _IntegerCodes as _IntegerCodes,
    _IntPCodes as _IntPCodes,
    _LongCodes as _LongCodes,
    _LongDoubleCodes as _LongDoubleCodes,
    _LongLongCodes as _LongLongCodes,
    _NumberCodes as _NumberCodes,
    _ObjectCodes as _ObjectCodes,
    _ShortCodes as _ShortCodes,
    _SignedIntegerCodes as _SignedIntegerCodes,
    _SingleCodes as _SingleCodes,
    _StrCodes as _StrCodes,
    _StringCodes as _StringCodes,
    _TD64Codes as _TD64Codes,
    _UByteCodes as _UByteCodes,
    _UInt8Codes as _UInt8Codes,
    _UInt16Codes as _UInt16Codes,
    _UInt32Codes as _UInt32Codes,
    _UInt64Codes as _UInt64Codes,
    _UIntCCodes as _UIntCCodes,
    _UIntCodes as _UIntCodes,
    _UIntPCodes as _UIntPCodes,
    _ULongCodes as _ULongCodes,
    _ULongLongCodes as _ULongLongCodes,
    _UnsignedIntegerCodes as _UnsignedIntegerCodes,
    _UShortCodes as _UShortCodes,
    _VoidCodes as _VoidCodes,
)

#
from ._dtype_like import (
    _DTypeLike as _DTypeLike,
    _DTypeLikeBool as _DTypeLikeBool,
    _DTypeLikeBytes as _DTypeLikeBytes,
    _DTypeLikeComplex as _DTypeLikeComplex,
    _DTypeLikeComplex_co as _DTypeLikeComplex_co,
    _DTypeLikeDT64 as _DTypeLikeDT64,
    _DTypeLikeFloat as _DTypeLikeFloat,
    _DTypeLikeInt as _DTypeLikeInt,
    _DTypeLikeObject as _DTypeLikeObject,
    _DTypeLikeStr as _DTypeLikeStr,
    _DTypeLikeTD64 as _DTypeLikeTD64,
    _DTypeLikeUInt as _DTypeLikeUInt,
    _DTypeLikeVoid as _DTypeLikeVoid,
    _HasDType as _HasDType,
    _SupportsDType as _SupportsDType,
    _VoidDTypeLike as _VoidDTypeLike,
)

#
from ._nbit import (
    _NBitByte as _NBitByte,
    _NBitDouble as _NBitDouble,
    _NBitHalf as _NBitHalf,
    _NBitInt as _NBitInt,
    _NBitIntC as _NBitIntC,
    _NBitIntP as _NBitIntP,
    _NBitLong as _NBitLong,
    _NBitLongDouble as _NBitLongDouble,
    _NBitLongLong as _NBitLongLong,
    _NBitShort as _NBitShort,
    _NBitSingle as _NBitSingle,
)

#
from ._nbit_base import (  # type: ignore[deprecated]
    NBitBase as NBitBase,  # pyright: ignore[reportDeprecated]
    _8Bit as _8Bit,
    _16Bit as _16Bit,
    _32Bit as _32Bit,
    _64Bit as _64Bit,
    _96Bit as _96Bit,
    _128Bit as _128Bit,
)

#
from ._nested_sequence import _NestedSequence as _NestedSequence

#
from ._scalars import (
    _BoolLike_co as _BoolLike_co,
    _CharLike_co as _CharLike_co,
    _ComplexLike_co as _ComplexLike_co,
    _FloatLike_co as _FloatLike_co,
    _IntLike_co as _IntLike_co,
    _NumberLike_co as _NumberLike_co,
    _ScalarLike_co as _ScalarLike_co,
    _TD64Like_co as _TD64Like_co,
    _UIntLike_co as _UIntLike_co,
    _VoidLike_co as _VoidLike_co,
)

#
from ._shape import _AnyShape as _AnyShape, _Shape as _Shape, _ShapeLike as _ShapeLike

#
from ._ufunc import (
    _GUFunc_Nin2_Nout1 as _GUFunc_Nin2_Nout1,
    _UFunc_Nin1_Nout1 as _UFunc_Nin1_Nout1,
    _UFunc_Nin1_Nout2 as _UFunc_Nin1_Nout2,
    _UFunc_Nin2_Nout1 as _UFunc_Nin2_Nout1,
    _UFunc_Nin2_Nout2 as _UFunc_Nin2_Nout2,
)

# wrapping the public aliases in `TypeAliasType` helps with introspection readability
if sys.version_info >= (3, 12):
    from typing import TypeAliasType

    from ._array_like import ArrayLike as _ArrayLikeAlias
    from ._dtype_like import DTypeLike as _DTypeLikeAlias

    ArrayLike = TypeAliasType("ArrayLike", _ArrayLikeAlias)
    DTypeLike = TypeAliasType("DTypeLike", _DTypeLikeAlias)

else:
    from ._array_like import ArrayLike as ArrayLike
    from ._dtype_like import DTypeLike as DTypeLike
