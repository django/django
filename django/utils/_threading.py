import threading


def from_local(local=None):
    static = type('static', (object,), {})
    if local is None:
        return static
    for attr in dir(local):
        if not attr.startswith('__'):
            value = getattr(local, attr)
            setattr(static, attr, value)
    return static


def to_local(static=None):
    local = threading.local()
    if static is None:
        return local
    for attr in dir(static):
        if not attr.startswith('__'):
            value = getattr(static, attr)
            setattr(local, attr, value)
    return local
