# ruff: noqa: PYI046

from collections.abc import Sequence
from typing import (
    Any,
    Literal,
    NoReturn,
    Protocol,
    Self,
    SupportsIndex,
    SupportsInt,
    TypeAlias,
    TypeVar,
    overload,
    type_check_only,
)

import numpy as np
import numpy.typing as npt
from numpy._typing import (
    _ArrayLikeComplex_co,
    # array-likes
    _ArrayLikeFloat_co,
    _ArrayLikeNumber_co,
    _ComplexLike_co,
    _FloatLike_co,
    # scalar-likes
    _IntLike_co,
    _NestedSequence,
    _NumberLike_co,
    _SupportsArray,
)

_T = TypeVar("_T")
_T_contra = TypeVar("_T_contra", contravariant=True)
_ScalarT = TypeVar("_ScalarT", bound=np.number | np.bool | np.object_)

# compatible with e.g. int, float, complex, Decimal, Fraction, and ABCPolyBase
@type_check_only
class _SupportsCoefOps(Protocol[_T_contra]):
    def __eq__(self, x: object, /) -> bool: ...
    def __ne__(self, x: object, /) -> bool: ...
    def __neg__(self, /) -> Self: ...
    def __pos__(self, /) -> Self: ...
    def __add__(self, x: _T_contra, /) -> Self: ...
    def __sub__(self, x: _T_contra, /) -> Self: ...
    def __mul__(self, x: _T_contra, /) -> Self: ...
    def __pow__(self, x: _T_contra, /) -> Self | float: ...
    def __radd__(self, x: _T_contra, /) -> Self: ...
    def __rsub__(self, x: _T_contra, /) -> Self: ...
    def __rmul__(self, x: _T_contra, /) -> Self: ...

_Series: TypeAlias = np.ndarray[tuple[int], np.dtype[_ScalarT]]

_FloatSeries: TypeAlias = _Series[np.floating]
_ComplexSeries: TypeAlias = _Series[np.complexfloating]
_ObjectSeries: TypeAlias = _Series[np.object_]
_CoefSeries: TypeAlias = _Series[np.inexact | np.object_]

_FloatArray: TypeAlias = npt.NDArray[np.floating]
_ComplexArray: TypeAlias = npt.NDArray[np.complexfloating]
_ObjectArray: TypeAlias = npt.NDArray[np.object_]
_CoefArray: TypeAlias = npt.NDArray[np.inexact | np.object_]

_Tuple2: TypeAlias = tuple[_T, _T]
_Array1: TypeAlias = np.ndarray[tuple[Literal[1]], np.dtype[_ScalarT]]
_Array2: TypeAlias = np.ndarray[tuple[Literal[2]], np.dtype[_ScalarT]]

_AnyInt: TypeAlias = SupportsInt | SupportsIndex

_CoefObjectLike_co: TypeAlias = np.object_ | _SupportsCoefOps[Any]
_CoefLike_co: TypeAlias = _NumberLike_co | _CoefObjectLike_co

# The term "series" is used here to refer to 1-d arrays of numeric scalars.
_SeriesLikeBool_co: TypeAlias = _SupportsArray[np.dtype[np.bool]] | Sequence[bool | np.bool]
_SeriesLikeInt_co: TypeAlias = _SupportsArray[np.dtype[np.integer | np.bool]] | Sequence[_IntLike_co]
_SeriesLikeFloat_co: TypeAlias = _SupportsArray[np.dtype[np.floating | np.integer | np.bool]] | Sequence[_FloatLike_co]
_SeriesLikeComplex_co: TypeAlias = _SupportsArray[np.dtype[np.number | np.bool]] | Sequence[_ComplexLike_co]
_SeriesLikeObject_co: TypeAlias = _SupportsArray[np.dtype[np.object_]] | Sequence[_CoefObjectLike_co]
_SeriesLikeCoef_co: TypeAlias = _SupportsArray[np.dtype[np.number | np.bool | np.object_]] | Sequence[_CoefLike_co]

_ArrayLikeCoefObject_co: TypeAlias = _CoefObjectLike_co | _SeriesLikeObject_co | _NestedSequence[_SeriesLikeObject_co]
_ArrayLikeCoef_co: TypeAlias = npt.NDArray[np.number | np.bool | np.object_] | _ArrayLikeNumber_co | _ArrayLikeCoefObject_co

