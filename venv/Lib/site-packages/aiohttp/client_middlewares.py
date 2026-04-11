"""Client middleware support."""

from collections.abc import Awaitable, Callable, Sequence

from .client_reqrep import ClientRequest, ClientResponse

__all__ = ("ClientMiddlewareType", "ClientHandlerType", "build_client_middlewares")

# Type alias for client request handlers - functions that process requests and return responses
ClientHandlerType = Callable[[ClientRequest], Awaitable[ClientResponse]]

# Type for client middleware - similar to server but uses ClientRequest/ClientResponse
ClientMiddlewareType = Callable[
    [ClientRequest, ClientHandlerType], Awaitable[ClientResponse]
]


def build_client_middlewares(
    handler: ClientHandlerType,
    middlewares: Sequence[ClientMiddlewareType],
) -> ClientHandlerType:
    """
    Apply middlewares to request handler.

    The middlewares are applied in reverse order, so the first middleware
    in the list wraps all subsequent middlewares and the handler.

    This implementation avoids using partial/update_wrapper to minimize overhead
    and doesn't cache to avoid holding references to stateful middleware.
    """
    # Optimize for single middleware case
    if len(middlewares) == 1:
        middleware = middlewares[0]

        async def single_middleware_handler(req: ClientRequest) -> ClientResponse:
            return await middleware(req, handler)

        return single_middleware_handler

    # Build the chain for multiple middlewares
    current_handler = handler

    for middleware in reversed(middlewares):
        # Create a new closure that captures the current state
        def make_wrapper(
            mw: ClientMiddlewareType, next_h: ClientHandlerType
        ) -> ClientHandlerType:
            async def wrapped(req: ClientRequest) -> ClientResponse:
                return await mw(req, next_h)

            return wrapped

        current_handler = make_wrapper(middleware, current_handler)

    return current_handler
