def make_hashable(value):
    if isinstance(value, list):
        return tuple(map(make_hashable, value))
    if isinstance(value, dict):
        return tuple([
            (key, make_hashable(nested_value))
            for key, nested_value in value.items()
        ])
    return value