_Line: TypeAlias = np.ndarray[tuple[int], np.dtype[_ScalarT]]

@type_check_only
class _FuncLine(Protocol):
    @overload
    def __call__(self, /, off: _ScalarT, scl: _ScalarT) -> _Line[_ScalarT]: ...
    @overload
    def __call__(self, /, off: int, scl: int) -> _Line[np.int_]: ...
    @overload
    def __call__(self, /, off: float, scl: float) -> _Line[np.float64]: ...
    @overload
    def __call__(self, /, off: complex, scl: complex) -> _Line[np.complex128]: ...
    @overload
    def __call__(self, /, off: _SupportsCoefOps[Any], scl: _SupportsCoefOps[Any]) -> _Line[np.object_]: ...

@type_check_only
class _FuncFromRoots(Protocol):
    @overload
    def __call__(self, /, roots: _SeriesLikeFloat_co) -> _FloatSeries: ...
    @overload
    def __call__(self, /, roots: _SeriesLikeComplex_co) -> _ComplexSeries: ...
    @overload
    def __call__(self, /, roots: _SeriesLikeCoef_co) -> _ObjectSeries: ...

@type_check_only
class _FuncBinOp(Protocol):
    @overload
    def __call__(self, /, c1: _SeriesLikeBool_co, c2: _SeriesLikeBool_co) -> NoReturn: ...
    @overload
    def __call__(self, /, c1: _SeriesLikeFloat_co, c2: _SeriesLikeFloat_co) -> _FloatSeries: ...
    @overload
    def __call__(self, /, c1: _SeriesLikeComplex_co, c2: _SeriesLikeComplex_co) -> _ComplexSeries: ...
    @overload
    def __call__(self, /, c1: _SeriesLikeCoef_co, c2: _SeriesLikeCoef_co) -> _ObjectSeries: ...

@type_check_only
class _FuncUnOp(Protocol):
    @overload
    def __call__(self, /, c: _SeriesLikeFloat_co) -> _FloatSeries: ...
    @overload
    def __call__(self, /, c: _SeriesLikeComplex_co) -> _ComplexSeries: ...
    @overload
    def __call__(self, /, c: _SeriesLikeCoef_co) -> _ObjectSeries: ...

@type_check_only
class _FuncPoly2Ortho(Protocol):
    @overload
    def __call__(self, /, pol: _SeriesLikeFloat_co) -> _FloatSeries: ...
    @overload
    def __call__(self, /, pol: _SeriesLikeComplex_co) -> _ComplexSeries: ...
    @overload
    def __call__(self, /, pol: _SeriesLikeCoef_co) -> _ObjectSeries: ...

@type_check_only
class _FuncPow(Protocol):
    @overload
    def __call__(self, /, c: _SeriesLikeFloat_co, pow: _IntLike_co, maxpower: _IntLike_co | None = ...) -> _FloatSeries: ...
    @overload
    def __call__(self, /, c: _SeriesLikeComplex_co, pow: _IntLike_co, maxpower: _IntLike_co | None = ...) -> _ComplexSeries: ...
    @overload
    def __call__(self, /, c: _SeriesLikeCoef_co, pow: _IntLike_co, maxpower: _IntLike_co | None = ...) -> _ObjectSeries: ...

@type_check_only
class _FuncDer(Protocol):
    @overload
    def __call__(
        self,
        /,
        c: _ArrayLikeFloat_co,
        m: SupportsIndex = 1,
        scl: _FloatLike_co = 1,
        axis: SupportsIndex = 0,
    ) -> _FloatArray: ...
    @overload
    def __call__(
        self,
        /,
        c: _ArrayLikeComplex_co,
        m: SupportsIndex = 1,
        scl: _ComplexLike_co = 1,
        axis: SupportsIndex = 0,
    ) -> _ComplexArray: ...
    @overload
    def __call__(
        self,
        /,
        c: _ArrayLikeCoef_co,
        m: SupportsIndex = 1,
        scl: _CoefLike_co = 1,
        axis: SupportsIndex = 0,
    ) -> _ObjectArray: ...

