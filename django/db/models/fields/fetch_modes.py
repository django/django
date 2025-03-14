from contextlib import contextmanager

from asgiref.local import Local

from django.core.exceptions import FieldFetchBlocked
from django.utils.inspect import get_func_args


def FETCH_ONE(fetcher, instance):
    fetcher.fetch_one(instance)


def FETCH_PEERS(fetcher, instance):
    if instance._state.peers:
        instances = [
            peer
            for weakref_peer in instance._state.peers
            if (peer := weakref_peer()) is not None
        ]
        fetcher.fetch_many(instances)
    else:
        # Peers aren’t tracked for QuerySets returning a single instance
        fetcher.fetch_one(instance)


def RAISE(fetcher, instance):
    klass = instance.__class__.__qualname__
    field_name = fetcher.name
    raise FieldFetchBlocked(f"Fetching of {klass}.{field_name} blocked.")


_default = FETCH_ONE
_local = Local()


def validate_mode(mode):
    if get_func_args(mode) != ["fetcher", "instance"]:
        raise TypeError("mode must have signature (fetcher, instance).")


def set_default_fetch_mode(mode):
    global _default
    validate_mode(mode)
    _default = mode


@contextmanager
def fetch_mode(mode):
    validate_mode(mode)

    orig = getattr(_local, "mode", None)
    _local.mode = mode
    try:
        yield
    finally:
        if orig is None:
            del _local.mode
        else:
            _local.mode = orig


def get_fetch_mode():
    return getattr(_local, "mode", _default)
