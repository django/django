"Functions that help with dynamically creating decorators for views."

def decorator_from_middleware(middleware_class):
    """
    Given a middleware class (not an instance), returns a view decorator. This
    lets you use middleware functionality on a per-view basis.
    """
    def _decorator_from_middleware(view_func, *args, **kwargs):
        middleware = middleware_class(*args, **kwargs)
        def _wrapped_view(request, *args, **kwargs):
            if hasattr(middleware, 'process_request'):
                result = middleware.process_request(request)
                if result is not None:
                    return result
            if hasattr(middleware, 'process_view'):
                result = middleware.process_view(request, view_func, **kwargs)
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
        return _wrapped_view
    return _decorator_from_middleware
