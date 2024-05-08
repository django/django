from collections.abc import Sequence
from typing import Union, SupportsIndex

_Shape = tuple[int, ...]

# Anything that can be coerced to a shape tuple
_ShapeLike = Union[SupportsIndex, Sequence[SupportsIndex]]
