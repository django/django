import sys

from .types import ModuleAware


def private(thing: ModuleAware) -> ModuleAware:
    """Remove names from __all__.

    This decorator documents private names and ensures that the names do not
    appear in the module's __all__.

    :param thing: An object with both a __module__ and a __name__ argument.
    :return: The original `thing` object.
    :raises ValueError: When this function finds a non-list __all__ attribute.
    """
    mdict = sys.modules[thing.__module__].__dict__
    dunder_all = mdict.setdefault('__all__', [])
    if not isinstance(dunder_all, list):
        # https://docs.astral.sh/ruff/rules/f-string-in-exception/
        msg = f'__all__ must be a list not: {type(dunder_all)}'
        raise TypeError(msg)
    if thing.__name__ in dunder_all:
        dunder_all.remove(thing.__name__)
    return thing
