from distutils.util import strtobool

INVALID_TYPE_ERROR = "'{value}' could not be cast to a boolean value."


def _force_cast_boolean_string(value):
    if value == '':
        return None
    else:
        return bool(strtobool(value))

def _cast_boolean_string(value):
    try:
        return _force_cast_boolean_string(value)
    except BaseException:
        return bool(value)

def cast_boolean(value):
    '''
    basic casting is used for form field inputs, where invalid input
    should be passsed through, and exceptions ignored
    '''
    if value in (0, 1):
        return bool(value)
    elif isinstance(value, str):
        return _cast_boolean_string(value)
    else:
        return value

def force_cast_boolean(value):
    '''
    forced casting is used for model field inputs, where invalid input
    should raise an exception
    '''
    if isinstance(value, str):
        return _force_cast_boolean_string(value)
    elif isinstance(cast_boolean(value), bool):
        return cast_boolean(value)
    elif cast_boolean(value) == None:
        return None
    else:
        raise TypeError(INVALID_TYPE_ERROR.format(value=value))
