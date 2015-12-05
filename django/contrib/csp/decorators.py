from functools import wraps


def csp_exempt(f):
    @wraps(f)
    def _wrapped(*a, **kw):
        r = f(*a, **kw)
        r._csp_exempt = True
        return r
    return _wrapped


def csp_update(**kwargs):
    update = dict((k.lower().replace('_', '-'), v) for k, v in kwargs.items())

    def decorator(f):
        @wraps(f)
        def _wrapped(*a, **kw):
            r = f(*a, **kw)
            r._csp_update = update
            return r
        return _wrapped
    return decorator


def csp_replace(**kwargs):
    replace = dict((k.lower().replace('_', '-'), v) for k, v in kwargs.items())

    def decorator(f):
        @wraps(f)
        def _wrapped(*a, **kw):
            r = f(*a, **kw)
            r._csp_replace = replace
            return r
        return _wrapped
    return decorator


def csp(**kwargs):
    config = dict((k.lower().replace('_', '-'), v) for k, v in kwargs.items())

    def decorator(f):
        @wraps(f)
        def _wrapped(*a, **kw):
            r = f(*a, **kw)
            r._csp_config = config
            return r
        return _wrapped
    return decorator
