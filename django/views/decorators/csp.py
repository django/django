from functools import wraps

from asgiref.sync import iscoroutinefunction


def csp_override(config, enforced=True, report_only=True):
    def _set_config(response, config, enforced, report_only):
        if enforced:
            response._csp_config = config
        if report_only:
            response._csp_config_ro = config
        return response

    def decorator(view_func):
        @wraps(view_func)
        async def _wrapped_async_view(request, *args, **kwargs):
            response = await view_func(request, *args, **kwargs)
            response = _set_config(response, config, enforced, report_only)
            return response

        @wraps(view_func)
        def _wrapped_sync_view(request, *args, **kwargs):
            response = view_func(request, *args, **kwargs)
            response = _set_config(response, config, enforced, report_only)
            return response

        # Determine whether to wrap as async or sync function
        if iscoroutinefunction(view_func):
            return _wrapped_async_view
        return _wrapped_sync_view

    return decorator


def csp_disabled(enforced=True, report_only=True):
    def _set_disabled(response, enforced, report_only):
        if enforced:
            response._csp_disabled = enforced
        if report_only:
            response._csp_disabled_ro = report_only
        return response

    def decorator(view_func):
        @wraps(view_func)
        async def _wrapped_async_view(request, *args, **kwargs):
            response = await view_func(request, *args, **kwargs)
            response = _set_disabled(response, enforced, report_only)
            return response

        @wraps(view_func)
        def _wrapped_sync_view(request, *args, **kwargs):
            response = view_func(request, *args, **kwargs)
            response = _set_disabled(response, enforced, report_only)
            return response

        # Determine whether to wrap as async or sync function
        if iscoroutinefunction(view_func):
            return _wrapped_async_view
        return _wrapped_sync_view

    # Check if called directly or with arguments
    if callable(enforced):
        # When no args passed, `enforced` is the view func.
        return decorator(enforced)

    # Called with arguments, return the actual decorator
    return decorator