@type_check_only
class _FuncInteg(Protocol):
    @overload
    def __call__(
        self,
        /,
        c: _ArrayLikeFloat_co,
        m: SupportsIndex = 1,
        k: _FloatLike_co | _SeriesLikeFloat_co = [],
        lbnd: _FloatLike_co = 0,
        scl: _FloatLike_co = 1,
        axis: SupportsIndex = 0,
    ) -> _FloatArray: ...
    @overload
    def __call__(
        self,
        /,
        c: _ArrayLikeComplex_co,
        m: SupportsIndex = 1,
        k: _ComplexLike_co | _SeriesLikeComplex_co = [],
        lbnd: _ComplexLike_co = 0,
        scl: _ComplexLike_co = 1,
        axis: SupportsIndex = 0,
    ) -> _ComplexArray: ...
    @overload
    def __call__(
        self,
        /,
        c: _ArrayLikeCoef_co,
        m: SupportsIndex = 1,
        k: _CoefLike_co | _SeriesLikeCoef_co = [],
        lbnd: _CoefLike_co = 0,
        scl: _CoefLike_co = 1,
        axis: SupportsIndex = 0,
    ) -> _ObjectArray: ...

@type_check_only
class _FuncVal(Protocol):
    @overload
    def __call__(self, /, x: _FloatLike_co, c: _SeriesLikeFloat_co, tensor: bool = True) -> np.floating: ...
    @overload
    def __call__(self, /, x: _NumberLike_co, c: _SeriesLikeComplex_co, tensor: bool = True) -> np.complexfloating: ...
    @overload
    def __call__(self, /, x: _ArrayLikeFloat_co, c: _ArrayLikeFloat_co, tensor: bool = True) -> _FloatArray: ...
    @overload
    def __call__(self, /, x: _ArrayLikeComplex_co, c: _ArrayLikeComplex_co, tensor: bool = True) -> _ComplexArray: ...
    @overload
    def __call__(self, /, x: _ArrayLikeCoef_co, c: _ArrayLikeCoef_co, tensor: bool = True) -> _ObjectArray: ...
    @overload
    def __call__(self, /, x: _CoefLike_co, c: _SeriesLikeObject_co, tensor: bool = True) -> _SupportsCoefOps[Any]: ...

@type_check_only
class _FuncVal2D(Protocol):
    @overload
    def __call__(self, /, x: _FloatLike_co, y: _FloatLike_co, c: _SeriesLikeFloat_co) -> np.floating: ...
    @overload
    def __call__(self, /, x: _NumberLike_co, y: _NumberLike_co, c: _SeriesLikeComplex_co) -> np.complexfloating: ...
    @overload
    def __call__(self, /, x: _ArrayLikeFloat_co, y: _ArrayLikeFloat_co, c: _ArrayLikeFloat_co) -> _FloatArray: ...
    @overload
    def __call__(self, /, x: _ArrayLikeComplex_co, y: _ArrayLikeComplex_co, c: _ArrayLikeComplex_co) -> _ComplexArray: ...
    @overload
    def __call__(self, /, x: _ArrayLikeCoef_co, y: _ArrayLikeCoef_co, c: _ArrayLikeCoef_co) -> _ObjectArray: ...
    @overload
    def __call__(self, /, x: _CoefLike_co, y: _CoefLike_co, c: _SeriesLikeCoef_co) -> _SupportsCoefOps[Any]: ...

