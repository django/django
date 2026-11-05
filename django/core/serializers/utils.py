import inspect
from functools import cache


class ClassLookupDict:
    """
    Take a dictionary with classes as keys. Lookups traverse the object's
    inheritance hierarchy in method resolution order and return the first
    matching value from the dictionary, or raise KeyError if nothing matches.
    """

    def __init__(self, mapping):
        self.mapping = mapping

    @cache
    def __getitem__(self, key):
        base_class = type(key)
        for cls in inspect.getmro(base_class):
            if cls in self.mapping:
                return self.mapping[cls]
        raise KeyError(f"Class {base_class.__name__} not found in mapping.")

    def __setitem__(self, key, value):
        self.mapping[key] = value
