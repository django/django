from __future__ import unicode_literals


def outer_decorator(func):
    def inner(*args, **kwargs):
        return func(*args, **kwargs)
    inner.decorated_by = 'outer'
    return inner


def inner_decorator(func):
    def inner(*args, **kwargs):
        return func(*args, **kwargs)
    inner.decorated_by = 'inner'
    return inner
