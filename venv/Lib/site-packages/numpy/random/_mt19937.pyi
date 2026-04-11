from typing import TypedDict, type_check_only

from numpy import uint32
from numpy._typing import _ArrayLikeInt_co
from numpy.random.bit_generator import BitGenerator, SeedSequence
from numpy.typing import NDArray

__all__ = ["MT19937"]

@type_check_only
class _MT19937Internal(TypedDict):
    key: NDArray[uint32]
    pos: int

@type_check_only
class _MT19937State(TypedDict):
    bit_generator: str
    state: _MT19937Internal

class MT19937(BitGenerator):
    def __init__(self, seed: _ArrayLikeInt_co | SeedSequence | None = ...) -> None: ...
    def _legacy_seeding(self, seed: _ArrayLikeInt_co) -> None: ...
    def jumped(self, jumps: int = 1) -> MT19937: ...
    @property  # type: ignore[override]
    def state(self) -> _MT19937State: ...
    @state.setter
    def state(self, value: _MT19937State) -> None: ...
