import os
from .exceptions import ImproperlyConfigured


class NoDefaultValue:
    pass


def from_env(name, default=NoDefaultValue, kind=str):
    """
    Get a configuration value from the environment.

    Arguments
    ---------
    name : str
        The name of the environment variable to pull from for this
        setting.
    default : any
        A default value of the return type in case the intended
        environment variable is not set. If this argument is not passed,
        the environment variable is considered to be required, and
        ``ImproperlyConfigured`` may be raised.
    kind : callable
        A callable that takes a string and returns a value of the return
        type.

    Returns
    -------
    any
        A value of the type returned by ``kind``.

    Raises
    ------
    ImproperlyConfigured
        If there is no ``default``, and the environment variable is not
        set.
    """
    try:
        val = os.environ[name]
    except KeyError:
        if default == NoDefaultValue:
            raise ImproperlyConfigured("Missing environment variable {}.".format(name))
        val = default
    val = kind(val)
    return val


def boolable(val):
    return val in ("True", "true", "T", "t", "1", 1, True)
