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
import json
from pathlib import Path
from types import SimpleNamespace
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Literal,
    Optional,
    Pattern,
    Sequence,
    Set,
    Union,
    cast,
)

from playwright._impl._api_structures import (
    Cookie,
    Geolocation,
    SetCookieParam,
    StorageState,
)
from playwright._impl._artifact import Artifact
from playwright._impl._cdp_session import CDPSession
from playwright._impl._clock import Clock
from playwright._impl._connection import (
    ChannelOwner,
    from_channel,
    from_nullable_channel,
)
from playwright._impl._console_message import ConsoleMessage
from playwright._impl._dialog import Dialog
from playwright._impl._errors import Error, TargetClosedError
from playwright._impl._event_context_manager import EventContextManagerImpl
from playwright._impl._fetch import APIRequestContext
from playwright._impl._frame import Frame
from playwright._impl._har_router import HarRouter
from playwright._impl._helper import (
    HarContentPolicy,
    HarMode,
    HarRecordingMetadata,
    RouteFromHarNotFoundPolicy,
    RouteHandler,
    RouteHandlerCallback,
    TimeoutSettings,
    URLMatch,
    WebSocketRouteHandlerCallback,
    async_readfile,
    async_writefile,
    locals_to_params,
    parse_error,
    to_impl,
)
from playwright._impl._network import (
    Request,
    Response,
    Route,
    WebSocketRoute,
    WebSocketRouteHandler,
    serialize_headers,
)
from playwright._impl._page import BindingCall, Page, Worker
from playwright._impl._str_utils import escape_regex_flags
from playwright._impl._tracing import Tracing
from playwright._impl._waiter import Waiter
from playwright._impl._web_error import WebError

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl._browser import Browser


