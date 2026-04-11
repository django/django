# https://docs.astral.sh/ruff/rules/future-rewritable-type-annotation/
#
# 2024-05-02(bwarsaw): We must ignore I001 on this line or the ruff formatter
# and linter will be in conflict between I001 and F404 (which wants to move
# this import to below `import sys`.  Ruff's unified linter and formatter
# will hopefully resolve this: https://github.com/astral-sh/ruff/issues/8232
from __future__ import annotations  # noqa: I001

import sys

from typing import Any, TYPE_CHECKING, overload

if TYPE_CHECKING:
    from .types import ModuleAware


# fmt: off
@overload
def public(thing: ModuleAware) -> ModuleAware:
    ...


@overload
def public(**kws: Any) -> Any | tuple[Any]:
    ...


# fmt: on
def public(thing: Any | None = None, **kws: Any) -> ModuleAware | Any | tuple[Any]:
    """Add a name or names to __all__.

    There are two forms of use for this function.  Most commonly it will
    be used as a decorator on a class or function at module scope.  In
    this case, ``thing`` will be an object with both ``__module__`` and
    ``__name__`` attributes, and the name is added to the module's
    ``__all__`` list, creating that if necessary.

    When used in its function call form, ``thing`` will be None.  ``__all__``
    is looked up in the globals at the function's call site, and each key in
    the keyword arguments is added to the ``__all__``.  In addition, the key
    will be bound to the value in the globals.  This form returns the keyword
    argument values in order.  If only a single keyword argument is given, its
    value is return, otherwise a tuple of the values is returned.

    Only one or the other format may be used.

    :param thing: None, or an object with both a __module__ and a __name__
        argument.
    :param kws: Keyword arguments.
    :return: In the decorator form, the original ``thing`` object is
        returned.  In the functional form, the keyword argument value is
        returned if only a single keyword argument is given, otherwise a
        tuple of the keyword argument values is returned.
    :raises ValueError: When the inputs are invalid, or this function finds
        a non-list ``__all__`` attribute.
    """
    # 2020-07-14(warsaw): I considered using inspect.getmodule() here but
    # looking at its implementation, I feel like it does a ton of unnecessary
    # work in the oddball cases (i.e. where the object does not have an
    # __module__ attribute).  Because @public runs at module import time, and
    # because I'm not really sure we even want to support those oddball cases,
    # I'm taking the more straightforward approach of just looking the module
    # up in sys.modules.  That should be good enough for our purposes.
    mdict = (
        # The function call syntax.
        sys._getframe(1).f_globals
        if thing is None
        # The decorator syntax.
        else sys.modules[thing.__module__].__dict__
    )
    dunder_all = mdict.setdefault('__all__', [])
    if not isinstance(dunder_all, list):
        # https://docs.astral.sh/ruff/rules/f-string-in-exception/
        msg = f'__all__ must be a list not: {type(dunder_all)}'
        raise TypeError(msg)
    if thing is None:
        # The function call form.
        retval = []
        for key, value in kws.items():
            # This overwrites any previous similarly named __all__ entry.
            if key not in dunder_all:
                dunder_all.append(key)
            # We currently do not check for duplications in the globals.
            mdict[key] = value
            retval.append(value)
        if len(retval) == 1:
            return retval[0]
        return tuple(retval)
    # I think it's impossible to use the @public decorator and pass in keyword
    # arguments.  Not quite syntactically impossible, but you'll get a
    # TypeError if you try it, before you even get to this code.
    assert len(kws) == 0, 'Keyword arguments are incompatible with use as decorator'
    if thing.__name__ not in dunder_all:
        dunder_all.append(thing.__name__)
    return thing
