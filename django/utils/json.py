from collections.abc import Mapping, Sequence


def normalize_json(obj):
    """Recursively normalize an object into JSON-compatible types."""
    match obj:
        case Mapping():
            return {normalize_json(k): normalize_json(v) for k, v in obj.items()}
        case bytes():
            try:
                return obj.decode("utf-8")
            except UnicodeDecodeError:
                raise ValueError(f"Unsupported value: {type(obj)}")
        case str() | int() | float() | bool() | None:
            return obj
        case Sequence():  # str and bytes were already handled.
            return [normalize_json(v) for v in obj]
        case _:  # Other types can't be serialized to JSON
            raise TypeError(f"Unsupported type: {type(obj)}")
