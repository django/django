"""
 Complex metaclass merger library for solving multiple metadatas inheritance.
 Main code and idea is from:
 http://code.activestate.com/recipes/204197-solving-the-metaclass-conflict/
"""
import inspect

from django.utils import six


memoized_metaclasses_map = {}

def _skip_redundant(iterable, skip_set=None):
    """Redundant items are repeated items or items in the original skip_set."""
    if skip_set is None:
        skip_set = set()
    for item in iterable:
        if item not in skip_set:
            skip_set.add(item)
            yield item


def _remove_redundant(metaclasses):
    skip_set = set(six.class_types)
    for meta in metaclasses:  # determines the metaclasses to be skipped
        skip_set.update(inspect.getmro(meta)[1:])
    return tuple(_skip_redundant(metaclasses, skip_set))


def _get_noconflict_metaclass(bases, left_metas, right_metas):
    """Not intended to be used outside of this module, unless you know
    what you are doing."""
    # make tuple of needed metaclasses in specified priority order
    metas = left_metas + tuple(map(type, bases)) + right_metas
    needed_metas = _remove_redundant(metas)

    # return existing confict-solving meta, if any
    if needed_metas in memoized_metaclasses_map:
        return memoized_metaclasses_map[needed_metas]
    # nope: compute, memoize and return needed conflict-solving meta
    elif not needed_metas:  # wee, a trivial case, happy us
        meta = type
    elif len(needed_metas) == 1:  # another trivial case
        meta = needed_metas[0]
    # check for recursion, can happen i.e. for Zope ExtensionClasses
    elif needed_metas == bases:
        raise TypeError("Incompatible root metatypes", needed_metas)
    else:  # gotta work ...
        metaname = '_' + ''.join([m.__name__ for m in needed_metas])
        meta = metaclassmaker()(metaname, needed_metas, {})
    memoized_metaclasses_map[needed_metas] = meta
    return meta


def metaclassmaker(left_metas=(), right_metas=()):
    """metaclass maker, has to be used as base metaclass if you inherit
    from more then one class with custom metaclass.
    It merges metaclasses from class bases and return new one.
    If there is only one custom metaclass it just returns it.
    If there is no custom metaclass then type is returned.
    """
    def make_class(name, bases, adict):
        metaclass = _get_noconflict_metaclass(bases, left_metas, right_metas)
        return metaclass(name, bases, adict)
    return make_class


def six_with_metaclassmaker(*bases):
    """Creates a base class type with a metaclassmaker.
    It's like six.with_metaclass but adjusted to work properly
    with metaclassmaker"""
    class Metaclass(type):
        def __new__(cls, name, this_bases, adict):
            return metaclassmaker()(name, bases, adict)
    return type.__new__(Metaclass, 'temporary_class', (), {})
