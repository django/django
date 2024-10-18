from functools import wraps


def csp(**kwargs):
    csp_header_value = "; ".join((f"{k} {v}" for k, v in kwargs.items()))

    def decorator(f):
        @wraps(f)
        def _wrapped(*a, **kw):
            resp = f(*a, **kw)  # response object from the view
            resp["Content-Security-Policy"] = csp_header_value
            return resp

        return _wrapped

    return decorator
