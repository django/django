from functools import wraps

from asgiref.sync import iscoroutinefunction


def _make_csp_decorator(config_attr_name, config_attr_value):
    """General CSP override decorator factory."""

    if not isinstance(config_attr_value, dict):
        raise TypeError("CSP config should be a mapping.")

    def decorator(view_func):
        @wraps(view_func)
        async def _wrapped_async_view(request, *args, **kwargs):
            response = await view_func(request, *args, **kwargs)
            setattr(response, config_attr_name, config_attr_value)
            return response

        @wraps(view_func)
        def _wrapped_sync_view(request, *args, **kwargs):
            response = view_func(request, *args, **kwargs)
            setattr(response, config_attr_name, config_attr_value)
            return response

        if iscoroutinefunction(view_func):
            return _wrapped_async_view
        return _wrapped_sync_view

    return decorator


def csp_override(config):
    """Override the Content-Security-Policy header for a view."""
    return _make_csp_decorator("_csp_config", config)


def csp_report_only_override(config):
    """Override the Content-Security-Policy-Report-Only header for a view."""
    return _make_csp_decorator("_csp_ro_config", config)
