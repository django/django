from typing import Any, Generic
from typing_extensions import TypeVar

import numpy as np
from numpy._typing import _AnyShape

from .core import MaskedArray

__all__ = [
    "MaskedRecords",
    "mrecarray",
    "fromarrays",
    "fromrecords",
    "fromtextfile",
    "addfield",
]

_ShapeT_co = TypeVar("_ShapeT_co", bound=tuple[int, ...], default=_AnyShape, covariant=True)
_DTypeT_co = TypeVar("_DTypeT_co", bound=np.dtype, default=np.dtype, covariant=True)

class MaskedRecords(MaskedArray[_ShapeT_co, _DTypeT_co], Generic[_ShapeT_co, _DTypeT_co]):
    def __new__(
        cls,
        shape,
        dtype=...,
        buf=...,
        offset=...,
        strides=...,
        formats=...,
        names=...,
        titles=...,
        byteorder=...,
        aligned=...,
        mask=...,
        hard_mask=...,
        fill_value=...,
        keep_mask=...,
        copy=...,
        **options,
    ): ...
    _mask: Any
    _fill_value: Any
    @property
    def _data(self): ...
    @property
    def _fieldmask(self): ...
    def __array_finalize__(self, obj): ...
    def __len__(self): ...
    def __getattribute__(self, attr): ...
    def __setattr__(self, attr, val): ...
    def __getitem__(self, indx): ...
    def __setitem__(self, indx, value): ...
    def view(self, dtype=None, type=None): ...
    def harden_mask(self): ...
    def soften_mask(self): ...
    def copy(self): ...
    def tolist(self, fill_value=None): ...
    def __reduce__(self): ...

mrecarray = MaskedRecords

def fromarrays(
    arraylist,
    dtype=None,
    shape=None,
    formats=None,
    names=None,
    titles=None,
    aligned=False,
    byteorder=None,
    fill_value=None,
): ...

def fromrecords(
    reclist,
    dtype=None,
    shape=None,
    formats=None,
    names=None,
    titles=None,
    aligned=False,
    byteorder=None,
    fill_value=None,
    mask=...,
): ...

def fromtextfile(
    fname,
    delimiter=None,
    commentchar="#",
    missingchar="",
    varnames=None,
    vartypes=None,
): ...

def addfield(mrecord, newfield, newfieldname=None): ...
