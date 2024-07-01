"Functions that help with dynamically creating decorators for views."

from functools import partial, update_wrapper, wraps

from asgiref.sync import iscoroutinefunction


class classonlymethod(classmethod):
    def __get__(self, instance, cls=None):
        if instance is not None:
            raise AttributeError(
                "This method is available only on the class, not on instances."
            )
        return super().__get__(instance, cls)


def _update_method_wrapper(_wrapper, decorator):
    """
    Update the wrapper method to include the attributes from the decorator.
    """

    @decorator
    def dummy(*args, **kwargs):
        pass

    update_wrapper(_wrapper, dummy)


def _multi_decorate(decorators, method):
    """
    Decorate `method` with one or more function decorators. `decorators` can be
    a single decorator or an iterable of decorators.
    """
    if hasattr(decorators, "__iter__"):
        # If 'decorators' is a list or tuple, reverse it to apply in correct order.
        decorators = decorators[::-1]
    else:
        # If it's a single decorator, make it a list.
        decorators = [decorators]

    if iscoroutinefunction(method):
        # If the method is asynchronous, define an async wrapper.
        async def _async_wrapper(self, *args, **kwargs):
            # Bind the method to the instance.
            bound_method = wraps(method)(partial(method.__get__(self, type(self))))
            # Apply each decorator in order.
            for dec in decorators:
                bound_method = dec(bound_method)
            # Await the decorated method.
            return await bound_method(*args, **kwargs)

        # Update the async wrapper with decorator attributes.
        for dec in decorators:
            _update_method_wrapper(_async_wrapper, dec)
        # Update the async wrapper with the original method's attributes.
        update_wrapper(_async_wrapper, method)
        return _async_wrapper
    else:
        # If the method is synchronous, define a sync wrapper.
        def _sync_wrapper(self, *args, **kwargs):
            # Bind the method to the instance.
            bound_method = wraps(method)(partial(method.__get__(self, type(self))))
            # Apply each decorator in order.
            for dec in decorators:
                bound_method = dec(bound_method)
            # Call the decorated method.
            return bound_method(*args, **kwargs)

        # Update the sync wrapper with decorator attributes.
        for dec in decorators:
            _update_method_wrapper(_sync_wrapper, dec)
        # Update the sync wrapper with the original method's attributes.
        update_wrapper(_sync_wrapper, method)
        return _sync_wrapper


def method_decorator(decorator, name=""):
    """
    Convert a function decorator into a method decorator.
    """

    def _dec(obj):
        if not isinstance(obj, type):
            # If 'obj' is a function, apply the decorator directly.
            return _multi_decorate(decorator, obj)
        if not (name and hasattr(obj, name)):
            raise ValueError(
                "The keyword argument `name` must be the name of a method "
                "of the decorated class: %s. Got '%s' instead." % (obj, name)
            )
        method = getattr(obj, name)
        if not callable(method):
            raise TypeError(
                "Cannot decorate '%s' as it isn't a callable attribute of "
                "%s (%s)." % (name, obj, method)
            )
        # Apply the decorator to the method.
        _wrapper = _multi_decorate(decorator, method)
        setattr(obj, name, _wrapper)
        return obj

    if not hasattr(decorator, "__iter__"):
        # Update the decorator function with attributes for debugging.
        update_wrapper(_dec, decorator)
    obj = decorator if hasattr(decorator, "__name__") else decorator.__class__
    _dec.__name__ = "method_decorator(%s)" % obj.__name__
    return _dec


def decorator_from_middleware_with_args(middleware_class):
    """
    Like decorator_from_middleware, but return a function
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
    Given a middleware class (not an instance), return a view decorator. This
    lets you use middleware functionality on a per-view basis. The middleware
    is created with no params passed.
    """
    return make_middleware_decorator(middleware_class)()


def make_middleware_decorator(middleware_class):
    def _make_decorator(*m_args, **m_kwargs):
        def _decorator(view_func):
            middleware = middleware_class(view_func, *m_args, **m_kwargs)

            def _pre_process_request(request, *args, **kwargs):
                if hasattr(middleware, "process_request"):
                    result = middleware.process_request(request)
                    if result is not None:
                        return result
                if hasattr(middleware, "process_view"):
                    result = middleware.process_view(request, view_func, args, kwargs)
                    if result is not None:
                        return result
                return None

            def _process_exception(request, exception):
                if hasattr(middleware, "process_exception"):
                    result = middleware.process_exception(request, exception)
                    if result is not None:
                        return result
                raise

            def _post_process_request(request, response):
                if hasattr(response, "render") and callable(response.render):
                    if hasattr(middleware, "process_template_response"):
                        response = middleware.process_template_response(
                            request, response
                        )
                    # Defer running of process_response until after the template
                    # has been rendered:
                    if hasattr(middleware, "process_response"):

                        def callback(response):
                            return middleware.process_response(request, response)

                        response.add_post_render_callback(callback)
                else:
                    if hasattr(middleware, "process_response"):
                        return middleware.process_response(request, response)
                return response

            if iscoroutinefunction(view_func):

                async def _view_wrapper(request, *args, **kwargs):
                    result = _pre_process_request(request, *args, **kwargs)
                    if result is not None:
                        return result

                    try:
                        response = await view_func(request, *args, **kwargs)
                    except Exception as e:
                        result = _process_exception(request, e)
                        if result is not None:
                            return result

                    return _post_process_request(request, response)

            else:

                def _view_wrapper(request, *args, **kwargs):
                    result = _pre_process_request(request, *args, **kwargs)
                    if result is not None:
                        return result

                    try:
                        response = view_func(request, *args, **kwargs)
                    except Exception as e:
                        result = _process_exception(request, e)
                        if result is not None:
                            return result

                    return _post_process_request(request, response)

            return wraps(view_func)(_view_wrapper)

        return _decorator

    return _make_decorator


def sync_and_async_middleware(func):
    """
    Mark a middleware factory as returning a hybrid middleware supporting both
    types of request.
    """
    func.sync_capable = True
    func.async_capable = True
    return func


def sync_only_middleware(func):
    """
    Mark a middleware factory as returning a sync middleware.
    This is the default.
    """
    func.sync_capable = True
    func.async_capable = False
    return func


def async_only_middleware(func):
    """Mark a middleware factory as returning an async middleware."""
    func.sync_capable = False
    func.async_capable = True
    return func
