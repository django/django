from contextlib import contextmanager

from asgiref.local import Local


def FETCH_ONE(instance, field, fetch_for_instances, **kwargs):
    fetch_for_instances((instance,))


def FETCH_PEERS(instance, field, fetch_for_instances, **kwargs):
    instances = [
        peer
        for weakref_peer in instance._state.peers
        if (peer := weakref_peer()) is not None
    ]
    if not instances:
        # Peers aren’t tracked for QuerySets returning a single instance
        instances = (instance,)

    fetch_for_instances(instances)


class LazyFieldAccess(Exception):
    """Blocked lazy access of a model field."""

    pass


def RAISE(instance, field, fetch_for_instances, **kwargs):
    raise LazyFieldAccess(
        f"Lazy loading of {instance.__class__.__qualname__}.{field.name} blocked."
    )


_default = FETCH_ONE
_local = Local()


def set_default_lazy_mode(mode):
    global _default
    if not callable(mode):  # TODO: verify signature
        raise TypeError("mode must be callable.")
    _default = mode


@contextmanager
def lazy_mode(mode):
    if not callable(mode):  # TODO: verify signature
        raise TypeError("on_delete must be callable.")

    orig = getattr(_local, "mode", None)
    _local.mode = mode
    try:
        yield
    finally:
        if orig is None:
            del _local.mode
        else:
            _local.mode = orig


def get_lazy_mode():
    return getattr(_local, "mode", _default)
