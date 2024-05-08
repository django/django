from __future__ import annotations

import sys
import warnings
from functools import wraps
from types import ModuleType
from typing import TYPE_CHECKING, ClassVar, TypeVar

import attrs

if TYPE_CHECKING:
    from collections.abc import Callable

    from typing_extensions import ParamSpec

    ArgsT = ParamSpec("ArgsT")

RetT = TypeVar("RetT")


# We want our warnings to be visible by default (at least for now), but we
# also want it to be possible to override that using the -W switch. AFAICT
# this means we cannot inherit from DeprecationWarning, because the only way
# to make it visible by default then would be to add our own filter at import
# time, but that would override -W switches...
class TrioDeprecationWarning(FutureWarning):
    """Warning emitted if you use deprecated Trio functionality.

    As a young project, Trio is currently quite aggressive about deprecating
    and/or removing functionality that we realize was a bad idea. If you use
    Trio, you should subscribe to `issue #1
    <https://github.com/python-trio/trio/issues/1>`__ to get information about
    upcoming deprecations and other backwards compatibility breaking changes.

    Despite the name, this class currently inherits from
    :class:`FutureWarning`, not :class:`DeprecationWarning`, because while
    we're in young-and-aggressive mode we want these warnings to be visible by
    default. You can hide them by installing a filter or with the ``-W``
    switch: see the :mod:`warnings` documentation for details.

    """


def _url_for_issue(issue: int) -> str:
    return f"https://github.com/python-trio/trio/issues/{issue}"


def _stringify(thing: object) -> str:
    if hasattr(thing, "__module__") and hasattr(thing, "__qualname__"):
        return f"{thing.__module__}.{thing.__qualname__}"
    return str(thing)


def warn_deprecated(
    thing: object,
    version: str,
    *,
    issue: int | None,
    instead: object,
    stacklevel: int = 2,
) -> None:
    stacklevel += 1
    msg = f"{_stringify(thing)} is deprecated since Trio {version}"
    if instead is None:
        msg += " with no replacement"
    else:
        msg += f"; use {_stringify(instead)} instead"
    if issue is not None:
        msg += f" ({_url_for_issue(issue)})"
    warnings.warn(TrioDeprecationWarning(msg), stacklevel=stacklevel)


# @deprecated("0.2.0", issue=..., instead=...)
# def ...
def deprecated(
    version: str, *, thing: object = None, issue: int | None, instead: object
) -> Callable[[Callable[ArgsT, RetT]], Callable[ArgsT, RetT]]:
    def do_wrap(fn: Callable[ArgsT, RetT]) -> Callable[ArgsT, RetT]:
        nonlocal thing

        @wraps(fn)
        def wrapper(*args: ArgsT.args, **kwargs: ArgsT.kwargs) -> RetT:
            warn_deprecated(thing, version, instead=instead, issue=issue)
            return fn(*args, **kwargs)

        # If our __module__ or __qualname__ get modified, we want to pick up
        # on that, so we read them off the wrapper object instead of the (now
        # hidden) fn object
        if thing is None:
            thing = wrapper

        if wrapper.__doc__ is not None:
            doc = wrapper.__doc__
            doc = doc.rstrip()
            doc += "\n\n"
            doc += f".. deprecated:: {version}\n"
            if instead is not None:
                doc += f"   Use {_stringify(instead)} instead.\n"
            if issue is not None:
                doc += f"   For details, see `issue #{issue} <{_url_for_issue(issue)}>`__.\n"
            doc += "\n"
            wrapper.__doc__ = doc

        return wrapper

    return do_wrap


def deprecated_alias(
    old_qualname: str,
    new_fn: Callable[ArgsT, RetT],
    version: str,
    *,
    issue: int | None,
) -> Callable[ArgsT, RetT]:
    @deprecated(version, issue=issue, instead=new_fn)
    @wraps(new_fn, assigned=("__module__", "__annotations__"))
    def wrapper(*args: ArgsT.args, **kwargs: ArgsT.kwargs) -> RetT:
        """Deprecated alias."""
        return new_fn(*args, **kwargs)

    wrapper.__qualname__ = old_qualname
    wrapper.__name__ = old_qualname.rpartition(".")[-1]
    return wrapper


@attrs.frozen(slots=False)
class DeprecatedAttribute:
    _not_set: ClassVar[object] = object()

    value: object
    version: str
    issue: int | None
    instead: object = _not_set


class _ModuleWithDeprecations(ModuleType):
    __deprecated_attributes__: dict[str, DeprecatedAttribute]

    def __getattr__(self, name: str) -> object:
        if name in self.__deprecated_attributes__:
            info = self.__deprecated_attributes__[name]
            instead = info.instead
            if instead is DeprecatedAttribute._not_set:
                instead = info.value
            thing = f"{self.__name__}.{name}"
            warn_deprecated(thing, info.version, issue=info.issue, instead=instead)
            return info.value

        msg = "module '{}' has no attribute '{}'"
        raise AttributeError(msg.format(self.__name__, name))


def enable_attribute_deprecations(module_name: str) -> None:
    module = sys.modules[module_name]
    module.__class__ = _ModuleWithDeprecations
    assert isinstance(module, _ModuleWithDeprecations)
    # Make sure that this is always defined so that
    # _ModuleWithDeprecations.__getattr__ can access it without jumping
    # through hoops or risking infinite recursion.
    module.__deprecated_attributes__ = {}
