"Functions that help with dynamically creating decorators for views."

# For backwards compatibility in Django 2.0.
from contextlib import ContextDecorator  # noqa
from functools import WRAPPER_ASSIGNMENTS, update_wrapper, wraps


class classonlymethod(classmethod):
    def __get__(self, instance, cls=None):
        if instance is not None:
            raise AttributeError("This method is available only on the class, not on instances.")
        return super().__get__(instance, cls)


def method_decorator(decorator, name=''):
    """
    Converts a function decorator into a method decorator
    """
    # 'obj' can be a class or a function. If 'obj' is a function at the time it
    # is passed to _dec,  it will eventually be a method of the class it is
    # defined on. If 'obj' is a class, the 'name' is required to be the name
    # of the method that will be decorated.
    def _dec(obj):
        is_class = isinstance(obj, type)
        if is_class:
            if name and hasattr(obj, name):
                func = getattr(obj, name)
                if not callable(func):
                    raise TypeError(
                        "Cannot decorate '{0}' as it isn't a callable "
                        "attribute of {1} ({2})".format(name, obj, func)
                    )
            else:
                raise ValueError(
                    "The keyword argument `name` must be the name of a method "
                    "of the decorated class: {0}. Got '{1}' instead".format(
                        obj, name,
                    )
                )
        else:
            func = obj

        def decorate(function):
            """
            Apply a list/tuple of decorators if decorator is one. Decorator
            functions are applied so that the call order is the same as the
            order in which they appear in the iterable.
            """
            if hasattr(decorator, '__iter__'):
                for dec in decorator[::-1]:
                    function = dec(function)
                return function
            return decorator(function)

        def _wrapper(self, *args, **kwargs):
            @decorate
            def bound_func(*args2, **kwargs2):
                return func.__get__(self, type(self))(*args2, **kwargs2)
            # bound_func has the signature that 'decorator' expects i.e.  no
            # 'self' argument, but it is a closure over self so it can call
            # 'func' correctly.
            return bound_func(*args, **kwargs)
        # In case 'decorator' adds attributes to the function it decorates, we
        # want to copy those. We don't have access to bound_func in this scope,
        # but we can cheat by using it on a dummy function.

        @decorate
        def dummy(*args, **kwargs):
            pass
        update_wrapper(_wrapper, dummy)
        # Need to preserve any existing attributes of 'func', including the name.
        update_wrapper(_wrapper, func)

        if is_class:
            setattr(obj, name, _wrapper)
            return obj

        return _wrapper
    # Don't worry about making _dec look similar to a list/tuple as it's rather
    # meaningless.
    if not hasattr(decorator, '__iter__'):
        update_wrapper(_dec, decorator)
    # Change the name to aid debugging.
    if hasattr(decorator, '__name__'):
        _dec.__name__ = 'method_decorator(%s)' % decorator.__name__
    else:
        _dec.__name__ = 'method_decorator(%s)' % decorator.__class__.__name__
    return _dec


def decorator_from_middleware_with_args(middleware_class):
    """
    Like decorator_from_middleware, but returns a function
    that accepts the arguments to be passed to the middleware_class.
    Use like::

         cache_page = decorator_from_middleware_with_args(CacheMiddleware)
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


# Unused, for backwards compatibility in Django 2.0.
def available_attrs(fn):
    """
    Return the list of functools-wrappable attributes on a callable.
    This was required as a workaround for http://bugs.python.org/issue3445
    under Python 2.
    """
    return WRAPPER_ASSIGNMENTS


def make_middleware_decorator(middleware_class):
    def _make_decorator(*m_args, **m_kwargs):
        middleware = middleware_class(*m_args, **m_kwargs)

        def _decorator(view_func):
            @wraps(view_func)
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
                except Exception as e:
                    if hasattr(middleware, 'process_exception'):
                        result = middleware.process_exception(request, e)
                        if result is not None:
                            return result
                    raise
                if hasattr(response, 'render') and callable(response.render):
                    if hasattr(middleware, 'process_template_response'):
                        response = middleware.process_template_response(request, response)
                    # Defer running of process_response until after the template
                    # has been rendered:
                    if hasattr(middleware, 'process_response'):
                        def callback(response):
                            return middleware.process_response(request, response)
                        response.add_post_render_callback(callback)
                else:
                    if hasattr(middleware, 'process_response'):
                        return middleware.process_response(request, response)
                return response
            return _wrapped_view
        return _decorator
    return _make_decorator


class classproperty:
    def __init__(self, method=None):
        self.fget = method

    def __get__(self, instance, cls=None):
        return self.fget(cls)

    def getter(self, method):
        self.fget = method
        return self