@type_check_only
class _FuncVal3D(Protocol):
    @overload
    def __call__(
        self,
        /,
        x: _FloatLike_co,
        y: _FloatLike_co,
        z: _FloatLike_co,
        c: _SeriesLikeFloat_co,
    ) -> np.floating: ...
    @overload
    def __call__(
        self,
        /,
        x: _NumberLike_co,
        y: _NumberLike_co,
        z: _NumberLike_co,
        c: _SeriesLikeComplex_co,
    ) -> np.complexfloating: ...
    @overload
    def __call__(
        self,
        /,
        x: _ArrayLikeFloat_co,
        y: _ArrayLikeFloat_co,
        z: _ArrayLikeFloat_co,
        c: _ArrayLikeFloat_co,
    ) -> _FloatArray: ...
    @overload
    def __call__(
        self,
        /,
        x: _ArrayLikeComplex_co,
        y: _ArrayLikeComplex_co,
        z: _ArrayLikeComplex_co,
        c: _ArrayLikeComplex_co,
    ) -> _ComplexArray: ...
    @overload
    def __call__(
        self,
        /,
        x: _ArrayLikeCoef_co,
        y: _ArrayLikeCoef_co,
        z: _ArrayLikeCoef_co,
        c: _ArrayLikeCoef_co,
    ) -> _ObjectArray: ...
    @overload
    def __call__(
        self,
        /,
        x: _CoefLike_co,
        y: _CoefLike_co,
        z: _CoefLike_co,
        c: _SeriesLikeCoef_co,
    ) -> _SupportsCoefOps[Any]: ...

@type_check_only
class _FuncVander(Protocol):
    @overload
    def __call__(self, /, x: _ArrayLikeFloat_co, deg: SupportsIndex) -> _FloatArray: ...
    @overload
    def __call__(self, /, x: _ArrayLikeComplex_co, deg: SupportsIndex) -> _ComplexArray: ...
    @overload
    def __call__(self, /, x: _ArrayLikeCoef_co, deg: SupportsIndex) -> _ObjectArray: ...
    @overload
    def __call__(self, /, x: npt.ArrayLike, deg: SupportsIndex) -> _CoefArray: ...

_AnyDegrees: TypeAlias = Sequence[SupportsIndex]

@type_check_only
class _FuncVander2D(Protocol):
    @overload
    def __call__(self, /, x: _ArrayLikeFloat_co, y: _ArrayLikeFloat_co, deg: _AnyDegrees) -> _FloatArray: ...
    @overload
    def __call__(self, /, x: _ArrayLikeComplex_co, y: _ArrayLikeComplex_co, deg: _AnyDegrees) -> _ComplexArray: ...
    @overload
    def __call__(self, /, x: _ArrayLikeCoef_co, y: _ArrayLikeCoef_co, deg: _AnyDegrees) -> _ObjectArray: ...
    @overload
    def __call__(self, /, x: npt.ArrayLike, y: npt.ArrayLike, deg: _AnyDegrees) -> _CoefArray: ...

@type_check_only
class _FuncVander3D(Protocol):
    @overload
    def __call__(
        self,
        /,
        x: _ArrayLikeFloat_co,
        y: _ArrayLikeFloat_co,
        z: _ArrayLikeFloat_co,
        deg: _AnyDegrees,
    ) -> _FloatArray: ...
    @overload
    def __call__(
        self,
        /,
        x: _ArrayLikeComplex_co,
        y: _ArrayLikeComplex_co,
        z: _ArrayLikeComplex_co,
        deg: _AnyDegrees,
    ) -> _ComplexArray: ...
    @overload
    def __call__(
        self,
        /,
        x: _ArrayLikeCoef_co,
        y: _ArrayLikeCoef_co,
        z: _ArrayLikeCoef_co,
        deg: _AnyDegrees,
    ) -> _ObjectArray: ...
    @overload
    def __call__(
        self,
        /,
        x: npt.ArrayLike,
        y: npt.ArrayLike,
        z: npt.ArrayLike,
        deg: _AnyDegrees,
    ) -> _CoefArray: ...

_FullFitResult: TypeAlias = Sequence[np.inexact | np.int32]

