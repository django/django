from django.utils.itercompat import is_iterable


def make_hashable(value):
    if isinstance(value, dict):
        return tuple([
            (key, make_hashable(nested_value))
            for key, nested_value in value.items()
        ])
    # Try hash to avoid converting a hashable iterable (e.g. string, frozenset)
    # to a tuple.
    try:
        hash(value)
    except TypeError:
        if is_iterable(value):
            return tuple(map(make_hashable, value))
        # Non-hashable, non-iterable.
        raise
    return value
