from functools import wraps

from asgiref.sync import iscoroutinefunction


def csp_enforced(policy):
    def decorator(func):
        if iscoroutinefunction(func):

            @wraps(func)
            async def inner(request, *args, **kwargs):
                response = await func(request, *args, **kwargs)
                setattr(response, "_csp_config", policy)
                return response

        else:

            @wraps(func)
            def inner(request, *args, **kwargs):
                response = func(request, *args, **kwargs)
                setattr(response, "_csp_config", policy)
                return response

        return inner

    return decorator


def csp_report_only(policy):
    def decorator(func):
        if iscoroutinefunction(func):

            @wraps(func)
            async def inner(request, *args, **kwargs):
                response = await func(request, *args, **kwargs)
                setattr(response, "_csp_config_ro", policy)
                return response

        else:

            @wraps(func)
            def inner(request, *args, **kwargs):
                response = func(request, *args, **kwargs)
                setattr(response, "_csp_config_ro", policy)
                return response

        return inner

    return decorator


def csp_exempt(enforced=False, report_only=False):
    def _set_exempt(response, enforced=False, report_only=False):
        if report_only:
            setattr(response, "_csp_exempt_ro", True)
        if enforced:
            setattr(response, "_csp_exempt", True)
        return response

    def decorator(func):
        if iscoroutinefunction(func):

            @wraps(func)
            async def inner(request, *args, **kwargs):
                response = await func(request, *args, **kwargs)
                response = _set_exempt(
                    response, enforced=enforced, report_only=report_only
                )
                return response

        else:

            @wraps(func)
            def inner(request, *args, **kwargs):
                response = func(request, *args, **kwargs)
                response = _set_exempt(
                    response, enforced=enforced, report_only=report_only
                )
                return response

        return inner

    return decorator