class BrowserContext(ChannelOwner):
    Events = SimpleNamespace(
        # Deprecated in v1.56, never emitted anymore.
        BackgroundPage="backgroundpage",
        Close="close",
        Console="console",
        Dialog="dialog",
        Page="page",
        WebError="weberror",
        ServiceWorker="serviceworker",
        Request="request",
        Response="response",
        RequestFailed="requestfailed",
        RequestFinished="requestfinished",
    )

    def __init__(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        # Browser is null for browser contexts created outside of normal browser, e.g. android or electron.
        # circular import workaround:
        self._browser: Optional["Browser"] = None
        if parent.__class__.__name__ == "Browser":
            self._browser = cast("Browser", parent)
        self._pages: List[Page] = []
        self._routes: List[RouteHandler] = []
        self._web_socket_routes: List[WebSocketRouteHandler] = []
        self._bindings: Dict[str, Any] = {}
        self._timeout_settings = TimeoutSettings(None)
        self._owner_page: Optional[Page] = None
        self._options: Dict[str, Any] = initializer["options"]
        self._service_workers: Set[Worker] = set()
        self._base_url: Optional[str] = self._options.get("baseURL")
        self._videos_dir: Optional[str] = self._options.get("recordVideo")
        self._tracing = cast(Tracing, from_channel(initializer["tracing"]))
        self._har_recorders: Dict[str, HarRecordingMetadata] = {}
        self._request: APIRequestContext = from_channel(initializer["requestContext"])
        self._clock = Clock(self)
        self._channel.on(
            "bindingCall",
            lambda params: self._on_binding(from_channel(params["binding"])),
        )
        self._channel.on("close", lambda _: self._on_close())
        self._channel.on(
            "page", lambda params: self._on_page(from_channel(params["page"]))
        )
        self._channel.on(
            "route",
            lambda params: self._loop.create_task(
                self._on_route(
                    from_channel(params.get("route")),
                )
            ),
        )
        self._channel.on(
            "webSocketRoute",
            lambda params: self._loop.create_task(
                self._on_web_socket_route(
                    from_channel(params["webSocketRoute"]),
                )
            ),
        )

        self._channel.on(
            "serviceWorker",
            lambda params: self._on_service_worker(from_channel(params["worker"])),
        )
        self._channel.on(
            "console",
            lambda event: self._on_console_message(event),
        )

        self._channel.on(
            "dialog", lambda params: self._on_dialog(from_channel(params["dialog"]))
        )
        self._channel.on(
            "pageError",
            lambda params: self._on_page_error(
                parse_error(params["error"]["error"]),
                from_nullable_channel(params["page"]),
            ),
        )
        self._channel.on(
            "request",
            lambda params: self._on_request(
                from_channel(params["request"]),
                from_nullable_channel(params.get("page")),
            ),
        )
        self._channel.on(
            "response",
            lambda params: self._on_response(
                from_channel(params["response"]),
                from_nullable_channel(params.get("page")),
            ),
        )
        self._channel.on(
            "requestFailed",
            lambda params: self._on_request_failed(
                from_channel(params["request"]),
                params["responseEndTiming"],
                params.get("failureText"),
                from_nullable_channel(params.get("page")),
            ),
        )
        self._channel.on(
            "requestFinished",
            lambda params: self._on_request_finished(
                from_channel(params["request"]),
                from_nullable_channel(params.get("response")),
                params["responseEndTiming"],
                from_nullable_channel(params.get("page")),
            ),
        )
        self._closed_future: asyncio.Future = asyncio.Future()
        self.once(
            self.Events.Close, lambda context: self._closed_future.set_result(True)
        )
        self._close_reason: Optional[str] = None
        self._har_routers: List[HarRouter] = []
        self._set_event_to_subscription_mapping(
            {
                BrowserContext.Events.Console: "console",
                BrowserContext.Events.Dialog: "dialog",
                BrowserContext.Events.Request: "request",
                BrowserContext.Events.Response: "response",
                BrowserContext.Events.RequestFinished: "requestFinished",
                BrowserContext.Events.RequestFailed: "requestFailed",
            }
        )
        self._closing_or_closed = False

    def __repr__(self) -> str:
        return f"<BrowserContext browser={self.browser}>"

    def _on_page(self, page: Page) -> None:
        self._pages.append(page)
        self.emit(BrowserContext.Events.Page, page)
        if page._opener and not page._opener.is_closed():
            page._opener.emit(Page.Events.Popup, page)

    async def _on_route(self, route: Route) -> None:
        route._context = self
        page = route.request._safe_page()
        route_handlers = self._routes.copy()
        for route_handler in route_handlers:
            # If the page or the context was closed we stall all requests right away.
            if (page and page._close_was_called) or self._closing_or_closed:
                return
            if not route_handler.matches(route.request.url):
                continue
            if route_handler not in self._routes:
                continue
            if route_handler.will_expire:
                self._routes.remove(route_handler)
            try:
                handled = await route_handler.handle(route)
            finally:
                if len(self._routes) == 0:
                    asyncio.create_task(
                        self._connection.wrap_api_call(
                            lambda: self._update_interception_patterns(), True
                        )
                    )
            if handled:
                return
        try:
            # If the page is closed or unrouteAll() was called without waiting and interception disabled,
            # the method will throw an error - silence it.
            await route._inner_continue(True)
        except Exception:
            pass

    async def _on_web_socket_route(self, web_socket_route: WebSocketRoute) -> None:
        route_handler = next(
            (
                route_handler
                for route_handler in self._web_socket_routes
                if route_handler.matches(web_socket_route.url)
            ),
            None,
        )
        if route_handler:
            await route_handler.handle(web_socket_route)
        else:
            web_socket_route.connect_to_server()

    def _on_binding(self, binding_call: BindingCall) -> None:
        func = self._bindings.get(binding_call._initializer["name"])
        if func is None:
            return
        asyncio.create_task(binding_call.call(func))

    def set_default_navigation_timeout(self, timeout: float) -> None:
        return self._set_default_navigation_timeout_impl(timeout)

    def _set_default_navigation_timeout_impl(self, timeout: Optional[float]) -> None:
        self._timeout_settings.set_default_navigation_timeout(timeout)

    def set_default_timeout(self, timeout: float) -> None:
        return self._set_default_timeout_impl(timeout)

    def _set_default_timeout_impl(self, timeout: Optional[float]) -> None:
        self._timeout_settings.set_default_timeout(timeout)

    @property
    def pages(self) -> List[Page]:
        return self._pages.copy()

    @property
    def browser(self) -> Optional["Browser"]:
        return self._browser

    async def _initialize_har_from_options(
        self,
        record_har_path: Optional[Union[Path, str]],
        record_har_content: Optional[HarContentPolicy],
        record_har_omit_content: Optional[bool],
        record_har_url_filter: Optional[Union[Pattern[str], str]],
        record_har_mode: Optional[HarMode],
    ) -> None:
        if not record_har_path:
            return
        record_har_path = str(record_har_path)
        default_policy: HarContentPolicy = (
            "attach" if record_har_path.endswith(".zip") else "embed"
        )
        content_policy: HarContentPolicy = record_har_content or (
            "omit" if record_har_omit_content is True else default_policy
        )
        await self._record_into_har(
            har=record_har_path,
            page=None,
            url=record_har_url_filter,
            update_content=content_policy,
            update_mode=(record_har_mode or "full"),
        )

    async def new_page(self) -> Page:
        if self._owner_page:
            raise Error("Please use browser.new_context()")
        return from_channel(await self._channel.send("newPage", None))

    async def cookies(self, urls: Union[str, Sequence[str]] = None) -> List[Cookie]:
        if urls is None:
            urls = []
        if isinstance(urls, str):
            urls = [urls]
        return await self._channel.send("cookies", None, dict(urls=urls))

    async def add_cookies(self, cookies: Sequence[SetCookieParam]) -> None:
        await self._channel.send("addCookies", None, dict(cookies=cookies))

    async def clear_cookies(
        self,
        name: Union[str, Pattern[str]] = None,
        domain: Union[str, Pattern[str]] = None,
        path: Union[str, Pattern[str]] = None,
    ) -> None:
        await self._channel.send(
            "clearCookies",
            None,
            {
                "name": name if isinstance(name, str) else None,
                "nameRegexSource": name.pattern if isinstance(name, Pattern) else None,
                "nameRegexFlags": (
                    escape_regex_flags(name) if isinstance(name, Pattern) else None
                ),
                "domain": domain if isinstance(domain, str) else None,
                "domainRegexSource": (
                    domain.pattern if isinstance(domain, Pattern) else None
                ),
                "domainRegexFlags": (
                    escape_regex_flags(domain) if isinstance(domain, Pattern) else None
                ),
                "path": path if isinstance(path, str) else None,
                "pathRegexSource": path.pattern if isinstance(path, Pattern) else None,
                "pathRegexFlags": (
                    escape_regex_flags(path) if isinstance(path, Pattern) else None
                ),
            },
        )

    async def grant_permissions(
        self, permissions: Sequence[str], origin: str = None
    ) -> None:
        await self._channel.send("grantPermissions", None, locals_to_params(locals()))

    async def clear_permissions(self) -> None:
        await self._channel.send("clearPermissions", None)

    async def set_geolocation(self, geolocation: Geolocation = None) -> None:
        await self._channel.send("setGeolocation", None, locals_to_params(locals()))

    async def set_extra_http_headers(self, headers: Dict[str, str]) -> None:
        await self._channel.send(
            "setExtraHTTPHeaders", None, dict(headers=serialize_headers(headers))
        )

    async def set_offline(self, offline: bool) -> None:
        await self._channel.send("setOffline", None, dict(offline=offline))

    async def add_init_script(
        self, script: str = None, path: Union[str, Path] = None
    ) -> None:
        if path:
            script = (await async_readfile(path)).decode()
        if not isinstance(script, str):
            raise Error("Either path or script parameter must be specified")
        await self._channel.send("addInitScript", None, dict(source=script))

    async def expose_binding(
        self, name: str, callback: Callable, handle: bool = None
    ) -> None:
        for page in self._pages:
            if name in page._bindings:
                raise Error(
                    f'Function "{name}" has been already registered in one of the pages'
                )
        if name in self._bindings:
            raise Error(f'Function "{name}" has been already registered')
        self._bindings[name] = callback
        await self._channel.send(
            "exposeBinding", None, dict(name=name, needsHandle=handle or False)
        )

    async def expose_function(self, name: str, callback: Callable) -> None:
        await self.expose_binding(name, lambda source, *args: callback(*args))

    async def route(
        self, url: URLMatch, handler: RouteHandlerCallback, times: int = None
    ) -> None:
        self._routes.insert(
            0,
            RouteHandler(
                self._base_url,
                url,
                handler,
                True if self._dispatcher_fiber else False,
                times,
            ),
        )
        await self._update_interception_patterns()

    async def unroute(
        self, url: URLMatch, handler: Optional[RouteHandlerCallback] = None
    ) -> None:
        removed = []
        remaining = []
        for route in self._routes:
            if route.url != url or (handler and route.handler != handler):
                remaining.append(route)
            else:
                removed.append(route)
        await self._unroute_internal(removed, remaining, "default")

    async def _unroute_internal(
        self,
        removed: List[RouteHandler],
        remaining: List[RouteHandler],
        behavior: Literal["default", "ignoreErrors", "wait"] = None,
    ) -> None:
        self._routes = remaining
        if behavior is not None and behavior != "default":
            await asyncio.gather(*map(lambda router: router.stop(behavior), removed))  # type: ignore
        await self._update_interception_patterns()

    async def route_web_socket(
        self, url: URLMatch, handler: WebSocketRouteHandlerCallback
    ) -> None:
        self._web_socket_routes.insert(
            0,
            WebSocketRouteHandler(self._base_url, url, handler),
        )
        await self._update_web_socket_interception_patterns()

    def _dispose_har_routers(self) -> None:
        for router in self._har_routers:
            router.dispose()
        self._har_routers = []

    async def unroute_all(
        self, behavior: Literal["default", "ignoreErrors", "wait"] = None
    ) -> None:
        await self._unroute_internal(self._routes, [], behavior)
        self._dispose_har_routers()

    async def _record_into_har(
        self,
        har: Union[Path, str],
        page: Optional[Page] = None,
        url: Union[Pattern[str], str] = None,
        update_content: HarContentPolicy = None,
        update_mode: HarMode = None,
    ) -> None:
        update_content = update_content or "attach"
        params: Dict[str, Any] = {
            "options": {
                "zip": str(har).endswith(".zip"),
                "content": update_content,
                "urlGlob": url if isinstance(url, str) else None,
                "urlRegexSource": url.pattern if isinstance(url, Pattern) else None,
                "urlRegexFlags": (
                    escape_regex_flags(url) if isinstance(url, Pattern) else None
                ),
                "mode": update_mode or "minimal",
            }
        }
        if page:
            params["page"] = page._channel
        har_id = await self._channel.send("harStart", None, params)
        self._har_recorders[har_id] = {
            "path": str(har),
            "content": update_content,
        }

    async def route_from_har(
        self,
        har: Union[Path, str],
        url: Union[Pattern[str], str] = None,
        notFound: RouteFromHarNotFoundPolicy = None,
        update: bool = None,
        updateContent: Literal["attach", "embed"] = None,
        updateMode: HarMode = None,
    ) -> None:
        if update:
            await self._record_into_har(
                har=har,
                page=None,
                url=url,
                update_content=updateContent,
                update_mode=updateMode,
            )
            return
        router = await HarRouter.create(
            local_utils=self._connection.local_utils,
            file=str(har),
            not_found_action=notFound or "abort",
            url_matcher=url,
        )
        self._har_routers.append(router)
        await router.add_context_route(self)

    async def _update_interception_patterns(self) -> None:
        patterns = RouteHandler.prepare_interception_patterns(self._routes)
        await self._channel.send(
            "setNetworkInterceptionPatterns", None, {"patterns": patterns}
        )

    async def _update_web_socket_interception_patterns(self) -> None:
        patterns = WebSocketRouteHandler.prepare_interception_patterns(
            self._web_socket_routes
        )
        await self._channel.send(
            "setWebSocketInterceptionPatterns", None, {"patterns": patterns}
        )

    def expect_event(
        self,
        event: str,
        predicate: Callable = None,
        timeout: float = None,
    ) -> EventContextManagerImpl:
        if timeout is None:
            timeout = self._timeout_settings.timeout()
        waiter = Waiter(self, f"browser_context.expect_event({event})")
        waiter.reject_on_timeout(
            timeout, f'Timeout {timeout}ms exceeded while waiting for event "{event}"'
        )
        if event != BrowserContext.Events.Close:
            waiter.reject_on_event(
                self, BrowserContext.Events.Close, lambda: TargetClosedError()
            )
        waiter.wait_for_event(self, event, predicate)
        return EventContextManagerImpl(waiter.result())

    def _on_close(self) -> None:
        self._closing_or_closed = True
        if self._browser:
            if self in self._browser._contexts:
                self._browser._contexts.remove(self)
            assert self._browser._browser_type is not None
            if (
                self
                in self._browser._browser_type._playwright.selectors._contexts_for_selectors
            ):
                self._browser._browser_type._playwright.selectors._contexts_for_selectors.remove(
                    self
                )

        self._dispose_har_routers()
        self._tracing._reset_stack_counter()
        self.emit(BrowserContext.Events.Close, self)

    async def close(self, reason: str = None) -> None:
        if self._closing_or_closed:
            return
        self._close_reason = reason
        self._closing_or_closed = True

        await self.request.dispose(reason=reason)

        async def _inner_close() -> None:
            for har_id, params in self._har_recorders.items():
                har = cast(
                    Artifact,
                    from_channel(
                        await self._channel.send("harExport", None, {"harId": har_id})
                    ),
                )
                # Server side will compress artifact if content is attach or if file is .zip.
                is_compressed = params.get("content") == "attach" or params[
                    "path"
                ].endswith(".zip")
                need_compressed = params["path"].endswith(".zip")
                if is_compressed and not need_compressed:
                    tmp_path = params["path"] + ".tmp"
                    await har.save_as(tmp_path)
                    await self._connection.local_utils.har_unzip(
                        zipFile=tmp_path, harFile=params["path"]
                    )
                else:
                    await har.save_as(params["path"])
                await har.delete()

        await self._channel._connection.wrap_api_call(_inner_close, True)
        await self._channel.send("close", None, {"reason": reason})
        await self._closed_future

    async def storage_state(
        self, path: Union[str, Path] = None, indexedDB: bool = None
    ) -> StorageState:
        result = await self._channel.send_return_as_dict(
            "storageState", None, {"indexedDB": indexedDB}
        )
        if path:
            await async_writefile(path, json.dumps(result))
        return result

    def _effective_close_reason(self) -> Optional[str]:
        if self._close_reason:
            return self._close_reason
        if self._browser:
            return self._browser._close_reason
        return None

    async def wait_for_event(
        self, event: str, predicate: Callable = None, timeout: float = None
    ) -> Any:
        async with self.expect_event(event, predicate, timeout) as event_info:
            pass
        return await event_info

    def expect_console_message(
        self,
        predicate: Callable[[ConsoleMessage], bool] = None,
        timeout: float = None,
    ) -> EventContextManagerImpl[ConsoleMessage]:
        return self.expect_event(Page.Events.Console, predicate, timeout)

    def expect_page(
        self,
        predicate: Callable[[Page], bool] = None,
        timeout: float = None,
    ) -> EventContextManagerImpl[Page]:
        return self.expect_event(BrowserContext.Events.Page, predicate, timeout)

    def _on_service_worker(self, worker: Worker) -> None:
        worker._context = self
        self._service_workers.add(worker)
        self.emit(BrowserContext.Events.ServiceWorker, worker)

    def _on_request_failed(
        self,
        request: Request,
        response_end_timing: float,
        failure_text: Optional[str],
        page: Optional[Page],
    ) -> None:
        request._failure_text = failure_text
        request._set_response_end_timing(response_end_timing)
        self.emit(BrowserContext.Events.RequestFailed, request)
        if page:
            page.emit(Page.Events.RequestFailed, request)

    def _on_request_finished(
        self,
        request: Request,
        response: Optional[Response],
        response_end_timing: float,
        page: Optional[Page],
    ) -> None:
        request._set_response_end_timing(response_end_timing)
        self.emit(BrowserContext.Events.RequestFinished, request)
        if page:
            page.emit(Page.Events.RequestFinished, request)
        if response:
            response._finished_future.set_result(True)

    def _on_console_message(self, event: Dict) -> None:
        message = ConsoleMessage(event, self._loop, self._dispatcher_fiber)
        worker = message.worker
        if worker:
            worker.emit(Worker.Events.Console, message)
        page = message.page
        if page:
            page.emit(Page.Events.Console, message)
        self.emit(BrowserContext.Events.Console, message)

    def _on_dialog(self, dialog: Dialog) -> None:
        has_listeners = self.emit(BrowserContext.Events.Dialog, dialog)
        page = dialog.page
        if page:
            has_listeners = page.emit(Page.Events.Dialog, dialog) or has_listeners
        if not has_listeners:
            # Although we do similar handling on the server side, we still need this logic
            # on the client side due to a possible race condition between two async calls:
            # a) removing "dialog" listener subscription (client->server)
            # b) actual "dialog" event (server->client)
            if dialog.type == "beforeunload":
                asyncio.create_task(dialog.accept())
            else:
                asyncio.create_task(dialog.dismiss())

    def _on_page_error(self, error: Error, page: Optional[Page]) -> None:
        self.emit(
            BrowserContext.Events.WebError,
            WebError(self._loop, self._dispatcher_fiber, page, error),
        )
        if page:
            page.emit(Page.Events.PageError, error)

    def _on_request(self, request: Request, page: Optional[Page]) -> None:
        self.emit(BrowserContext.Events.Request, request)
        if page:
            page.emit(Page.Events.Request, request)

    def _on_response(self, response: Response, page: Optional[Page]) -> None:
        self.emit(BrowserContext.Events.Response, response)
        if page:
            page.emit(Page.Events.Response, response)

    @property
    def background_pages(self) -> List[Page]:
        return []

    @property
    def service_workers(self) -> List[Worker]:
        return list(self._service_workers)

    async def new_cdp_session(self, page: Union[Page, Frame]) -> CDPSession:
        page = to_impl(page)
        params = {}
        if isinstance(page, Page):
            params["page"] = page._channel
        elif isinstance(page, Frame):
            params["frame"] = page._channel
        else:
            raise Error("page: expected Page or Frame")
        return from_channel(await self._channel.send("newCDPSession", None, params))

    @property
    def tracing(self) -> Tracing:
        return self._tracing

    @property
    def request(self) -> "APIRequestContext":
        return self._request

    @property
    def clock(self) -> Clock:
        return self._clock
