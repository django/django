# Copyright (c) Microsoft Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import asyncio
import base64
import inspect
import json
import json as json_utils
import mimetypes
import re
from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Coroutine,
    Dict,
    List,
    Optional,
    TypedDict,
    Union,
    cast,
)
from urllib import parse

from playwright._impl._api_structures import (
    ClientCertificate,
    Headers,
    HeadersArray,
    RemoteAddr,
    RequestSizes,
    ResourceTiming,
    SecurityDetails,
)
from playwright._impl._connection import (
    ChannelOwner,
    from_channel,
    from_nullable_channel,
)
from playwright._impl._errors import Error
from playwright._impl._event_context_manager import EventContextManagerImpl
from playwright._impl._helper import (
    URLMatch,
    WebSocketRouteHandlerCallback,
    async_readfile,
    locals_to_params,
    url_matches,
)
from playwright._impl._str_utils import escape_regex_flags
from playwright._impl._waiter import Waiter

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl._browser_context import BrowserContext
    from playwright._impl._fetch import APIResponse
    from playwright._impl._frame import Frame
    from playwright._impl._page import Page, Worker


class FallbackOverrideParameters(TypedDict, total=False):
    url: Optional[str]
    method: Optional[str]
    headers: Optional[Dict[str, str]]
    postData: Optional[Union[str, bytes]]


class SerializedFallbackOverrides:
    def __init__(self) -> None:
        self.url: Optional[str] = None
        self.method: Optional[str] = None
        self.headers: Optional[Dict[str, str]] = None
        self.post_data_buffer: Optional[bytes] = None


def serialize_headers(headers: Dict[str, str]) -> HeadersArray:
    return [
        {"name": name, "value": value}
        for name, value in headers.items()
        if value is not None
    ]


async def to_client_certificates_protocol(
    clientCertificates: Optional[List[ClientCertificate]],
) -> Optional[List[Dict[str, str]]]:
    if not clientCertificates:
        return None
    out = []
    for clientCertificate in clientCertificates:
        out_record = {
            "origin": clientCertificate["origin"],
        }
        if passphrase := clientCertificate.get("passphrase"):
            out_record["passphrase"] = passphrase
        if pfx := clientCertificate.get("pfx"):
            out_record["pfx"] = base64.b64encode(pfx).decode()
        if pfx_path := clientCertificate.get("pfxPath"):
            out_record["pfx"] = base64.b64encode(
                await async_readfile(pfx_path)
            ).decode()
        if cert := clientCertificate.get("cert"):
            out_record["cert"] = base64.b64encode(cert).decode()
        if cert_path := clientCertificate.get("certPath"):
            out_record["cert"] = base64.b64encode(
                await async_readfile(cert_path)
            ).decode()
        if key := clientCertificate.get("key"):
            out_record["key"] = base64.b64encode(key).decode()
        if key_path := clientCertificate.get("keyPath"):
            out_record["key"] = base64.b64encode(
                await async_readfile(key_path)
            ).decode()
        out.append(out_record)
    return out


