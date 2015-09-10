import types


def name_that_thing(thing):
    """
    Returns either the function/class path or just the object's repr
    """
    if hasattr(thing, "__name__"):
        if hasattr(thing, "__class__") and not isinstance(thing, types.FunctionType):
            if thing.__class__ is not type:
                return name_that_thing(thing.__class__)
        if hasattr(thing, "__module__"):
            return "%s.%s" % (thing.__module__, thing.__name__)
    return repr(thing)
