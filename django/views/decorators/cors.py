from functools import wraps
from inspect import iscoroutinefunction

CROSS_ORIGIN_RESOURCE_POLICY_VALUES = {"same-origin", "same-site", "cross-origin"}


def cross_origin_resource_policy(policy):
    """
    Set the Cross-Origin-Resource-Policy header on a response.

    Use this decorator on views that serve resources intended to be loaded
    cross-origin (e.g. public API endpoints, shared static assets):

        @cross_origin_resource_policy("cross-origin")
        def my_public_api(request):
            ...

    Valid values are "same-origin", "same-site", and "cross-origin".
    """
    if policy not in CROSS_ORIGIN_RESOURCE_POLICY_VALUES:
        raise ValueError(
            f"Invalid Cross-Origin-Resource-Policy value {policy!r}. "
            f"Valid values are: {', '.join(sorted(CROSS_ORIGIN_RESOURCE_POLICY_VALUES))}."
        )

    def decorator(view_func):
        if iscoroutinefunction(view_func):

            @wraps(view_func)
            async def _wrapped_async_view(request, *args, **kwargs):
                response = await view_func(request, *args, **kwargs)
                response._cross_origin_resource_policy = policy
                return response

            return _wrapped_async_view

        @wraps(view_func)
        def _wrapped_sync_view(request, *args, **kwargs):
            response = view_func(request, *args, **kwargs)
            response._cross_origin_resource_policy = policy
            return response

        return _wrapped_sync_view

    return decorator
