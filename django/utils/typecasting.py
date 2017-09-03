from distutils.util import strtobool

INVALID_TYPE_ERROR = "'{value}' could not be cast to a boolean value."


def _cast_boolean_string(value, nullable=False):
    if value == '':
        return None
    try:
        return bool(strtobool(value))
    except BaseException:
        if not nullable:
            return bool(value)
        else:
            return None


def _cast_boolean(value, nullable=False):
    # cast to true boolean types for convenience
    if value in (0, 1):
        return bool(value)
    elif isinstance(value, str):
        return _cast_boolean_string(value, nullable)
    else:
        return value


def cast_boolean_from_field(value, nullable=True):
    '''
    basic casting is used for form field inputs,
    where invalid input should be passsed through
    '''
    # obtain value
    if value == '':
        value = None
    else:
        value = _cast_boolean(value, nullable)
    # evaluate nullable
    if not nullable and value is None:
        return False
    else:
        return value


def cast_boolean_from_html(value):
    '''
    html casting is used for form widgets, and should handle
    the idiosyncrasies of HTML POST data
    '''
    # A value of '0' should be interpreted as a True value (#16820)
    if value == '0':
        return True
    if value == '':
        return None
    else:
        return _cast_boolean(value)


def force_cast_boolean(value, nullable=False):
    '''
    forced casting is used for model field inputs,
    where invalid input should raise an exception
    '''
    # obtain value
    if isinstance(value, str):
        value = bool(strtobool(value))
    elif isinstance(_cast_boolean(value, nullable), bool):
        value = _cast_boolean(value, nullable)
    elif _cast_boolean(value, nullable) is None:
        value = None
    # evaluate nullable, boolean
    if nullable and value is None:
        return None
    elif (
        not nullable and value is None
        or not isinstance(value, bool)
    ):
        raise TypeError(INVALID_TYPE_ERROR.format(value=value))
    else:
        return value
