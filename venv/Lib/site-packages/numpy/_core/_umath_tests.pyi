# undocumented internal testing module for ufunc features, defined in
# numpy/_core/src/umath/_umath_tests.c.src

from typing import Final, Literal as L, TypedDict, type_check_only

import numpy as np
from numpy._typing import _GUFunc_Nin2_Nout1, _UFunc_Nin1_Nout1, _UFunc_Nin2_Nout1

@type_check_only
class _TestDispatchResult(TypedDict):
    func: str  # e.g. 'func_AVX2'
    var: str  # e.g. 'var_AVX2'
    func_xb: str  # e.g. 'func_AVX2'
    var_xb: str  # e.g. 'var_AVX2'
    all: list[str]  # e.g. ['func_AVX2', 'func_SSE41', 'func']

###

# undocumented
def test_signature(
    nin: int, nout: int, signature: str, /
) -> tuple[
    L[0, 1],  # core_enabled (0 for scalar ufunc; 1 for generalized ufunc)
    tuple[int, ...] | None,  # core_num_dims
    tuple[int, ...] | None,  # core_dim_ixs
    tuple[int, ...] | None,  # core_dim_flags
    tuple[int, ...] | None,  # core_dim_sizes
]: ...

# undocumented
def test_dispatch() -> _TestDispatchResult: ...

# undocumented ufuncs and gufuncs
always_error: Final[_UFunc_Nin2_Nout1[L["always_error"], L[1], None]] = ...
always_error_unary: Final[_UFunc_Nin1_Nout1[L["always_error_unary"], L[1], None]] = ...
always_error_gufunc: Final[_GUFunc_Nin2_Nout1[L["always_error_gufunc"], L[1], None, L["(i),()->()"]]] = ...
inner1d: Final[_GUFunc_Nin2_Nout1[L["inner1d"], L[2], None, L["(i),(i)->()"]]] = ...
innerwt: Final[np.ufunc] = ...  # we have no specialized type for 3->1 gufuncs
matrix_multiply: Final[_GUFunc_Nin2_Nout1[L["matrix_multiply"], L[3], None, L["(m,n),(n,p)->(m,p)"]]] = ...
matmul: Final[_GUFunc_Nin2_Nout1[L["matmul"], L[3], None, L["(m?,n),(n,p?)->(m?,p?)"]]] = ...
euclidean_pdist: Final[_GUFunc_Nin2_Nout1[L["euclidean_pdist"], L[2], None, L["(n,d)->(p)"]]] = ...
cumsum: Final[np.ufunc] = ...  # we have no specialized type for 1->1 gufuncs
inner1d_no_doc: Final[_GUFunc_Nin2_Nout1[L["inner1d_no_doc"], L[2], None, L["(i),(i)->()"]]] = ...
cross1d: Final[_GUFunc_Nin2_Nout1[L["cross1d"], L[2], None, L["(3),(3)->(3)"]]] = ...
_pickleable_module_global_ufunc: Final[np.ufunc] = ...  # 0->0 ufunc; segfaults if called
indexed_negative: Final[_UFunc_Nin1_Nout1[L["indexed_negative"], L[0], L[0]]] = ...  # ntypes=0; can't be called
conv1d_full: Final[_GUFunc_Nin2_Nout1[L["conv1d_full"], L[1], None, L["(m),(n)->(p)"]]] = ...
