import inspect
import json
from traceback import format_exception

from django.utils.crypto import get_random_string


def is_module_level_function(func):
    if not inspect.isfunction(func) or inspect.isbuiltin(func):
        return False

    if "<locals>" in func.__qualname__:
        return False

    return True


def json_normalize(obj):
    """
    Round-trip encode object as JSON to normalize types.
    """
    return json.loads(json.dumps(obj))


def get_exception_traceback(exc):
    return "".join(format_exception(exc))


def get_random_id():
    """
    Return a random string for use as a Task or worker id.

    Whilst 64 characters is the max, just use 32 as a sensible middle-ground.
    """
    return get_random_string(32)