class Request(ChannelOwner):
    def __init__(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        self._redirected_from: Optional["Request"] = from_nullable_channel(
            initializer.get("redirectedFrom")
        )
        self._redirected_to: Optional["Request"] = None
        if self._redirected_from:
            self._redirected_from._redirected_to = self
        self._failure_text: Optional[str] = None
        self._timing: ResourceTiming = {
            "startTime": 0,
            "domainLookupStart": -1,
            "domainLookupEnd": -1,
            "connectStart": -1,
            "secureConnectionStart": -1,
            "connectEnd": -1,
            "requestStart": -1,
            "responseStart": -1,
            "responseEnd": -1,
        }
        self._provisional_headers = RawHeaders(self._initializer["headers"])
        self._all_headers_future: Optional[asyncio.Future[RawHeaders]] = None
        self._fallback_overrides: SerializedFallbackOverrides = (
            SerializedFallbackOverrides()
        )

    def __repr__(self) -> str:
        return f"<Request url={self.url!r} method={self.method!r}>"

    def _apply_fallback_overrides(self, overrides: FallbackOverrideParameters) -> None:
        self._fallback_overrides.url = overrides.get(
            "url", self._fallback_overrides.url
        )
        self._fallback_overrides.method = overrides.get(
            "method", self._fallback_overrides.method
        )
        self._fallback_overrides.headers = overrides.get(
            "headers", self._fallback_overrides.headers
        )
        post_data = overrides.get("postData")
        if isinstance(post_data, str):
            self._fallback_overrides.post_data_buffer = post_data.encode()
        elif isinstance(post_data, bytes):
            self._fallback_overrides.post_data_buffer = post_data
        elif post_data is not None:
            self._fallback_overrides.post_data_buffer = json.dumps(post_data).encode()

    @property
    def url(self) -> str:
        return cast(str, self._fallback_overrides.url or self._initializer["url"])

    @property
    def resource_type(self) -> str:
        return self._initializer["resourceType"]

    @property
    def service_worker(self) -> Optional["Worker"]:
        return cast(
            Optional["Worker"],
            from_nullable_channel(self._initializer.get("serviceWorker")),
        )

    @property
    def method(self) -> str:
        return cast(str, self._fallback_overrides.method or self._initializer["method"])

    async def sizes(self) -> RequestSizes:
        response = await self.response()
        if not response:
            raise Error("Unable to fetch sizes for failed request")
        return await response._channel.send(
            "sizes",
            None,
        )

    @property
    def post_data(self) -> Optional[str]:
        data = self._fallback_overrides.post_data_buffer
        if data:
            return data.decode()
        base64_post_data = self._initializer.get("postData")
        if base64_post_data is not None:
            return base64.b64decode(base64_post_data).decode()
        return None

    @property
    def post_data_json(self) -> Optional[Any]:
        post_data = self.post_data
        if not post_data:
            return None
        content_type = self.headers["content-type"]
        if "application/x-www-form-urlencoded" in content_type:
            return dict(parse.parse_qsl(post_data))
        try:
            return json.loads(post_data)
        except Exception:
            raise Error(f"POST data is not a valid JSON object: {post_data}")

    @property
    def post_data_buffer(self) -> Optional[bytes]:
        if self._fallback_overrides.post_data_buffer:
            return self._fallback_overrides.post_data_buffer
        if self._initializer.get("postData"):
            return base64.b64decode(self._initializer["postData"])
        return None

    async def response(self) -> Optional["Response"]:
        return from_nullable_channel(
            await self._channel.send(
                "response",
                None,
            )
        )

    @property
    def frame(self) -> "Frame":
        if not self._initializer.get("frame"):
            raise Error("Service Worker requests do not have an associated frame.")
        frame = cast("Frame", from_channel(self._initializer["frame"]))
        if not frame._page:
            raise Error(
                "\n".join(
                    [
                        "Frame for this navigation request is not available, because the request",
                        "was issued before the frame is created. You can check whether the request",
                        "is a navigation request by calling isNavigationRequest() method.",
                    ]
                )
            )
        return frame

    def is_navigation_request(self) -> bool:
        return self._initializer["isNavigationRequest"]

    @property
    def redirected_from(self) -> Optional["Request"]:
        return self._redirected_from

    @property
    def redirected_to(self) -> Optional["Request"]:
        return self._redirected_to

    @property
    def failure(self) -> Optional[str]:
        return self._failure_text

    @property
    def timing(self) -> ResourceTiming:
        return self._timing

    def _set_response_end_timing(self, response_end_timing: float) -> None:
        self._timing["responseEnd"] = response_end_timing
        if self._timing["responseStart"] == -1:
            self._timing["responseStart"] = response_end_timing

    @property
    def headers(self) -> Headers:
        override = self._fallback_overrides.headers
        if override:
            return RawHeaders._from_headers_dict_lossy(override).headers()
        return self._provisional_headers.headers()

    async def all_headers(self) -> Headers:
        return (await self._actual_headers()).headers()

    async def headers_array(self) -> HeadersArray:
        return (await self._actual_headers()).headers_array()

    async def header_value(self, name: str) -> Optional[str]:
        return (await self._actual_headers()).get(name)

    async def _actual_headers(self) -> "RawHeaders":
        override = self._fallback_overrides.headers
        if override:
            return RawHeaders(serialize_headers(override))
        if not self._all_headers_future:
            self._all_headers_future = asyncio.Future()
            headers = await self._channel.send(
                "rawRequestHeaders", None, is_internal=True
            )
            self._all_headers_future.set_result(RawHeaders(headers))
        return await self._all_headers_future

    def _target_closed_future(self) -> asyncio.Future:
        frame = cast(
            Optional["Frame"], from_nullable_channel(self._initializer.get("frame"))
        )
        if not frame:
            return asyncio.Future()
        page = frame._page
        if not page:
            return asyncio.Future()
        return page._closed_or_crashed_future

    def _safe_page(self) -> "Optional[Page]":
        frame = from_nullable_channel(self._initializer.get("frame"))
        if not frame:
            return None
        return cast("Frame", frame)._page


class Route(ChannelOwner):
    def __init__(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        self._handling_future: Optional[asyncio.Future["bool"]] = None
        self._context: "BrowserContext" = cast("BrowserContext", None)
        self._did_throw = False

    def _start_handling(self) -> "asyncio.Future[bool]":
        self._handling_future = asyncio.Future()
        return self._handling_future

    def _report_handled(self, done: bool) -> None:
        chain = self._handling_future
        assert chain
        self._handling_future = None
        chain.set_result(done)

    def _check_not_handled(self) -> None:
        if not self._handling_future:
            raise Error("Route is already handled!")

    def __repr__(self) -> str:
        return f"<Route request={self.request}>"

    @property
    def request(self) -> Request:
        return from_channel(self._initializer["request"])

    async def abort(self, errorCode: str = None) -> None:
        await self._handle_route(
            lambda: self._race_with_page_close(
                self._channel.send(
                    "abort",
                    None,
                    {
                        "errorCode": errorCode,
                    },
                )
            )
        )

    async def fulfill(
        self,
        status: int = None,
        headers: Dict[str, str] = None,
        body: Union[str, bytes] = None,
        json: Any = None,
        path: Union[str, Path] = None,
        contentType: str = None,
        response: "APIResponse" = None,
    ) -> None:
        await self._handle_route(
            lambda: self._inner_fulfill(
                status, headers, body, json, path, contentType, response
            )
        )

    async def _inner_fulfill(
        self,
        status: int = None,
        headers: Dict[str, str] = None,
        body: Union[str, bytes] = None,
        json: Any = None,
        path: Union[str, Path] = None,
        contentType: str = None,
        response: "APIResponse" = None,
    ) -> None:
        params = locals_to_params(locals())

        if json is not None:
            if body is not None:
                raise Error("Can specify either body or json parameters")
            body = json_utils.dumps(json)

        if response:
            del params["response"]
            params["status"] = (
                params["status"] if params.get("status") else response.status
            )
            params["headers"] = (
                params["headers"] if params.get("headers") else response.headers
            )
            from playwright._impl._fetch import APIResponse

            if body is None and path is None and isinstance(response, APIResponse):
                if response._request._connection is self._connection:
                    params["fetchResponseUid"] = response._fetch_uid
                else:
                    body = await response.body()

        length = 0
        if isinstance(body, str):
            params["body"] = body
            params["isBase64"] = False
            length = len(body.encode())
        elif isinstance(body, bytes):
            params["body"] = base64.b64encode(body).decode()
            params["isBase64"] = True
            length = len(body)
        elif path:
            del params["path"]
            file_content = Path(path).read_bytes()
            params["body"] = base64.b64encode(file_content).decode()
            params["isBase64"] = True
            length = len(file_content)

        headers = {k.lower(): str(v) for k, v in params.get("headers", {}).items()}
        if params.get("contentType"):
            headers["content-type"] = params["contentType"]
        elif json:
            headers["content-type"] = "application/json"
        elif path:
            headers["content-type"] = (
                mimetypes.guess_type(str(Path(path)))[0] or "application/octet-stream"
            )
        if length and "content-length" not in headers:
            headers["content-length"] = str(length)
        params["headers"] = serialize_headers(headers)

        await self._race_with_page_close(self._channel.send("fulfill", None, params))

    async def _handle_route(self, callback: Callable) -> None:
        self._check_not_handled()
        try:
            await callback()
            self._report_handled(True)
        except Exception as e:
            self._did_throw = True
            raise e

    async def fetch(
        self,
        url: str = None,
        method: str = None,
        headers: Dict[str, str] = None,
        postData: Union[Any, str, bytes] = None,
        maxRedirects: int = None,
        maxRetries: int = None,
        timeout: float = None,
    ) -> "APIResponse":
        return await self._connection.wrap_api_call(
            lambda: self._context.request._inner_fetch(
                self.request,
                url,
                method,
                headers,
                postData,
                maxRedirects=maxRedirects,
                maxRetries=maxRetries,
                timeout=timeout,
            )
        )

    async def fallback(
        self,
        url: str = None,
        method: str = None,
        headers: Dict[str, str] = None,
        postData: Union[Any, str, bytes] = None,
    ) -> None:
        overrides = cast(FallbackOverrideParameters, locals_to_params(locals()))
        self._check_not_handled()
        self.request._apply_fallback_overrides(overrides)
        self._report_handled(False)

    async def continue_(
        self,
        url: str = None,
        method: str = None,
        headers: Dict[str, str] = None,
        postData: Union[Any, str, bytes] = None,
    ) -> None:
        overrides = cast(FallbackOverrideParameters, locals_to_params(locals()))

        async def _inner() -> None:
            self.request._apply_fallback_overrides(overrides)
            await self._inner_continue(False)

        return await self._handle_route(_inner)

    async def _inner_continue(self, is_fallback: bool = False) -> None:
        options = self.request._fallback_overrides
        await self._race_with_page_close(
            self._channel.send(
                "continue",
                None,
                {
                    "url": options.url,
                    "method": options.method,
                    "headers": (
                        serialize_headers(options.headers) if options.headers else None
                    ),
                    "postData": (
                        base64.b64encode(options.post_data_buffer).decode()
                        if options.post_data_buffer is not None
                        else None
                    ),
                    "isFallback": is_fallback,
                },
            )
        )

    async def _redirected_navigation_request(self, url: str) -> None:
        await self._handle_route(
            lambda: self._race_with_page_close(
                self._channel.send("redirectNavigationRequest", None, {"url": url})
            )
        )

    async def _race_with_page_close(self, future: Coroutine) -> None:
        fut = asyncio.create_task(future)
        # Rewrite the user's stack to the new task which runs in the background.
        setattr(
            fut,
            "__pw_stack__",
            getattr(asyncio.current_task(self._loop), "__pw_stack__", inspect.stack(0)),
        )
        target_closed_future = self.request._target_closed_future()
        await asyncio.wait(
            [fut, target_closed_future],
            return_when=asyncio.FIRST_COMPLETED,
        )
        if fut.done() and fut.exception():
            raise cast(BaseException, fut.exception())
        if target_closed_future.done():
            await asyncio.gather(fut, return_exceptions=True)


def _create_task_and_ignore_exception(
    loop: asyncio.AbstractEventLoop, coro: Coroutine
) -> None:
    async def _ignore_exception() -> None:
        try:
            await coro
        except Exception:
            pass

    loop.create_task(_ignore_exception())


class ServerWebSocketRoute:
    def __init__(self, ws: "WebSocketRoute"):
        self._ws = ws

    def on_message(self, handler: Callable[[Union[str, bytes]], Any]) -> None:
        self._ws._on_server_message = handler

    def on_close(self, handler: Callable[[Optional[int], Optional[str]], Any]) -> None:
        self._ws._on_server_close = handler

    def connect_to_server(self) -> None:
        raise NotImplementedError(
            "connectToServer must be called on the page-side WebSocketRoute"
        )

    @property
    def url(self) -> str:
        return self._ws._initializer["url"]

    def close(self, code: int = None, reason: str = None) -> None:
        _create_task_and_ignore_exception(
            self._ws._loop,
            self._ws._channel.send(
                "closeServer",
                None,
                {
                    "code": code,
                    "reason": reason,
                    "wasClean": True,
                },
            ),
        )

    def send(self, message: Union[str, bytes]) -> None:
        if isinstance(message, str):
            _create_task_and_ignore_exception(
                self._ws._loop,
                self._ws._channel.send(
                    "sendToServer", None, {"message": message, "isBase64": False}
                ),
            )
        else:
            _create_task_and_ignore_exception(
                self._ws._loop,
                self._ws._channel.send(
                    "sendToServer",
                    None,
                    {"message": base64.b64encode(message).decode(), "isBase64": True},
                ),
            )


class WebSocketRoute(ChannelOwner):
    def __init__(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        self._on_page_message: Optional[Callable[[Union[str, bytes]], Any]] = None
        self._on_page_close: Optional[Callable[[Optional[int], Optional[str]], Any]] = (
            None
        )
        self._on_server_message: Optional[Callable[[Union[str, bytes]], Any]] = None
        self._on_server_close: Optional[
            Callable[[Optional[int], Optional[str]], Any]
        ] = None
        self._server = ServerWebSocketRoute(self)
        self._connected = False

        self._channel.on("messageFromPage", self._channel_message_from_page)
        self._channel.on("messageFromServer", self._channel_message_from_server)
        self._channel.on("closePage", self._channel_close_page)
        self._channel.on("closeServer", self._channel_close_server)

    def _channel_message_from_page(self, event: Dict) -> None:
        if self._on_page_message:
            self._on_page_message(
                base64.b64decode(event["message"])
                if event["isBase64"]
                else event["message"]
            )
        elif self._connected:
            _create_task_and_ignore_exception(
                self._loop, self._channel.send("sendToServer", None, event)
            )

    def _channel_message_from_server(self, event: Dict) -> None:
        if self._on_server_message:
            self._on_server_message(
                base64.b64decode(event["message"])
                if event["isBase64"]
                else event["message"]
            )
        else:
            _create_task_and_ignore_exception(
                self._loop, self._channel.send("sendToPage", None, event)
            )

    def _channel_close_page(self, event: Dict) -> None:
        if self._on_page_close:
            self._on_page_close(event["code"], event["reason"])
        else:
            _create_task_and_ignore_exception(
                self._loop, self._channel.send("closeServer", None, event)
            )

    def _channel_close_server(self, event: Dict) -> None:
        if self._on_server_close:
            self._on_server_close(event["code"], event["reason"])
        else:
            _create_task_and_ignore_exception(
                self._loop, self._channel.send("closePage", None, event)
            )

    @property
    def url(self) -> str:
        return self._initializer["url"]

    async def close(self, code: int = None, reason: str = None) -> None:
        try:
            await self._channel.send(
                "closePage", None, {"code": code, "reason": reason, "wasClean": True}
            )
        except Exception:
            pass

    def connect_to_server(self) -> "WebSocketRoute":
        if self._connected:
            raise Error("Already connected to the server")
        self._connected = True
        asyncio.create_task(
            self._channel.send(
                "connect",
                None,
            )
        )
        return cast("WebSocketRoute", self._server)

    def send(self, message: Union[str, bytes]) -> None:
        if isinstance(message, str):
            _create_task_and_ignore_exception(
                self._loop,
                self._channel.send(
                    "sendToPage", None, {"message": message, "isBase64": False}
                ),
            )
        else:
            _create_task_and_ignore_exception(
                self._loop,
                self._channel.send(
                    "sendToPage",
                    None,
                    {
                        "message": base64.b64encode(message).decode(),
                        "isBase64": True,
                    },
                ),
            )

    def on_message(self, handler: Callable[[Union[str, bytes]], Any]) -> None:
        self._on_page_message = handler

    def on_close(self, handler: Callable[[Optional[int], Optional[str]], Any]) -> None:
        self._on_page_close = handler

    async def _after_handle(self) -> None:
        if self._connected:
            return
        # Ensure that websocket is "open" and can send messages without an actual server connection.
        try:
            await self._channel.send(
                "ensureOpened",
                None,
            )
        except Exception:
            pass


class WebSocketRouteHandler:
    def __init__(
        self,
        base_url: Optional[str],
        url: URLMatch,
        handler: WebSocketRouteHandlerCallback,
    ):
        self._base_url = base_url
        self.url = url
        self.handler = handler

    @staticmethod
    def prepare_interception_patterns(
        handlers: List["WebSocketRouteHandler"],
    ) -> List[dict]:
        patterns = []
        all_urls = False
        for handler in handlers:
            if isinstance(handler.url, str):
                patterns.append({"glob": handler.url})
            elif isinstance(handler.url, re.Pattern):
                patterns.append(
                    {
                        "regexSource": handler.url.pattern,
                        "regexFlags": escape_regex_flags(handler.url),
                    }
                )
            else:
                all_urls = True

        if all_urls:
            return [{"glob": "**/*"}]
        return patterns

    def matches(self, ws_url: str) -> bool:
        return url_matches(self._base_url, ws_url, self.url, True)

    async def handle(self, websocket_route: "WebSocketRoute") -> None:
        coro_or_future = self.handler(websocket_route)
        if asyncio.iscoroutine(coro_or_future):
            await coro_or_future
        await websocket_route._after_handle()


class Response(ChannelOwner):
    def __init__(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        self._request: Request = from_channel(self._initializer["request"])
        timing = self._initializer["timing"]
        self._request._timing["startTime"] = timing["startTime"]
        self._request._timing["domainLookupStart"] = timing["domainLookupStart"]
        self._request._timing["domainLookupEnd"] = timing["domainLookupEnd"]
        self._request._timing["connectStart"] = timing["connectStart"]
        self._request._timing["secureConnectionStart"] = timing["secureConnectionStart"]
        self._request._timing["connectEnd"] = timing["connectEnd"]
        self._request._timing["requestStart"] = timing["requestStart"]
        self._request._timing["responseStart"] = timing["responseStart"]
        self._provisional_headers = RawHeaders(
            cast(HeadersArray, self._initializer["headers"])
        )
        self._raw_headers_future: Optional[asyncio.Future[RawHeaders]] = None
        self._finished_future: asyncio.Future[bool] = asyncio.Future()

    def __repr__(self) -> str:
        return f"<Response url={self.url!r} request={self.request}>"

    @property
    def url(self) -> str:
        return self._initializer["url"]

    @property
    def ok(self) -> bool:
        # Status 0 is for file:// URLs
        return self._initializer["status"] == 0 or (
            self._initializer["status"] >= 200 and self._initializer["status"] <= 299
        )

    @property
    def status(self) -> int:
        return self._initializer["status"]

    @property
    def status_text(self) -> str:
        return self._initializer["statusText"]

    @property
    def headers(self) -> Headers:
        return self._provisional_headers.headers()

    @property
    def from_service_worker(self) -> bool:
        return self._initializer["fromServiceWorker"]

    async def all_headers(self) -> Headers:
        return (await self._actual_headers()).headers()

    async def headers_array(self) -> HeadersArray:
        return (await self._actual_headers()).headers_array()

    async def header_value(self, name: str) -> Optional[str]:
        return (await self._actual_headers()).get(name)

    async def header_values(self, name: str) -> List[str]:
        return (await self._actual_headers()).get_all(name)

    async def _actual_headers(self) -> "RawHeaders":
        if not self._raw_headers_future:
            self._raw_headers_future = asyncio.Future()
            headers = cast(
                HeadersArray,
                await self._channel.send(
                    "rawResponseHeaders",
                    None,
                ),
            )
            self._raw_headers_future.set_result(RawHeaders(headers))
        return await self._raw_headers_future

    async def server_addr(self) -> Optional[RemoteAddr]:
        return await self._channel.send(
            "serverAddr",
            None,
        )

    async def security_details(self) -> Optional[SecurityDetails]:
        return await self._channel.send(
            "securityDetails",
            None,
        )

    async def finished(self) -> None:
        async def on_finished() -> None:
            await self._request._target_closed_future()
            raise Error("Target closed")

        on_finished_task = asyncio.create_task(on_finished())
        await asyncio.wait(
            cast(
                List[Union[asyncio.Task, asyncio.Future]],
                [self._finished_future, on_finished_task],
            ),
            return_when=asyncio.FIRST_COMPLETED,
        )
        if on_finished_task.done():
            await on_finished_task

    async def body(self) -> bytes:
        binary = await self._channel.send(
            "body",
            None,
        )
        return base64.b64decode(binary)

    async def text(self) -> str:
        content = await self.body()
        return content.decode()

    async def json(self) -> Any:
        return json.loads(await self.text())

    @property
    def request(self) -> Request:
        return self._request

    @property
    def frame(self) -> "Frame":
        return self._request.frame


class WebSocket(ChannelOwner):
    Events = SimpleNamespace(
        Close="close",
        FrameReceived="framereceived",
        FrameSent="framesent",
        Error="socketerror",
    )

    def __init__(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        self._is_closed = False
        self._page = cast("Page", parent)
        self._channel.on(
            "frameSent",
            lambda params: self._on_frame_sent(params["opcode"], params["data"]),
        )
        self._channel.on(
            "frameReceived",
            lambda params: self._on_frame_received(params["opcode"], params["data"]),
        )
        self._channel.on(
            "socketError",
            lambda params: self.emit(WebSocket.Events.Error, params["error"]),
        )
        self._channel.on("close", lambda params: self._on_close())

    def __repr__(self) -> str:
        return f"<WebSocket url={self.url!r}>"

    @property
    def url(self) -> str:
        return self._initializer["url"]

    def expect_event(
        self,
        event: str,
        predicate: Callable = None,
        timeout: float = None,
    ) -> EventContextManagerImpl:
        if timeout is None:
            timeout = cast(Any, self._parent)._timeout_settings.timeout()
        waiter = Waiter(self, f"web_socket.expect_event({event})")
        waiter.reject_on_timeout(
            cast(float, timeout),
            f'Timeout {timeout}ms exceeded while waiting for event "{event}"',
        )
        if event != WebSocket.Events.Close:
            waiter.reject_on_event(self, WebSocket.Events.Close, Error("Socket closed"))
        if event != WebSocket.Events.Error:
            waiter.reject_on_event(self, WebSocket.Events.Error, Error("Socket error"))
        waiter.reject_on_event(
            self._page, "close", lambda: self._page._close_error_with_reason()
        )
        waiter.wait_for_event(self, event, predicate)
        return EventContextManagerImpl(waiter.result())

    async def wait_for_event(
        self, event: str, predicate: Callable = None, timeout: float = None
    ) -> Any:
        async with self.expect_event(event, predicate, timeout) as event_info:
            pass
        return await event_info

    def _on_frame_sent(self, opcode: int, data: str) -> None:
        if opcode == 2:
            self.emit(WebSocket.Events.FrameSent, base64.b64decode(data))
        elif opcode == 1:
            self.emit(WebSocket.Events.FrameSent, data)

    def _on_frame_received(self, opcode: int, data: str) -> None:
        if opcode == 2:
            self.emit(WebSocket.Events.FrameReceived, base64.b64decode(data))
        elif opcode == 1:
            self.emit(WebSocket.Events.FrameReceived, data)

    def is_closed(self) -> bool:
        return self._is_closed

    def _on_close(self) -> None:
        self._is_closed = True
        self.emit(WebSocket.Events.Close, self)


class RawHeaders:
    def __init__(self, headers: HeadersArray) -> None:
        self._headers_array = headers
        self._headers_map: Dict[str, Dict[str, bool]] = defaultdict(dict)
        for header in headers:
            self._headers_map[header["name"].lower()][header["value"]] = True

    @staticmethod
    def _from_headers_dict_lossy(headers: Dict[str, str]) -> "RawHeaders":
        return RawHeaders(serialize_headers(headers))

    def get(self, name: str) -> Optional[str]:
        values = self.get_all(name)
        if not values:
            return None
        separator = "\n" if name.lower() == "set-cookie" else ", "
        return separator.join(values)

    def get_all(self, name: str) -> List[str]:
        return list(self._headers_map[name.lower()].keys())

    def headers(self) -> Dict[str, str]:
        result = {}
        for name in self._headers_map.keys():
            result[name] = cast(str, self.get(name))
        return result

    def headers_array(self) -> HeadersArray:
        return self._headers_array
