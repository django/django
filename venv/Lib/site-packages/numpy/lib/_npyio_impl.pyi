import types
import zipfile
from _typeshed import (
    StrOrBytesPath,
    StrPath,
    SupportsKeysAndGetItem,
    SupportsRead,
    SupportsWrite,
)
from collections.abc import Callable, Collection, Iterable, Iterator, Mapping, Sequence
from re import Pattern
from typing import (
    IO,
    Any,
    ClassVar,
    Generic,
    Literal as L,
    Protocol,
    Self,
    TypeAlias,
    overload,
    type_check_only,
)
from typing_extensions import TypeVar, override

import numpy as np
from numpy._core.multiarray import packbits, unpackbits
from numpy._typing import ArrayLike, DTypeLike, NDArray, _DTypeLike, _SupportsArrayFunc
from numpy.ma.mrecords import MaskedRecords

from ._datasource import DataSource as DataSource

__all__ = [
    "fromregex",
    "genfromtxt",
    "load",
    "loadtxt",
    "packbits",
    "save",
    "savetxt",
    "savez",
    "savez_compressed",
    "unpackbits",
]

_T = TypeVar("_T")
_T_co = TypeVar("_T_co", covariant=True)
_ScalarT = TypeVar("_ScalarT", bound=np.generic)
_ScalarT_co = TypeVar("_ScalarT_co", bound=np.generic, default=Any, covariant=True)

_FName: TypeAlias = StrPath | Iterable[str] | Iterable[bytes]
_FNameRead: TypeAlias = StrPath | SupportsRead[str] | SupportsRead[bytes]
_FNameWriteBytes: TypeAlias = StrPath | SupportsWrite[bytes]
_FNameWrite: TypeAlias = _FNameWriteBytes | SupportsWrite[str]

@type_check_only
class _SupportsReadSeek(SupportsRead[_T_co], Protocol[_T_co]):
    def seek(self, offset: int, whence: int, /) -> object: ...

class BagObj(Generic[_T_co]):
    def __init__(self, /, obj: SupportsKeysAndGetItem[str, _T_co]) -> None: ...
    def __getattribute__(self, key: str, /) -> _T_co: ...
    def __dir__(self) -> list[str]: ...

class NpzFile(Mapping[str, NDArray[_ScalarT_co]]):
    _MAX_REPR_ARRAY_COUNT: ClassVar[int] = 5

    zip: zipfile.ZipFile | None = None
    fid: IO[str] | None = None
    files: list[str]
    allow_pickle: bool
    pickle_kwargs: Mapping[str, Any] | None
    f: BagObj[NpzFile[_ScalarT_co]]

    #
    def __init__(
        self,
        /,
        fid: IO[Any],
        own_fid: bool = False,
        allow_pickle: bool = False,
        pickle_kwargs: Mapping[str, object] | None = None,
        *,
        max_header_size: int = 10_000,
    ) -> None: ...
    def __del__(self) -> None: ...
    def __enter__(self) -> Self: ...
    def __exit__(self, cls: type[BaseException] | None, e: BaseException | None, tb: types.TracebackType | None, /) -> None: ...
    @override
    def __len__(self) -> int: ...
    @override
    def __iter__(self) -> Iterator[str]: ...
    @override
    def __getitem__(self, key: str, /) -> NDArray[_ScalarT_co]: ...

    #
    @override
    @overload
    def get(self, key: str, default: None = None, /) -> NDArray[_ScalarT_co] | None: ...
    @overload
    def get(self, key: str, default: NDArray[_ScalarT_co] | _T, /) -> NDArray[_ScalarT_co] | _T: ...  # pyright: ignore[reportIncompatibleMethodOverride]

    #
    def close(self) -> None: ...

# NOTE: Returns a `NpzFile` if file is a zip file;
# returns an `ndarray`/`memmap` otherwise
def load(
    file: StrOrBytesPath | _SupportsReadSeek[bytes],
    mmap_mode: L["r+", "r", "w+", "c"] | None = None,
    allow_pickle: bool = False,
    fix_imports: bool = True,
    encoding: L["ASCII", "latin1", "bytes"] = "ASCII",
    *,
    max_header_size: int = 10_000,
) -> Any: ...

def save(file: _FNameWriteBytes, arr: ArrayLike, allow_pickle: bool = True) -> None: ...
def savez(file: _FNameWriteBytes, *args: ArrayLike, allow_pickle: bool = True, **kwds: ArrayLike) -> None: ...
def savez_compressed(file: _FNameWriteBytes, *args: ArrayLike, allow_pickle: bool = True, **kwds: ArrayLike) -> None: ...

# File-like objects only have to implement `__iter__` and,
# optionally, `encoding`
@overload
def loadtxt(
    fname: _FName,
    dtype: None = None,
    comments: str | Sequence[str] | None = "#",
    delimiter: str | None = None,
    converters: Mapping[int | str, Callable[[str], Any]] | Callable[[str], Any] | None = None,
    skiprows: int = 0,
    usecols: int | Sequence[int] | None = None,
    unpack: bool = False,
    ndmin: L[0, 1, 2] = 0,
    encoding: str | None = None,
    max_rows: int | None = None,
    *,
    quotechar: str | None = None,
    like: _SupportsArrayFunc | None = None,
) -> NDArray[np.float64]: ...
@overload
def loadtxt(
    fname: _FName,
    dtype: _DTypeLike[_ScalarT],
    comments: str | Sequence[str] | None = "#",
    delimiter: str | None = None,
    converters: Mapping[int | str, Callable[[str], Any]] | Callable[[str], Any] | None = None,
    skiprows: int = 0,
    usecols: int | Sequence[int] | None = None,
    unpack: bool = False,
    ndmin: L[0, 1, 2] = 0,
    encoding: str | None = None,
    max_rows: int | None = None,
    *,
    quotechar: str | None = None,
    like: _SupportsArrayFunc | None = None,
) -> NDArray[_ScalarT]: ...
@overload
def loadtxt(
    fname: _FName,
    dtype: DTypeLike | None,
    comments: str | Sequence[str] | None = "#",
    delimiter: str | None = None,
    converters: Mapping[int | str, Callable[[str], Any]] | Callable[[str], Any] | None = None,
    skiprows: int = 0,
    usecols: int | Sequence[int] | None = None,
    unpack: bool = False,
    ndmin: L[0, 1, 2] = 0,
    encoding: str | None = None,
    max_rows: int | None = None,
    *,
    quotechar: str | None = None,
    like: _SupportsArrayFunc | None = None,
) -> NDArray[Any]: ...

