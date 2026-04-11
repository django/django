from typing import TypedDict, type_check_only

from numpy._typing import _ArrayLikeInt_co
from numpy.random.bit_generator import BitGenerator, SeedSequence

__all__ = ["PCG64"]

@type_check_only
class _PCG64Internal(TypedDict):
    state: int
    inc: int

@type_check_only
class _PCG64State(TypedDict):
    bit_generator: str
    state: _PCG64Internal
    has_uint32: int
    uinteger: int

class PCG64(BitGenerator):
    def __init__(self, seed: _ArrayLikeInt_co | SeedSequence | None = ...) -> None: ...
    def jumped(self, jumps: int = 1) -> PCG64: ...
    @property  # type: ignore[override]
    def state(
        self,
    ) -> _PCG64State: ...
    @state.setter
    def state(
        self,
        value: _PCG64State,
    ) -> None: ...
    def advance(self, delta: int) -> PCG64: ...

class PCG64DXSM(BitGenerator):
    def __init__(self, seed: _ArrayLikeInt_co | SeedSequence | None = ...) -> None: ...
    def jumped(self, jumps: int = 1) -> PCG64DXSM: ...
    @property  # type: ignore[override]
    def state(self) -> _PCG64State: ...
    @state.setter
    def state(self, value: _PCG64State) -> None: ...
    def advance(self, delta: int) -> PCG64DXSM: ...
