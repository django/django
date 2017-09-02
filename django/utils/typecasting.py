from distutils.util import strtobool

def cast_boolean(value):
    if value in (0, 1):
        return bool(value)
    try:
        return bool(strtobool(value))
    except BaseException:
        return value

def force_cast_boolean(value):
    cast_value = cast_boolean(value)
    if isinstance(cast_value, bool):
        return cast_value
    else:
        raise TypeError(
            "'%(value)s' could not be cast to a boolean value.",
            code='typeerror',
            params={'value': value},
        )
