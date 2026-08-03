from functools import wraps
from inspect import iscoroutinefunction

CROSS_ORIGIN_EMBEDDER_POLICY_VALUES = {
    "unsafe-none",
    "require-corp",
    "credentialless",
}


def cross_origin_embedder_policy(policy):
    """
    Set the Cross-Origin-Embedder-Policy header on a response.

    Use this decorator on views that need a specific embedder policy,
    overriding the global SECURE_CROSS_ORIGIN_EMBEDDER_POLICY setting:

        @cross_origin_embedder_policy("require-corp")
        def my_isolated_view(request):
            ...

    Valid values are "unsafe-none", "require-corp", and
    "credentialless".
    """
    if policy not in CROSS_ORIGIN_EMBEDDER_POLICY_VALUES:
        raise ValueError(
            f"Invalid Cross-Origin-Embedder-Policy value {policy!r}. "
            f"Valid values are: "
            f"{', '.join(sorted(CROSS_ORIGIN_EMBEDDER_POLICY_VALUES))}."
        )

    def decorator(view_func):
        if iscoroutinefunction(view_func):

            @wraps(view_func)
            async def _wrapped_async_view(request, *args, **kwargs):
                response = await view_func(request, *args, **kwargs)
                response._cross_origin_embedder_policy = policy
                return response

            return _wrapped_async_view

        @wraps(view_func)
        def _wrapped_sync_view(request, *args, **kwargs):
            response = view_func(request, *args, **kwargs)
            response._cross_origin_embedder_policy = policy
            return response

        return _wrapped_sync_view

    return decorator
