"Functions that help with dynamically creating decorators for views."

import types
try:
    from functools import wraps
except ImportError:
    from django.utils.functional import wraps  # Python 2.3, 2.4 fallback.

def decorator_from_middleware(middleware_class):
    """
    Given a middleware class (not an instance), returns a view decorator. This
    lets you use middleware functionality on a per-view basis.
    """
    def _decorator_from_middleware(*args, **kwargs):
        # For historical reasons, these "decorators" are also called as
        # dec(func, *args) instead of dec(*args)(func). We handle both forms
        # for backwards compatibility.
        has_func = True
        try:
            view_func = kwargs.pop('view_func')
        except KeyError:
            if len(args):
                view_func, args = args[0], args[1:]
            else:
                has_func = False
        if not (has_func and isinstance(view_func, types.FunctionType)):
            # We are being called as a decorator.
            if has_func:
                args = (view_func,) + args
            middleware = middleware_class(*args, **kwargs)

            def decorator_func(fn):
                return _decorator_from_middleware(fn, *args, **kwargs)
            return decorator_func

        middleware = middleware_class(*args, **kwargs)

        def _wrapped_view(request, *args, **kwargs):
            if hasattr(middleware, 'process_request'):
                result = middleware.process_request(request)
                if result is not None:
                    return result
            if hasattr(middleware, 'process_view'):
                result = middleware.process_view(request, view_func, args, kwargs)
                if result is not None:
                    return result
            try:
                response = view_func(request, *args, **kwargs)
            except Exception, e:
                if hasattr(middleware, 'process_exception'):
                    result = middleware.process_exception(request, e)
                    if result is not None:
                        return result
                raise
            if hasattr(middleware, 'process_response'):
                result = middleware.process_response(request, response)
                if result is not None:
                    return result
            return response
        return wraps(view_func)(_wrapped_view)
    return _decorator_from_middleware