def savetxt(
    fname: _FNameWrite,
    X: ArrayLike,
    fmt: str | Sequence[str] = "%.18e",
    delimiter: str = " ",
    newline: str = "\n",
    header: str = "",
    footer: str = "",
    comments: str = "# ",
    encoding: str | None = None,
) -> None: ...

@overload
def fromregex(
    file: _FNameRead,
    regexp: str | bytes | Pattern[Any],
    dtype: _DTypeLike[_ScalarT],
    encoding: str | None = None,
) -> NDArray[_ScalarT]: ...
@overload
def fromregex(
    file: _FNameRead,
    regexp: str | bytes | Pattern[Any],
    dtype: DTypeLike | None,
    encoding: str | None = None,
) -> NDArray[Any]: ...

@overload
def genfromtxt(
    fname: _FName,
    dtype: None = None,
    comments: str = "#",
    delimiter: str | int | Iterable[int] | None = None,
    skip_header: int = 0,
    skip_footer: int = 0,
    converters: Mapping[int | str, Callable[[str], Any]] | None = None,
    missing_values: Any = None,
    filling_values: Any = None,
    usecols: Sequence[int] | None = None,
    names: L[True] | str | Collection[str] | None = None,
    excludelist: Sequence[str] | None = None,
    deletechars: str = " !#$%&'()*+,-./:;<=>?@[\\]^{|}~",
    replace_space: str = "_",
    autostrip: bool = False,
    case_sensitive: bool | L["upper", "lower"] = True,
    defaultfmt: str = "f%i",
    unpack: bool | None = None,
    usemask: bool = False,
    loose: bool = True,
    invalid_raise: bool = True,
    max_rows: int | None = None,
    encoding: str | None = None,
    *,
    ndmin: L[0, 1, 2] = 0,
    like: _SupportsArrayFunc | None = None,
) -> NDArray[Any]: ...
@overload
def genfromtxt(
    fname: _FName,
    dtype: _DTypeLike[_ScalarT],
    comments: str = "#",
    delimiter: str | int | Iterable[int] | None = None,
    skip_header: int = 0,
    skip_footer: int = 0,
    converters: Mapping[int | str, Callable[[str], Any]] | None = None,
    missing_values: Any = None,
    filling_values: Any = None,
    usecols: Sequence[int] | None = None,
    names: L[True] | str | Collection[str] | None = None,
    excludelist: Sequence[str] | None = None,
    deletechars: str = " !#$%&'()*+,-./:;<=>?@[\\]^{|}~",
    replace_space: str = "_",
    autostrip: bool = False,
    case_sensitive: bool | L["upper", "lower"] = True,
    defaultfmt: str = "f%i",
    unpack: bool | None = None,
    usemask: bool = False,
    loose: bool = True,
    invalid_raise: bool = True,
    max_rows: int | None = None,
    encoding: str | None = None,
    *,
    ndmin: L[0, 1, 2] = 0,
    like: _SupportsArrayFunc | None = None,
) -> NDArray[_ScalarT]: ...
@overload
def genfromtxt(
    fname: _FName,
    dtype: DTypeLike | None,
    comments: str = "#",
    delimiter: str | int | Iterable[int] | None = None,
    skip_header: int = 0,
    skip_footer: int = 0,
    converters: Mapping[int | str, Callable[[str], Any]] | None = None,
    missing_values: Any = None,
    filling_values: Any = None,
    usecols: Sequence[int] | None = None,
    names: L[True] | str | Collection[str] | None = None,
    excludelist: Sequence[str] | None = None,
    deletechars: str = " !#$%&'()*+,-./:;<=>?@[\\]^{|}~",
    replace_space: str = "_",
    autostrip: bool = False,
    case_sensitive: bool | L["upper", "lower"] = True,
    defaultfmt: str = "f%i",
    unpack: bool | None = None,
    usemask: bool = False,
    loose: bool = True,
    invalid_raise: bool = True,
    max_rows: int | None = None,
    encoding: str | None = None,
    *,
    ndmin: L[0, 1, 2] = 0,
    like: _SupportsArrayFunc | None = None,
) -> NDArray[Any]: ...

@overload
def recfromtxt(fname: _FName, *, usemask: L[False] = False, **kwargs: object) -> np.recarray[Any, np.dtype[np.record]]: ...
@overload
def recfromtxt(fname: _FName, *, usemask: L[True], **kwargs: object) -> MaskedRecords[Any, np.dtype[np.void]]: ...

@overload
def recfromcsv(fname: _FName, *, usemask: L[False] = False, **kwargs: object) -> np.recarray[Any, np.dtype[np.record]]: ...
@overload
def recfromcsv(fname: _FName, *, usemask: L[True], **kwargs: object) -> MaskedRecords[Any, np.dtype[np.void]]: ...
