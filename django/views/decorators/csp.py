from functools import wraps

from asgiref.sync import iscoroutinefunction


def csp_override(config):
    """Decorator to set enforced CSP header."""

    def _set_config(response, config):
        response._csp_config = config
        return response

    def decorator(view_func):
        @wraps(view_func)
        async def _wrapped_async_view(request, *args, **kwargs):
            response = await view_func(request, *args, **kwargs)
            response = _set_config(response, config)
            return response

        @wraps(view_func)
        def _wrapped_sync_view(request, *args, **kwargs):
            response = view_func(request, *args, **kwargs)
            response = _set_config(response, config)
            return response

        if iscoroutinefunction(view_func):
            return _wrapped_async_view
        return _wrapped_sync_view

    return decorator


def csp_override_report_only(config):
    """Decorator to set report-only CSP header."""

    def _set_config_ro(response, config):
        response._csp_config_ro = config
        return response

    def decorator(view_func):
        @wraps(view_func)
        async def _wrapped_async_view(request, *args, **kwargs):
            response = await view_func(request, *args, **kwargs)
            response = _set_config_ro(response, config)
            return response

        @wraps(view_func)
        def _wrapped_sync_view(request, *args, **kwargs):
            response = view_func(request, *args, **kwargs)
            response = _set_config_ro(response, config)
            return response

        if iscoroutinefunction(view_func):
            return _wrapped_async_view
        return _wrapped_sync_view

    return decorator


def csp_disabled(view_func):
    """Decorator to disable enforced CSP header."""

    def _set_disabled(response):
        response._csp_disabled = True
        return response

    @wraps(view_func)
    async def _wrapped_async_view(request, *args, **kwargs):
        response = await view_func(request, *args, **kwargs)
        response = _set_disabled(response)
        return response

    @wraps(view_func)
    def _wrapped_sync_view(request, *args, **kwargs):
        response = view_func(request, *args, **kwargs)
        response = _set_disabled(response)
        return response

    if iscoroutinefunction(view_func):
        return _wrapped_async_view
    return _wrapped_sync_view


def csp_disabled_report_only(view_func):
    """Decorator to disable report-only CSP header."""

    def _set_disabled_ro(response):
        response._csp_disabled_ro = True
        return response

    @wraps(view_func)
    async def _wrapped_async_view(request, *args, **kwargs):
        response = await view_func(request, *args, **kwargs)
        response = _set_disabled_ro(response)
        return response

    @wraps(view_func)
    def _wrapped_sync_view(request, *args, **kwargs):
        response = view_func(request, *args, **kwargs)
        response = _set_disabled_ro(response)
        return response

    if iscoroutinefunction(view_func):
        return _wrapped_async_view
    return _wrapped_sync_view
