regular = "hi"

import sys

from .. import _deprecate

_deprecate.deprecate_attributes(
    __name__,
    {
        "dep1": _deprecate.DeprecatedAttribute("value1", "1.1", issue=1),
        "dep2": _deprecate.DeprecatedAttribute(
            "value2",
            "1.2",
            issue=1,
            instead="instead-string",
        ),
    },
)

this_mod = sys.modules[__name__]
assert this_mod.regular == "hi"
assert "dep1" not in globals()
