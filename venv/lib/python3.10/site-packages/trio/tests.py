import importlib
import sys
from typing import Any

from . import _tests
from ._deprecate import warn_deprecated

warn_deprecated(
    "trio.tests",
    "0.22.1",
    instead="trio._tests",
    issue="https://github.com/python-trio/trio/issues/274",
)


# This won't give deprecation warning on import, but will give a warning on use of any
# attribute in tests, and static analysis tools will also not see any content inside.
class TestsDeprecationWrapper:
    __name__ = "trio.tests"

    def __getattr__(self, attr: str) -> Any:
        warn_deprecated(
            f"trio.tests.{attr}",
            "0.22.1",
            instead=f"trio._tests.{attr}",
            issue="https://github.com/python-trio/trio/issues/274",
        )

        # needed to access e.g. trio._tests.tools, although pytest doesn't need it
        if not hasattr(_tests, attr):  # pragma: no cover
            importlib.import_module(f"trio._tests.{attr}", "trio._tests")
            return attr

        return getattr(_tests, attr)


# https://stackoverflow.com/questions/2447353/getattr-on-a-module
sys.modules[__name__] = TestsDeprecationWrapper()  # type: ignore[assignment]
