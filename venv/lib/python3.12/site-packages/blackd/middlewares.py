from collections.abc import Awaitable, Callable, Collection, Iterable

from aiohttp import web
from aiohttp.typedefs import Middleware
from aiohttp.web_middlewares import middleware
from aiohttp.web_request import Request
from aiohttp.web_response import StreamResponse

Handler = Callable[[Request], Awaitable[StreamResponse]]


def cors(
    *,
    allow_headers: Iterable[str],
    allow_origins: Collection[str],
    expose_headers: Iterable[str],
) -> Middleware:
    @middleware
    async def impl(request: Request, handler: Handler) -> StreamResponse:
        origin = request.headers.get("Origin")
        if not origin:
            return await handler(request)

        if origin not in allow_origins:
            return web.Response(status=403, text="CORS origin is not allowed")

        is_options = request.method == "OPTIONS"
        is_preflight = is_options and "Access-Control-Request-Method" in request.headers
        if is_preflight:
            resp = StreamResponse()
        else:
            resp = await handler(request)

        resp.headers["Access-Control-Allow-Origin"] = origin
        if expose_headers:
            resp.headers["Access-Control-Expose-Headers"] = ", ".join(expose_headers)
        if is_options:
            resp.headers["Access-Control-Allow-Headers"] = ", ".join(allow_headers)
            resp.headers["Access-Control-Allow-Methods"] = ", ".join(
                ("OPTIONS", "POST")
            )

        return resp

    return impl
