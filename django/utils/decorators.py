"Functions that help with dynamically creating decorators for views."

import types
try:
    from functools import wraps, update_wrapper
except ImportError:
    from django.utils.functional import wraps, update_wrapper  # Python 2.3, 2.4 fallback.

class MethodDecoratorAdaptor(object):
    """
    Generic way of creating decorators that adapt to being
    used on methods
    """
    def __init__(self, decorator, func):
        update_wrapper(self, func)
        # NB: update the __dict__ first, *then* set
        # our own .func and .decorator, in case 'func' is actually
        # another MethodDecoratorAdaptor object, which has its
        # 'func' and 'decorator' attributes in its own __dict__
        self.decorator = decorator
        self.func = func
    def __call__(self, *args, **kwargs):
        return self.decorator(self.func)(*args, **kwargs)
    def __get__(self, instance, owner):
        return self.decorator(self.func.__get__(instance, owner))
    def _get_name(self):
        return self.func.__name__
    def _get_doc(self):
        return self.func.__doc__

def auto_adapt_to_methods(decorator):
    """Allows you to use the same decorator on methods and functions,
    hiding the self argument from the decorator."""
    def adapt(func):
        return MethodDecoratorAdaptor(decorator, func)
    return wraps(decorator)(adapt)

def decorator_from_middleware_with_args(middleware_class):
    """
    Like decorator_from_middleware, but returns a function
    that accepts the arguments to be passed to the middleware_class.
    Use like::

         cache_page = decorator_from_middleware(CacheMiddleware)
         # ...

         @cache_page(3600)
         def my_view(request):
             # ...
    """
    return make_middleware_decorator(middleware_class)

def decorator_from_middleware(middleware_class):
    """
    Given a middleware class (not an instance), returns a view decorator. This
    lets you use middleware functionality on a per-view basis. The middleware
    is created with no params passed.
    """
    return make_middleware_decorator(middleware_class)()

def make_middleware_decorator(middleware_class):
    def _make_decorator(*m_args, **m_kwargs):
        middleware = middleware_class(*m_args, **m_kwargs)
        def _decorator(view_func):
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
        return auto_adapt_to_methods(_decorator)
    return _make_decorator