@type_check_only
class _FuncFit(Protocol):
    @overload
    def __call__(
        self,
        /,
        x: _SeriesLikeFloat_co,
        y: _ArrayLikeFloat_co,
        deg: int | _SeriesLikeInt_co,
        rcond: float | None = ...,
        full: Literal[False] = False,
        w: _SeriesLikeFloat_co | None = ...,
    ) -> _FloatArray: ...
    @overload
    def __call__(
        self,
        x: _SeriesLikeFloat_co,
        y: _ArrayLikeFloat_co,
        deg: int | _SeriesLikeInt_co,
        rcond: float | None,
        full: Literal[True],
        /,
        w: _SeriesLikeFloat_co | None = ...,
    ) -> tuple[_FloatArray, _FullFitResult]: ...
    @overload
    def __call__(
        self,
        /,
        x: _SeriesLikeFloat_co,
        y: _ArrayLikeFloat_co,
        deg: int | _SeriesLikeInt_co,
        rcond: float | None = ...,
        *,
        full: Literal[True],
        w: _SeriesLikeFloat_co | None = ...,
    ) -> tuple[_FloatArray, _FullFitResult]: ...
    @overload
    def __call__(
        self,
        /,
        x: _SeriesLikeComplex_co,
        y: _ArrayLikeComplex_co,
        deg: int | _SeriesLikeInt_co,
        rcond: float | None = ...,
        full: Literal[False] = False,
        w: _SeriesLikeFloat_co | None = ...,
    ) -> _ComplexArray: ...
    @overload
    def __call__(
        self,
        x: _SeriesLikeComplex_co,
        y: _ArrayLikeComplex_co,
        deg: int | _SeriesLikeInt_co,
        rcond: float | None,
        full: Literal[True],
        /,
        w: _SeriesLikeFloat_co | None = ...,
    ) -> tuple[_ComplexArray, _FullFitResult]: ...
    @overload
    def __call__(
        self,
        /,
        x: _SeriesLikeComplex_co,
        y: _ArrayLikeComplex_co,
        deg: int | _SeriesLikeInt_co,
        rcond: float | None = ...,
        *,
        full: Literal[True],
        w: _SeriesLikeFloat_co | None = ...,
    ) -> tuple[_ComplexArray, _FullFitResult]: ...
    @overload
    def __call__(
        self,
        /,
        x: _SeriesLikeComplex_co,
        y: _ArrayLikeCoef_co,
        deg: int | _SeriesLikeInt_co,
        rcond: float | None = ...,
        full: Literal[False] = False,
        w: _SeriesLikeFloat_co | None = ...,
    ) -> _ObjectArray: ...
    @overload
    def __call__(
        self,
        x: _SeriesLikeComplex_co,
        y: _ArrayLikeCoef_co,
        deg: int | _SeriesLikeInt_co,
        rcond: float | None,
        full: Literal[True],
        /,
        w: _SeriesLikeFloat_co | None = ...,
    ) -> tuple[_ObjectArray, _FullFitResult]: ...
    @overload
    def __call__(
        self,
        /,
        x: _SeriesLikeComplex_co,
        y: _ArrayLikeCoef_co,
        deg: int | _SeriesLikeInt_co,
        rcond: float | None = ...,
        *,
        full: Literal[True],
        w: _SeriesLikeFloat_co | None = ...,
    ) -> tuple[_ObjectArray, _FullFitResult]: ...

@type_check_only
class _FuncRoots(Protocol):
    @overload
    def __call__(self, /, c: _SeriesLikeFloat_co) -> _Series[np.float64]: ...
    @overload
    def __call__(self, /, c: _SeriesLikeComplex_co) -> _Series[np.complex128]: ...
    @overload
    def __call__(self, /, c: _SeriesLikeCoef_co) -> _ObjectSeries: ...

_Companion: TypeAlias = np.ndarray[tuple[int, int], np.dtype[_ScalarT]]

@type_check_only
class _FuncCompanion(Protocol):
    @overload
    def __call__(self, /, c: _SeriesLikeFloat_co) -> _Companion[np.float64]: ...
    @overload
    def __call__(self, /, c: _SeriesLikeComplex_co) -> _Companion[np.complex128]: ...
    @overload
    def __call__(self, /, c: _SeriesLikeCoef_co) -> _Companion[np.object_]: ...

@type_check_only
class _FuncGauss(Protocol):
    def __call__(self, /, deg: SupportsIndex) -> _Tuple2[_Series[np.float64]]: ...

@type_check_only
class _FuncWeight(Protocol):
    @overload
    def __call__(self, /, x: _ArrayLikeFloat_co) -> npt.NDArray[np.float64]: ...
    @overload
    def __call__(self, /, x: _ArrayLikeComplex_co) -> npt.NDArray[np.complex128]: ...
    @overload
    def __call__(self, /, x: _ArrayLikeCoef_co) -> _ObjectArray: ...
