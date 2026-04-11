from collections.abc import Iterable
from typing import Literal as L

__all__ = ["PytestTester"]

class PytestTester:
    module_name: str
    def __init__(self, module_name: str) -> None: ...
    def __call__(
        self,
        label: L["fast", "full"] = "fast",
        verbose: int = 1,
        extra_argv: Iterable[str] | None = None,
        doctests: L[False] = False,
        coverage: bool = False,
        durations: int = -1,
        tests: Iterable[str] | None = None,
    ) -> bool: ...
