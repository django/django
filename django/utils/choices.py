import collections.abc


def normalize_field_choices(value):
    if isinstance(value, collections.abc.Mapping):
        value = value.items()
    elif isinstance(value, collections.abc.Iterator):
        pass
    elif isinstance(value, collections.abc.Sequence):
        # Normalize outer sequence to list, unless value is a string which
        # should be returned as-is to ensure system checks fail correctly.
        return value if isinstance(value, (list, str)) else list(value)
    else:
        return value

    # Convert potentially nested dictionaries to a flat list of two-tuples.
    return [
        (k, list(v.items()) if isinstance(v, collections.abc.Mapping) else v)
        for k, v in value
    ]
