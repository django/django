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


import datetime
import pathlib
import typing
from typing import Literal

from playwright._impl._api_structures import (
    ClientCertificate,
    Cookie,
    FilePayload,
    FloatRect,
    Geolocation,
    HttpCredentials,
    NameValue,
    PdfMargins,
    Position,
    ProxySettings,
    RemoteAddr,
    RequestSizes,
    ResourceTiming,
    SecurityDetails,
    SetCookieParam,
    SourceLocation,
    StorageState,
    TracingGroupLocation,
    ViewportSize,
)
from playwright._impl._assertions import (
    APIResponseAssertions as APIResponseAssertionsImpl,
)
from playwright._impl._assertions import LocatorAssertions as LocatorAssertionsImpl
from playwright._impl._assertions import PageAssertions as PageAssertionsImpl
from playwright._impl._async_base import (
    AsyncBase,
    AsyncContextManager,
    AsyncEventContextManager,
    mapping,
)
from playwright._impl._browser import Browser as BrowserImpl
from playwright._impl._browser_context import BrowserContext as BrowserContextImpl
from playwright._impl._browser_type import BrowserType as BrowserTypeImpl
from playwright._impl._cdp_session import CDPSession as CDPSessionImpl
from playwright._impl._clock import Clock as ClockImpl
from playwright._impl._console_message import ConsoleMessage as ConsoleMessageImpl
from playwright._impl._dialog import Dialog as DialogImpl
from playwright._impl._download import Download as DownloadImpl
from playwright._impl._element_handle import ElementHandle as ElementHandleImpl
from playwright._impl._errors import Error
from playwright._impl._fetch import APIRequest as APIRequestImpl
from playwright._impl._fetch import APIRequestContext as APIRequestContextImpl
from playwright._impl._fetch import APIResponse as APIResponseImpl
from playwright._impl._file_chooser import FileChooser as FileChooserImpl
from playwright._impl._frame import Frame as FrameImpl
from playwright._impl._input import Keyboard as KeyboardImpl
from playwright._impl._input import Mouse as MouseImpl
from playwright._impl._input import Touchscreen as TouchscreenImpl
from playwright._impl._js_handle import JSHandle as JSHandleImpl
from playwright._impl._locator import FrameLocator as FrameLocatorImpl
from playwright._impl._locator import Locator as LocatorImpl
from playwright._impl._network import Request as RequestImpl
from playwright._impl._network import Response as ResponseImpl
from playwright._impl._network import Route as RouteImpl
from playwright._impl._network import WebSocket as WebSocketImpl
from playwright._impl._network import WebSocketRoute as WebSocketRouteImpl
from playwright._impl._page import Page as PageImpl
from playwright._impl._page import Worker as WorkerImpl
from playwright._impl._playwright import Playwright as PlaywrightImpl
from playwright._impl._selectors import Selectors as SelectorsImpl
from playwright._impl._tracing import Tracing as TracingImpl
from playwright._impl._video import Video as VideoImpl
from playwright._impl._web_error import WebError as WebErrorImpl


class Request(AsyncBase):

    @property
    def url(self) -> str:
        """Request.url

        URL of the request.

        Returns
        -------
        str
        """
        return mapping.from_maybe_impl(self._impl_obj.url)

    @property
    def resource_type(self) -> str:
        """Request.resource_type

        Contains the request's resource type as it was perceived by the rendering engine. ResourceType will be one of the
        following: `document`, `stylesheet`, `image`, `media`, `font`, `script`, `texttrack`, `xhr`, `fetch`,
        `eventsource`, `websocket`, `manifest`, `other`.

        Returns
        -------
        str
        """
        return mapping.from_maybe_impl(self._impl_obj.resource_type)

    @property
    def service_worker(self) -> typing.Optional["Worker"]:
        """Request.service_worker

        The Service `Worker` that is performing the request.

        **Details**

        This method is Chromium only. It's safe to call when using other browsers, but it will always be `null`.

        Requests originated in a Service Worker do not have a `request.frame()` available.

        Returns
        -------
        Union[Worker, None]
        """
        return mapping.from_impl_nullable(self._impl_obj.service_worker)

    @property
    def method(self) -> str:
        """Request.method

        Request's method (GET, POST, etc.)

        Returns
        -------
        str
        """
        return mapping.from_maybe_impl(self._impl_obj.method)

    @property
    def post_data(self) -> typing.Optional[str]:
        """Request.post_data

        Request's post body, if any.

        Returns
        -------
        Union[str, None]
        """
        return mapping.from_maybe_impl(self._impl_obj.post_data)

    @property
    def post_data_json(self) -> typing.Optional[typing.Any]:
        """Request.post_data_json

        Returns parsed request's body for `form-urlencoded` and JSON as a fallback if any.

        When the response is `application/x-www-form-urlencoded` then a key/value object of the values will be returned.
        Otherwise it will be parsed as JSON.

        Returns
        -------
        Union[Any, None]
        """
        return mapping.from_maybe_impl(self._impl_obj.post_data_json)

    @property
    def post_data_buffer(self) -> typing.Optional[bytes]:
        """Request.post_data_buffer

        Request's post body in a binary form, if any.

        Returns
        -------
        Union[bytes, None]
        """
        return mapping.from_maybe_impl(self._impl_obj.post_data_buffer)

    @property
    def frame(self) -> "Frame":
        """Request.frame

        Returns the `Frame` that initiated this request.

        **Usage**

        ```py
        frame_url = request.frame.url
        ```

        **Details**

        Note that in some cases the frame is not available, and this method will throw.
        - When request originates in the Service Worker. You can use `request.serviceWorker()` to check that.
        - When navigation request is issued before the corresponding frame is created. You can use
          `request.is_navigation_request()` to check that.

        Here is an example that handles all the cases:

        Returns
        -------
        Frame
        """
        return mapping.from_impl(self._impl_obj.frame)

    @property
    def redirected_from(self) -> typing.Optional["Request"]:
        """Request.redirected_from

        Request that was redirected by the server to this one, if any.

        When the server responds with a redirect, Playwright creates a new `Request` object. The two requests are connected
        by `redirectedFrom()` and `redirectedTo()` methods. When multiple server redirects has happened, it is possible to
        construct the whole redirect chain by repeatedly calling `redirectedFrom()`.

        **Usage**

        For example, if the website `http://example.com` redirects to `https://example.com`:

        ```py
        response = await page.goto(\"http://example.com\")
        print(response.request.redirected_from.url) # \"http://example.com\"
        ```

        If the website `https://google.com` has no redirects:

        ```py
        response = await page.goto(\"https://google.com\")
        print(response.request.redirected_from) # None
        ```

        Returns
        -------
        Union[Request, None]
        """
        return mapping.from_impl_nullable(self._impl_obj.redirected_from)

    @property
    def redirected_to(self) -> typing.Optional["Request"]:
        """Request.redirected_to

        New request issued by the browser if the server responded with redirect.

        **Usage**

        This method is the opposite of `request.redirected_from()`:

        ```py
        assert request.redirected_from.redirected_to == request
        ```

        Returns
        -------
        Union[Request, None]
        """
        return mapping.from_impl_nullable(self._impl_obj.redirected_to)

    @property
    def failure(self) -> typing.Optional[str]:
        """Request.failure

        The method returns `null` unless this request has failed, as reported by `requestfailed` event.

        **Usage**

        Example of logging of all the failed requests:

        ```py
        page.on(\"requestfailed\", lambda request: print(request.url + \" \" + request.failure))
        ```

        Returns
        -------
        Union[str, None]
        """
        return mapping.from_maybe_impl(self._impl_obj.failure)

    @property
    def timing(self) -> ResourceTiming:
        """Request.timing

        Returns resource timing information for given request. Most of the timing values become available upon the
        response, `responseEnd` becomes available when request finishes. Find more information at
        [Resource Timing API](https://developer.mozilla.org/en-US/docs/Web/API/PerformanceResourceTiming).

        **Usage**

        ```py
        async with page.expect_event(\"requestfinished\") as request_info:
            await page.goto(\"http://example.com\")
        request = await request_info.value
        print(request.timing)
        ```

        Returns
        -------
        {startTime: float, domainLookupStart: float, domainLookupEnd: float, connectStart: float, secureConnectionStart: float, connectEnd: float, requestStart: float, responseStart: float, responseEnd: float}
        """
        return mapping.from_impl(self._impl_obj.timing)

    @property
    def headers(self) -> typing.Dict[str, str]:
        """Request.headers

        An object with the request HTTP headers. The header names are lower-cased. Note that this method does not return
        security-related headers, including cookie-related ones. You can use `request.all_headers()` for complete
        list of headers that include `cookie` information.

        Returns
        -------
        Dict[str, str]
        """
        return mapping.from_maybe_impl(self._impl_obj.headers)

    async def sizes(self) -> RequestSizes:
        """Request.sizes

        Returns resource size information for given request.

        Returns
        -------
        {requestBodySize: int, requestHeadersSize: int, responseBodySize: int, responseHeadersSize: int}
        """

        return mapping.from_impl(await self._impl_obj.sizes())

    async def response(self) -> typing.Optional["Response"]:
        """Request.response

        Returns the matching `Response` object, or `null` if the response was not received due to error.

        Returns
        -------
        Union[Response, None]
        """

        return mapping.from_impl_nullable(await self._impl_obj.response())

    def is_navigation_request(self) -> bool:
        """Request.is_navigation_request

        Whether this request is driving frame's navigation.

        Some navigation requests are issued before the corresponding frame is created, and therefore do not have
        `request.frame()` available.

        Returns
        -------
        bool
        """

        return mapping.from_maybe_impl(self._impl_obj.is_navigation_request())

    async def all_headers(self) -> typing.Dict[str, str]:
        """Request.all_headers

        An object with all the request HTTP headers associated with this request. The header names are lower-cased.

        Returns
        -------
        Dict[str, str]
        """

        return mapping.from_maybe_impl(await self._impl_obj.all_headers())

    async def headers_array(self) -> typing.List[NameValue]:
        """Request.headers_array

        An array with all the request HTTP headers associated with this request. Unlike `request.all_headers()`,
        header names are NOT lower-cased. Headers with multiple entries, such as `Set-Cookie`, appear in the array multiple
        times.

        Returns
        -------
        List[{name: str, value: str}]
        """

        return mapping.from_impl_list(await self._impl_obj.headers_array())

    async def header_value(self, name: str) -> typing.Optional[str]:
        """Request.header_value

        Returns the value of the header matching the name. The name is case-insensitive.

        Parameters
        ----------
        name : str
            Name of the header.

        Returns
        -------
        Union[str, None]
        """

        return mapping.from_maybe_impl(await self._impl_obj.header_value(name=name))


mapping.register(RequestImpl, Request)


class Response(AsyncBase):

    @property
    def url(self) -> str:
        """Response.url

        Contains the URL of the response.

        Returns
        -------
        str
        """
        return mapping.from_maybe_impl(self._impl_obj.url)

    @property
    def ok(self) -> bool:
        """Response.ok

        Contains a boolean stating whether the response was successful (status in the range 200-299) or not.

        Returns
        -------
        bool
        """
        return mapping.from_maybe_impl(self._impl_obj.ok)

    @property
    def status(self) -> int:
        """Response.status

        Contains the status code of the response (e.g., 200 for a success).

        Returns
        -------
        int
        """
        return mapping.from_maybe_impl(self._impl_obj.status)

    @property
    def status_text(self) -> str:
        """Response.status_text

        Contains the status text of the response (e.g. usually an \"OK\" for a success).

        Returns
        -------
        str
        """
        return mapping.from_maybe_impl(self._impl_obj.status_text)

    @property
    def headers(self) -> typing.Dict[str, str]:
        """Response.headers

        An object with the response HTTP headers. The header names are lower-cased. Note that this method does not return
        security-related headers, including cookie-related ones. You can use `response.all_headers()` for complete
        list of headers that include `cookie` information.

        Returns
        -------
        Dict[str, str]
        """
        return mapping.from_maybe_impl(self._impl_obj.headers)

    @property
    def from_service_worker(self) -> bool:
        """Response.from_service_worker

        Indicates whether this Response was fulfilled by a Service Worker's Fetch Handler (i.e. via
        [FetchEvent.respondWith](https://developer.mozilla.org/en-US/docs/Web/API/FetchEvent/respondWith)).

        Returns
        -------
        bool
        """
        return mapping.from_maybe_impl(self._impl_obj.from_service_worker)

    @property
    def request(self) -> "Request":
        """Response.request

        Returns the matching `Request` object.

        Returns
        -------
        Request
        """
        return mapping.from_impl(self._impl_obj.request)

    @property
    def frame(self) -> "Frame":
        """Response.frame

        Returns the `Frame` that initiated this response.

        Returns
        -------
        Frame
        """
        return mapping.from_impl(self._impl_obj.frame)

    async def all_headers(self) -> typing.Dict[str, str]:
        """Response.all_headers

        An object with all the response HTTP headers associated with this response.

        Returns
        -------
        Dict[str, str]
        """

        return mapping.from_maybe_impl(await self._impl_obj.all_headers())

    async def headers_array(self) -> typing.List[NameValue]:
        """Response.headers_array

        An array with all the request HTTP headers associated with this response. Unlike `response.all_headers()`,
        header names are NOT lower-cased. Headers with multiple entries, such as `Set-Cookie`, appear in the array multiple
        times.

        Returns
        -------
        List[{name: str, value: str}]
        """

        return mapping.from_impl_list(await self._impl_obj.headers_array())

    async def header_value(self, name: str) -> typing.Optional[str]:
        """Response.header_value

        Returns the value of the header matching the name. The name is case-insensitive. If multiple headers have the same
        name (except `set-cookie`), they are returned as a list separated by `, `. For `set-cookie`, the `\\n` separator is
        used. If no headers are found, `null` is returned.

        Parameters
        ----------
        name : str
            Name of the header.

        Returns
        -------
        Union[str, None]
        """

        return mapping.from_maybe_impl(await self._impl_obj.header_value(name=name))

    async def header_values(self, name: str) -> typing.List[str]:
        """Response.header_values

        Returns all values of the headers matching the name, for example `set-cookie`. The name is case-insensitive.

        Parameters
        ----------
        name : str
            Name of the header.

        Returns
        -------
        List[str]
        """

        return mapping.from_maybe_impl(await self._impl_obj.header_values(name=name))

    async def server_addr(self) -> typing.Optional[RemoteAddr]:
        """Response.server_addr

        Returns the IP address and port of the server.

        Returns
        -------
        Union[{ipAddress: str, port: int}, None]
        """

        return mapping.from_impl_nullable(await self._impl_obj.server_addr())

    async def security_details(self) -> typing.Optional[SecurityDetails]:
        """Response.security_details

        Returns SSL and other security information.

        Returns
        -------
        Union[{issuer: Union[str, None], protocol: Union[str, None], subjectName: Union[str, None], validFrom: Union[float, None], validTo: Union[float, None]}, None]
        """

        return mapping.from_impl_nullable(await self._impl_obj.security_details())

    async def finished(self) -> None:
        """Response.finished

        Waits for this response to finish, returns always `null`.
        """

        return mapping.from_maybe_impl(await self._impl_obj.finished())

    async def body(self) -> bytes:
        """Response.body

        Returns the buffer with response body.

        Returns
        -------
        bytes
        """

        return mapping.from_maybe_impl(await self._impl_obj.body())

    async def text(self) -> str:
        """Response.text

        Returns the text representation of response body.

        Returns
        -------
        str
        """

        return mapping.from_maybe_impl(await self._impl_obj.text())

    async def json(self) -> typing.Any:
        """Response.json

        Returns the JSON representation of response body.

        This method will throw if the response body is not parsable via `JSON.parse`.

        Returns
        -------
        Any
        """

        return mapping.from_maybe_impl(await self._impl_obj.json())


mapping.register(ResponseImpl, Response)


class Route(AsyncBase):

    @property
    def request(self) -> "Request":
        """Route.request

        A request to be routed.

        Returns
        -------
        Request
        """
        return mapping.from_impl(self._impl_obj.request)

    async def abort(self, error_code: typing.Optional[str] = None) -> None:
        """Route.abort

        Aborts the route's request.

        Parameters
        ----------
        error_code : Union[str, None]
            Optional error code. Defaults to `failed`, could be one of the following:
            - `'aborted'` - An operation was aborted (due to user action)
            - `'accessdenied'` - Permission to access a resource, other than the network, was denied
            - `'addressunreachable'` - The IP address is unreachable. This usually means that there is no route to the
              specified host or network.
            - `'blockedbyclient'` - The client chose to block the request.
            - `'blockedbyresponse'` - The request failed because the response was delivered along with requirements which are
              not met ('X-Frame-Options' and 'Content-Security-Policy' ancestor checks, for instance).
            - `'connectionaborted'` - A connection timed out as a result of not receiving an ACK for data sent.
            - `'connectionclosed'` - A connection was closed (corresponding to a TCP FIN).
            - `'connectionfailed'` - A connection attempt failed.
            - `'connectionrefused'` - A connection attempt was refused.
            - `'connectionreset'` - A connection was reset (corresponding to a TCP RST).
            - `'internetdisconnected'` - The Internet connection has been lost.
            - `'namenotresolved'` - The host name could not be resolved.
            - `'timedout'` - An operation timed out.
            - `'failed'` - A generic failure occurred.
        """

        return mapping.from_maybe_impl(await self._impl_obj.abort(errorCode=error_code))

    async def fulfill(
        self,
        *,
        status: typing.Optional[int] = None,
        headers: typing.Optional[typing.Dict[str, str]] = None,
        body: typing.Optional[typing.Union[str, bytes]] = None,
        json: typing.Optional[typing.Any] = None,
        path: typing.Optional[typing.Union[pathlib.Path, str]] = None,
        content_type: typing.Optional[str] = None,
        response: typing.Optional["APIResponse"] = None,
    ) -> None:
        """Route.fulfill

        Fulfills route's request with given response.

        **Usage**

        An example of fulfilling all requests with 404 responses:

        ```py
        await page.route(\"**/*\", lambda route: route.fulfill(
            status=404,
            content_type=\"text/plain\",
            body=\"not found!\"))
        ```

        An example of serving static file:

        ```py
        await page.route(\"**/xhr_endpoint\", lambda route: route.fulfill(path=\"mock_data.json\"))
        ```

        Parameters
        ----------
        status : Union[int, None]
            Response status code, defaults to `200`.
        headers : Union[Dict[str, str], None]
            Response headers. Header values will be converted to a string.
        body : Union[bytes, str, None]
            Response body.
        json : Union[Any, None]
            JSON response. This method will set the content type to `application/json` if not set.
        path : Union[pathlib.Path, str, None]
            File path to respond with. The content type will be inferred from file extension. If `path` is a relative path,
            then it is resolved relative to the current working directory.
        content_type : Union[str, None]
            If set, equals to setting `Content-Type` response header.
        response : Union[APIResponse, None]
            `APIResponse` to fulfill route's request with. Individual fields of the response (such as headers) can be
            overridden using fulfill options.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.fulfill(
                status=status,
                headers=mapping.to_impl(headers),
                body=body,
                json=mapping.to_impl(json),
                path=path,
                contentType=content_type,
                response=response._impl_obj if response else None,
            )
        )

    async def fetch(
        self,
        *,
        url: typing.Optional[str] = None,
        method: typing.Optional[str] = None,
        headers: typing.Optional[typing.Dict[str, str]] = None,
        post_data: typing.Optional[typing.Union[typing.Any, str, bytes]] = None,
        max_redirects: typing.Optional[int] = None,
        max_retries: typing.Optional[int] = None,
        timeout: typing.Optional[float] = None,
    ) -> "APIResponse":
        """Route.fetch

        Performs the request and fetches result without fulfilling it, so that the response could be modified and then
        fulfilled.

        **Usage**

        ```py
        async def handle(route):
            response = await route.fetch()
            json = await response.json()
            json[\"message\"][\"big_red_dog\"] = []
            await route.fulfill(response=response, json=json)

        await page.route(\"https://dog.ceo/api/breeds/list/all\", handle)
        ```

        **Details**

        Note that `headers` option will apply to the fetched request as well as any redirects initiated by it. If you want
        to only apply `headers` to the original request, but not to redirects, look into `route.continue_()`
        instead.

        Parameters
        ----------
        url : Union[str, None]
            If set changes the request URL. New URL must have same protocol as original one.
        method : Union[str, None]
            If set changes the request method (e.g. GET or POST).
        headers : Union[Dict[str, str], None]
            If set changes the request HTTP headers. Header values will be converted to a string.
        post_data : Union[Any, bytes, str, None]
            Allows to set post data of the request. If the data parameter is an object, it will be serialized to json string
            and `content-type` header will be set to `application/json` if not explicitly set. Otherwise the `content-type`
            header will be set to `application/octet-stream` if not explicitly set.
        max_redirects : Union[int, None]
            Maximum number of request redirects that will be followed automatically. An error will be thrown if the number is
            exceeded. Defaults to `20`. Pass `0` to not follow redirects.
        max_retries : Union[int, None]
            Maximum number of times network errors should be retried. Currently only `ECONNRESET` error is retried. Does not
            retry based on HTTP response codes. An error will be thrown if the limit is exceeded. Defaults to `0` - no retries.
        timeout : Union[float, None]
            Request timeout in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout.

        Returns
        -------
        APIResponse
        """

        return mapping.from_impl(
            await self._impl_obj.fetch(
                url=url,
                method=method,
                headers=mapping.to_impl(headers),
                postData=mapping.to_impl(post_data),
                maxRedirects=max_redirects,
                maxRetries=max_retries,
                timeout=timeout,
            )
        )

    async def fallback(
        self,
        *,
        url: typing.Optional[str] = None,
        method: typing.Optional[str] = None,
        headers: typing.Optional[typing.Dict[str, str]] = None,
        post_data: typing.Optional[typing.Union[typing.Any, str, bytes]] = None,
    ) -> None:
        """Route.fallback

        Continues route's request with optional overrides. The method is similar to `route.continue_()` with the
        difference that other matching handlers will be invoked before sending the request.

        **Usage**

        When several routes match the given pattern, they run in the order opposite to their registration. That way the
        last registered route can always override all the previous ones. In the example below, request will be handled by
        the bottom-most handler first, then it'll fall back to the previous one and in the end will be aborted by the first
        registered route.

        ```py
        await page.route(\"**/*\", lambda route: route.abort())  # Runs last.
        await page.route(\"**/*\", lambda route: route.fallback())  # Runs second.
        await page.route(\"**/*\", lambda route: route.fallback())  # Runs first.
        ```

        Registering multiple routes is useful when you want separate handlers to handle different kinds of requests, for
        example API calls vs page resources or GET requests vs POST requests as in the example below.

        ```py
        # Handle GET requests.
        async def handle_get(route):
            if route.request.method != \"GET\":
                await route.fallback()
                return
          # Handling GET only.
          # ...

        # Handle POST requests.
        async def handle_post(route):
            if route.request.method != \"POST\":
                await route.fallback()
                return
          # Handling POST only.
          # ...

        await page.route(\"**/*\", handle_get)
        await page.route(\"**/*\", handle_post)
        ```

        One can also modify request while falling back to the subsequent handler, that way intermediate route handler can
        modify url, method, headers and postData of the request.

        ```py
        async def handle(route, request):
            # override headers
            headers = {
                **request.headers,
                \"foo\": \"foo-value\", # set \"foo\" header
                \"bar\": None # remove \"bar\" header
            }
            await route.fallback(headers=headers)

        await page.route(\"**/*\", handle)
        ```

        Use `route.continue_()` to immediately send the request to the network, other matching handlers won't be
        invoked in that case.

        Parameters
        ----------
        url : Union[str, None]
            If set changes the request URL. New URL must have same protocol as original one. Changing the URL won't affect the
            route matching, all the routes are matched using the original request URL.
        method : Union[str, None]
            If set changes the request method (e.g. GET or POST).
        headers : Union[Dict[str, str], None]
            If set changes the request HTTP headers. Header values will be converted to a string.
        post_data : Union[Any, bytes, str, None]
            If set changes the post data of request.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.fallback(
                url=url,
                method=method,
                headers=mapping.to_impl(headers),
                postData=mapping.to_impl(post_data),
            )
        )

    async def continue_(
        self,
        *,
        url: typing.Optional[str] = None,
        method: typing.Optional[str] = None,
        headers: typing.Optional[typing.Dict[str, str]] = None,
        post_data: typing.Optional[typing.Union[typing.Any, str, bytes]] = None,
    ) -> None:
        """Route.continue_

        Sends route's request to the network with optional overrides.

        **Usage**

        ```py
        async def handle(route, request):
            # override headers
            headers = {
                **request.headers,
                \"foo\": \"foo-value\", # set \"foo\" header
                \"bar\": None # remove \"bar\" header
            }
            await route.continue_(headers=headers)

        await page.route(\"**/*\", handle)
        ```

        **Details**

        The `headers` option applies to both the routed request and any redirects it initiates. However, `url`, `method`,
        and `postData` only apply to the original request and are not carried over to redirected requests.

        `route.continue_()` will immediately send the request to the network, other matching handlers won't be
        invoked. Use `route.fallback()` If you want next matching handler in the chain to be invoked.

        **NOTE** Some request headers are **forbidden** and cannot be overridden (for example, `Cookie`, `Host`,
        `Content-Length` and others, see
        [this MDN page](https://developer.mozilla.org/en-US/docs/Glossary/Forbidden_request_header) for full list). If an
        override is provided for a forbidden header, it will be ignored and the original request header will be used.

        To set custom cookies, use `browser_context.add_cookies()`.

        Parameters
        ----------
        url : Union[str, None]
            If set changes the request URL. New URL must have same protocol as original one.
        method : Union[str, None]
            If set changes the request method (e.g. GET or POST).
        headers : Union[Dict[str, str], None]
            If set changes the request HTTP headers. Header values will be converted to a string.
        post_data : Union[Any, bytes, str, None]
            If set changes the post data of request.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.continue_(
                url=url,
                method=method,
                headers=mapping.to_impl(headers),
                postData=mapping.to_impl(post_data),
            )
        )


mapping.register(RouteImpl, Route)


class WebSocket(AsyncBase):

    @typing.overload
    def on(
        self,
        event: Literal["close"],
        f: typing.Callable[["WebSocket"], "typing.Union[typing.Awaitable[None], None]"],
    ) -> None:
        """
        Fired when the websocket closes."""

    @typing.overload
    def on(
        self,
        event: Literal["framereceived"],
        f: typing.Callable[
            ["typing.Union[bytes, str]"], "typing.Union[typing.Awaitable[None], None]"
        ],
    ) -> None:
        """
        Fired when the websocket receives a frame."""

    @typing.overload
    def on(
        self,
        event: Literal["framesent"],
        f: typing.Callable[
            ["typing.Union[bytes, str]"], "typing.Union[typing.Awaitable[None], None]"
        ],
    ) -> None:
        """
        Fired when the websocket sends a frame."""

    @typing.overload
    def on(
        self,
        event: Literal["socketerror"],
        f: typing.Callable[["str"], "typing.Union[typing.Awaitable[None], None]"],
    ) -> None:
        """
        Fired when the websocket has an error."""

    def on(
        self,
        event: str,
        f: typing.Callable[..., typing.Union[typing.Awaitable[None], None]],
    ) -> None:
        return super().on(event=event, f=f)

    @typing.overload
    def once(
        self,
        event: Literal["close"],
        f: typing.Callable[["WebSocket"], "typing.Union[typing.Awaitable[None], None]"],
    ) -> None:
        """
        Fired when the websocket closes."""

    @typing.overload
    def once(
        self,
        event: Literal["framereceived"],
        f: typing.Callable[
            ["typing.Union[bytes, str]"], "typing.Union[typing.Awaitable[None], None]"
        ],
    ) -> None:
        """
        Fired when the websocket receives a frame."""

    @typing.overload
    def once(
        self,
        event: Literal["framesent"],
        f: typing.Callable[
            ["typing.Union[bytes, str]"], "typing.Union[typing.Awaitable[None], None]"
        ],
    ) -> None:
        """
        Fired when the websocket sends a frame."""

    @typing.overload
    def once(
        self,
        event: Literal["socketerror"],
        f: typing.Callable[["str"], "typing.Union[typing.Awaitable[None], None]"],
    ) -> None:
        """
        Fired when the websocket has an error."""

    def once(
        self,
        event: str,
        f: typing.Callable[..., typing.Union[typing.Awaitable[None], None]],
    ) -> None:
        return super().once(event=event, f=f)

    @property
    def url(self) -> str:
        """WebSocket.url

        Contains the URL of the WebSocket.

        Returns
        -------
        str
        """
        return mapping.from_maybe_impl(self._impl_obj.url)

    def expect_event(
        self,
        event: str,
        predicate: typing.Optional[typing.Callable] = None,
        *,
        timeout: typing.Optional[float] = None,
    ) -> AsyncEventContextManager:
        """WebSocket.expect_event

        Waits for event to fire and passes its value into the predicate function. Returns when the predicate returns truthy
        value. Will throw an error if the webSocket is closed before the event is fired. Returns the event data value.

        Parameters
        ----------
        event : str
            Event name, same one would pass into `webSocket.on(event)`.
        predicate : Union[Callable, None]
            Receives the event data and resolves to truthy value when the waiting should resolve.
        timeout : Union[float, None]
            Maximum time to wait for in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The
            default value can be changed by using the `browser_context.set_default_timeout()`.

        Returns
        -------
        EventContextManager
        """

        return AsyncEventContextManager(
            self._impl_obj.expect_event(
                event=event, predicate=self._wrap_handler(predicate), timeout=timeout
            ).future
        )

    async def wait_for_event(
        self,
        event: str,
        predicate: typing.Optional[typing.Callable] = None,
        *,
        timeout: typing.Optional[float] = None,
    ) -> typing.Any:
        """WebSocket.wait_for_event

        **NOTE** In most cases, you should use `web_socket.expect_event()`.

        Waits for given `event` to fire. If predicate is provided, it passes event's value into the `predicate` function
        and waits for `predicate(event)` to return a truthy value. Will throw an error if the socket is closed before the
        `event` is fired.

        Parameters
        ----------
        event : str
            Event name, same one typically passed into `*.on(event)`.
        predicate : Union[Callable, None]
            Receives the event data and resolves to truthy value when the waiting should resolve.
        timeout : Union[float, None]
            Maximum time to wait for in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The
            default value can be changed by using the `browser_context.set_default_timeout()`.

        Returns
        -------
        Any
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.wait_for_event(
                event=event, predicate=self._wrap_handler(predicate), timeout=timeout
            )
        )

    def is_closed(self) -> bool:
        """WebSocket.is_closed

        Indicates that the web socket has been closed.

        Returns
        -------
        bool
        """

        return mapping.from_maybe_impl(self._impl_obj.is_closed())


mapping.register(WebSocketImpl, WebSocket)


class WebSocketRoute(AsyncBase):

    @property
    def url(self) -> str:
        """WebSocketRoute.url

        URL of the WebSocket created in the page.

        Returns
        -------
        str
        """
        return mapping.from_maybe_impl(self._impl_obj.url)

    async def close(
        self, *, code: typing.Optional[int] = None, reason: typing.Optional[str] = None
    ) -> None:
        """WebSocketRoute.close

        Closes one side of the WebSocket connection.

        Parameters
        ----------
        code : Union[int, None]
            Optional [close code](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket/close#code).
        reason : Union[str, None]
            Optional [close reason](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket/close#reason).
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.close(code=code, reason=reason)
        )

    def connect_to_server(self) -> "WebSocketRoute":
        """WebSocketRoute.connect_to_server

        By default, routed WebSocket does not connect to the server, so you can mock entire WebSocket communication. This
        method connects to the actual WebSocket server, and returns the server-side `WebSocketRoute` instance, giving the
        ability to send and receive messages from the server.

        Once connected to the server:
        - Messages received from the server will be **automatically forwarded** to the WebSocket in the page, unless
          `web_socket_route.on_message()` is called on the server-side `WebSocketRoute`.
        - Messages sent by the [`WebSocket.send()`](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket/send) call
          in the page will be **automatically forwarded** to the server, unless `web_socket_route.on_message()` is
          called on the original `WebSocketRoute`.

        See examples at the top for more details.

        Returns
        -------
        WebSocketRoute
        """

        return mapping.from_impl(self._impl_obj.connect_to_server())

    def send(self, message: typing.Union[str, bytes]) -> None:
        """WebSocketRoute.send

        Sends a message to the WebSocket. When called on the original WebSocket, sends the message to the page. When called
        on the result of `web_socket_route.connect_to_server()`, sends the message to the server. See examples at the
        top for more details.

        Parameters
        ----------
        message : Union[bytes, str]
            Message to send.
        """

        return mapping.from_maybe_impl(self._impl_obj.send(message=message))

    def on_message(
        self, handler: typing.Callable[[typing.Union[str, bytes]], typing.Any]
    ) -> None:
        """WebSocketRoute.on_message

        This method allows to handle messages that are sent by the WebSocket, either from the page or from the server.

        When called on the original WebSocket route, this method handles messages sent from the page. You can handle this
        messages by responding to them with `web_socket_route.send()`, forwarding them to the server-side connection
        returned by `web_socket_route.connect_to_server()` or do something else.

        Once this method is called, messages are not automatically forwarded to the server or to the page - you should do
        that manually by calling `web_socket_route.send()`. See examples at the top for more details.

        Calling this method again will override the handler with a new one.

        Parameters
        ----------
        handler : Callable[[Union[bytes, str]], Any]
            Function that will handle messages.
        """

        return mapping.from_maybe_impl(
            self._impl_obj.on_message(handler=self._wrap_handler(handler))
        )

    def on_close(
        self,
        handler: typing.Callable[
            [typing.Optional[int], typing.Optional[str]], typing.Any
        ],
    ) -> None:
        """WebSocketRoute.on_close

        Allows to handle [`WebSocket.close`](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket/close).

        By default, closing one side of the connection, either in the page or on the server, will close the other side.
        However, when `web_socket_route.on_close()` handler is set up, the default forwarding of closure is disabled,
        and handler should take care of it.

        Parameters
        ----------
        handler : Callable[[Union[int, None], Union[str, None]], Any]
            Function that will handle WebSocket closure. Received an optional
            [close code](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket/close#code) and an optional
            [close reason](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket/close#reason).
        """

        return mapping.from_maybe_impl(
            self._impl_obj.on_close(handler=self._wrap_handler(handler))
        )


mapping.register(WebSocketRouteImpl, WebSocketRoute)


class Keyboard(AsyncBase):

    async def down(self, key: str) -> None:
        """Keyboard.down

        Dispatches a `keydown` event.

        `key` can specify the intended
        [keyboardEvent.key](https://developer.mozilla.org/en-US/docs/Web/API/KeyboardEvent/key) value or a single character
        to generate the text for. A superset of the `key` values can be found
        [here](https://developer.mozilla.org/en-US/docs/Web/API/KeyboardEvent/key/Key_Values). Examples of the keys are:

        `F1` - `F12`, `Digit0`- `Digit9`, `KeyA`- `KeyZ`, `Backquote`, `Minus`, `Equal`, `Backslash`, `Backspace`, `Tab`,
        `Delete`, `Escape`, `ArrowDown`, `End`, `Enter`, `Home`, `Insert`, `PageDown`, `PageUp`, `ArrowRight`, `ArrowUp`,
        etc.

        Following modification shortcuts are also supported: `Shift`, `Control`, `Alt`, `Meta`, `ShiftLeft`,
        `ControlOrMeta`. `ControlOrMeta` resolves to `Control` on Windows and Linux and to `Meta` on macOS.

        Holding down `Shift` will type the text that corresponds to the `key` in the upper case.

        If `key` is a single character, it is case-sensitive, so the values `a` and `A` will generate different respective
        texts.

        If `key` is a modifier key, `Shift`, `Meta`, `Control`, or `Alt`, subsequent key presses will be sent with that
        modifier active. To release the modifier key, use `keyboard.up()`.

        After the key is pressed once, subsequent calls to `keyboard.down()` will have
        [repeat](https://developer.mozilla.org/en-US/docs/Web/API/KeyboardEvent/repeat) set to true. To release the key,
        use `keyboard.up()`.

        **NOTE** Modifier keys DO influence `keyboard.down`. Holding down `Shift` will type the text in upper case.

        Parameters
        ----------
        key : str
            Name of the key to press or a character to generate, such as `ArrowLeft` or `a`.
        """

        return mapping.from_maybe_impl(await self._impl_obj.down(key=key))

    async def up(self, key: str) -> None:
        """Keyboard.up

        Dispatches a `keyup` event.

        Parameters
        ----------
        key : str
            Name of the key to press or a character to generate, such as `ArrowLeft` or `a`.
        """

        return mapping.from_maybe_impl(await self._impl_obj.up(key=key))

    async def insert_text(self, text: str) -> None:
        """Keyboard.insert_text

        Dispatches only `input` event, does not emit the `keydown`, `keyup` or `keypress` events.

        **Usage**

        ```py
        await page.keyboard.insert_text(\"嗨\")
        ```

        **NOTE** Modifier keys DO NOT effect `keyboard.insertText`. Holding down `Shift` will not type the text in upper
        case.

        Parameters
        ----------
        text : str
            Sets input to the specified text value.
        """

        return mapping.from_maybe_impl(await self._impl_obj.insert_text(text=text))

    async def type(self, text: str, *, delay: typing.Optional[float] = None) -> None:
        """Keyboard.type

        **NOTE** In most cases, you should use `locator.fill()` instead. You only need to press keys one by one if
        there is special keyboard handling on the page - in this case use `locator.press_sequentially()`.

        Sends a `keydown`, `keypress`/`input`, and `keyup` event for each character in the text.

        To press a special key, like `Control` or `ArrowDown`, use `keyboard.press()`.

        **Usage**

        ```py
        await page.keyboard.type(\"Hello\") # types instantly
        await page.keyboard.type(\"World\", delay=100) # types slower, like a user
        ```

        **NOTE** Modifier keys DO NOT effect `keyboard.type`. Holding down `Shift` will not type the text in upper case.

        **NOTE** For characters that are not on a US keyboard, only an `input` event will be sent.

        Parameters
        ----------
        text : str
            A text to type into a focused element.
        delay : Union[float, None]
            Time to wait between key presses in milliseconds. Defaults to 0.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.type(text=text, delay=delay)
        )

    async def press(self, key: str, *, delay: typing.Optional[float] = None) -> None:
        """Keyboard.press

        **NOTE** In most cases, you should use `locator.press()` instead.

        `key` can specify the intended
        [keyboardEvent.key](https://developer.mozilla.org/en-US/docs/Web/API/KeyboardEvent/key) value or a single character
        to generate the text for. A superset of the `key` values can be found
        [here](https://developer.mozilla.org/en-US/docs/Web/API/KeyboardEvent/key/Key_Values). Examples of the keys are:

        `F1` - `F12`, `Digit0`- `Digit9`, `KeyA`- `KeyZ`, `Backquote`, `Minus`, `Equal`, `Backslash`, `Backspace`, `Tab`,
        `Delete`, `Escape`, `ArrowDown`, `End`, `Enter`, `Home`, `Insert`, `PageDown`, `PageUp`, `ArrowRight`, `ArrowUp`,
        etc.

        Following modification shortcuts are also supported: `Shift`, `Control`, `Alt`, `Meta`, `ShiftLeft`,
        `ControlOrMeta`. `ControlOrMeta` resolves to `Control` on Windows and Linux and to `Meta` on macOS.

        Holding down `Shift` will type the text that corresponds to the `key` in the upper case.

        If `key` is a single character, it is case-sensitive, so the values `a` and `A` will generate different respective
        texts.

        Shortcuts such as `key: \"Control+o\"`, `key: \"Control++` or `key: \"Control+Shift+T\"` are supported as well. When
        specified with the modifier, modifier is pressed and being held while the subsequent key is being pressed.

        **Usage**

        ```py
        page = await browser.new_page()
        await page.goto(\"https://keycode.info\")
        await page.keyboard.press(\"a\")
        await page.screenshot(path=\"a.png\")
        await page.keyboard.press(\"ArrowLeft\")
        await page.screenshot(path=\"arrow_left.png\")
        await page.keyboard.press(\"Shift+O\")
        await page.screenshot(path=\"o.png\")
        await browser.close()
        ```

        Shortcut for `keyboard.down()` and `keyboard.up()`.

        Parameters
        ----------
        key : str
            Name of the key to press or a character to generate, such as `ArrowLeft` or `a`.
        delay : Union[float, None]
            Time to wait between `keydown` and `keyup` in milliseconds. Defaults to 0.
        """

        return mapping.from_maybe_impl(await self._impl_obj.press(key=key, delay=delay))


mapping.register(KeyboardImpl, Keyboard)


class Mouse(AsyncBase):

    async def move(
        self, x: float, y: float, *, steps: typing.Optional[int] = None
    ) -> None:
        """Mouse.move

        Dispatches a `mousemove` event.

        Parameters
        ----------
        x : float
            X coordinate relative to the main frame's viewport in CSS pixels.
        y : float
            Y coordinate relative to the main frame's viewport in CSS pixels.
        steps : Union[int, None]
            Defaults to 1. Sends `n` interpolated `mousemove` events to represent travel between Playwright's current cursor
            position and the provided destination. When set to 1, emits a single `mousemove` event at the destination location.
        """

        return mapping.from_maybe_impl(await self._impl_obj.move(x=x, y=y, steps=steps))

    async def down(
        self,
        *,
        button: typing.Optional[Literal["left", "middle", "right"]] = None,
        click_count: typing.Optional[int] = None,
    ) -> None:
        """Mouse.down

        Dispatches a `mousedown` event.

        Parameters
        ----------
        button : Union["left", "middle", "right", None]
            Defaults to `left`.
        click_count : Union[int, None]
            defaults to 1. See [UIEvent.detail].
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.down(button=button, clickCount=click_count)
        )

    async def up(
        self,
        *,
        button: typing.Optional[Literal["left", "middle", "right"]] = None,
        click_count: typing.Optional[int] = None,
    ) -> None:
        """Mouse.up

        Dispatches a `mouseup` event.

        Parameters
        ----------
        button : Union["left", "middle", "right", None]
            Defaults to `left`.
        click_count : Union[int, None]
            defaults to 1. See [UIEvent.detail].
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.up(button=button, clickCount=click_count)
        )

    async def click(
        self,
        x: float,
        y: float,
        *,
        delay: typing.Optional[float] = None,
        button: typing.Optional[Literal["left", "middle", "right"]] = None,
        click_count: typing.Optional[int] = None,
    ) -> None:
        """Mouse.click

        Shortcut for `mouse.move()`, `mouse.down()`, `mouse.up()`.

        Parameters
        ----------
        x : float
            X coordinate relative to the main frame's viewport in CSS pixels.
        y : float
            Y coordinate relative to the main frame's viewport in CSS pixels.
        delay : Union[float, None]
            Time to wait between `mousedown` and `mouseup` in milliseconds. Defaults to 0.
        button : Union["left", "middle", "right", None]
            Defaults to `left`.
        click_count : Union[int, None]
            defaults to 1. See [UIEvent.detail].
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.click(
                x=x, y=y, delay=delay, button=button, clickCount=click_count
            )
        )

    async def dblclick(
        self,
        x: float,
        y: float,
        *,
        delay: typing.Optional[float] = None,
        button: typing.Optional[Literal["left", "middle", "right"]] = None,
    ) -> None:
        """Mouse.dblclick

        Shortcut for `mouse.move()`, `mouse.down()`, `mouse.up()`, `mouse.down()` and
        `mouse.up()`.

        Parameters
        ----------
        x : float
            X coordinate relative to the main frame's viewport in CSS pixels.
        y : float
            Y coordinate relative to the main frame's viewport in CSS pixels.
        delay : Union[float, None]
            Time to wait between `mousedown` and `mouseup` in milliseconds. Defaults to 0.
        button : Union["left", "middle", "right", None]
            Defaults to `left`.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.dblclick(x=x, y=y, delay=delay, button=button)
        )

    async def wheel(self, delta_x: float, delta_y: float) -> None:
        """Mouse.wheel

        Dispatches a `wheel` event. This method is usually used to manually scroll the page. See
        [scrolling](https://playwright.dev/python/docs/input#scrolling) for alternative ways to scroll.

        **NOTE** Wheel events may cause scrolling if they are not handled, and this method does not wait for the scrolling
        to finish before returning.

        Parameters
        ----------
        delta_x : float
            Pixels to scroll horizontally.
        delta_y : float
            Pixels to scroll vertically.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.wheel(deltaX=delta_x, deltaY=delta_y)
        )


mapping.register(MouseImpl, Mouse)


class Touchscreen(AsyncBase):

    async def tap(self, x: float, y: float) -> None:
        """Touchscreen.tap

        Dispatches a `touchstart` and `touchend` event with a single touch at the position (`x`,`y`).

        **NOTE** `page.tap()` the method will throw if `hasTouch` option of the browser context is false.

        Parameters
        ----------
        x : float
            X coordinate relative to the main frame's viewport in CSS pixels.
        y : float
            Y coordinate relative to the main frame's viewport in CSS pixels.
        """

        return mapping.from_maybe_impl(await self._impl_obj.tap(x=x, y=y))


mapping.register(TouchscreenImpl, Touchscreen)


class JSHandle(AsyncBase):

    async def evaluate(
        self, expression: str, arg: typing.Optional[typing.Any] = None
    ) -> typing.Any:
        """JSHandle.evaluate

        Returns the return value of `expression`.

        This method passes this handle as the first argument to `expression`.

        If `expression` returns a [Promise], then `handle.evaluate` would wait for the promise to resolve and return its
        value.

        **Usage**

        ```py
        tweet_handle = await page.query_selector(\".tweet .retweets\")
        assert await tweet_handle.evaluate(\"node => node.innerText\") == \"10 retweets\"
        ```

        Parameters
        ----------
        expression : str
            JavaScript expression to be evaluated in the browser context. If the expression evaluates to a function, the
            function is automatically invoked.
        arg : Union[Any, None]
            Optional argument to pass to `expression`.

        Returns
        -------
        Any
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.evaluate(
                expression=expression, arg=mapping.to_impl(arg)
            )
        )

    async def evaluate_handle(
        self, expression: str, arg: typing.Optional[typing.Any] = None
    ) -> "JSHandle":
        """JSHandle.evaluate_handle

        Returns the return value of `expression` as a `JSHandle`.

        This method passes this handle as the first argument to `expression`.

        The only difference between `jsHandle.evaluate` and `jsHandle.evaluateHandle` is that `jsHandle.evaluateHandle`
        returns `JSHandle`.

        If the function passed to the `jsHandle.evaluateHandle` returns a [Promise], then `jsHandle.evaluateHandle` would
        wait for the promise to resolve and return its value.

        See `page.evaluate_handle()` for more details.

        Parameters
        ----------
        expression : str
            JavaScript expression to be evaluated in the browser context. If the expression evaluates to a function, the
            function is automatically invoked.
        arg : Union[Any, None]
            Optional argument to pass to `expression`.

        Returns
        -------
        JSHandle
        """

        return mapping.from_impl(
            await self._impl_obj.evaluate_handle(
                expression=expression, arg=mapping.to_impl(arg)
            )
        )

    async def get_property(self, property_name: str) -> "JSHandle":
        """JSHandle.get_property

        Fetches a single property from the referenced object.

        Parameters
        ----------
        property_name : str
            property to get

        Returns
        -------
        JSHandle
        """

        return mapping.from_impl(
            await self._impl_obj.get_property(propertyName=property_name)
        )

    async def get_properties(self) -> typing.Dict[str, "JSHandle"]:
        """JSHandle.get_properties

        The method returns a map with **own property names** as keys and JSHandle instances for the property values.

        **Usage**

        ```py
        handle = await page.evaluate_handle(\"({ window, document })\")
        properties = await handle.get_properties()
        window_handle = properties.get(\"window\")
        document_handle = properties.get(\"document\")
        await handle.dispose()
        ```

        Returns
        -------
        Dict[str, JSHandle]
        """

        return mapping.from_impl_dict(await self._impl_obj.get_properties())

    def as_element(self) -> typing.Optional["ElementHandle"]:
        """JSHandle.as_element

        Returns either `null` or the object handle itself, if the object handle is an instance of `ElementHandle`.

        Returns
        -------
        Union[ElementHandle, None]
        """

        return mapping.from_impl_nullable(self._impl_obj.as_element())

    async def dispose(self) -> None:
        """JSHandle.dispose

        The `jsHandle.dispose` method stops referencing the element handle.
        """

        return mapping.from_maybe_impl(await self._impl_obj.dispose())

    async def json_value(self) -> typing.Any:
        """JSHandle.json_value

        Returns a JSON representation of the object. If the object has a `toJSON` function, it **will not be called**.

        **NOTE** The method will return an empty JSON object if the referenced object is not stringifiable. It will throw
        an error if the object has circular references.

        Returns
        -------
        Any
        """

        return mapping.from_maybe_impl(await self._impl_obj.json_value())


mapping.register(JSHandleImpl, JSHandle)


class ElementHandle(JSHandle):

    def as_element(self) -> typing.Optional["ElementHandle"]:
        """ElementHandle.as_element

        Returns either `null` or the object handle itself, if the object handle is an instance of `ElementHandle`.

        Returns
        -------
        Union[ElementHandle, None]
        """

        return mapping.from_impl_nullable(self._impl_obj.as_element())

    async def owner_frame(self) -> typing.Optional["Frame"]:
        """ElementHandle.owner_frame

        Returns the frame containing the given element.

        Returns
        -------
        Union[Frame, None]
        """

        return mapping.from_impl_nullable(await self._impl_obj.owner_frame())

    async def content_frame(self) -> typing.Optional["Frame"]:
        """ElementHandle.content_frame

        Returns the content frame for element handles referencing iframe nodes, or `null` otherwise

        Returns
        -------
        Union[Frame, None]
        """

        return mapping.from_impl_nullable(await self._impl_obj.content_frame())

    async def get_attribute(self, name: str) -> typing.Optional[str]:
        """ElementHandle.get_attribute

        Returns element attribute value.

        Parameters
        ----------
        name : str
            Attribute name to get the value for.

        Returns
        -------
        Union[str, None]
        """

        return mapping.from_maybe_impl(await self._impl_obj.get_attribute(name=name))

    async def text_content(self) -> typing.Optional[str]:
        """ElementHandle.text_content

        Returns the `node.textContent`.

        Returns
        -------
        Union[str, None]
        """

        return mapping.from_maybe_impl(await self._impl_obj.text_content())

    async def inner_text(self) -> str:
        """ElementHandle.inner_text

        Returns the `element.innerText`.

        Returns
        -------
        str
        """

        return mapping.from_maybe_impl(await self._impl_obj.inner_text())

    async def inner_html(self) -> str:
        """ElementHandle.inner_html

        Returns the `element.innerHTML`.

        Returns
        -------
        str
        """

        return mapping.from_maybe_impl(await self._impl_obj.inner_html())

    async def is_checked(self) -> bool:
        """ElementHandle.is_checked

        Returns whether the element is checked. Throws if the element is not a checkbox or radio input.

        Returns
        -------
        bool
        """

        return mapping.from_maybe_impl(await self._impl_obj.is_checked())

    async def is_disabled(self) -> bool:
        """ElementHandle.is_disabled

        Returns whether the element is disabled, the opposite of [enabled](https://playwright.dev/python/docs/actionability#enabled).

        Returns
        -------
        bool
        """

        return mapping.from_maybe_impl(await self._impl_obj.is_disabled())

    async def is_editable(self) -> bool:
        """ElementHandle.is_editable

        Returns whether the element is [editable](https://playwright.dev/python/docs/actionability#editable).

        Returns
        -------
        bool
        """

        return mapping.from_maybe_impl(await self._impl_obj.is_editable())

    async def is_enabled(self) -> bool:
        """ElementHandle.is_enabled

        Returns whether the element is [enabled](https://playwright.dev/python/docs/actionability#enabled).

        Returns
        -------
        bool
        """

        return mapping.from_maybe_impl(await self._impl_obj.is_enabled())

    async def is_hidden(self) -> bool:
        """ElementHandle.is_hidden

        Returns whether the element is hidden, the opposite of [visible](https://playwright.dev/python/docs/actionability#visible).

        Returns
        -------
        bool
        """

        return mapping.from_maybe_impl(await self._impl_obj.is_hidden())

    async def is_visible(self) -> bool:
        """ElementHandle.is_visible

        Returns whether the element is [visible](https://playwright.dev/python/docs/actionability#visible).

        Returns
        -------
        bool
        """

        return mapping.from_maybe_impl(await self._impl_obj.is_visible())

    async def dispatch_event(
        self, type: str, event_init: typing.Optional[typing.Dict] = None
    ) -> None:
        """ElementHandle.dispatch_event

        The snippet below dispatches the `click` event on the element. Regardless of the visibility state of the element,
        `click` is dispatched. This is equivalent to calling
        [element.click()](https://developer.mozilla.org/en-US/docs/Web/API/HTMLElement/click).

        **Usage**

        ```py
        await element_handle.dispatch_event(\"click\")
        ```

        Under the hood, it creates an instance of an event based on the given `type`, initializes it with `eventInit`
        properties and dispatches it on the element. Events are `composed`, `cancelable` and bubble by default.

        Since `eventInit` is event-specific, please refer to the events documentation for the lists of initial properties:
        - [DeviceMotionEvent](https://developer.mozilla.org/en-US/docs/Web/API/DeviceMotionEvent/DeviceMotionEvent)
        - [DeviceOrientationEvent](https://developer.mozilla.org/en-US/docs/Web/API/DeviceOrientationEvent/DeviceOrientationEvent)
        - [DragEvent](https://developer.mozilla.org/en-US/docs/Web/API/DragEvent/DragEvent)
        - [Event](https://developer.mozilla.org/en-US/docs/Web/API/Event/Event)
        - [FocusEvent](https://developer.mozilla.org/en-US/docs/Web/API/FocusEvent/FocusEvent)
        - [KeyboardEvent](https://developer.mozilla.org/en-US/docs/Web/API/KeyboardEvent/KeyboardEvent)
        - [MouseEvent](https://developer.mozilla.org/en-US/docs/Web/API/MouseEvent/MouseEvent)
        - [PointerEvent](https://developer.mozilla.org/en-US/docs/Web/API/PointerEvent/PointerEvent)
        - [TouchEvent](https://developer.mozilla.org/en-US/docs/Web/API/TouchEvent/TouchEvent)
        - [WheelEvent](https://developer.mozilla.org/en-US/docs/Web/API/WheelEvent/WheelEvent)

        You can also specify `JSHandle` as the property value if you want live objects to be passed into the event:

        ```py
        # note you can only create data_transfer in chromium and firefox
        data_transfer = await page.evaluate_handle(\"new DataTransfer()\")
        await element_handle.dispatch_event(\"#source\", \"dragstart\", {\"dataTransfer\": data_transfer})
        ```

        Parameters
        ----------
        type : str
            DOM event type: `"click"`, `"dragstart"`, etc.
        event_init : Union[Dict, None]
            Optional event-specific initialization properties.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.dispatch_event(
                type=type, eventInit=mapping.to_impl(event_init)
            )
        )

    async def scroll_into_view_if_needed(
        self, *, timeout: typing.Optional[float] = None
    ) -> None:
        """ElementHandle.scroll_into_view_if_needed

        This method waits for [actionability](https://playwright.dev/python/docs/actionability) checks, then tries to scroll element into view, unless
        it is completely visible as defined by
        [IntersectionObserver](https://developer.mozilla.org/en-US/docs/Web/API/Intersection_Observer_API)'s `ratio`.

        Throws when `elementHandle` does not point to an element
        [connected](https://developer.mozilla.org/en-US/docs/Web/API/Node/isConnected) to a Document or a ShadowRoot.

        See [scrolling](https://playwright.dev/python/docs/input#scrolling) for alternative ways to scroll.

        Parameters
        ----------
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.scroll_into_view_if_needed(timeout=timeout)
        )

    async def hover(
        self,
        *,
        modifiers: typing.Optional[
            typing.Sequence[Literal["Alt", "Control", "ControlOrMeta", "Meta", "Shift"]]
        ] = None,
        position: typing.Optional[Position] = None,
        timeout: typing.Optional[float] = None,
        no_wait_after: typing.Optional[bool] = None,
        force: typing.Optional[bool] = None,
        trial: typing.Optional[bool] = None,
    ) -> None:
        """ElementHandle.hover

        This method hovers over the element by performing the following steps:
        1. Wait for [actionability](https://playwright.dev/python/docs/actionability) checks on the element, unless `force` option is set.
        1. Scroll the element into view if needed.
        1. Use `page.mouse` to hover over the center of the element, or the specified `position`.

        If the element is detached from the DOM at any moment during the action, this method throws.

        When all steps combined have not finished during the specified `timeout`, this method throws a `TimeoutError`.
        Passing zero timeout disables this.

        Parameters
        ----------
        modifiers : Union[Sequence[Union["Alt", "Control", "ControlOrMeta", "Meta", "Shift"]], None]
            Modifier keys to press. Ensures that only these modifiers are pressed during the operation, and then restores
            current modifiers back. If not specified, currently pressed modifiers are used. "ControlOrMeta" resolves to
            "Control" on Windows and Linux and to "Meta" on macOS.
        position : Union[{x: float, y: float}, None]
            A point to use relative to the top-left corner of element padding box. If not specified, uses some visible point of
            the element.
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        no_wait_after : Union[bool, None]
            This option has no effect.
            Deprecated: This option has no effect.
        force : Union[bool, None]
            Whether to bypass the [actionability](../actionability.md) checks. Defaults to `false`.
        trial : Union[bool, None]
            When set, this method only performs the [actionability](../actionability.md) checks and skips the action. Defaults
            to `false`. Useful to wait until the element is ready for the action without performing it.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.hover(
                modifiers=mapping.to_impl(modifiers),
                position=position,
                timeout=timeout,
                noWaitAfter=no_wait_after,
                force=force,
                trial=trial,
            )
        )

    async def click(
        self,
        *,
        modifiers: typing.Optional[
            typing.Sequence[Literal["Alt", "Control", "ControlOrMeta", "Meta", "Shift"]]
        ] = None,
        position: typing.Optional[Position] = None,
        delay: typing.Optional[float] = None,
        button: typing.Optional[Literal["left", "middle", "right"]] = None,
        click_count: typing.Optional[int] = None,
        timeout: typing.Optional[float] = None,
        force: typing.Optional[bool] = None,
        no_wait_after: typing.Optional[bool] = None,
        trial: typing.Optional[bool] = None,
        steps: typing.Optional[int] = None,
    ) -> None:
        """ElementHandle.click

        This method clicks the element by performing the following steps:
        1. Wait for [actionability](https://playwright.dev/python/docs/actionability) checks on the element, unless `force` option is set.
        1. Scroll the element into view if needed.
        1. Use `page.mouse` to click in the center of the element, or the specified `position`.
        1. Wait for initiated navigations to either succeed or fail, unless `noWaitAfter` option is set.

        If the element is detached from the DOM at any moment during the action, this method throws.

        When all steps combined have not finished during the specified `timeout`, this method throws a `TimeoutError`.
        Passing zero timeout disables this.

        Parameters
        ----------
        modifiers : Union[Sequence[Union["Alt", "Control", "ControlOrMeta", "Meta", "Shift"]], None]
            Modifier keys to press. Ensures that only these modifiers are pressed during the operation, and then restores
            current modifiers back. If not specified, currently pressed modifiers are used. "ControlOrMeta" resolves to
            "Control" on Windows and Linux and to "Meta" on macOS.
        position : Union[{x: float, y: float}, None]
            A point to use relative to the top-left corner of element padding box. If not specified, uses some visible point of
            the element.
        delay : Union[float, None]
            Time to wait between `mousedown` and `mouseup` in milliseconds. Defaults to 0.
        button : Union["left", "middle", "right", None]
            Defaults to `left`.
        click_count : Union[int, None]
            defaults to 1. See [UIEvent.detail].
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        force : Union[bool, None]
            Whether to bypass the [actionability](../actionability.md) checks. Defaults to `false`.
        no_wait_after : Union[bool, None]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You
            can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as
            navigating to inaccessible pages. Defaults to `false`.
            Deprecated: This option will default to `true` in the future.
        trial : Union[bool, None]
            When set, this method only performs the [actionability](../actionability.md) checks and skips the action. Defaults
            to `false`. Useful to wait until the element is ready for the action without performing it.
        steps : Union[int, None]
            Defaults to 1. Sends `n` interpolated `mousemove` events to represent travel between Playwright's current cursor
            position and the provided destination. When set to 1, emits a single `mousemove` event at the destination location.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.click(
                modifiers=mapping.to_impl(modifiers),
                position=position,
                delay=delay,
                button=button,
                clickCount=click_count,
                timeout=timeout,
                force=force,
                noWaitAfter=no_wait_after,
                trial=trial,
                steps=steps,
            )
        )

    async def dblclick(
        self,
        *,
        modifiers: typing.Optional[
            typing.Sequence[Literal["Alt", "Control", "ControlOrMeta", "Meta", "Shift"]]
        ] = None,
        position: typing.Optional[Position] = None,
        delay: typing.Optional[float] = None,
        button: typing.Optional[Literal["left", "middle", "right"]] = None,
        timeout: typing.Optional[float] = None,
        force: typing.Optional[bool] = None,
        no_wait_after: typing.Optional[bool] = None,
        trial: typing.Optional[bool] = None,
        steps: typing.Optional[int] = None,
    ) -> None:
        """ElementHandle.dblclick

        This method double clicks the element by performing the following steps:
        1. Wait for [actionability](https://playwright.dev/python/docs/actionability) checks on the element, unless `force` option is set.
        1. Scroll the element into view if needed.
        1. Use `page.mouse` to double click in the center of the element, or the specified `position`.

        If the element is detached from the DOM at any moment during the action, this method throws.

        When all steps combined have not finished during the specified `timeout`, this method throws a `TimeoutError`.
        Passing zero timeout disables this.

        **NOTE** `elementHandle.dblclick()` dispatches two `click` events and a single `dblclick` event.

        Parameters
        ----------
        modifiers : Union[Sequence[Union["Alt", "Control", "ControlOrMeta", "Meta", "Shift"]], None]
            Modifier keys to press. Ensures that only these modifiers are pressed during the operation, and then restores
            current modifiers back. If not specified, currently pressed modifiers are used. "ControlOrMeta" resolves to
            "Control" on Windows and Linux and to "Meta" on macOS.
        position : Union[{x: float, y: float}, None]
            A point to use relative to the top-left corner of element padding box. If not specified, uses some visible point of
            the element.
        delay : Union[float, None]
            Time to wait between `mousedown` and `mouseup` in milliseconds. Defaults to 0.
        button : Union["left", "middle", "right", None]
            Defaults to `left`.
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        force : Union[bool, None]
            Whether to bypass the [actionability](../actionability.md) checks. Defaults to `false`.
        no_wait_after : Union[bool, None]
            This option has no effect.
            Deprecated: This option has no effect.
        trial : Union[bool, None]
            When set, this method only performs the [actionability](../actionability.md) checks and skips the action. Defaults
            to `false`. Useful to wait until the element is ready for the action without performing it.
        steps : Union[int, None]
            Defaults to 1. Sends `n` interpolated `mousemove` events to represent travel between Playwright's current cursor
            position and the provided destination. When set to 1, emits a single `mousemove` event at the destination location.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.dblclick(
                modifiers=mapping.to_impl(modifiers),
                position=position,
                delay=delay,
                button=button,
                timeout=timeout,
                force=force,
                noWaitAfter=no_wait_after,
                trial=trial,
                steps=steps,
            )
        )

    async def select_option(
        self,
        value: typing.Optional[typing.Union[str, typing.Sequence[str]]] = None,
        *,
        index: typing.Optional[typing.Union[int, typing.Sequence[int]]] = None,
        label: typing.Optional[typing.Union[str, typing.Sequence[str]]] = None,
        element: typing.Optional[
            typing.Union["ElementHandle", typing.Sequence["ElementHandle"]]
        ] = None,
        timeout: typing.Optional[float] = None,
        force: typing.Optional[bool] = None,
        no_wait_after: typing.Optional[bool] = None,
    ) -> typing.List[str]:
        """ElementHandle.select_option

        This method waits for [actionability](https://playwright.dev/python/docs/actionability) checks, waits until all specified options are present in
        the `<select>` element and selects these options.

        If the target element is not a `<select>` element, this method throws an error. However, if the element is inside
        the `<label>` element that has an associated
        [control](https://developer.mozilla.org/en-US/docs/Web/API/HTMLLabelElement/control), the control will be used
        instead.

        Returns the array of option values that have been successfully selected.

        Triggers a `change` and `input` event once all the provided options have been selected.

        **Usage**

        ```py
        # Single selection matching the value or label
        await handle.select_option(\"blue\")
        # single selection matching the label
        await handle.select_option(label=\"blue\")
        # multiple selection
        await handle.select_option(value=[\"red\", \"green\", \"blue\"])
        ```

        Parameters
        ----------
        value : Union[Sequence[str], str, None]
            Options to select by value. If the `<select>` has the `multiple` attribute, all given options are selected,
            otherwise only the first option matching one of the passed options is selected. Optional.
        index : Union[Sequence[int], int, None]
            Options to select by index. Optional.
        label : Union[Sequence[str], str, None]
            Options to select by label. If the `<select>` has the `multiple` attribute, all given options are selected,
            otherwise only the first option matching one of the passed options is selected. Optional.
        element : Union[ElementHandle, Sequence[ElementHandle], None]
            Option elements to select. Optional.
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        force : Union[bool, None]
            Whether to bypass the [actionability](../actionability.md) checks. Defaults to `false`.
        no_wait_after : Union[bool, None]
            This option has no effect.
            Deprecated: This option has no effect.

        Returns
        -------
        List[str]
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.select_option(
                value=mapping.to_impl(value),
                index=mapping.to_impl(index),
                label=mapping.to_impl(label),
                element=mapping.to_impl(element),
                timeout=timeout,
                force=force,
                noWaitAfter=no_wait_after,
            )
        )

    async def tap(
        self,
        *,
        modifiers: typing.Optional[
            typing.Sequence[Literal["Alt", "Control", "ControlOrMeta", "Meta", "Shift"]]
        ] = None,
        position: typing.Optional[Position] = None,
        timeout: typing.Optional[float] = None,
        force: typing.Optional[bool] = None,
        no_wait_after: typing.Optional[bool] = None,
        trial: typing.Optional[bool] = None,
    ) -> None:
        """ElementHandle.tap

        This method taps the element by performing the following steps:
        1. Wait for [actionability](https://playwright.dev/python/docs/actionability) checks on the element, unless `force` option is set.
        1. Scroll the element into view if needed.
        1. Use `page.touchscreen` to tap the center of the element, or the specified `position`.

        If the element is detached from the DOM at any moment during the action, this method throws.

        When all steps combined have not finished during the specified `timeout`, this method throws a `TimeoutError`.
        Passing zero timeout disables this.

        **NOTE** `elementHandle.tap()` requires that the `hasTouch` option of the browser context be set to true.

        Parameters
        ----------
        modifiers : Union[Sequence[Union["Alt", "Control", "ControlOrMeta", "Meta", "Shift"]], None]
            Modifier keys to press. Ensures that only these modifiers are pressed during the operation, and then restores
            current modifiers back. If not specified, currently pressed modifiers are used. "ControlOrMeta" resolves to
            "Control" on Windows and Linux and to "Meta" on macOS.
        position : Union[{x: float, y: float}, None]
            A point to use relative to the top-left corner of element padding box. If not specified, uses some visible point of
            the element.
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        force : Union[bool, None]
            Whether to bypass the [actionability](../actionability.md) checks. Defaults to `false`.
        no_wait_after : Union[bool, None]
            This option has no effect.
            Deprecated: This option has no effect.
        trial : Union[bool, None]
            When set, this method only performs the [actionability](../actionability.md) checks and skips the action. Defaults
            to `false`. Useful to wait until the element is ready for the action without performing it.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.tap(
                modifiers=mapping.to_impl(modifiers),
                position=position,
                timeout=timeout,
                force=force,
                noWaitAfter=no_wait_after,
                trial=trial,
            )
        )

    async def fill(
        self,
        value: str,
        *,
        timeout: typing.Optional[float] = None,
        no_wait_after: typing.Optional[bool] = None,
        force: typing.Optional[bool] = None,
    ) -> None:
        """ElementHandle.fill

        This method waits for [actionability](https://playwright.dev/python/docs/actionability) checks, focuses the element, fills it and triggers an
        `input` event after filling. Note that you can pass an empty string to clear the input field.

        If the target element is not an `<input>`, `<textarea>` or `[contenteditable]` element, this method throws an
        error. However, if the element is inside the `<label>` element that has an associated
        [control](https://developer.mozilla.org/en-US/docs/Web/API/HTMLLabelElement/control), the control will be filled
        instead.

        To send fine-grained keyboard events, use `locator.press_sequentially()`.

        Parameters
        ----------
        value : str
            Value to set for the `<input>`, `<textarea>` or `[contenteditable]` element.
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        no_wait_after : Union[bool, None]
            This option has no effect.
            Deprecated: This option has no effect.
        force : Union[bool, None]
            Whether to bypass the [actionability](../actionability.md) checks. Defaults to `false`.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.fill(
                value=value, timeout=timeout, noWaitAfter=no_wait_after, force=force
            )
        )

    async def select_text(
        self,
        *,
        force: typing.Optional[bool] = None,
        timeout: typing.Optional[float] = None,
    ) -> None:
        """ElementHandle.select_text

        This method waits for [actionability](https://playwright.dev/python/docs/actionability) checks, then focuses the element and selects all its
        text content.

        If the element is inside the `<label>` element that has an associated
        [control](https://developer.mozilla.org/en-US/docs/Web/API/HTMLLabelElement/control), focuses and selects text in
        the control instead.

        Parameters
        ----------
        force : Union[bool, None]
            Whether to bypass the [actionability](../actionability.md) checks. Defaults to `false`.
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.select_text(force=force, timeout=timeout)
        )

    async def input_value(self, *, timeout: typing.Optional[float] = None) -> str:
        """ElementHandle.input_value

        Returns `input.value` for the selected `<input>` or `<textarea>` or `<select>` element.

        Throws for non-input elements. However, if the element is inside the `<label>` element that has an associated
        [control](https://developer.mozilla.org/en-US/docs/Web/API/HTMLLabelElement/control), returns the value of the
        control.

        Parameters
        ----------
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.

        Returns
        -------
        str
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.input_value(timeout=timeout)
        )

    async def set_input_files(
        self,
        files: typing.Union[
            str,
            pathlib.Path,
            FilePayload,
            typing.Sequence[typing.Union[str, pathlib.Path]],
            typing.Sequence[FilePayload],
        ],
        *,
        timeout: typing.Optional[float] = None,
        no_wait_after: typing.Optional[bool] = None,
    ) -> None:
        """ElementHandle.set_input_files

        Sets the value of the file input to these file paths or files. If some of the `filePaths` are relative paths, then
        they are resolved relative to the current working directory. For empty array, clears the selected files. For inputs
        with a `[webkitdirectory]` attribute, only a single directory path is supported.

        This method expects `ElementHandle` to point to an
        [input element](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/input). However, if the element is inside
        the `<label>` element that has an associated
        [control](https://developer.mozilla.org/en-US/docs/Web/API/HTMLLabelElement/control), targets the control instead.

        Parameters
        ----------
        files : Union[Sequence[Union[pathlib.Path, str]], Sequence[{name: str, mimeType: str, buffer: bytes}], pathlib.Path, str, {name: str, mimeType: str, buffer: bytes}]
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        no_wait_after : Union[bool, None]
            This option has no effect.
            Deprecated: This option has no effect.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.set_input_files(
                files=mapping.to_impl(files), timeout=timeout, noWaitAfter=no_wait_after
            )
        )

    async def focus(self) -> None:
        """ElementHandle.focus

        Calls [focus](https://developer.mozilla.org/en-US/docs/Web/API/HTMLElement/focus) on the element.
        """

        return mapping.from_maybe_impl(await self._impl_obj.focus())

    async def type(
        self,
        text: str,
        *,
        delay: typing.Optional[float] = None,
        timeout: typing.Optional[float] = None,
        no_wait_after: typing.Optional[bool] = None,
    ) -> None:
        """ElementHandle.type

        Focuses the element, and then sends a `keydown`, `keypress`/`input`, and `keyup` event for each character in the
        text.

        To press a special key, like `Control` or `ArrowDown`, use `element_handle.press()`.

        **Usage**

        Parameters
        ----------
        text : str
            A text to type into a focused element.
        delay : Union[float, None]
            Time to wait between key presses in milliseconds. Defaults to 0.
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        no_wait_after : Union[bool, None]
            This option has no effect.
            Deprecated: This option has no effect.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.type(
                text=text, delay=delay, timeout=timeout, noWaitAfter=no_wait_after
            )
        )

    async def press(
        self,
        key: str,
        *,
        delay: typing.Optional[float] = None,
        timeout: typing.Optional[float] = None,
        no_wait_after: typing.Optional[bool] = None,
    ) -> None:
        """ElementHandle.press

        Focuses the element, and then uses `keyboard.down()` and `keyboard.up()`.

        `key` can specify the intended
        [keyboardEvent.key](https://developer.mozilla.org/en-US/docs/Web/API/KeyboardEvent/key) value or a single character
        to generate the text for. A superset of the `key` values can be found
        [here](https://developer.mozilla.org/en-US/docs/Web/API/KeyboardEvent/key/Key_Values). Examples of the keys are:

        `F1` - `F12`, `Digit0`- `Digit9`, `KeyA`- `KeyZ`, `Backquote`, `Minus`, `Equal`, `Backslash`, `Backspace`, `Tab`,
        `Delete`, `Escape`, `ArrowDown`, `End`, `Enter`, `Home`, `Insert`, `PageDown`, `PageUp`, `ArrowRight`, `ArrowUp`,
        etc.

        Following modification shortcuts are also supported: `Shift`, `Control`, `Alt`, `Meta`, `ShiftLeft`,
        `ControlOrMeta`.

        Holding down `Shift` will type the text that corresponds to the `key` in the upper case.

        If `key` is a single character, it is case-sensitive, so the values `a` and `A` will generate different respective
        texts.

        Shortcuts such as `key: \"Control+o\"`, `key: \"Control++` or `key: \"Control+Shift+T\"` are supported as well. When
        specified with the modifier, modifier is pressed and being held while the subsequent key is being pressed.

        Parameters
        ----------
        key : str
            Name of the key to press or a character to generate, such as `ArrowLeft` or `a`.
        delay : Union[float, None]
            Time to wait between `keydown` and `keyup` in milliseconds. Defaults to 0.
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        no_wait_after : Union[bool, None]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You
            can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as
            navigating to inaccessible pages. Defaults to `false`.
            Deprecated: This option will default to `true` in the future.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.press(
                key=key, delay=delay, timeout=timeout, noWaitAfter=no_wait_after
            )
        )

    async def set_checked(
        self,
        checked: bool,
        *,
        position: typing.Optional[Position] = None,
        timeout: typing.Optional[float] = None,
        force: typing.Optional[bool] = None,
        no_wait_after: typing.Optional[bool] = None,
        trial: typing.Optional[bool] = None,
    ) -> None:
        """ElementHandle.set_checked

        This method checks or unchecks an element by performing the following steps:
        1. Ensure that element is a checkbox or a radio input. If not, this method throws.
        1. If the element already has the right checked state, this method returns immediately.
        1. Wait for [actionability](https://playwright.dev/python/docs/actionability) checks on the matched element, unless `force` option is set. If
           the element is detached during the checks, the whole action is retried.
        1. Scroll the element into view if needed.
        1. Use `page.mouse` to click in the center of the element.
        1. Ensure that the element is now checked or unchecked. If not, this method throws.

        When all steps combined have not finished during the specified `timeout`, this method throws a `TimeoutError`.
        Passing zero timeout disables this.

        Parameters
        ----------
        checked : bool
            Whether to check or uncheck the checkbox.
        position : Union[{x: float, y: float}, None]
            A point to use relative to the top-left corner of element padding box. If not specified, uses some visible point of
            the element.
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        force : Union[bool, None]
            Whether to bypass the [actionability](../actionability.md) checks. Defaults to `false`.
        no_wait_after : Union[bool, None]
            This option has no effect.
            Deprecated: This option has no effect.
        trial : Union[bool, None]
            When set, this method only performs the [actionability](../actionability.md) checks and skips the action. Defaults
            to `false`. Useful to wait until the element is ready for the action without performing it.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.set_checked(
                checked=checked,
                position=position,
                timeout=timeout,
                force=force,
                noWaitAfter=no_wait_after,
                trial=trial,
            )
        )

    async def check(
        self,
        *,
        position: typing.Optional[Position] = None,
        timeout: typing.Optional[float] = None,
        force: typing.Optional[bool] = None,
        no_wait_after: typing.Optional[bool] = None,
        trial: typing.Optional[bool] = None,
    ) -> None:
        """ElementHandle.check

        This method checks the element by performing the following steps:
        1. Ensure that element is a checkbox or a radio input. If not, this method throws. If the element is already
           checked, this method returns immediately.
        1. Wait for [actionability](https://playwright.dev/python/docs/actionability) checks on the element, unless `force` option is set.
        1. Scroll the element into view if needed.
        1. Use `page.mouse` to click in the center of the element.
        1. Ensure that the element is now checked. If not, this method throws.

        If the element is detached from the DOM at any moment during the action, this method throws.

        When all steps combined have not finished during the specified `timeout`, this method throws a `TimeoutError`.
        Passing zero timeout disables this.

        Parameters
        ----------
        position : Union[{x: float, y: float}, None]
            A point to use relative to the top-left corner of element padding box. If not specified, uses some visible point of
            the element.
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        force : Union[bool, None]
            Whether to bypass the [actionability](../actionability.md) checks. Defaults to `false`.
        no_wait_after : Union[bool, None]
            This option has no effect.
            Deprecated: This option has no effect.
        trial : Union[bool, None]
            When set, this method only performs the [actionability](../actionability.md) checks and skips the action. Defaults
            to `false`. Useful to wait until the element is ready for the action without performing it.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.check(
                position=position,
                timeout=timeout,
                force=force,
                noWaitAfter=no_wait_after,
                trial=trial,
            )
        )

    async def uncheck(
        self,
        *,
        position: typing.Optional[Position] = None,
        timeout: typing.Optional[float] = None,
        force: typing.Optional[bool] = None,
        no_wait_after: typing.Optional[bool] = None,
        trial: typing.Optional[bool] = None,
    ) -> None:
        """ElementHandle.uncheck

        This method checks the element by performing the following steps:
        1. Ensure that element is a checkbox or a radio input. If not, this method throws. If the element is already
           unchecked, this method returns immediately.
        1. Wait for [actionability](https://playwright.dev/python/docs/actionability) checks on the element, unless `force` option is set.
        1. Scroll the element into view if needed.
        1. Use `page.mouse` to click in the center of the element.
        1. Ensure that the element is now unchecked. If not, this method throws.

        If the element is detached from the DOM at any moment during the action, this method throws.

        When all steps combined have not finished during the specified `timeout`, this method throws a `TimeoutError`.
        Passing zero timeout disables this.

        Parameters
        ----------
        position : Union[{x: float, y: float}, None]
            A point to use relative to the top-left corner of element padding box. If not specified, uses some visible point of
            the element.
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        force : Union[bool, None]
            Whether to bypass the [actionability](../actionability.md) checks. Defaults to `false`.
        no_wait_after : Union[bool, None]
            This option has no effect.
            Deprecated: This option has no effect.
        trial : Union[bool, None]
            When set, this method only performs the [actionability](../actionability.md) checks and skips the action. Defaults
            to `false`. Useful to wait until the element is ready for the action without performing it.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.uncheck(
                position=position,
                timeout=timeout,
                force=force,
                noWaitAfter=no_wait_after,
                trial=trial,
            )
        )

    async def bounding_box(self) -> typing.Optional[FloatRect]:
        """ElementHandle.bounding_box

        This method returns the bounding box of the element, or `null` if the element is not visible. The bounding box is
        calculated relative to the main frame viewport - which is usually the same as the browser window.

        Scrolling affects the returned bounding box, similarly to
        [Element.getBoundingClientRect](https://developer.mozilla.org/en-US/docs/Web/API/Element/getBoundingClientRect).
        That means `x` and/or `y` may be negative.

        Elements from child frames return the bounding box relative to the main frame, unlike the
        [Element.getBoundingClientRect](https://developer.mozilla.org/en-US/docs/Web/API/Element/getBoundingClientRect).

        Assuming the page is static, it is safe to use bounding box coordinates to perform input. For example, the
        following snippet should click the center of the element.

        **Usage**

        ```py
        box = await element_handle.bounding_box()
        await page.mouse.click(box[\"x\"] + box[\"width\"] / 2, box[\"y\"] + box[\"height\"] / 2)
        ```

        Returns
        -------
        Union[{x: float, y: float, width: float, height: float}, None]
        """

        return mapping.from_impl_nullable(await self._impl_obj.bounding_box())

    async def screenshot(
        self,
        *,
        timeout: typing.Optional[float] = None,
        type: typing.Optional[Literal["jpeg", "png"]] = None,
        path: typing.Optional[typing.Union[pathlib.Path, str]] = None,
        quality: typing.Optional[int] = None,
        omit_background: typing.Optional[bool] = None,
        animations: typing.Optional[Literal["allow", "disabled"]] = None,
        caret: typing.Optional[Literal["hide", "initial"]] = None,
        scale: typing.Optional[Literal["css", "device"]] = None,
        mask: typing.Optional[typing.Sequence["Locator"]] = None,
        mask_color: typing.Optional[str] = None,
        style: typing.Optional[str] = None,
    ) -> bytes:
        """ElementHandle.screenshot

        This method captures a screenshot of the page, clipped to the size and position of this particular element. If the
        element is covered by other elements, it will not be actually visible on the screenshot. If the element is a
        scrollable container, only the currently scrolled content will be visible on the screenshot.

        This method waits for the [actionability](https://playwright.dev/python/docs/actionability) checks, then scrolls element into view before taking
        a screenshot. If the element is detached from DOM, the method throws an error.

        Returns the buffer with the captured screenshot.

        Parameters
        ----------
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        type : Union["jpeg", "png", None]
            Specify screenshot type, defaults to `png`.
        path : Union[pathlib.Path, str, None]
            The file path to save the image to. The screenshot type will be inferred from file extension. If `path` is a
            relative path, then it is resolved relative to the current working directory. If no path is provided, the image
            won't be saved to the disk.
        quality : Union[int, None]
            The quality of the image, between 0-100. Not applicable to `png` images.
        omit_background : Union[bool, None]
            Hides default white background and allows capturing screenshots with transparency. Not applicable to `jpeg` images.
            Defaults to `false`.
        animations : Union["allow", "disabled", None]
            When set to `"disabled"`, stops CSS animations, CSS transitions and Web Animations. Animations get different
            treatment depending on their duration:
            - finite animations are fast-forwarded to completion, so they'll fire `transitionend` event.
            - infinite animations are canceled to initial state, and then played over after the screenshot.

            Defaults to `"allow"` that leaves animations untouched.
        caret : Union["hide", "initial", None]
            When set to `"hide"`, screenshot will hide text caret. When set to `"initial"`, text caret behavior will not be
            changed.  Defaults to `"hide"`.
        scale : Union["css", "device", None]
            When set to `"css"`, screenshot will have a single pixel per each css pixel on the page. For high-dpi devices, this
            will keep screenshots small. Using `"device"` option will produce a single pixel per each device pixel, so
            screenshots of high-dpi devices will be twice as large or even larger.

            Defaults to `"device"`.
        mask : Union[Sequence[Locator], None]
            Specify locators that should be masked when the screenshot is taken. Masked elements will be overlaid with a pink
            box `#FF00FF` (customized by `maskColor`) that completely covers its bounding box. The mask is also applied to
            invisible elements, see [Matching only visible elements](../locators.md#matching-only-visible-elements) to disable
            that.
        mask_color : Union[str, None]
            Specify the color of the overlay box for masked elements, in
            [CSS color format](https://developer.mozilla.org/en-US/docs/Web/CSS/color_value). Default color is pink `#FF00FF`.
        style : Union[str, None]
            Text of the stylesheet to apply while making the screenshot. This is where you can hide dynamic elements, make
            elements invisible or change their properties to help you creating repeatable screenshots. This stylesheet pierces
            the Shadow DOM and applies to the inner frames.

        Returns
        -------
        bytes
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.screenshot(
                timeout=timeout,
                type=type,
                path=path,
                quality=quality,
                omitBackground=omit_background,
                animations=animations,
                caret=caret,
                scale=scale,
                mask=mapping.to_impl(mask),
                maskColor=mask_color,
                style=style,
            )
        )

    async def query_selector(self, selector: str) -> typing.Optional["ElementHandle"]:
        """ElementHandle.query_selector

        The method finds an element matching the specified selector in the `ElementHandle`'s subtree. If no elements match
        the selector, returns `null`.

        Parameters
        ----------
        selector : str
            A selector to query for.

        Returns
        -------
        Union[ElementHandle, None]
        """

        return mapping.from_impl_nullable(
            await self._impl_obj.query_selector(selector=selector)
        )

    async def query_selector_all(self, selector: str) -> typing.List["ElementHandle"]:
        """ElementHandle.query_selector_all

        The method finds all elements matching the specified selector in the `ElementHandle`s subtree. If no elements match
        the selector, returns empty array.

        Parameters
        ----------
        selector : str
            A selector to query for.

        Returns
        -------
        List[ElementHandle]
        """

        return mapping.from_impl_list(
            await self._impl_obj.query_selector_all(selector=selector)
        )

    async def eval_on_selector(
        self, selector: str, expression: str, arg: typing.Optional[typing.Any] = None
    ) -> typing.Any:
        """ElementHandle.eval_on_selector

        Returns the return value of `expression`.

        The method finds an element matching the specified selector in the `ElementHandle`s subtree and passes it as a
        first argument to `expression`. If no elements match the selector, the method throws an error.

        If `expression` returns a [Promise], then `element_handle.eval_on_selector()` would wait for the promise to
        resolve and return its value.

        **Usage**

        ```py
        tweet_handle = await page.query_selector(\".tweet\")
        assert await tweet_handle.eval_on_selector(\".like\", \"node => node.innerText\") == \"100\"
        assert await tweet_handle.eval_on_selector(\".retweets\", \"node => node.innerText\") == \"10\"
        ```

        Parameters
        ----------
        selector : str
            A selector to query for.
        expression : str
            JavaScript expression to be evaluated in the browser context. If the expression evaluates to a function, the
            function is automatically invoked.
        arg : Union[Any, None]
            Optional argument to pass to `expression`.

        Returns
        -------
        Any
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.eval_on_selector(
                selector=selector, expression=expression, arg=mapping.to_impl(arg)
            )
        )

    async def eval_on_selector_all(
        self, selector: str, expression: str, arg: typing.Optional[typing.Any] = None
    ) -> typing.Any:
        """ElementHandle.eval_on_selector_all

        Returns the return value of `expression`.

        The method finds all elements matching the specified selector in the `ElementHandle`'s subtree and passes an array
        of matched elements as a first argument to `expression`.

        If `expression` returns a [Promise], then `element_handle.eval_on_selector_all()` would wait for the promise to
        resolve and return its value.

        **Usage**

        ```html
        <div class=\"feed\">
          <div class=\"tweet\">Hello!</div>
          <div class=\"tweet\">Hi!</div>
        </div>
        ```

        ```py
        feed_handle = await page.query_selector(\".feed\")
        assert await feed_handle.eval_on_selector_all(\".tweet\", \"nodes => nodes.map(n => n.innerText)\") == [\"hello!\", \"hi!\"]
        ```

        Parameters
        ----------
        selector : str
            A selector to query for.
        expression : str
            JavaScript expression to be evaluated in the browser context. If the expression evaluates to a function, the
            function is automatically invoked.
        arg : Union[Any, None]
            Optional argument to pass to `expression`.

        Returns
        -------
        Any
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.eval_on_selector_all(
                selector=selector, expression=expression, arg=mapping.to_impl(arg)
            )
        )

    async def wait_for_element_state(
        self,
        state: Literal[
            "disabled", "editable", "enabled", "hidden", "stable", "visible"
        ],
        *,
        timeout: typing.Optional[float] = None,
    ) -> None:
        """ElementHandle.wait_for_element_state

        Returns when the element satisfies the `state`.

        Depending on the `state` parameter, this method waits for one of the [actionability](https://playwright.dev/python/docs/actionability) checks to
        pass. This method throws when the element is detached while waiting, unless waiting for the `\"hidden\"` state.
        - `\"visible\"` Wait until the element is [visible](https://playwright.dev/python/docs/actionability#visible).
        - `\"hidden\"` Wait until the element is [not visible](https://playwright.dev/python/docs/actionability#visible) or not attached. Note that
          waiting for hidden does not throw when the element detaches.
        - `\"stable\"` Wait until the element is both [visible](https://playwright.dev/python/docs/actionability#visible) and
          [stable](https://playwright.dev/python/docs/actionability#stable).
        - `\"enabled\"` Wait until the element is [enabled](https://playwright.dev/python/docs/actionability#enabled).
        - `\"disabled\"` Wait until the element is [not enabled](https://playwright.dev/python/docs/actionability#enabled).
        - `\"editable\"` Wait until the element is [editable](https://playwright.dev/python/docs/actionability#editable).

        If the element does not satisfy the condition for the `timeout` milliseconds, this method will throw.

        Parameters
        ----------
        state : Union["disabled", "editable", "enabled", "hidden", "stable", "visible"]
            A state to wait for, see below for more details.
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.wait_for_element_state(state=state, timeout=timeout)
        )

    async def wait_for_selector(
        self,
        selector: str,
        *,
        state: typing.Optional[
            Literal["attached", "detached", "hidden", "visible"]
        ] = None,
        timeout: typing.Optional[float] = None,
        strict: typing.Optional[bool] = None,
    ) -> typing.Optional["ElementHandle"]:
        """ElementHandle.wait_for_selector

        Returns element specified by selector when it satisfies `state` option. Returns `null` if waiting for `hidden` or
        `detached`.

        Wait for the `selector` relative to the element handle to satisfy `state` option (either appear/disappear from dom,
        or become visible/hidden). If at the moment of calling the method `selector` already satisfies the condition, the
        method will return immediately. If the selector doesn't satisfy the condition for the `timeout` milliseconds, the
        function will throw.

        **Usage**

        ```py
        await page.set_content(\"<div><span></span></div>\")
        div = await page.query_selector(\"div\")
        # waiting for the \"span\" selector relative to the div.
        span = await div.wait_for_selector(\"span\", state=\"attached\")
        ```

        **NOTE** This method does not work across navigations, use `page.wait_for_selector()` instead.

        Parameters
        ----------
        selector : str
            A selector to query for.
        state : Union["attached", "detached", "hidden", "visible", None]
            Defaults to `'visible'`. Can be either:
            - `'attached'` - wait for element to be present in DOM.
            - `'detached'` - wait for element to not be present in DOM.
            - `'visible'` - wait for element to have non-empty bounding box and no `visibility:hidden`. Note that element
              without any content or with `display:none` has an empty bounding box and is not considered visible.
            - `'hidden'` - wait for element to be either detached from DOM, or have an empty bounding box or
              `visibility:hidden`. This is opposite to the `'visible'` option.
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        strict : Union[bool, None]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more than one
            element, the call throws an exception.

        Returns
        -------
        Union[ElementHandle, None]
        """

        return mapping.from_impl_nullable(
            await self._impl_obj.wait_for_selector(
                selector=selector, state=state, timeout=timeout, strict=strict
            )
        )


mapping.register(ElementHandleImpl, ElementHandle)


class FileChooser(AsyncBase):

    @property
    def page(self) -> "Page":
        """FileChooser.page

        Returns page this file chooser belongs to.

        Returns
        -------
        Page
        """
        return mapping.from_impl(self._impl_obj.page)

    @property
    def element(self) -> "ElementHandle":
        """FileChooser.element

        Returns input element associated with this file chooser.

        Returns
        -------
        ElementHandle
        """
        return mapping.from_impl(self._impl_obj.element)

    def is_multiple(self) -> bool:
        """FileChooser.is_multiple

        Returns whether this file chooser accepts multiple files.

        Returns
        -------
        bool
        """

        return mapping.from_maybe_impl(self._impl_obj.is_multiple())

    async def set_files(
        self,
        files: typing.Union[
            str,
            pathlib.Path,
            FilePayload,
            typing.Sequence[typing.Union[str, pathlib.Path]],
            typing.Sequence[FilePayload],
        ],
        *,
        timeout: typing.Optional[float] = None,
        no_wait_after: typing.Optional[bool] = None,
    ) -> None:
        """FileChooser.set_files

        Sets the value of the file input this chooser is associated with. If some of the `filePaths` are relative paths,
        then they are resolved relative to the current working directory. For empty array, clears the selected files.

        Parameters
        ----------
        files : Union[Sequence[Union[pathlib.Path, str]], Sequence[{name: str, mimeType: str, buffer: bytes}], pathlib.Path, str, {name: str, mimeType: str, buffer: bytes}]
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        no_wait_after : Union[bool, None]
            This option has no effect.
            Deprecated: This option has no effect.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.set_files(
                files=mapping.to_impl(files), timeout=timeout, noWaitAfter=no_wait_after
            )
        )


mapping.register(FileChooserImpl, FileChooser)


class Frame(AsyncBase):

    @property
    def page(self) -> "Page":
        """Frame.page

        Returns the page containing this frame.

        Returns
        -------
        Page
        """
        return mapping.from_impl(self._impl_obj.page)

    @property
    def name(self) -> str:
        """Frame.name

        Returns frame's name attribute as specified in the tag.

        If the name is empty, returns the id attribute instead.

        **NOTE** This value is calculated once when the frame is created, and will not update if the attribute is changed
        later.

        Returns
        -------
        str
        """
        return mapping.from_maybe_impl(self._impl_obj.name)

    @property
    def url(self) -> str:
        """Frame.url

        Returns frame's url.

        Returns
        -------
        str
        """
        return mapping.from_maybe_impl(self._impl_obj.url)

    @property
    def parent_frame(self) -> typing.Optional["Frame"]:
        """Frame.parent_frame

        Parent frame, if any. Detached frames and main frames return `null`.

        Returns
        -------
        Union[Frame, None]
        """
        return mapping.from_impl_nullable(self._impl_obj.parent_frame)

    @property
    def child_frames(self) -> typing.List["Frame"]:
        """Frame.child_frames

        Returns
        -------
        List[Frame]
        """
        return mapping.from_impl_list(self._impl_obj.child_frames)

    async def goto(
        self,
        url: str,
        *,
        timeout: typing.Optional[float] = None,
        wait_until: typing.Optional[
            Literal["commit", "domcontentloaded", "load", "networkidle"]
        ] = None,
        referer: typing.Optional[str] = None,
    ) -> typing.Optional["Response"]:
        """Frame.goto

        Returns the main resource response. In case of multiple redirects, the navigation will resolve with the response of
        the last redirect.

        The method will throw an error if:
        - there's an SSL error (e.g. in case of self-signed certificates).
        - target URL is invalid.
        - the `timeout` is exceeded during navigation.
        - the remote server does not respond or is unreachable.
        - the main resource failed to load.

        The method will not throw an error when any valid HTTP status code is returned by the remote server, including 404
        \"Not Found\" and 500 \"Internal Server Error\".  The status code for such responses can be retrieved by calling
        `response.status()`.

        **NOTE** The method either throws an error or returns a main resource response. The only exceptions are navigation
        to `about:blank` or navigation to the same URL with a different hash, which would succeed and return `null`.

        **NOTE** Headless mode doesn't support navigation to a PDF document. See the
        [upstream issue](https://bugs.chromium.org/p/chromium/issues/detail?id=761295).

        Parameters
        ----------
        url : str
            URL to navigate frame to. The url should include scheme, e.g. `https://`.
        timeout : Union[float, None]
            Maximum operation time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_navigation_timeout()`,
            `browser_context.set_default_timeout()`, `page.set_default_navigation_timeout()` or
            `page.set_default_timeout()` methods.
        wait_until : Union["commit", "domcontentloaded", "load", "networkidle", None]
            When to consider operation succeeded, defaults to `load`. Events can be either:
            - `'domcontentloaded'` - consider operation to be finished when the `DOMContentLoaded` event is fired.
            - `'load'` - consider operation to be finished when the `load` event is fired.
            - `'networkidle'` - **DISCOURAGED** consider operation to be finished when there are no network connections for
              at least `500` ms. Don't use this method for testing, rely on web assertions to assess readiness instead.
            - `'commit'` - consider operation to be finished when network response is received and the document started
              loading.
        referer : Union[str, None]
            Referer header value. If provided it will take preference over the referer header value set by
            `page.set_extra_http_headers()`.

        Returns
        -------
        Union[Response, None]
        """

        return mapping.from_impl_nullable(
            await self._impl_obj.goto(
                url=url, timeout=timeout, waitUntil=wait_until, referer=referer
            )
        )

    def expect_navigation(
        self,
        *,
        url: typing.Optional[
            typing.Union[str, typing.Pattern[str], typing.Callable[[str], bool]]
        ] = None,
        wait_until: typing.Optional[
            Literal["commit", "domcontentloaded", "load", "networkidle"]
        ] = None,
        timeout: typing.Optional[float] = None,
    ) -> AsyncEventContextManager["Response"]:
        """Frame.expect_navigation

        Waits for the frame navigation and returns the main resource response. In case of multiple redirects, the
        navigation will resolve with the response of the last redirect. In case of navigation to a different anchor or
        navigation due to History API usage, the navigation will resolve with `null`.

        **Usage**

        This method waits for the frame to navigate to a new URL. It is useful for when you run code which will indirectly
        cause the frame to navigate. Consider this example:

        ```py
        async with frame.expect_navigation():
            await frame.click(\"a.delayed-navigation\") # clicking the link will indirectly cause a navigation
        # Resolves after navigation has finished
        ```

        **NOTE** Usage of the [History API](https://developer.mozilla.org/en-US/docs/Web/API/History_API) to change the URL
        is considered a navigation.

        Parameters
        ----------
        url : Union[Callable[[str], bool], Pattern[str], str, None]
            A glob pattern, regex pattern or predicate receiving [URL] to match while waiting for the navigation. Note that if
            the parameter is a string without wildcard characters, the method will wait for navigation to URL that is exactly
            equal to the string.
        wait_until : Union["commit", "domcontentloaded", "load", "networkidle", None]
            When to consider operation succeeded, defaults to `load`. Events can be either:
            - `'domcontentloaded'` - consider operation to be finished when the `DOMContentLoaded` event is fired.
            - `'load'` - consider operation to be finished when the `load` event is fired.
            - `'networkidle'` - **DISCOURAGED** consider operation to be finished when there are no network connections for
              at least `500` ms. Don't use this method for testing, rely on web assertions to assess readiness instead.
            - `'commit'` - consider operation to be finished when network response is received and the document started
              loading.
        timeout : Union[float, None]
            Maximum operation time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_navigation_timeout()`,
            `browser_context.set_default_timeout()`, `page.set_default_navigation_timeout()` or
            `page.set_default_timeout()` methods.

        Returns
        -------
        EventContextManager[Response]
        """

        return AsyncEventContextManager(
            self._impl_obj.expect_navigation(
                url=self._wrap_handler(url), waitUntil=wait_until, timeout=timeout
            ).future
        )

    async def wait_for_url(
        self,
        url: typing.Union[str, typing.Pattern[str], typing.Callable[[str], bool]],
        *,
        wait_until: typing.Optional[
            Literal["commit", "domcontentloaded", "load", "networkidle"]
        ] = None,
        timeout: typing.Optional[float] = None,
    ) -> None:
        """Frame.wait_for_url

        Waits for the frame to navigate to the given URL.

        **Usage**

        ```py
        await frame.click(\"a.delayed-navigation\") # clicking the link will indirectly cause a navigation
        await frame.wait_for_url(\"**/target.html\")
        ```

        Parameters
        ----------
        url : Union[Callable[[str], bool], Pattern[str], str]
            A glob pattern, regex pattern or predicate receiving [URL] to match while waiting for the navigation. Note that if
            the parameter is a string without wildcard characters, the method will wait for navigation to URL that is exactly
            equal to the string.
        wait_until : Union["commit", "domcontentloaded", "load", "networkidle", None]
            When to consider operation succeeded, defaults to `load`. Events can be either:
            - `'domcontentloaded'` - consider operation to be finished when the `DOMContentLoaded` event is fired.
            - `'load'` - consider operation to be finished when the `load` event is fired.
            - `'networkidle'` - **DISCOURAGED** consider operation to be finished when there are no network connections for
              at least `500` ms. Don't use this method for testing, rely on web assertions to assess readiness instead.
            - `'commit'` - consider operation to be finished when network response is received and the document started
              loading.
        timeout : Union[float, None]
            Maximum operation time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_navigation_timeout()`,
            `browser_context.set_default_timeout()`, `page.set_default_navigation_timeout()` or
            `page.set_default_timeout()` methods.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.wait_for_url(
                url=self._wrap_handler(url), waitUntil=wait_until, timeout=timeout
            )
        )

    async def wait_for_load_state(
        self,
        state: typing.Optional[
            Literal["domcontentloaded", "load", "networkidle"]
        ] = None,
        *,
        timeout: typing.Optional[float] = None,
    ) -> None:
        """Frame.wait_for_load_state

        Waits for the required load state to be reached.

        This returns when the frame reaches a required load state, `load` by default. The navigation must have been
        committed when this method is called. If current document has already reached the required state, resolves
        immediately.

        **NOTE** Most of the time, this method is not needed because Playwright
        [auto-waits before every action](https://playwright.dev/python/docs/actionability).

        **Usage**

        ```py
        await frame.click(\"button\") # click triggers navigation.
        await frame.wait_for_load_state() # the promise resolves after \"load\" event.
        ```

        Parameters
        ----------
        state : Union["domcontentloaded", "load", "networkidle", None]
            Optional load state to wait for, defaults to `load`. If the state has been already reached while loading current
            document, the method resolves immediately. Can be one of:
            - `'load'` - wait for the `load` event to be fired.
            - `'domcontentloaded'` - wait for the `DOMContentLoaded` event to be fired.
            - `'networkidle'` - **DISCOURAGED** wait until there are no network connections for at least `500` ms. Don't use
              this method for testing, rely on web assertions to assess readiness instead.
        timeout : Union[float, None]
            Maximum operation time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_navigation_timeout()`,
            `browser_context.set_default_timeout()`, `page.set_default_navigation_timeout()` or
            `page.set_default_timeout()` methods.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.wait_for_load_state(state=state, timeout=timeout)
        )

    async def frame_element(self) -> "ElementHandle":
        """Frame.frame_element

        Returns the `frame` or `iframe` element handle which corresponds to this frame.

        This is an inverse of `element_handle.content_frame()`. Note that returned handle actually belongs to the
        parent frame.

        This method throws an error if the frame has been detached before `frameElement()` returns.

        **Usage**

        ```py
        frame_element = await frame.frame_element()
        content_frame = await frame_element.content_frame()
        assert frame == content_frame
        ```

        Returns
        -------
        ElementHandle
        """

        return mapping.from_impl(await self._impl_obj.frame_element())

    async def evaluate(
        self, expression: str, arg: typing.Optional[typing.Any] = None
    ) -> typing.Any:
        """Frame.evaluate

        Returns the return value of `expression`.

        If the function passed to the `frame.evaluate()` returns a [Promise], then `frame.evaluate()` would
        wait for the promise to resolve and return its value.

        If the function passed to the `frame.evaluate()` returns a non-[Serializable] value, then
        `frame.evaluate()` returns `undefined`. Playwright also supports transferring some additional values that
        are not serializable by `JSON`: `-0`, `NaN`, `Infinity`, `-Infinity`.

        **Usage**

        ```py
        result = await frame.evaluate(\"([x, y]) => Promise.resolve(x * y)\", [7, 8])
        print(result) # prints \"56\"
        ```

        A string can also be passed in instead of a function.

        ```py
        print(await frame.evaluate(\"1 + 2\")) # prints \"3\"
        x = 10
        print(await frame.evaluate(f\"1 + {x}\")) # prints \"11\"
        ```

        `ElementHandle` instances can be passed as an argument to the `frame.evaluate()`:

        ```py
        body_handle = await frame.evaluate(\"document.body\")
        html = await frame.evaluate(\"([body, suffix]) => body.innerHTML + suffix\", [body_handle, \"hello\"])
        await body_handle.dispose()
        ```

        Parameters
        ----------
        expression : str
            JavaScript expression to be evaluated in the browser context. If the expression evaluates to a function, the
            function is automatically invoked.
        arg : Union[Any, None]
            Optional argument to pass to `expression`.

        Returns
        -------
        Any
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.evaluate(
                expression=expression, arg=mapping.to_impl(arg)
            )
        )

    async def evaluate_handle(
        self, expression: str, arg: typing.Optional[typing.Any] = None
    ) -> "JSHandle":
        """Frame.evaluate_handle

        Returns the return value of `expression` as a `JSHandle`.

        The only difference between `frame.evaluate()` and `frame.evaluate_handle()` is that
        `frame.evaluate_handle()` returns `JSHandle`.

        If the function, passed to the `frame.evaluate_handle()`, returns a [Promise], then
        `frame.evaluate_handle()` would wait for the promise to resolve and return its value.

        **Usage**

        ```py
        a_window_handle = await frame.evaluate_handle(\"Promise.resolve(window)\")
        a_window_handle # handle for the window object.
        ```

        A string can also be passed in instead of a function.

        ```py
        a_handle = await page.evaluate_handle(\"document\") # handle for the \"document\"
        ```

        `JSHandle` instances can be passed as an argument to the `frame.evaluate_handle()`:

        ```py
        a_handle = await page.evaluate_handle(\"document.body\")
        result_handle = await page.evaluate_handle(\"body => body.innerHTML\", a_handle)
        print(await result_handle.json_value())
        await result_handle.dispose()
        ```

        Parameters
        ----------
        expression : str
            JavaScript expression to be evaluated in the browser context. If the expression evaluates to a function, the
            function is automatically invoked.
        arg : Union[Any, None]
            Optional argument to pass to `expression`.

        Returns
        -------
        JSHandle
        """

        return mapping.from_impl(
            await self._impl_obj.evaluate_handle(
                expression=expression, arg=mapping.to_impl(arg)
            )
        )

    async def query_selector(
        self, selector: str, *, strict: typing.Optional[bool] = None
    ) -> typing.Optional["ElementHandle"]:
        """Frame.query_selector

        Returns the ElementHandle pointing to the frame element.

        **NOTE** The use of `ElementHandle` is discouraged, use `Locator` objects and web-first assertions instead.

        The method finds an element matching the specified selector within the frame. If no elements match the selector,
        returns `null`.

        Parameters
        ----------
        selector : str
            A selector to query for.
        strict : Union[bool, None]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more than one
            element, the call throws an exception.

        Returns
        -------
        Union[ElementHandle, None]
        """

        return mapping.from_impl_nullable(
            await self._impl_obj.query_selector(selector=selector, strict=strict)
        )

    async def query_selector_all(self, selector: str) -> typing.List["ElementHandle"]:
        """Frame.query_selector_all

        Returns the ElementHandles pointing to the frame elements.

        **NOTE** The use of `ElementHandle` is discouraged, use `Locator` objects instead.

        The method finds all elements matching the specified selector within the frame. If no elements match the selector,
        returns empty array.

        Parameters
        ----------
        selector : str
            A selector to query for.

        Returns
        -------
        List[ElementHandle]
        """

        return mapping.from_impl_list(
            await self._impl_obj.query_selector_all(selector=selector)
        )

    async def wait_for_selector(
        self,
        selector: str,
        *,
        strict: typing.Optional[bool] = None,
        timeout: typing.Optional[float] = None,
        state: typing.Optional[
            Literal["attached", "detached", "hidden", "visible"]
        ] = None,
    ) -> typing.Optional["ElementHandle"]:
        """Frame.wait_for_selector

        Returns when element specified by selector satisfies `state` option. Returns `null` if waiting for `hidden` or
        `detached`.

        **NOTE** Playwright automatically waits for element to be ready before performing an action. Using `Locator`
        objects and web-first assertions make the code wait-for-selector-free.

        Wait for the `selector` to satisfy `state` option (either appear/disappear from dom, or become visible/hidden). If
        at the moment of calling the method `selector` already satisfies the condition, the method will return immediately.
        If the selector doesn't satisfy the condition for the `timeout` milliseconds, the function will throw.

        **Usage**

        This method works across navigations:

        ```py
        import asyncio
        from playwright.async_api import async_playwright, Playwright

        async def run(playwright: Playwright):
            chromium = playwright.chromium
            browser = await chromium.launch()
            page = await browser.new_page()
            for current_url in [\"https://google.com\", \"https://bbc.com\"]:
                await page.goto(current_url, wait_until=\"domcontentloaded\")
                element = await page.main_frame.wait_for_selector(\"img\")
                print(\"Loaded image: \" + str(await element.get_attribute(\"src\")))
            await browser.close()

        async def main():
            async with async_playwright() as playwright:
                await run(playwright)
        asyncio.run(main())
        ```

        Parameters
        ----------
        selector : str
            A selector to query for.
        strict : Union[bool, None]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more than one
            element, the call throws an exception.
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        state : Union["attached", "detached", "hidden", "visible", None]
            Defaults to `'visible'`. Can be either:
            - `'attached'` - wait for element to be present in DOM.
            - `'detached'` - wait for element to not be present in DOM.
            - `'visible'` - wait for element to have non-empty bounding box and no `visibility:hidden`. Note that element
              without any content or with `display:none` has an empty bounding box and is not considered visible.
            - `'hidden'` - wait for element to be either detached from DOM, or have an empty bounding box or
              `visibility:hidden`. This is opposite to the `'visible'` option.

        Returns
        -------
        Union[ElementHandle, None]
        """

        return mapping.from_impl_nullable(
            await self._impl_obj.wait_for_selector(
                selector=selector, strict=strict, timeout=timeout, state=state
            )
        )

    async def is_checked(
        self,
        selector: str,
        *,
        strict: typing.Optional[bool] = None,
        timeout: typing.Optional[float] = None,
    ) -> bool:
        """Frame.is_checked

        Returns whether the element is checked. Throws if the element is not a checkbox or radio input.

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be
            used.
        strict : Union[bool, None]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more than one
            element, the call throws an exception.
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.

        Returns
        -------
        bool
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.is_checked(
                selector=selector, strict=strict, timeout=timeout
            )
        )

    async def is_disabled(
        self,
        selector: str,
        *,
        strict: typing.Optional[bool] = None,
        timeout: typing.Optional[float] = None,
    ) -> bool:
        """Frame.is_disabled

        Returns whether the element is disabled, the opposite of [enabled](https://playwright.dev/python/docs/actionability#enabled).

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be
            used.
        strict : Union[bool, None]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more than one
            element, the call throws an exception.
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.

        Returns
        -------
        bool
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.is_disabled(
                selector=selector, strict=strict, timeout=timeout
            )
        )

    async def is_editable(
        self,
        selector: str,
        *,
        strict: typing.Optional[bool] = None,
        timeout: typing.Optional[float] = None,
    ) -> bool:
        """Frame.is_editable

        Returns whether the element is [editable](https://playwright.dev/python/docs/actionability#editable).

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be
            used.
        strict : Union[bool, None]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more than one
            element, the call throws an exception.
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.

        Returns
        -------
        bool
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.is_editable(
                selector=selector, strict=strict, timeout=timeout
            )
        )

    async def is_enabled(
        self,
        selector: str,
        *,
        strict: typing.Optional[bool] = None,
        timeout: typing.Optional[float] = None,
    ) -> bool:
        """Frame.is_enabled

        Returns whether the element is [enabled](https://playwright.dev/python/docs/actionability#enabled).

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be
            used.
        strict : Union[bool, None]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more than one
            element, the call throws an exception.
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.

        Returns
        -------
        bool
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.is_enabled(
                selector=selector, strict=strict, timeout=timeout
            )
        )

    async def is_hidden(
        self, selector: str, *, strict: typing.Optional[bool] = None
    ) -> bool:
        """Frame.is_hidden

        Returns whether the element is hidden, the opposite of [visible](https://playwright.dev/python/docs/actionability#visible).  `selector` that
        does not match any elements is considered hidden.

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be
            used.
        strict : Union[bool, None]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more than one
            element, the call throws an exception.

        Returns
        -------
        bool
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.is_hidden(selector=selector, strict=strict)
        )

    async def is_visible(
        self, selector: str, *, strict: typing.Optional[bool] = None
    ) -> bool:
        """Frame.is_visible

        Returns whether the element is [visible](https://playwright.dev/python/docs/actionability#visible). `selector` that does not match any elements
        is considered not visible.

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be
            used.
        strict : Union[bool, None]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more than one
            element, the call throws an exception.

        Returns
        -------
        bool
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.is_visible(selector=selector, strict=strict)
        )

    async def dispatch_event(
        self,
        selector: str,
        type: str,
        event_init: typing.Optional[typing.Dict] = None,
        *,
        strict: typing.Optional[bool] = None,
        timeout: typing.Optional[float] = None,
    ) -> None:
        """Frame.dispatch_event

        The snippet below dispatches the `click` event on the element. Regardless of the visibility state of the element,
        `click` is dispatched. This is equivalent to calling
        [element.click()](https://developer.mozilla.org/en-US/docs/Web/API/HTMLElement/click).

        **Usage**

        ```py
        await frame.dispatch_event(\"button#submit\", \"click\")
        ```

        Under the hood, it creates an instance of an event based on the given `type`, initializes it with `eventInit`
        properties and dispatches it on the element. Events are `composed`, `cancelable` and bubble by default.

        Since `eventInit` is event-specific, please refer to the events documentation for the lists of initial properties:
        - [DeviceMotionEvent](https://developer.mozilla.org/en-US/docs/Web/API/DeviceMotionEvent/DeviceMotionEvent)
        - [DeviceOrientationEvent](https://developer.mozilla.org/en-US/docs/Web/API/DeviceOrientationEvent/DeviceOrientationEvent)
        - [DragEvent](https://developer.mozilla.org/en-US/docs/Web/API/DragEvent/DragEvent)
        - [Event](https://developer.mozilla.org/en-US/docs/Web/API/Event/Event)
        - [FocusEvent](https://developer.mozilla.org/en-US/docs/Web/API/FocusEvent/FocusEvent)
        - [KeyboardEvent](https://developer.mozilla.org/en-US/docs/Web/API/KeyboardEvent/KeyboardEvent)
        - [MouseEvent](https://developer.mozilla.org/en-US/docs/Web/API/MouseEvent/MouseEvent)
        - [PointerEvent](https://developer.mozilla.org/en-US/docs/Web/API/PointerEvent/PointerEvent)
        - [TouchEvent](https://developer.mozilla.org/en-US/docs/Web/API/TouchEvent/TouchEvent)
        - [WheelEvent](https://developer.mozilla.org/en-US/docs/Web/API/WheelEvent/WheelEvent)

        You can also specify `JSHandle` as the property value if you want live objects to be passed into the event:

        ```py
        # note you can only create data_transfer in chromium and firefox
        data_transfer = await frame.evaluate_handle(\"new DataTransfer()\")
        await frame.dispatch_event(\"#source\", \"dragstart\", { \"dataTransfer\": data_transfer })
        ```

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be
            used.
        type : str
            DOM event type: `"click"`, `"dragstart"`, etc.
        event_init : Union[Dict, None]
            Optional event-specific initialization properties.
        strict : Union[bool, None]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more than one
            element, the call throws an exception.
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.dispatch_event(
                selector=selector,
                type=type,
                eventInit=mapping.to_impl(event_init),
                strict=strict,
                timeout=timeout,
            )
        )

    async def eval_on_selector(
        self,
        selector: str,
        expression: str,
        arg: typing.Optional[typing.Any] = None,
        *,
        strict: typing.Optional[bool] = None,
    ) -> typing.Any:
        """Frame.eval_on_selector

        Returns the return value of `expression`.

        The method finds an element matching the specified selector within the frame and passes it as a first argument to
        `expression`. If no elements match the selector, the method throws an error.

        If `expression` returns a [Promise], then `frame.eval_on_selector()` would wait for the promise to resolve
        and return its value.

        **Usage**

        ```py
        search_value = await frame.eval_on_selector(\"#search\", \"el => el.value\")
        preload_href = await frame.eval_on_selector(\"link[rel=preload]\", \"el => el.href\")
        html = await frame.eval_on_selector(\".main-container\", \"(e, suffix) => e.outerHTML + suffix\", \"hello\")
        ```

        Parameters
        ----------
        selector : str
            A selector to query for.
        expression : str
            JavaScript expression to be evaluated in the browser context. If the expression evaluates to a function, the
            function is automatically invoked.
        arg : Union[Any, None]
            Optional argument to pass to `expression`.
        strict : Union[bool, None]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more than one
            element, the call throws an exception.

        Returns
        -------
        Any
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.eval_on_selector(
                selector=selector,
                expression=expression,
                arg=mapping.to_impl(arg),
                strict=strict,
            )
        )

    async def eval_on_selector_all(
        self, selector: str, expression: str, arg: typing.Optional[typing.Any] = None
    ) -> typing.Any:
        """Frame.eval_on_selector_all

        Returns the return value of `expression`.

        The method finds all elements matching the specified selector within the frame and passes an array of matched
        elements as a first argument to `expression`.

        If `expression` returns a [Promise], then `frame.eval_on_selector_all()` would wait for the promise to resolve
        and return its value.

        **Usage**

        ```py
        divs_counts = await frame.eval_on_selector_all(\"div\", \"(divs, min) => divs.length >= min\", 10)
        ```

        Parameters
        ----------
        selector : str
            A selector to query for.
        expression : str
            JavaScript expression to be evaluated in the browser context. If the expression evaluates to a function, the
            function is automatically invoked.
        arg : Union[Any, None]
            Optional argument to pass to `expression`.

        Returns
        -------
        Any
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.eval_on_selector_all(
                selector=selector, expression=expression, arg=mapping.to_impl(arg)
            )
        )

    async def content(self) -> str:
        """Frame.content

        Gets the full HTML contents of the frame, including the doctype.

        Returns
        -------
        str
        """

        return mapping.from_maybe_impl(await self._impl_obj.content())

    async def set_content(
        self,
        html: str,
        *,
        timeout: typing.Optional[float] = None,
        wait_until: typing.Optional[
            Literal["commit", "domcontentloaded", "load", "networkidle"]
        ] = None,
    ) -> None:
        """Frame.set_content

        This method internally calls [document.write()](https://developer.mozilla.org/en-US/docs/Web/API/Document/write),
        inheriting all its specific characteristics and behaviors.

        Parameters
        ----------
        html : str
            HTML markup to assign to the page.
        timeout : Union[float, None]
            Maximum operation time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_navigation_timeout()`,
            `browser_context.set_default_timeout()`, `page.set_default_navigation_timeout()` or
            `page.set_default_timeout()` methods.
        wait_until : Union["commit", "domcontentloaded", "load", "networkidle", None]
            When to consider operation succeeded, defaults to `load`. Events can be either:
            - `'domcontentloaded'` - consider operation to be finished when the `DOMContentLoaded` event is fired.
            - `'load'` - consider operation to be finished when the `load` event is fired.
            - `'networkidle'` - **DISCOURAGED** consider operation to be finished when there are no network connections for
              at least `500` ms. Don't use this method for testing, rely on web assertions to assess readiness instead.
            - `'commit'` - consider operation to be finished when network response is received and the document started
              loading.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.set_content(
                html=html, timeout=timeout, waitUntil=wait_until
            )
        )

    def is_detached(self) -> bool:
        """Frame.is_detached

        Returns `true` if the frame has been detached, or `false` otherwise.

        Returns
        -------
        bool
        """

        return mapping.from_maybe_impl(self._impl_obj.is_detached())

    async def add_script_tag(
        self,
        *,
        url: typing.Optional[str] = None,
        path: typing.Optional[typing.Union[pathlib.Path, str]] = None,
        content: typing.Optional[str] = None,
        type: typing.Optional[str] = None,
    ) -> "ElementHandle":
        """Frame.add_script_tag

        Returns the added tag when the script's onload fires or when the script content was injected into frame.

        Adds a `<script>` tag into the page with the desired url or content.

        Parameters
        ----------
        url : Union[str, None]
            URL of a script to be added.
        path : Union[pathlib.Path, str, None]
            Path to the JavaScript file to be injected into frame. If `path` is a relative path, then it is resolved relative
            to the current working directory.
        content : Union[str, None]
            Raw JavaScript content to be injected into frame.
        type : Union[str, None]
            Script type. Use 'module' in order to load a JavaScript ES6 module. See
            [script](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/script) for more details.

        Returns
        -------
        ElementHandle
        """

        return mapping.from_impl(
            await self._impl_obj.add_script_tag(
                url=url, path=path, content=content, type=type
            )
        )

    async def add_style_tag(
        self,
        *,
        url: typing.Optional[str] = None,
        path: typing.Optional[typing.Union[pathlib.Path, str]] = None,
        content: typing.Optional[str] = None,
    ) -> "ElementHandle":
        """Frame.add_style_tag

        Returns the added tag when the stylesheet's onload fires or when the CSS content was injected into frame.

        Adds a `<link rel=\"stylesheet\">` tag into the page with the desired url or a `<style type=\"text/css\">` tag with the
        content.

        Parameters
        ----------
        url : Union[str, None]
            URL of the `<link>` tag.
        path : Union[pathlib.Path, str, None]
            Path to the CSS file to be injected into frame. If `path` is a relative path, then it is resolved relative to the
            current working directory.
        content : Union[str, None]
            Raw CSS content to be injected into frame.

        Returns
        -------
        ElementHandle
        """

        return mapping.from_impl(
            await self._impl_obj.add_style_tag(url=url, path=path, content=content)
        )

    async def click(
        self,
        selector: str,
        *,
        modifiers: typing.Optional[
            typing.Sequence[Literal["Alt", "Control", "ControlOrMeta", "Meta", "Shift"]]
        ] = None,
        position: typing.Optional[Position] = None,
        delay: typing.Optional[float] = None,
        button: typing.Optional[Literal["left", "middle", "right"]] = None,
        click_count: typing.Optional[int] = None,
        timeout: typing.Optional[float] = None,
        force: typing.Optional[bool] = None,
        no_wait_after: typing.Optional[bool] = None,
        strict: typing.Optional[bool] = None,
        trial: typing.Optional[bool] = None,
    ) -> None:
        """Frame.click

        This method clicks an element matching `selector` by performing the following steps:
        1. Find an element matching `selector`. If there is none, wait until a matching element is attached to the DOM.
        1. Wait for [actionability](https://playwright.dev/python/docs/actionability) checks on the matched element, unless `force` option is set. If
           the element is detached during the checks, the whole action is retried.
        1. Scroll the element into view if needed.
        1. Use `page.mouse` to click in the center of the element, or the specified `position`.
        1. Wait for initiated navigations to either succeed or fail, unless `noWaitAfter` option is set.

        When all steps combined have not finished during the specified `timeout`, this method throws a `TimeoutError`.
        Passing zero timeout disables this.

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be
            used.
        modifiers : Union[Sequence[Union["Alt", "Control", "ControlOrMeta", "Meta", "Shift"]], None]
            Modifier keys to press. Ensures that only these modifiers are pressed during the operation, and then restores
            current modifiers back. If not specified, currently pressed modifiers are used. "ControlOrMeta" resolves to
            "Control" on Windows and Linux and to "Meta" on macOS.
        position : Union[{x: float, y: float}, None]
            A point to use relative to the top-left corner of element padding box. If not specified, uses some visible point of
            the element.
        delay : Union[float, None]
            Time to wait between `mousedown` and `mouseup` in milliseconds. Defaults to 0.
        button : Union["left", "middle", "right", None]
            Defaults to `left`.
        click_count : Union[int, None]
            defaults to 1. See [UIEvent.detail].
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        force : Union[bool, None]
            Whether to bypass the [actionability](../actionability.md) checks. Defaults to `false`.
        no_wait_after : Union[bool, None]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You
            can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as
            navigating to inaccessible pages. Defaults to `false`.
            Deprecated: This option will default to `true` in the future.
        strict : Union[bool, None]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more than one
            element, the call throws an exception.
        trial : Union[bool, None]
            When set, this method only performs the [actionability](../actionability.md) checks and skips the action. Defaults
            to `false`. Useful to wait until the element is ready for the action without performing it. Note that keyboard
            `modifiers` will be pressed regardless of `trial` to allow testing elements which are only visible when those keys
            are pressed.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.click(
                selector=selector,
                modifiers=mapping.to_impl(modifiers),
                position=position,
                delay=delay,
                button=button,
                clickCount=click_count,
                timeout=timeout,
                force=force,
                noWaitAfter=no_wait_after,
                strict=strict,
                trial=trial,
            )
        )

    async def dblclick(
        self,
        selector: str,
        *,
        modifiers: typing.Optional[
            typing.Sequence[Literal["Alt", "Control", "ControlOrMeta", "Meta", "Shift"]]
        ] = None,
        position: typing.Optional[Position] = None,
        delay: typing.Optional[float] = None,
        button: typing.Optional[Literal["left", "middle", "right"]] = None,
        timeout: typing.Optional[float] = None,
        force: typing.Optional[bool] = None,
        no_wait_after: typing.Optional[bool] = None,
        strict: typing.Optional[bool] = None,
        trial: typing.Optional[bool] = None,
    ) -> None:
        """Frame.dblclick

        This method double clicks an element matching `selector` by performing the following steps:
        1. Find an element matching `selector`. If there is none, wait until a matching element is attached to the DOM.
        1. Wait for [actionability](https://playwright.dev/python/docs/actionability) checks on the matched element, unless `force` option is set. If
           the element is detached during the checks, the whole action is retried.
        1. Scroll the element into view if needed.
        1. Use `page.mouse` to double click in the center of the element, or the specified `position`. if
           the first click of the `dblclick()` triggers a navigation event, this method will throw.

        When all steps combined have not finished during the specified `timeout`, this method throws a `TimeoutError`.
        Passing zero timeout disables this.

        **NOTE** `frame.dblclick()` dispatches two `click` events and a single `dblclick` event.

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be
            used.
        modifiers : Union[Sequence[Union["Alt", "Control", "ControlOrMeta", "Meta", "Shift"]], None]
            Modifier keys to press. Ensures that only these modifiers are pressed during the operation, and then restores
            current modifiers back. If not specified, currently pressed modifiers are used. "ControlOrMeta" resolves to
            "Control" on Windows and Linux and to "Meta" on macOS.
        position : Union[{x: float, y: float}, None]
            A point to use relative to the top-left corner of element padding box. If not specified, uses some visible point of
            the element.
        delay : Union[float, None]
            Time to wait between `mousedown` and `mouseup` in milliseconds. Defaults to 0.
        button : Union["left", "middle", "right", None]
            Defaults to `left`.
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        force : Union[bool, None]
            Whether to bypass the [actionability](../actionability.md) checks. Defaults to `false`.
        no_wait_after : Union[bool, None]
            This option has no effect.
            Deprecated: This option has no effect.
        strict : Union[bool, None]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more than one
            element, the call throws an exception.
        trial : Union[bool, None]
            When set, this method only performs the [actionability](../actionability.md) checks and skips the action. Defaults
            to `false`. Useful to wait until the element is ready for the action without performing it. Note that keyboard
            `modifiers` will be pressed regardless of `trial` to allow testing elements which are only visible when those keys
            are pressed.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.dblclick(
                selector=selector,
                modifiers=mapping.to_impl(modifiers),
                position=position,
                delay=delay,
                button=button,
                timeout=timeout,
                force=force,
                noWaitAfter=no_wait_after,
                strict=strict,
                trial=trial,
            )
        )

    async def tap(
        self,
        selector: str,
        *,
        modifiers: typing.Optional[
            typing.Sequence[Literal["Alt", "Control", "ControlOrMeta", "Meta", "Shift"]]
        ] = None,
        position: typing.Optional[Position] = None,
        timeout: typing.Optional[float] = None,
        force: typing.Optional[bool] = None,
        no_wait_after: typing.Optional[bool] = None,
        strict: typing.Optional[bool] = None,
        trial: typing.Optional[bool] = None,
    ) -> None:
        """Frame.tap

        This method taps an element matching `selector` by performing the following steps:
        1. Find an element matching `selector`. If there is none, wait until a matching element is attached to the DOM.
        1. Wait for [actionability](https://playwright.dev/python/docs/actionability) checks on the matched element, unless `force` option is set. If
           the element is detached during the checks, the whole action is retried.
        1. Scroll the element into view if needed.
        1. Use `page.touchscreen` to tap the center of the element, or the specified `position`.

        When all steps combined have not finished during the specified `timeout`, this method throws a `TimeoutError`.
        Passing zero timeout disables this.

        **NOTE** `frame.tap()` requires that the `hasTouch` option of the browser context be set to true.

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be
            used.
        modifiers : Union[Sequence[Union["Alt", "Control", "ControlOrMeta", "Meta", "Shift"]], None]
            Modifier keys to press. Ensures that only these modifiers are pressed during the operation, and then restores
            current modifiers back. If not specified, currently pressed modifiers are used. "ControlOrMeta" resolves to
            "Control" on Windows and Linux and to "Meta" on macOS.
        position : Union[{x: float, y: float}, None]
            A point to use relative to the top-left corner of element padding box. If not specified, uses some visible point of
            the element.
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        force : Union[bool, None]
            Whether to bypass the [actionability](../actionability.md) checks. Defaults to `false`.
        no_wait_after : Union[bool, None]
            This option has no effect.
            Deprecated: This option has no effect.
        strict : Union[bool, None]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more than one
            element, the call throws an exception.
        trial : Union[bool, None]
            When set, this method only performs the [actionability](../actionability.md) checks and skips the action. Defaults
            to `false`. Useful to wait until the element is ready for the action without performing it. Note that keyboard
            `modifiers` will be pressed regardless of `trial` to allow testing elements which are only visible when those keys
            are pressed.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.tap(
                selector=selector,
                modifiers=mapping.to_impl(modifiers),
                position=position,
                timeout=timeout,
                force=force,
                noWaitAfter=no_wait_after,
                strict=strict,
                trial=trial,
            )
        )

    async def fill(
        self,
        selector: str,
        value: str,
        *,
        timeout: typing.Optional[float] = None,
        no_wait_after: typing.Optional[bool] = None,
        strict: typing.Optional[bool] = None,
        force: typing.Optional[bool] = None,
    ) -> None:
        """Frame.fill

        This method waits for an element matching `selector`, waits for [actionability](https://playwright.dev/python/docs/actionability) checks,
        focuses the element, fills it and triggers an `input` event after filling. Note that you can pass an empty string
        to clear the input field.

        If the target element is not an `<input>`, `<textarea>` or `[contenteditable]` element, this method throws an
        error. However, if the element is inside the `<label>` element that has an associated
        [control](https://developer.mozilla.org/en-US/docs/Web/API/HTMLLabelElement/control), the control will be filled
        instead.

        To send fine-grained keyboard events, use `locator.press_sequentially()`.

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be
            used.
        value : str
            Value to fill for the `<input>`, `<textarea>` or `[contenteditable]` element.
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        no_wait_after : Union[bool, None]
            This option has no effect.
            Deprecated: This option has no effect.
        strict : Union[bool, None]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more than one
            element, the call throws an exception.
        force : Union[bool, None]
            Whether to bypass the [actionability](../actionability.md) checks. Defaults to `false`.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.fill(
                selector=selector,
                value=value,
                timeout=timeout,
                noWaitAfter=no_wait_after,
                strict=strict,
                force=force,
            )
        )

    def locator(
        self,
        selector: str,
        *,
        has_text: typing.Optional[typing.Union[typing.Pattern[str], str]] = None,
        has_not_text: typing.Optional[typing.Union[typing.Pattern[str], str]] = None,
        has: typing.Optional["Locator"] = None,
        has_not: typing.Optional["Locator"] = None,
    ) -> "Locator":
        """Frame.locator

        The method returns an element locator that can be used to perform actions on this page / frame. Locator is resolved
        to the element immediately before performing an action, so a series of actions on the same locator can in fact be
        performed on different DOM elements. That would happen if the DOM structure between those actions has changed.

        [Learn more about locators](https://playwright.dev/python/docs/locators).

        [Learn more about locators](https://playwright.dev/python/docs/locators).

        Parameters
        ----------
        selector : str
            A selector to use when resolving DOM element.
        has_text : Union[Pattern[str], str, None]
            Matches elements containing specified text somewhere inside, possibly in a child or a descendant element. When
            passed a [string], matching is case-insensitive and searches for a substring. For example, `"Playwright"` matches
            `<article><div>Playwright</div></article>`.
        has_not_text : Union[Pattern[str], str, None]
            Matches elements that do not contain specified text somewhere inside, possibly in a child or a descendant element.
            When passed a [string], matching is case-insensitive and searches for a substring.
        has : Union[Locator, None]
            Narrows down the results of the method to those which contain elements matching this relative locator. For example,
            `article` that has `text=Playwright` matches `<article><div>Playwright</div></article>`.

            Inner locator **must be relative** to the outer locator and is queried starting with the outer locator match, not
            the document root. For example, you can find `content` that has `div` in
            `<article><content><div>Playwright</div></content></article>`. However, looking for `content` that has `article
            div` will fail, because the inner locator must be relative and should not use any elements outside the `content`.

            Note that outer and inner locators must belong to the same frame. Inner locator must not contain `FrameLocator`s.
        has_not : Union[Locator, None]
            Matches elements that do not contain an element that matches an inner locator. Inner locator is queried against the
            outer one. For example, `article` that does not have `div` matches `<article><span>Playwright</span></article>`.

            Note that outer and inner locators must belong to the same frame. Inner locator must not contain `FrameLocator`s.

        Returns
        -------
        Locator
        """

        return mapping.from_impl(
            self._impl_obj.locator(
                selector=selector,
                hasText=has_text,
                hasNotText=has_not_text,
                has=has._impl_obj if has else None,
                hasNot=has_not._impl_obj if has_not else None,
            )
        )

    def get_by_alt_text(
        self,
        text: typing.Union[str, typing.Pattern[str]],
        *,
        exact: typing.Optional[bool] = None,
    ) -> "Locator":
        """Frame.get_by_alt_text

        Allows locating elements by their alt text.

        **Usage**

        For example, this method will find the image by alt text \"Playwright logo\":

        ```html
        <img alt='Playwright logo'>
        ```

        ```py
        await page.get_by_alt_text(\"Playwright logo\").click()
        ```

        Parameters
        ----------
        text : Union[Pattern[str], str]
            Text to locate the element for.
        exact : Union[bool, None]
            Whether to find an exact match: case-sensitive and whole-string. Default to false. Ignored when locating by a
            regular expression. Note that exact match still trims whitespace.

        Returns
        -------
        Locator
        """

        return mapping.from_impl(self._impl_obj.get_by_alt_text(text=text, exact=exact))

    def get_by_label(
        self,
        text: typing.Union[str, typing.Pattern[str]],
        *,
        exact: typing.Optional[bool] = None,
    ) -> "Locator":
        """Frame.get_by_label

        Allows locating input elements by the text of the associated `<label>` or `aria-labelledby` element, or by the
        `aria-label` attribute.

        **Usage**

        For example, this method will find inputs by label \"Username\" and \"Password\" in the following DOM:

        ```html
        <input aria-label=\"Username\">
        <label for=\"password-input\">Password:</label>
        <input id=\"password-input\">
        ```

        ```py
        await page.get_by_label(\"Username\").fill(\"john\")
        await page.get_by_label(\"Password\").fill(\"secret\")
        ```

        Parameters
        ----------
        text : Union[Pattern[str], str]
            Text to locate the element for.
        exact : Union[bool, None]
            Whether to find an exact match: case-sensitive and whole-string. Default to false. Ignored when locating by a
            regular expression. Note that exact match still trims whitespace.

        Returns
        -------
        Locator
        """

        return mapping.from_impl(self._impl_obj.get_by_label(text=text, exact=exact))

    def get_by_placeholder(
        self,
        text: typing.Union[str, typing.Pattern[str]],
        *,
        exact: typing.Optional[bool] = None,
    ) -> "Locator":
        """Frame.get_by_placeholder

        Allows locating input elements by the placeholder text.

        **Usage**

        For example, consider the following DOM structure.

        ```html
        <input type=\"email\" placeholder=\"name@example.com\" />
        ```

        You can fill the input after locating it by the placeholder text:

        ```py
        await page.get_by_placeholder(\"name@example.com\").fill(\"playwright@microsoft.com\")
        ```

        Parameters
        ----------
        text : Union[Pattern[str], str]
            Text to locate the element for.
        exact : Union[bool, None]
            Whether to find an exact match: case-sensitive and whole-string. Default to false. Ignored when locating by a
            regular expression. Note that exact match still trims whitespace.

        Returns
        -------
        Locator
        """

        return mapping.from_impl(
            self._impl_obj.get_by_placeholder(text=text, exact=exact)
        )

    def get_by_role(
        self,
        role: Literal[
            "alert",
            "alertdialog",
            "application",
            "article",
            "banner",
            "blockquote",
            "button",
            "caption",
            "cell",
            "checkbox",
            "code",
            "columnheader",
            "combobox",
            "complementary",
            "contentinfo",
            "definition",
            "deletion",
            "dialog",
            "directory",
            "document",
            "emphasis",
            "feed",
            "figure",
            "form",
            "generic",
            "grid",
            "gridcell",
            "group",
            "heading",
            "img",
            "insertion",
            "link",
            "list",
            "listbox",
            "listitem",
            "log",
            "main",
            "marquee",
            "math",
            "menu",
            "menubar",
            "menuitem",
            "menuitemcheckbox",
            "menuitemradio",
            "meter",
            "navigation",
            "none",
            "note",
            "option",
            "paragraph",
            "presentation",
            "progressbar",
            "radio",
            "radiogroup",
            "region",
            "row",
            "rowgroup",
            "rowheader",
            "scrollbar",
            "search",
            "searchbox",
            "separator",
            "slider",
            "spinbutton",
            "status",
            "strong",
            "subscript",
            "superscript",
            "switch",
            "tab",
            "table",
            "tablist",
            "tabpanel",
            "term",
            "textbox",
            "time",
            "timer",
            "toolbar",
            "tooltip",
            "tree",
            "treegrid",
            "treeitem",
        ],
        *,
        checked: typing.Optional[bool] = None,
        disabled: typing.Optional[bool] = None,
        expanded: typing.Optional[bool] = None,
        include_hidden: typing.Optional[bool] = None,
        level: typing.Optional[int] = None,
        name: typing.Optional[typing.Union[typing.Pattern[str], str]] = None,
        pressed: typing.Optional[bool] = None,
        selected: typing.Optional[bool] = None,
        exact: typing.Optional[bool] = None,
    ) -> "Locator":
        """Frame.get_by_role

        Allows locating elements by their [ARIA role](https://www.w3.org/TR/wai-aria-1.2/#roles),
        [ARIA attributes](https://www.w3.org/TR/wai-aria-1.2/#aria-attributes) and
        [accessible name](https://w3c.github.io/accname/#dfn-accessible-name).

        **Usage**

        Consider the following DOM structure.

        ```html
        <h3>Sign up</h3>
        <label>
          <input type=\"checkbox\" /> Subscribe
        </label>
        <br/>
        <button>Submit</button>
        ```

        You can locate each element by it's implicit role:

        ```py
        await expect(page.get_by_role(\"heading\", name=\"Sign up\")).to_be_visible()

        await page.get_by_role(\"checkbox\", name=\"Subscribe\").check()

        await page.get_by_role(\"button\", name=re.compile(\"submit\", re.IGNORECASE)).click()
        ```

        **Details**

        Role selector **does not replace** accessibility audits and conformance tests, but rather gives early feedback
        about the ARIA guidelines.

        Many html elements have an implicitly [defined role](https://w3c.github.io/html-aam/#html-element-role-mappings)
        that is recognized by the role selector. You can find all the
        [supported roles here](https://www.w3.org/TR/wai-aria-1.2/#role_definitions). ARIA guidelines **do not recommend**
        duplicating implicit roles and attributes by setting `role` and/or `aria-*` attributes to default values.

        Parameters
        ----------
        role : Union["alert", "alertdialog", "application", "article", "banner", "blockquote", "button", "caption", "cell", "checkbox", "code", "columnheader", "combobox", "complementary", "contentinfo", "definition", "deletion", "dialog", "directory", "document", "emphasis", "feed", "figure", "form", "generic", "grid", "gridcell", "group", "heading", "img", "insertion", "link", "list", "listbox", "listitem", "log", "main", "marquee", "math", "menu", "menubar", "menuitem", "menuitemcheckbox", "menuitemradio", "meter", "navigation", "none", "note", "option", "paragraph", "presentation", "progressbar", "radio", "radiogroup", "region", "row", "rowgroup", "rowheader", "scrollbar", "search", "searchbox", "separator", "slider", "spinbutton", "status", "strong", "subscript", "superscript", "switch", "tab", "table", "tablist", "tabpanel", "term", "textbox", "time", "timer", "toolbar", "tooltip", "tree", "treegrid", "treeitem"]
            Required aria role.
        checked : Union[bool, None]
            An attribute that is usually set by `aria-checked` or native `<input type=checkbox>` controls.

            Learn more about [`aria-checked`](https://www.w3.org/TR/wai-aria-1.2/#aria-checked).
        disabled : Union[bool, None]
            An attribute that is usually set by `aria-disabled` or `disabled`.

            **NOTE** Unlike most other attributes, `disabled` is inherited through the DOM hierarchy. Learn more about
            [`aria-disabled`](https://www.w3.org/TR/wai-aria-1.2/#aria-disabled).

        expanded : Union[bool, None]
            An attribute that is usually set by `aria-expanded`.

            Learn more about [`aria-expanded`](https://www.w3.org/TR/wai-aria-1.2/#aria-expanded).
        include_hidden : Union[bool, None]
            Option that controls whether hidden elements are matched. By default, only non-hidden elements, as
            [defined by ARIA](https://www.w3.org/TR/wai-aria-1.2/#tree_exclusion), are matched by role selector.

            Learn more about [`aria-hidden`](https://www.w3.org/TR/wai-aria-1.2/#aria-hidden).
        level : Union[int, None]
            A number attribute that is usually present for roles `heading`, `listitem`, `row`, `treeitem`, with default values
            for `<h1>-<h6>` elements.

            Learn more about [`aria-level`](https://www.w3.org/TR/wai-aria-1.2/#aria-level).
        name : Union[Pattern[str], str, None]
            Option to match the [accessible name](https://w3c.github.io/accname/#dfn-accessible-name). By default, matching is
            case-insensitive and searches for a substring, use `exact` to control this behavior.

            Learn more about [accessible name](https://w3c.github.io/accname/#dfn-accessible-name).
        pressed : Union[bool, None]
            An attribute that is usually set by `aria-pressed`.

            Learn more about [`aria-pressed`](https://www.w3.org/TR/wai-aria-1.2/#aria-pressed).
        selected : Union[bool, None]
            An attribute that is usually set by `aria-selected`.

            Learn more about [`aria-selected`](https://www.w3.org/TR/wai-aria-1.2/#aria-selected).
        exact : Union[bool, None]
            Whether `name` is matched exactly: case-sensitive and whole-string. Defaults to false. Ignored when `name` is a
            regular expression. Note that exact match still trims whitespace.

        Returns
        -------
        Locator
        """

        return mapping.from_impl(
            self._impl_obj.get_by_role(
                role=role,
                checked=checked,
                disabled=disabled,
                expanded=expanded,
                includeHidden=include_hidden,
                level=level,
                name=name,
                pressed=pressed,
                selected=selected,
                exact=exact,
            )
        )

    def get_by_test_id(
        self, test_id: typing.Union[str, typing.Pattern[str]]
    ) -> "Locator":
        """Frame.get_by_test_id

        Locate element by the test id.

        **Usage**

        Consider the following DOM structure.

        ```html
        <button data-testid=\"directions\">Itinéraire</button>
        ```

        You can locate the element by it's test id:

        ```py
        await page.get_by_test_id(\"directions\").click()
        ```

        **Details**

        By default, the `data-testid` attribute is used as a test id. Use `selectors.set_test_id_attribute()` to
        configure a different test id attribute if necessary.

        Parameters
        ----------
        test_id : Union[Pattern[str], str]
            Id to locate the element by.

        Returns
        -------
        Locator
        """

        return mapping.from_impl(self._impl_obj.get_by_test_id(testId=test_id))

    def get_by_text(
        self,
        text: typing.Union[str, typing.Pattern[str]],
        *,
        exact: typing.Optional[bool] = None,
    ) -> "Locator":
        """Frame.get_by_text

        Allows locating elements that contain given text.

        See also `locator.filter()` that allows to match by another criteria, like an accessible role, and then
        filter by the text content.

        **Usage**

        Consider the following DOM structure:

        ```html
        <div>Hello <span>world</span></div>
        <div>Hello</div>
        ```

        You can locate by text substring, exact string, or a regular expression:

        ```py
        # Matches <span>
        page.get_by_text(\"world\")

        # Matches first <div>
        page.get_by_text(\"Hello world\")

        # Matches second <div>
        page.get_by_text(\"Hello\", exact=True)

        # Matches both <div>s
        page.get_by_text(re.compile(\"Hello\"))

        # Matches second <div>
        page.get_by_text(re.compile(\"^hello$\", re.IGNORECASE))
        ```

        **Details**

        Matching by text always normalizes whitespace, even with exact match. For example, it turns multiple spaces into
        one, turns line breaks into spaces and ignores leading and trailing whitespace.

        Input elements of the type `button` and `submit` are matched by their `value` instead of the text content. For
        example, locating by text `\"Log in\"` matches `<input type=button value=\"Log in\">`.

        Parameters
        ----------
        text : Union[Pattern[str], str]
            Text to locate the element for.
        exact : Union[bool, None]
            Whether to find an exact match: case-sensitive and whole-string. Default to false. Ignored when locating by a
            regular expression. Note that exact match still trims whitespace.

        Returns
        -------
        Locator
        """

        return mapping.from_impl(self._impl_obj.get_by_text(text=text, exact=exact))

    def get_by_title(
        self,
        text: typing.Union[str, typing.Pattern[str]],
        *,
        exact: typing.Optional[bool] = None,
    ) -> "Locator":
        """Frame.get_by_title

        Allows locating elements by their title attribute.

        **Usage**

        Consider the following DOM structure.

        ```html
        <span title='Issues count'>25 issues</span>
        ```

        You can check the issues count after locating it by the title text:

        ```py
        await expect(page.get_by_title(\"Issues count\")).to_have_text(\"25 issues\")
        ```

        Parameters
        ----------
        text : Union[Pattern[str], str]
            Text to locate the element for.
        exact : Union[bool, None]
            Whether to find an exact match: case-sensitive and whole-string. Default to false. Ignored when locating by a
            regular expression. Note that exact match still trims whitespace.

        Returns
        -------
        Locator
        """

        return mapping.from_impl(self._impl_obj.get_by_title(text=text, exact=exact))

    def frame_locator(self, selector: str) -> "FrameLocator":
        """Frame.frame_locator

        When working with iframes, you can create a frame locator that will enter the iframe and allow selecting elements
        in that iframe.

        **Usage**

        Following snippet locates element with text \"Submit\" in the iframe with id `my-frame`, like `<iframe
        id=\"my-frame\">`:

        ```py
        locator = frame.frame_locator(\"#my-iframe\").get_by_text(\"Submit\")
        await locator.click()
        ```

        Parameters
        ----------
        selector : str
            A selector to use when resolving DOM element.

        Returns
        -------
        FrameLocator
        """

        return mapping.from_impl(self._impl_obj.frame_locator(selector=selector))

    async def focus(
        self,
        selector: str,
        *,
        strict: typing.Optional[bool] = None,
        timeout: typing.Optional[float] = None,
    ) -> None:
        """Frame.focus

        This method fetches an element with `selector` and focuses it. If there's no element matching `selector`, the
        method waits until a matching element appears in the DOM.

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be
            used.
        strict : Union[bool, None]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more than one
            element, the call throws an exception.
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.focus(
                selector=selector, strict=strict, timeout=timeout
            )
        )

    async def text_content(
        self,
        selector: str,
        *,
        strict: typing.Optional[bool] = None,
        timeout: typing.Optional[float] = None,
    ) -> typing.Optional[str]:
        """Frame.text_content

        Returns `element.textContent`.

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be
            used.
        strict : Union[bool, None]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more than one
            element, the call throws an exception.
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.

        Returns
        -------
        Union[str, None]
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.text_content(
                selector=selector, strict=strict, timeout=timeout
            )
        )

    async def inner_text(
        self,
        selector: str,
        *,
        strict: typing.Optional[bool] = None,
        timeout: typing.Optional[float] = None,
    ) -> str:
        """Frame.inner_text

        Returns `element.innerText`.

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be
            used.
        strict : Union[bool, None]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more than one
            element, the call throws an exception.
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.

        Returns
        -------
        str
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.inner_text(
                selector=selector, strict=strict, timeout=timeout
            )
        )

    async def inner_html(
        self,
        selector: str,
        *,
        strict: typing.Optional[bool] = None,
        timeout: typing.Optional[float] = None,
    ) -> str:
        """Frame.inner_html

        Returns `element.innerHTML`.

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be
            used.
        strict : Union[bool, None]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more than one
            element, the call throws an exception.
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.

        Returns
        -------
        str
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.inner_html(
                selector=selector, strict=strict, timeout=timeout
            )
        )

    async def get_attribute(
        self,
        selector: str,
        name: str,
        *,
        strict: typing.Optional[bool] = None,
        timeout: typing.Optional[float] = None,
    ) -> typing.Optional[str]:
        """Frame.get_attribute

        Returns element attribute value.

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be
            used.
        name : str
            Attribute name to get the value for.
        strict : Union[bool, None]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more than one
            element, the call throws an exception.
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.

        Returns
        -------
        Union[str, None]
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.get_attribute(
                selector=selector, name=name, strict=strict, timeout=timeout
            )
        )

    async def hover(
        self,
        selector: str,
        *,
        modifiers: typing.Optional[
            typing.Sequence[Literal["Alt", "Control", "ControlOrMeta", "Meta", "Shift"]]
        ] = None,
        position: typing.Optional[Position] = None,
        timeout: typing.Optional[float] = None,
        no_wait_after: typing.Optional[bool] = None,
        force: typing.Optional[bool] = None,
        strict: typing.Optional[bool] = None,
        trial: typing.Optional[bool] = None,
    ) -> None:
        """Frame.hover

        This method hovers over an element matching `selector` by performing the following steps:
        1. Find an element matching `selector`. If there is none, wait until a matching element is attached to the DOM.
        1. Wait for [actionability](https://playwright.dev/python/docs/actionability) checks on the matched element, unless `force` option is set. If
           the element is detached during the checks, the whole action is retried.
        1. Scroll the element into view if needed.
        1. Use `page.mouse` to hover over the center of the element, or the specified `position`.

        When all steps combined have not finished during the specified `timeout`, this method throws a `TimeoutError`.
        Passing zero timeout disables this.

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be
            used.
        modifiers : Union[Sequence[Union["Alt", "Control", "ControlOrMeta", "Meta", "Shift"]], None]
            Modifier keys to press. Ensures that only these modifiers are pressed during the operation, and then restores
            current modifiers back. If not specified, currently pressed modifiers are used. "ControlOrMeta" resolves to
            "Control" on Windows and Linux and to "Meta" on macOS.
        position : Union[{x: float, y: float}, None]
            A point to use relative to the top-left corner of element padding box. If not specified, uses some visible point of
            the element.
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        no_wait_after : Union[bool, None]
            This option has no effect.
            Deprecated: This option has no effect.
        force : Union[bool, None]
            Whether to bypass the [actionability](../actionability.md) checks. Defaults to `false`.
        strict : Union[bool, None]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more than one
            element, the call throws an exception.
        trial : Union[bool, None]
            When set, this method only performs the [actionability](../actionability.md) checks and skips the action. Defaults
            to `false`. Useful to wait until the element is ready for the action without performing it. Note that keyboard
            `modifiers` will be pressed regardless of `trial` to allow testing elements which are only visible when those keys
            are pressed.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.hover(
                selector=selector,
                modifiers=mapping.to_impl(modifiers),
                position=position,
                timeout=timeout,
                noWaitAfter=no_wait_after,
                force=force,
                strict=strict,
                trial=trial,
            )
        )

    async def drag_and_drop(
        self,
        source: str,
        target: str,
        *,
        source_position: typing.Optional[Position] = None,
        target_position: typing.Optional[Position] = None,
        force: typing.Optional[bool] = None,
        no_wait_after: typing.Optional[bool] = None,
        strict: typing.Optional[bool] = None,
        timeout: typing.Optional[float] = None,
        trial: typing.Optional[bool] = None,
        steps: typing.Optional[int] = None,
    ) -> None:
        """Frame.drag_and_drop

        Parameters
        ----------
        source : str
            A selector to search for an element to drag. If there are multiple elements satisfying the selector, the first will
            be used.
        target : str
            A selector to search for an element to drop onto. If there are multiple elements satisfying the selector, the first
            will be used.
        source_position : Union[{x: float, y: float}, None]
            Clicks on the source element at this point relative to the top-left corner of the element's padding box. If not
            specified, some visible point of the element is used.
        target_position : Union[{x: float, y: float}, None]
            Drops on the target element at this point relative to the top-left corner of the element's padding box. If not
            specified, some visible point of the element is used.
        force : Union[bool, None]
            Whether to bypass the [actionability](../actionability.md) checks. Defaults to `false`.
        no_wait_after : Union[bool, None]
            This option has no effect.
            Deprecated: This option has no effect.
        strict : Union[bool, None]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more than one
            element, the call throws an exception.
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        trial : Union[bool, None]
            When set, this method only performs the [actionability](../actionability.md) checks and skips the action. Defaults
            to `false`. Useful to wait until the element is ready for the action without performing it.
        steps : Union[int, None]
            Defaults to 1. Sends `n` interpolated `mousemove` events to represent travel between the `mousedown` and `mouseup`
            of the drag. When set to 1, emits a single `mousemove` event at the destination location.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.drag_and_drop(
                source=source,
                target=target,
                sourcePosition=source_position,
                targetPosition=target_position,
                force=force,
                noWaitAfter=no_wait_after,
                strict=strict,
                timeout=timeout,
                trial=trial,
                steps=steps,
            )
        )

    async def select_option(
        self,
        selector: str,
        value: typing.Optional[typing.Union[str, typing.Sequence[str]]] = None,
        *,
        index: typing.Optional[typing.Union[int, typing.Sequence[int]]] = None,
        label: typing.Optional[typing.Union[str, typing.Sequence[str]]] = None,
        element: typing.Optional[
            typing.Union["ElementHandle", typing.Sequence["ElementHandle"]]
        ] = None,
        timeout: typing.Optional[float] = None,
        no_wait_after: typing.Optional[bool] = None,
        strict: typing.Optional[bool] = None,
        force: typing.Optional[bool] = None,
    ) -> typing.List[str]:
        """Frame.select_option

        This method waits for an element matching `selector`, waits for [actionability](https://playwright.dev/python/docs/actionability) checks, waits
        until all specified options are present in the `<select>` element and selects these options.

        If the target element is not a `<select>` element, this method throws an error. However, if the element is inside
        the `<label>` element that has an associated
        [control](https://developer.mozilla.org/en-US/docs/Web/API/HTMLLabelElement/control), the control will be used
        instead.

        Returns the array of option values that have been successfully selected.

        Triggers a `change` and `input` event once all the provided options have been selected.

        **Usage**

        ```py
        # Single selection matching the value or label
        await frame.select_option(\"select#colors\", \"blue\")
        # single selection matching the label
        await frame.select_option(\"select#colors\", label=\"blue\")
        # multiple selection
        await frame.select_option(\"select#colors\", value=[\"red\", \"green\", \"blue\"])
        ```

        Parameters
        ----------
        selector : str
            A selector to query for.
        value : Union[Sequence[str], str, None]
            Options to select by value. If the `<select>` has the `multiple` attribute, all given options are selected,
            otherwise only the first option matching one of the passed options is selected. Optional.
        index : Union[Sequence[int], int, None]
            Options to select by index. Optional.
        label : Union[Sequence[str], str, None]
            Options to select by label. If the `<select>` has the `multiple` attribute, all given options are selected,
            otherwise only the first option matching one of the passed options is selected. Optional.
        element : Union[ElementHandle, Sequence[ElementHandle], None]
            Option elements to select. Optional.
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        no_wait_after : Union[bool, None]
            This option has no effect.
            Deprecated: This option has no effect.
        strict : Union[bool, None]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more than one
            element, the call throws an exception.
        force : Union[bool, None]
            Whether to bypass the [actionability](../actionability.md) checks. Defaults to `false`.

        Returns
        -------
        List[str]
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.select_option(
                selector=selector,
                value=mapping.to_impl(value),
                index=mapping.to_impl(index),
                label=mapping.to_impl(label),
                element=mapping.to_impl(element),
                timeout=timeout,
                noWaitAfter=no_wait_after,
                strict=strict,
                force=force,
            )
        )

    async def input_value(
        self,
        selector: str,
        *,
        strict: typing.Optional[bool] = None,
        timeout: typing.Optional[float] = None,
    ) -> str:
        """Frame.input_value

        Returns `input.value` for the selected `<input>` or `<textarea>` or `<select>` element.

        Throws for non-input elements. However, if the element is inside the `<label>` element that has an associated
        [control](https://developer.mozilla.org/en-US/docs/Web/API/HTMLLabelElement/control), returns the value of the
        control.

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be
            used.
        strict : Union[bool, None]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more than one
            element, the call throws an exception.
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.

        Returns
        -------
        str
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.input_value(
                selector=selector, strict=strict, timeout=timeout
            )
        )

    async def set_input_files(
        self,
        selector: str,
        files: typing.Union[
            str,
            pathlib.Path,
            FilePayload,
            typing.Sequence[typing.Union[str, pathlib.Path]],
            typing.Sequence[FilePayload],
        ],
        *,
        strict: typing.Optional[bool] = None,
        timeout: typing.Optional[float] = None,
        no_wait_after: typing.Optional[bool] = None,
    ) -> None:
        """Frame.set_input_files

        Sets the value of the file input to these file paths or files. If some of the `filePaths` are relative paths, then
        they are resolved relative to the current working directory. For empty array, clears the selected files.

        This method expects `selector` to point to an
        [input element](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/input). However, if the element is inside
        the `<label>` element that has an associated
        [control](https://developer.mozilla.org/en-US/docs/Web/API/HTMLLabelElement/control), targets the control instead.

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be
            used.
        files : Union[Sequence[Union[pathlib.Path, str]], Sequence[{name: str, mimeType: str, buffer: bytes}], pathlib.Path, str, {name: str, mimeType: str, buffer: bytes}]
        strict : Union[bool, None]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more than one
            element, the call throws an exception.
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        no_wait_after : Union[bool, None]
            This option has no effect.
            Deprecated: This option has no effect.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.set_input_files(
                selector=selector,
                files=mapping.to_impl(files),
                strict=strict,
                timeout=timeout,
                noWaitAfter=no_wait_after,
            )
        )

    async def type(
        self,
        selector: str,
        text: str,
        *,
        delay: typing.Optional[float] = None,
        strict: typing.Optional[bool] = None,
        timeout: typing.Optional[float] = None,
        no_wait_after: typing.Optional[bool] = None,
    ) -> None:
        """Frame.type

        Sends a `keydown`, `keypress`/`input`, and `keyup` event for each character in the text. `frame.type` can be used
        to send fine-grained keyboard events. To fill values in form fields, use `frame.fill()`.

        To press a special key, like `Control` or `ArrowDown`, use `keyboard.press()`.

        **Usage**

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be
            used.
        text : str
            A text to type into a focused element.
        delay : Union[float, None]
            Time to wait between key presses in milliseconds. Defaults to 0.
        strict : Union[bool, None]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more than one
            element, the call throws an exception.
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        no_wait_after : Union[bool, None]
            This option has no effect.
            Deprecated: This option has no effect.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.type(
                selector=selector,
                text=text,
                delay=delay,
                strict=strict,
                timeout=timeout,
                noWaitAfter=no_wait_after,
            )
        )

    async def press(
        self,
        selector: str,
        key: str,
        *,
        delay: typing.Optional[float] = None,
        strict: typing.Optional[bool] = None,
        timeout: typing.Optional[float] = None,
        no_wait_after: typing.Optional[bool] = None,
    ) -> None:
        """Frame.press

        `key` can specify the intended
        [keyboardEvent.key](https://developer.mozilla.org/en-US/docs/Web/API/KeyboardEvent/key) value or a single character
        to generate the text for. A superset of the `key` values can be found
        [here](https://developer.mozilla.org/en-US/docs/Web/API/KeyboardEvent/key/Key_Values). Examples of the keys are:

        `F1` - `F12`, `Digit0`- `Digit9`, `KeyA`- `KeyZ`, `Backquote`, `Minus`, `Equal`, `Backslash`, `Backspace`, `Tab`,
        `Delete`, `Escape`, `ArrowDown`, `End`, `Enter`, `Home`, `Insert`, `PageDown`, `PageUp`, `ArrowRight`, `ArrowUp`,
        etc.

        Following modification shortcuts are also supported: `Shift`, `Control`, `Alt`, `Meta`, `ShiftLeft`,
        `ControlOrMeta`. `ControlOrMeta` resolves to `Control` on Windows and Linux and to `Meta` on macOS.

        Holding down `Shift` will type the text that corresponds to the `key` in the upper case.

        If `key` is a single character, it is case-sensitive, so the values `a` and `A` will generate different respective
        texts.

        Shortcuts such as `key: \"Control+o\"`, `key: \"Control++` or `key: \"Control+Shift+T\"` are supported as well. When
        specified with the modifier, modifier is pressed and being held while the subsequent key is being pressed.

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be
            used.
        key : str
            Name of the key to press or a character to generate, such as `ArrowLeft` or `a`.
        delay : Union[float, None]
            Time to wait between `keydown` and `keyup` in milliseconds. Defaults to 0.
        strict : Union[bool, None]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more than one
            element, the call throws an exception.
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        no_wait_after : Union[bool, None]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You
            can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as
            navigating to inaccessible pages. Defaults to `false`.
            Deprecated: This option will default to `true` in the future.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.press(
                selector=selector,
                key=key,
                delay=delay,
                strict=strict,
                timeout=timeout,
                noWaitAfter=no_wait_after,
            )
        )

    async def check(
        self,
        selector: str,
        *,
        position: typing.Optional[Position] = None,
        timeout: typing.Optional[float] = None,
        force: typing.Optional[bool] = None,
        no_wait_after: typing.Optional[bool] = None,
        strict: typing.Optional[bool] = None,
        trial: typing.Optional[bool] = None,
    ) -> None:
        """Frame.check

        This method checks an element matching `selector` by performing the following steps:
        1. Find an element matching `selector`. If there is none, wait until a matching element is attached to the DOM.
        1. Ensure that matched element is a checkbox or a radio input. If not, this method throws. If the element is
           already checked, this method returns immediately.
        1. Wait for [actionability](https://playwright.dev/python/docs/actionability) checks on the matched element, unless `force` option is set. If
           the element is detached during the checks, the whole action is retried.
        1. Scroll the element into view if needed.
        1. Use `page.mouse` to click in the center of the element.
        1. Ensure that the element is now checked. If not, this method throws.

        When all steps combined have not finished during the specified `timeout`, this method throws a `TimeoutError`.
        Passing zero timeout disables this.

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be
            used.
        position : Union[{x: float, y: float}, None]
            A point to use relative to the top-left corner of element padding box. If not specified, uses some visible point of
            the element.
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        force : Union[bool, None]
            Whether to bypass the [actionability](../actionability.md) checks. Defaults to `false`.
        no_wait_after : Union[bool, None]
            This option has no effect.
            Deprecated: This option has no effect.
        strict : Union[bool, None]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more than one
            element, the call throws an exception.
        trial : Union[bool, None]
            When set, this method only performs the [actionability](../actionability.md) checks and skips the action. Defaults
            to `false`. Useful to wait until the element is ready for the action without performing it.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.check(
                selector=selector,
                position=position,
                timeout=timeout,
                force=force,
                noWaitAfter=no_wait_after,
                strict=strict,
                trial=trial,
            )
        )

    async def uncheck(
        self,
        selector: str,
        *,
        position: typing.Optional[Position] = None,
        timeout: typing.Optional[float] = None,
        force: typing.Optional[bool] = None,
        no_wait_after: typing.Optional[bool] = None,
        strict: typing.Optional[bool] = None,
        trial: typing.Optional[bool] = None,
    ) -> None:
        """Frame.uncheck

        This method checks an element matching `selector` by performing the following steps:
        1. Find an element matching `selector`. If there is none, wait until a matching element is attached to the DOM.
        1. Ensure that matched element is a checkbox or a radio input. If not, this method throws. If the element is
           already unchecked, this method returns immediately.
        1. Wait for [actionability](https://playwright.dev/python/docs/actionability) checks on the matched element, unless `force` option is set. If
           the element is detached during the checks, the whole action is retried.
        1. Scroll the element into view if needed.
        1. Use `page.mouse` to click in the center of the element.
        1. Ensure that the element is now unchecked. If not, this method throws.

        When all steps combined have not finished during the specified `timeout`, this method throws a `TimeoutError`.
        Passing zero timeout disables this.

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be
            used.
        position : Union[{x: float, y: float}, None]
            A point to use relative to the top-left corner of element padding box. If not specified, uses some visible point of
            the element.
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        force : Union[bool, None]
            Whether to bypass the [actionability](../actionability.md) checks. Defaults to `false`.
        no_wait_after : Union[bool, None]
            This option has no effect.
            Deprecated: This option has no effect.
        strict : Union[bool, None]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more than one
            element, the call throws an exception.
        trial : Union[bool, None]
            When set, this method only performs the [actionability](../actionability.md) checks and skips the action. Defaults
            to `false`. Useful to wait until the element is ready for the action without performing it.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.uncheck(
                selector=selector,
                position=position,
                timeout=timeout,
                force=force,
                noWaitAfter=no_wait_after,
                strict=strict,
                trial=trial,
            )
        )

    async def wait_for_timeout(self, timeout: float) -> None:
        """Frame.wait_for_timeout

        Waits for the given `timeout` in milliseconds.

        Note that `frame.waitForTimeout()` should only be used for debugging. Tests using the timer in production are going
        to be flaky. Use signals such as network events, selectors becoming visible and others instead.

        Parameters
        ----------
        timeout : float
            A timeout to wait for
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.wait_for_timeout(timeout=timeout)
        )

    async def wait_for_function(
        self,
        expression: str,
        *,
        arg: typing.Optional[typing.Any] = None,
        timeout: typing.Optional[float] = None,
        polling: typing.Optional[typing.Union[float, Literal["raf"]]] = None,
    ) -> "JSHandle":
        """Frame.wait_for_function

        Returns when the `expression` returns a truthy value, returns that value.

        **Usage**

        The `frame.wait_for_function()` can be used to observe viewport size change:

        ```py
        import asyncio
        from playwright.async_api import async_playwright, Playwright

        async def run(playwright: Playwright):
            webkit = playwright.webkit
            browser = await webkit.launch()
            page = await browser.new_page()
            await page.evaluate(\"window.x = 0; setTimeout(() => { window.x = 100 }, 1000);\")
            await page.main_frame.wait_for_function(\"() => window.x > 0\")
            await browser.close()

        async def main():
            async with async_playwright() as playwright:
                await run(playwright)
        asyncio.run(main())
        ```

        To pass an argument to the predicate of `frame.waitForFunction` function:

        ```py
        selector = \".foo\"
        await frame.wait_for_function(\"selector => !!document.querySelector(selector)\", selector)
        ```

        Parameters
        ----------
        expression : str
            JavaScript expression to be evaluated in the browser context. If the expression evaluates to a function, the
            function is automatically invoked.
        arg : Union[Any, None]
            Optional argument to pass to `expression`.
        timeout : Union[float, None]
            Maximum time to wait for in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The
            default value can be changed by using the `browser_context.set_default_timeout()` or
            `page.set_default_timeout()` methods.
        polling : Union["raf", float, None]
            If `polling` is `'raf'`, then `expression` is constantly executed in `requestAnimationFrame` callback. If `polling`
            is a number, then it is treated as an interval in milliseconds at which the function would be executed. Defaults to
            `raf`.

        Returns
        -------
        JSHandle
        """

        return mapping.from_impl(
            await self._impl_obj.wait_for_function(
                expression=expression,
                arg=mapping.to_impl(arg),
                timeout=timeout,
                polling=polling,
            )
        )

    async def title(self) -> str:
        """Frame.title

        Returns the page title.

        Returns
        -------
        str
        """

        return mapping.from_maybe_impl(await self._impl_obj.title())

    async def set_checked(
        self,
        selector: str,
        checked: bool,
        *,
        position: typing.Optional[Position] = None,
        timeout: typing.Optional[float] = None,
        force: typing.Optional[bool] = None,
        no_wait_after: typing.Optional[bool] = None,
        strict: typing.Optional[bool] = None,
        trial: typing.Optional[bool] = None,
    ) -> None:
        """Frame.set_checked

        This method checks or unchecks an element matching `selector` by performing the following steps:
        1. Find an element matching `selector`. If there is none, wait until a matching element is attached to the DOM.
        1. Ensure that matched element is a checkbox or a radio input. If not, this method throws.
        1. If the element already has the right checked state, this method returns immediately.
        1. Wait for [actionability](https://playwright.dev/python/docs/actionability) checks on the matched element, unless `force` option is set. If
           the element is detached during the checks, the whole action is retried.
        1. Scroll the element into view if needed.
        1. Use `page.mouse` to click in the center of the element.
        1. Ensure that the element is now checked or unchecked. If not, this method throws.

        When all steps combined have not finished during the specified `timeout`, this method throws a `TimeoutError`.
        Passing zero timeout disables this.

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be
            used.
        checked : bool
            Whether to check or uncheck the checkbox.
        position : Union[{x: float, y: float}, None]
            A point to use relative to the top-left corner of element padding box. If not specified, uses some visible point of
            the element.
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        force : Union[bool, None]
            Whether to bypass the [actionability](../actionability.md) checks. Defaults to `false`.
        no_wait_after : Union[bool, None]
            This option has no effect.
            Deprecated: This option has no effect.
        strict : Union[bool, None]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more than one
            element, the call throws an exception.
        trial : Union[bool, None]
            When set, this method only performs the [actionability](../actionability.md) checks and skips the action. Defaults
            to `false`. Useful to wait until the element is ready for the action without performing it.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.set_checked(
                selector=selector,
                checked=checked,
                position=position,
                timeout=timeout,
                force=force,
                noWaitAfter=no_wait_after,
                strict=strict,
                trial=trial,
            )
        )


mapping.register(FrameImpl, Frame)


class FrameLocator(AsyncBase):

    @property
    def first(self) -> "FrameLocator":
        """FrameLocator.first

        Returns locator to the first matching frame.

        Returns
        -------
        FrameLocator
        """
        return mapping.from_impl(self._impl_obj.first)

    @property
    def last(self) -> "FrameLocator":
        """FrameLocator.last

        Returns locator to the last matching frame.

        Returns
        -------
        FrameLocator
        """
        return mapping.from_impl(self._impl_obj.last)

    @property
    def owner(self) -> "Locator":
        """FrameLocator.owner

        Returns a `Locator` object pointing to the same `iframe` as this frame locator.

        Useful when you have a `FrameLocator` object obtained somewhere, and later on would like to interact with the
        `iframe` element.

        For a reverse operation, use `locator.content_frame()`.

        **Usage**

        ```py
        frame_locator = page.locator(\"iframe[name=\\\"embedded\\\"]\").content_frame
        # ...
        locator = frame_locator.owner
        await expect(locator).to_be_visible()
        ```

        Returns
        -------
        Locator
        """
        return mapping.from_impl(self._impl_obj.owner)

    def locator(
        self,
        selector_or_locator: typing.Union["Locator", str],
        *,
        has_text: typing.Optional[typing.Union[typing.Pattern[str], str]] = None,
        has_not_text: typing.Optional[typing.Union[typing.Pattern[str], str]] = None,
        has: typing.Optional["Locator"] = None,
        has_not: typing.Optional["Locator"] = None,
    ) -> "Locator":
        """FrameLocator.locator

        The method finds an element matching the specified selector in the locator's subtree. It also accepts filter
        options, similar to `locator.filter()` method.

        [Learn more about locators](https://playwright.dev/python/docs/locators).

        Parameters
        ----------
        selector_or_locator : Union[Locator, str]
            A selector or locator to use when resolving DOM element.
        has_text : Union[Pattern[str], str, None]
            Matches elements containing specified text somewhere inside, possibly in a child or a descendant element. When
            passed a [string], matching is case-insensitive and searches for a substring. For example, `"Playwright"` matches
            `<article><div>Playwright</div></article>`.
        has_not_text : Union[Pattern[str], str, None]
            Matches elements that do not contain specified text somewhere inside, possibly in a child or a descendant element.
            When passed a [string], matching is case-insensitive and searches for a substring.
        has : Union[Locator, None]
            Narrows down the results of the method to those which contain elements matching this relative locator. For example,
            `article` that has `text=Playwright` matches `<article><div>Playwright</div></article>`.

            Inner locator **must be relative** to the outer locator and is queried starting with the outer locator match, not
            the document root. For example, you can find `content` that has `div` in
            `<article><content><div>Playwright</div></content></article>`. However, looking for `content` that has `article
            div` will fail, because the inner locator must be relative and should not use any elements outside the `content`.

            Note that outer and inner locators must belong to the same frame. Inner locator must not contain `FrameLocator`s.
        has_not : Union[Locator, None]
            Matches elements that do not contain an element that matches an inner locator. Inner locator is queried against the
            outer one. For example, `article` that does not have `div` matches `<article><span>Playwright</span></article>`.

            Note that outer and inner locators must belong to the same frame. Inner locator must not contain `FrameLocator`s.

        Returns
        -------
        Locator
        """

        return mapping.from_impl(
            self._impl_obj.locator(
                selectorOrLocator=selector_or_locator,
                hasText=has_text,
                hasNotText=has_not_text,
                has=has._impl_obj if has else None,
                hasNot=has_not._impl_obj if has_not else None,
            )
        )

    def get_by_alt_text(
        self,
        text: typing.Union[str, typing.Pattern[str]],
        *,
        exact: typing.Optional[bool] = None,
    ) -> "Locator":
        """FrameLocator.get_by_alt_text

        Allows locating elements by their alt text.

        **Usage**

        For example, this method will find the image by alt text \"Playwright logo\":

        ```html
        <img alt='Playwright logo'>
        ```

        ```py
        await page.get_by_alt_text(\"Playwright logo\").click()
        ```

        Parameters
        ----------
        text : Union[Pattern[str], str]
            Text to locate the element for.
        exact : Union[bool, None]
            Whether to find an exact match: case-sensitive and whole-string. Default to false. Ignored when locating by a
            regular expression. Note that exact match still trims whitespace.

        Returns
        -------
        Locator
        """

        return mapping.from_impl(self._impl_obj.get_by_alt_text(text=text, exact=exact))

    def get_by_label(
        self,
        text: typing.Union[str, typing.Pattern[str]],
        *,
        exact: typing.Optional[bool] = None,
    ) -> "Locator":
        """FrameLocator.get_by_label

        Allows locating input elements by the text of the associated `<label>` or `aria-labelledby` element, or by the
        `aria-label` attribute.

        **Usage**

        For example, this method will find inputs by label \"Username\" and \"Password\" in the following DOM:

        ```html
        <input aria-label=\"Username\">
        <label for=\"password-input\">Password:</label>
        <input id=\"password-input\">
        ```

        ```py
        await page.get_by_label(\"Username\").fill(\"john\")
        await page.get_by_label(\"Password\").fill(\"secret\")
        ```

        Parameters
        ----------
        text : Union[Pattern[str], str]
            Text to locate the element for.
        exact : Union[bool, None]
            Whether to find an exact match: case-sensitive and whole-string. Default to false. Ignored when locating by a
            regular expression. Note that exact match still trims whitespace.

        Returns
        -------
        Locator
        """

        return mapping.from_impl(self._impl_obj.get_by_label(text=text, exact=exact))

    def get_by_placeholder(
        self,
        text: typing.Union[str, typing.Pattern[str]],
        *,
        exact: typing.Optional[bool] = None,
    ) -> "Locator":
        """FrameLocator.get_by_placeholder

        Allows locating input elements by the placeholder text.

        **Usage**

        For example, consider the following DOM structure.

        ```html
        <input type=\"email\" placeholder=\"name@example.com\" />
        ```

        You can fill the input after locating it by the placeholder text:

        ```py
        await page.get_by_placeholder(\"name@example.com\").fill(\"playwright@microsoft.com\")
        ```

        Parameters
        ----------
        text : Union[Pattern[str], str]
            Text to locate the element for.
        exact : Union[bool, None]
            Whether to find an exact match: case-sensitive and whole-string. Default to false. Ignored when locating by a
            regular expression. Note that exact match still trims whitespace.

        Returns
        -------
        Locator
        """

        return mapping.from_impl(
            self._impl_obj.get_by_placeholder(text=text, exact=exact)
        )

    def get_by_role(
        self,
        role: Literal[
            "alert",
            "alertdialog",
            "application",
            "article",
            "banner",
            "blockquote",
            "button",
            "caption",
            "cell",
            "checkbox",
            "code",
            "columnheader",
            "combobox",
            "complementary",
            "contentinfo",
            "definition",
            "deletion",
            "dialog",
            "directory",
            "document",
            "emphasis",
            "feed",
            "figure",
            "form",
            "generic",
            "grid",
            "gridcell",
            "group",
            "heading",
            "img",
            "insertion",
            "link",
            "list",
            "listbox",
            "listitem",
            "log",
            "main",
            "marquee",
            "math",
            "menu",
            "menubar",
            "menuitem",
            "menuitemcheckbox",
            "menuitemradio",
            "meter",
            "navigation",
            "none",
            "note",
            "option",
            "paragraph",
            "presentation",
            "progressbar",
            "radio",
            "radiogroup",
            "region",
            "row",
            "rowgroup",
            "rowheader",
            "scrollbar",
            "search",
            "searchbox",
            "separator",
            "slider",
            "spinbutton",
            "status",
            "strong",
            "subscript",
            "superscript",
            "switch",
            "tab",
            "table",
            "tablist",
            "tabpanel",
            "term",
            "textbox",
            "time",
            "timer",
            "toolbar",
            "tooltip",
            "tree",
            "treegrid",
            "treeitem",
        ],
        *,
        checked: typing.Optional[bool] = None,
        disabled: typing.Optional[bool] = None,
        expanded: typing.Optional[bool] = None,
        include_hidden: typing.Optional[bool] = None,
        level: typing.Optional[int] = None,
        name: typing.Optional[typing.Union[typing.Pattern[str], str]] = None,
        pressed: typing.Optional[bool] = None,
        selected: typing.Optional[bool] = None,
        exact: typing.Optional[bool] = None,
    ) -> "Locator":
        """FrameLocator.get_by_role

        Allows locating elements by their [ARIA role](https://www.w3.org/TR/wai-aria-1.2/#roles),
        [ARIA attributes](https://www.w3.org/TR/wai-aria-1.2/#aria-attributes) and
        [accessible name](https://w3c.github.io/accname/#dfn-accessible-name).

        **Usage**

        Consider the following DOM structure.

        ```html
        <h3>Sign up</h3>
        <label>
          <input type=\"checkbox\" /> Subscribe
        </label>
        <br/>
        <button>Submit</button>
        ```

        You can locate each element by it's implicit role:

        ```py
        await expect(page.get_by_role(\"heading\", name=\"Sign up\")).to_be_visible()

        await page.get_by_role(\"checkbox\", name=\"Subscribe\").check()

        await page.get_by_role(\"button\", name=re.compile(\"submit\", re.IGNORECASE)).click()
        ```

        **Details**

        Role selector **does not replace** accessibility audits and conformance tests, but rather gives early feedback
        about the ARIA guidelines.

        Many html elements have an implicitly [defined role](https://w3c.github.io/html-aam/#html-element-role-mappings)
        that is recognized by the role selector. You can find all the
        [supported roles here](https://www.w3.org/TR/wai-aria-1.2/#role_definitions). ARIA guidelines **do not recommend**
        duplicating implicit roles and attributes by setting `role` and/or `aria-*` attributes to default values.

        Parameters
        ----------
        role : Union["alert", "alertdialog", "application", "article", "banner", "blockquote", "button", "caption", "cell", "checkbox", "code", "columnheader", "combobox", "complementary", "contentinfo", "definition", "deletion", "dialog", "directory", "document", "emphasis", "feed", "figure", "form", "generic", "grid", "gridcell", "group", "heading", "img", "insertion", "link", "list", "listbox", "listitem", "log", "main", "marquee", "math", "menu", "menubar", "menuitem", "menuitemcheckbox", "menuitemradio", "meter", "navigation", "none", "note", "option", "paragraph", "presentation", "progressbar", "radio", "radiogroup", "region", "row", "rowgroup", "rowheader", "scrollbar", "search", "searchbox", "separator", "slider", "spinbutton", "status", "strong", "subscript", "superscript", "switch", "tab", "table", "tablist", "tabpanel", "term", "textbox", "time", "timer", "toolbar", "tooltip", "tree", "treegrid", "treeitem"]
            Required aria role.
        checked : Union[bool, None]
            An attribute that is usually set by `aria-checked` or native `<input type=checkbox>` controls.

            Learn more about [`aria-checked`](https://www.w3.org/TR/wai-aria-1.2/#aria-checked).
        disabled : Union[bool, None]
            An attribute that is usually set by `aria-disabled` or `disabled`.

            **NOTE** Unlike most other attributes, `disabled` is inherited through the DOM hierarchy. Learn more about
            [`aria-disabled`](https://www.w3.org/TR/wai-aria-1.2/#aria-disabled).

        expanded : Union[bool, None]
            An attribute that is usually set by `aria-expanded`.

            Learn more about [`aria-expanded`](https://www.w3.org/TR/wai-aria-1.2/#aria-expanded).
        include_hidden : Union[bool, None]
            Option that controls whether hidden elements are matched. By default, only non-hidden elements, as
            [defined by ARIA](https://www.w3.org/TR/wai-aria-1.2/#tree_exclusion), are matched by role selector.

            Learn more about [`aria-hidden`](https://www.w3.org/TR/wai-aria-1.2/#aria-hidden).
        level : Union[int, None]
            A number attribute that is usually present for roles `heading`, `listitem`, `row`, `treeitem`, with default values
            for `<h1>-<h6>` elements.

            Learn more about [`aria-level`](https://www.w3.org/TR/wai-aria-1.2/#aria-level).
        name : Union[Pattern[str], str, None]
            Option to match the [accessible name](https://w3c.github.io/accname/#dfn-accessible-name). By default, matching is
            case-insensitive and searches for a substring, use `exact` to control this behavior.

            Learn more about [accessible name](https://w3c.github.io/accname/#dfn-accessible-name).
        pressed : Union[bool, None]
            An attribute that is usually set by `aria-pressed`.

            Learn more about [`aria-pressed`](https://www.w3.org/TR/wai-aria-1.2/#aria-pressed).
        selected : Union[bool, None]
            An attribute that is usually set by `aria-selected`.

            Learn more about [`aria-selected`](https://www.w3.org/TR/wai-aria-1.2/#aria-selected).
        exact : Union[bool, None]
            Whether `name` is matched exactly: case-sensitive and whole-string. Defaults to false. Ignored when `name` is a
            regular expression. Note that exact match still trims whitespace.

        Returns
        -------
        Locator
        """

        return mapping.from_impl(
            self._impl_obj.get_by_role(
                role=role,
                checked=checked,
                disabled=disabled,
                expanded=expanded,
                includeHidden=include_hidden,
                level=level,
                name=name,
                pressed=pressed,
                selected=selected,
                exact=exact,
            )
        )

    def get_by_test_id(
        self, test_id: typing.Union[str, typing.Pattern[str]]
    ) -> "Locator":
        """FrameLocator.get_by_test_id

        Locate element by the test id.

        **Usage**

        Consider the following DOM structure.

        ```html
        <button data-testid=\"directions\">Itinéraire</button>
        ```

        You can locate the element by it's test id:

        ```py
        await page.get_by_test_id(\"directions\").click()
        ```

        **Details**

        By default, the `data-testid` attribute is used as a test id. Use `selectors.set_test_id_attribute()` to
        configure a different test id attribute if necessary.

        Parameters
        ----------
        test_id : Union[Pattern[str], str]
            Id to locate the element by.

        Returns
        -------
        Locator
        """

        return mapping.from_impl(self._impl_obj.get_by_test_id(testId=test_id))

    def get_by_text(
        self,
        text: typing.Union[str, typing.Pattern[str]],
        *,
        exact: typing.Optional[bool] = None,
    ) -> "Locator":
        """FrameLocator.get_by_text

        Allows locating elements that contain given text.

        See also `locator.filter()` that allows to match by another criteria, like an accessible role, and then
        filter by the text content.

        **Usage**

        Consider the following DOM structure:

        ```html
        <div>Hello <span>world</span></div>
        <div>Hello</div>
        ```

        You can locate by text substring, exact string, or a regular expression:

        ```py
        # Matches <span>
        page.get_by_text(\"world\")

        # Matches first <div>
        page.get_by_text(\"Hello world\")

        # Matches second <div>
        page.get_by_text(\"Hello\", exact=True)

        # Matches both <div>s
        page.get_by_text(re.compile(\"Hello\"))

        # Matches second <div>
        page.get_by_text(re.compile(\"^hello$\", re.IGNORECASE))
        ```

        **Details**

        Matching by text always normalizes whitespace, even with exact match. For example, it turns multiple spaces into
        one, turns line breaks into spaces and ignores leading and trailing whitespace.

        Input elements of the type `button` and `submit` are matched by their `value` instead of the text content. For
        example, locating by text `\"Log in\"` matches `<input type=button value=\"Log in\">`.

        Parameters
        ----------
        text : Union[Pattern[str], str]
            Text to locate the element for.
        exact : Union[bool, None]
            Whether to find an exact match: case-sensitive and whole-string. Default to false. Ignored when locating by a
            regular expression. Note that exact match still trims whitespace.

        Returns
        -------
        Locator
        """

        return mapping.from_impl(self._impl_obj.get_by_text(text=text, exact=exact))

    def get_by_title(
        self,
        text: typing.Union[str, typing.Pattern[str]],
        *,
        exact: typing.Optional[bool] = None,
    ) -> "Locator":
        """FrameLocator.get_by_title

        Allows locating elements by their title attribute.

        **Usage**

        Consider the following DOM structure.

        ```html
        <span title='Issues count'>25 issues</span>
        ```

        You can check the issues count after locating it by the title text:

        ```py
        await expect(page.get_by_title(\"Issues count\")).to_have_text(\"25 issues\")
        ```

        Parameters
        ----------
        text : Union[Pattern[str], str]
            Text to locate the element for.
        exact : Union[bool, None]
            Whether to find an exact match: case-sensitive and whole-string. Default to false. Ignored when locating by a
            regular expression. Note that exact match still trims whitespace.

        Returns
        -------
        Locator
        """

        return mapping.from_impl(self._impl_obj.get_by_title(text=text, exact=exact))

    def frame_locator(self, selector: str) -> "FrameLocator":
        """FrameLocator.frame_locator

        When working with iframes, you can create a frame locator that will enter the iframe and allow selecting elements
        in that iframe.

        Parameters
        ----------
        selector : str
            A selector to use when resolving DOM element.

        Returns
        -------
        FrameLocator
        """

        return mapping.from_impl(self._impl_obj.frame_locator(selector=selector))

    def nth(self, index: int) -> "FrameLocator":
        """FrameLocator.nth

        Returns locator to the n-th matching frame. It's zero based, `nth(0)` selects the first frame.

        Parameters
        ----------
        index : int

        Returns
        -------
        FrameLocator
        """

        return mapping.from_impl(self._impl_obj.nth(index=index))


mapping.register(FrameLocatorImpl, FrameLocator)


class Worker(AsyncBase):

    @typing.overload
    def on(
        self,
        event: Literal["close"],
        f: typing.Callable[["Worker"], "typing.Union[typing.Awaitable[None], None]"],
    ) -> None:
        """
        Emitted when this dedicated [WebWorker](https://developer.mozilla.org/en-US/docs/Web/API/Web_Workers_API) is
        terminated."""

    @typing.overload
    def on(
        self,
        event: Literal["console"],
        f: typing.Callable[
            ["ConsoleMessage"], "typing.Union[typing.Awaitable[None], None]"
        ],
    ) -> None:
        """
        Emitted when JavaScript within the worker calls one of console API methods, e.g. `console.log` or `console.dir`.
        """

    def on(
        self,
        event: str,
        f: typing.Callable[..., typing.Union[typing.Awaitable[None], None]],
    ) -> None:
        return super().on(event=event, f=f)

    @typing.overload
    def once(
        self,
        event: Literal["close"],
        f: typing.Callable[["Worker"], "typing.Union[typing.Awaitable[None], None]"],
    ) -> None:
        """
        Emitted when this dedicated [WebWorker](https://developer.mozilla.org/en-US/docs/Web/API/Web_Workers_API) is
        terminated."""

    @typing.overload
    def once(
        self,
        event: Literal["console"],
        f: typing.Callable[
            ["ConsoleMessage"], "typing.Union[typing.Awaitable[None], None]"
        ],
    ) -> None:
        """
        Emitted when JavaScript within the worker calls one of console API methods, e.g. `console.log` or `console.dir`.
        """

    def once(
        self,
        event: str,
        f: typing.Callable[..., typing.Union[typing.Awaitable[None], None]],
    ) -> None:
        return super().once(event=event, f=f)

    @property
    def url(self) -> str:
        """Worker.url

        Returns
        -------
        str
        """
        return mapping.from_maybe_impl(self._impl_obj.url)

    async def evaluate(
        self, expression: str, arg: typing.Optional[typing.Any] = None
    ) -> typing.Any:
        """Worker.evaluate

        Returns the return value of `expression`.

        If the function passed to the `worker.evaluate()` returns a [Promise], then `worker.evaluate()`
        would wait for the promise to resolve and return its value.

        If the function passed to the `worker.evaluate()` returns a non-[Serializable] value, then
        `worker.evaluate()` returns `undefined`. Playwright also supports transferring some additional values that
        are not serializable by `JSON`: `-0`, `NaN`, `Infinity`, `-Infinity`.

        Parameters
        ----------
        expression : str
            JavaScript expression to be evaluated in the browser context. If the expression evaluates to a function, the
            function is automatically invoked.
        arg : Union[Any, None]
            Optional argument to pass to `expression`.

        Returns
        -------
        Any
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.evaluate(
                expression=expression, arg=mapping.to_impl(arg)
            )
        )

    async def evaluate_handle(
        self, expression: str, arg: typing.Optional[typing.Any] = None
    ) -> "JSHandle":
        """Worker.evaluate_handle

        Returns the return value of `expression` as a `JSHandle`.

        The only difference between `worker.evaluate()` and `worker.evaluate_handle()` is that
        `worker.evaluate_handle()` returns `JSHandle`.

        If the function passed to the `worker.evaluate_handle()` returns a [Promise], then
        `worker.evaluate_handle()` would wait for the promise to resolve and return its value.

        Parameters
        ----------
        expression : str
            JavaScript expression to be evaluated in the browser context. If the expression evaluates to a function, the
            function is automatically invoked.
        arg : Union[Any, None]
            Optional argument to pass to `expression`.

        Returns
        -------
        JSHandle
        """

        return mapping.from_impl(
            await self._impl_obj.evaluate_handle(
                expression=expression, arg=mapping.to_impl(arg)
            )
        )

    def expect_event(
        self,
        event: str,
        predicate: typing.Optional[typing.Callable] = None,
        *,
        timeout: typing.Optional[float] = None,
    ) -> AsyncEventContextManager:
        """Worker.expect_event

        Waits for event to fire and passes its value into the predicate function. Returns when the predicate returns truthy
        value. Will throw an error if the page is closed before the event is fired. Returns the event data value.

        **Usage**

        ```py
        async with worker.expect_event(\"console\") as event_info:
            await worker.evaluate(\"console.log(42)\")
        message = await event_info.value
        ```

        Parameters
        ----------
        event : str
            Event name, same one typically passed into `*.on(event)`.
        predicate : Union[Callable, None]
            Receives the event data and resolves to truthy value when the waiting should resolve.
        timeout : Union[float, None]
            Maximum time to wait for in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The
            default value can be changed by using the `browser_context.set_default_timeout()`.

        Returns
        -------
        EventContextManager
        """

        return AsyncEventContextManager(
            self._impl_obj.expect_event(
                event=event, predicate=self._wrap_handler(predicate), timeout=timeout
            ).future
        )


mapping.register(WorkerImpl, Worker)


class Selectors(AsyncBase):

    async def register(
        self,
        name: str,
        script: typing.Optional[str] = None,
        *,
        path: typing.Optional[typing.Union[pathlib.Path, str]] = None,
        content_script: typing.Optional[bool] = None,
    ) -> None:
        """Selectors.register

        Selectors must be registered before creating the page.

        **Usage**

        An example of registering selector engine that queries elements based on a tag name:

        ```py
        import asyncio
        from playwright.async_api import async_playwright, Playwright

        async def run(playwright: Playwright):
            tag_selector = \"\"\"
              {
                  // Returns the first element matching given selector in the root's subtree.
                  query(root, selector) {
                      return root.querySelector(selector);
                  },
                  // Returns all elements matching given selector in the root's subtree.
                  queryAll(root, selector) {
                      return Array.from(root.querySelectorAll(selector));
                  }
              }\"\"\"

            # Register the engine. Selectors will be prefixed with \"tag=\".
            await playwright.selectors.register(\"tag\", tag_selector)
            browser = await playwright.chromium.launch()
            page = await browser.new_page()
            await page.set_content('<div><button>Click me</button></div>')

            # Use the selector prefixed with its name.
            button = await page.query_selector('tag=button')
            # Combine it with built-in locators.
            await page.locator('tag=div').get_by_text('Click me').click()
            # Can use it in any methods supporting selectors.
            button_count = await page.locator('tag=button').count()
            print(button_count)
            await browser.close()

        async def main():
            async with async_playwright() as playwright:
                await run(playwright)

        asyncio.run(main())
        ```

        Parameters
        ----------
        name : str
            Name that is used in selectors as a prefix, e.g. `{name: 'foo'}` enables `foo=myselectorbody` selectors. May only
            contain `[a-zA-Z0-9_]` characters.
        script : Union[str, None]
            Raw script content.
        path : Union[pathlib.Path, str, None]
            Path to the JavaScript file. If `path` is a relative path, then it is resolved relative to the current working
            directory.
        content_script : Union[bool, None]
            Whether to run this selector engine in isolated JavaScript environment. This environment has access to the same
            DOM, but not any JavaScript objects from the frame's scripts. Defaults to `false`. Note that running as a content
            script is not guaranteed when this engine is used together with other registered engines.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.register(
                name=name, script=script, path=path, contentScript=content_script
            )
        )

    def set_test_id_attribute(self, attribute_name: str) -> None:
        """Selectors.set_test_id_attribute

        Defines custom attribute name to be used in `page.get_by_test_id()`. `data-testid` is used by default.

        Parameters
        ----------
        attribute_name : str
            Test id attribute name.
        """

        return mapping.from_maybe_impl(
            self._impl_obj.set_test_id_attribute(attributeName=attribute_name)
        )


mapping.register(SelectorsImpl, Selectors)


class Clock(AsyncBase):

    async def install(
        self,
        *,
        time: typing.Optional[typing.Union[float, str, datetime.datetime]] = None,
    ) -> None:
        """Clock.install

        Install fake implementations for the following time-related functions:
        - `Date`
        - `setTimeout`
        - `clearTimeout`
        - `setInterval`
        - `clearInterval`
        - `requestAnimationFrame`
        - `cancelAnimationFrame`
        - `requestIdleCallback`
        - `cancelIdleCallback`
        - `performance`

        Fake timers are used to manually control the flow of time in tests. They allow you to advance time, fire timers,
        and control the behavior of time-dependent functions. See `clock.run_for()` and
        `clock.fast_forward()` for more information.

        Parameters
        ----------
        time : Union[datetime.datetime, float, str, None]
            Time to initialize with, current system time by default.
        """

        return mapping.from_maybe_impl(await self._impl_obj.install(time=time))

    async def fast_forward(self, ticks: typing.Union[int, str]) -> None:
        """Clock.fast_forward

        Advance the clock by jumping forward in time. Only fires due timers at most once. This is equivalent to user
        closing the laptop lid for a while and reopening it later, after given time.

        **Usage**

        ```py
        await page.clock.fast_forward(1000)
        await page.clock.fast_forward(\"30:00\")
        ```

        Parameters
        ----------
        ticks : Union[int, str]
            Time may be the number of milliseconds to advance the clock by or a human-readable string. Valid string formats are
            "08" for eight seconds, "01:00" for one minute and "02:34:10" for two hours, 34 minutes and ten seconds.
        """

        return mapping.from_maybe_impl(await self._impl_obj.fast_forward(ticks=ticks))

    async def pause_at(self, time: typing.Union[float, str, datetime.datetime]) -> None:
        """Clock.pause_at

        Advance the clock by jumping forward in time and pause the time. Once this method is called, no timers are fired
        unless `clock.run_for()`, `clock.fast_forward()`, `clock.pause_at()` or
        `clock.resume()` is called.

        Only fires due timers at most once. This is equivalent to user closing the laptop lid for a while and reopening it
        at the specified time and pausing.

        **Usage**

        ```py
        await page.clock.pause_at(datetime.datetime(2020, 2, 2))
        await page.clock.pause_at(\"2020-02-02\")
        ```

        For best results, install the clock before navigating the page and set it to a time slightly before the intended
        test time. This ensures that all timers run normally during page loading, preventing the page from getting stuck.
        Once the page has fully loaded, you can safely use `clock.pause_at()` to pause the clock.

        ```py
        # Initialize clock with some time before the test time and let the page load
        # naturally. `Date.now` will progress as the timers fire.
        await page.clock.install(time=datetime.datetime(2024, 12, 10, 8, 0, 0))
        await page.goto(\"http://localhost:3333\")
        await page.clock.pause_at(datetime.datetime(2024, 12, 10, 10, 0, 0))
        ```

        Parameters
        ----------
        time : Union[datetime.datetime, float, str]
            Time to pause at.
        """

        return mapping.from_maybe_impl(await self._impl_obj.pause_at(time=time))

    async def resume(self) -> None:
        """Clock.resume

        Resumes timers. Once this method is called, time resumes flowing, timers are fired as usual.
        """

        return mapping.from_maybe_impl(await self._impl_obj.resume())

    async def run_for(self, ticks: typing.Union[int, str]) -> None:
        """Clock.run_for

        Advance the clock, firing all the time-related callbacks.

        **Usage**

        ```py
        await page.clock.run_for(1000);
        await page.clock.run_for(\"30:00\")
        ```

        Parameters
        ----------
        ticks : Union[int, str]
            Time may be the number of milliseconds to advance the clock by or a human-readable string. Valid string formats are
            "08" for eight seconds, "01:00" for one minute and "02:34:10" for two hours, 34 minutes and ten seconds.
        """

        return mapping.from_maybe_impl(await self._impl_obj.run_for(ticks=ticks))

    async def set_fixed_time(
        self, time: typing.Union[float, str, datetime.datetime]
    ) -> None:
        """Clock.set_fixed_time

        Makes `Date.now` and `new Date()` return fixed fake time at all times, keeps all the timers running.

        Use this method for simple scenarios where you only need to test with a predefined time. For more advanced
        scenarios, use `clock.install()` instead. Read docs on [clock emulation](https://playwright.dev/python/docs/clock) to learn more.

        **Usage**

        ```py
        await page.clock.set_fixed_time(datetime.datetime.now())
        await page.clock.set_fixed_time(datetime.datetime(2020, 2, 2))
        await page.clock.set_fixed_time(\"2020-02-02\")
        ```

        Parameters
        ----------
        time : Union[datetime.datetime, float, str]
            Time to be set.
        """

        return mapping.from_maybe_impl(await self._impl_obj.set_fixed_time(time=time))

    async def set_system_time(
        self, time: typing.Union[float, str, datetime.datetime]
    ) -> None:
        """Clock.set_system_time

        Sets system time, but does not trigger any timers. Use this to test how the web page reacts to a time shift, for
        example switching from summer to winter time, or changing time zones.

        **Usage**

        ```py
        await page.clock.set_system_time(datetime.datetime.now())
        await page.clock.set_system_time(datetime.datetime(2020, 2, 2))
        await page.clock.set_system_time(\"2020-02-02\")
        ```

        Parameters
        ----------
        time : Union[datetime.datetime, float, str]
            Time to be set.
        """

        return mapping.from_maybe_impl(await self._impl_obj.set_system_time(time=time))


mapping.register(ClockImpl, Clock)


class ConsoleMessage(AsyncBase):

    @property
    def type(
        self,
    ) -> typing.Union[
        Literal["assert"],
        Literal["clear"],
        Literal["count"],
        Literal["debug"],
        Literal["dir"],
        Literal["dirxml"],
        Literal["endGroup"],
        Literal["error"],
        Literal["info"],
        Literal["log"],
        Literal["profile"],
        Literal["profileEnd"],
        Literal["startGroup"],
        Literal["startGroupCollapsed"],
        Literal["table"],
        Literal["time"],
        Literal["timeEnd"],
        Literal["trace"],
        Literal["warning"],
    ]:
        """ConsoleMessage.type

        Returns
        -------
        Union["assert", "clear", "count", "debug", "dir", "dirxml", "endGroup", "error", "info", "log", "profile", "profileEnd", "startGroup", "startGroupCollapsed", "table", "time", "timeEnd", "trace", "warning"]
        """
        return mapping.from_maybe_impl(self._impl_obj.type)

    @property
    def text(self) -> str:
        """ConsoleMessage.text

        The text of the console message.

        Returns
        -------
        str
        """
        return mapping.from_maybe_impl(self._impl_obj.text)

    @property
    def args(self) -> typing.List["JSHandle"]:
        """ConsoleMessage.args

        List of arguments passed to a `console` function call. See also `page.on('console')`.

        Returns
        -------
        List[JSHandle]
        """
        return mapping.from_impl_list(self._impl_obj.args)

    @property
    def location(self) -> SourceLocation:
        """ConsoleMessage.location

        Returns
        -------
        {url: str, lineNumber: int, columnNumber: int}
        """
        return mapping.from_impl(self._impl_obj.location)

    @property
    def page(self) -> typing.Optional["Page"]:
        """ConsoleMessage.page

        The page that produced this console message, if any.

        Returns
        -------
        Union[Page, None]
        """
        return mapping.from_impl_nullable(self._impl_obj.page)

    @property
    def worker(self) -> typing.Optional["Worker"]:
        """ConsoleMessage.worker

        The web worker or service worker that produced this console message, if any. Note that console messages from web
        workers also have non-null `console_message.page()`.

        Returns
        -------
        Union[Worker, None]
        """
        return mapping.from_impl_nullable(self._impl_obj.worker)


mapping.register(ConsoleMessageImpl, ConsoleMessage)


class Dialog(AsyncBase):

    @property
    def type(self) -> str:
        """Dialog.type

        Returns dialog's type, can be one of `alert`, `beforeunload`, `confirm` or `prompt`.

        Returns
        -------
        str
        """
        return mapping.from_maybe_impl(self._impl_obj.type)

    @property
    def message(self) -> str:
        """Dialog.message

        A message displayed in the dialog.

        Returns
        -------
        str
        """
        return mapping.from_maybe_impl(self._impl_obj.message)

    @property
    def default_value(self) -> str:
        """Dialog.default_value

        If dialog is prompt, returns default prompt value. Otherwise, returns empty string.

        Returns
        -------
        str
        """
        return mapping.from_maybe_impl(self._impl_obj.default_value)

    @property
    def page(self) -> typing.Optional["Page"]:
        """Dialog.page

        The page that initiated this dialog, if available.

        Returns
        -------
        Union[Page, None]
        """
        return mapping.from_impl_nullable(self._impl_obj.page)

    async def accept(self, prompt_text: typing.Optional[str] = None) -> None:
        """Dialog.accept

        Returns when the dialog has been accepted.

        Parameters
        ----------
        prompt_text : Union[str, None]
            A text to enter in prompt. Does not cause any effects if the dialog's `type` is not prompt. Optional.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.accept(promptText=prompt_text)
        )

    async def dismiss(self) -> None:
        """Dialog.dismiss

        Returns when the dialog has been dismissed.
        """

        return mapping.from_maybe_impl(await self._impl_obj.dismiss())


mapping.register(DialogImpl, Dialog)


class Download(AsyncBase):

    @property
    def page(self) -> "Page":
        """Download.page

        Get the page that the download belongs to.

        Returns
        -------
        Page
        """
        return mapping.from_impl(self._impl_obj.page)

    @property
    def url(self) -> str:
        """Download.url

        Returns downloaded url.

        Returns
        -------
        str
        """
        return mapping.from_maybe_impl(self._impl_obj.url)

    @property
    def suggested_filename(self) -> str:
        """Download.suggested_filename

        Returns suggested filename for this download. It is typically computed by the browser from the
        [`Content-Disposition`](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Content-Disposition) response
        header or the `download` attribute. See the spec on [whatwg](https://html.spec.whatwg.org/#downloading-resources).
        Different browsers can use different logic for computing it.

        Returns
        -------
        str
        """
        return mapping.from_maybe_impl(self._impl_obj.suggested_filename)

    async def delete(self) -> None:
        """Download.delete

        Deletes the downloaded file. Will wait for the download to finish if necessary.
        """

        return mapping.from_maybe_impl(await self._impl_obj.delete())

    async def failure(self) -> typing.Optional[str]:
        """Download.failure

        Returns download error if any. Will wait for the download to finish if necessary.

        Returns
        -------
        Union[str, None]
        """

        return mapping.from_maybe_impl(await self._impl_obj.failure())

    async def path(self) -> pathlib.Path:
        """Download.path

        Returns path to the downloaded file for a successful download, or throws for a failed/canceled download. The method
        will wait for the download to finish if necessary. The method throws when connected remotely.

        Note that the download's file name is a random GUID, use `download.suggested_filename()` to get suggested
        file name.

        Returns
        -------
        pathlib.Path
        """

        return mapping.from_maybe_impl(await self._impl_obj.path())

    async def save_as(self, path: typing.Union[str, pathlib.Path]) -> None:
        """Download.save_as

        Copy the download to a user-specified path. It is safe to call this method while the download is still in progress.
        Will wait for the download to finish if necessary.

        **Usage**

        ```py
        await download.save_as(\"/path/to/save/at/\" + download.suggested_filename)
        ```

        Parameters
        ----------
        path : Union[pathlib.Path, str]
            Path where the download should be copied.
        """

        return mapping.from_maybe_impl(await self._impl_obj.save_as(path=path))

    async def cancel(self) -> None:
        """Download.cancel

        Cancels a download. Will not fail if the download is already finished or canceled. Upon successful cancellations,
        `download.failure()` would resolve to `'canceled'`.
        """

        return mapping.from_maybe_impl(await self._impl_obj.cancel())


mapping.register(DownloadImpl, Download)


class Video(AsyncBase):

    async def path(self) -> pathlib.Path:
        """Video.path

        Returns the file system path this video will be recorded to. The video is guaranteed to be written to the
        filesystem upon closing the browser context. This method throws when connected remotely.

        Returns
        -------
        pathlib.Path
        """

        return mapping.from_maybe_impl(await self._impl_obj.path())

    async def save_as(self, path: typing.Union[str, pathlib.Path]) -> None:
        """Video.save_as

        Saves the video to a user-specified path. It is safe to call this method while the video is still in progress, or
        after the page has closed. This method waits until the page is closed and the video is fully saved.

        Parameters
        ----------
        path : Union[pathlib.Path, str]
            Path where the video should be saved.
        """

        return mapping.from_maybe_impl(await self._impl_obj.save_as(path=path))

    async def delete(self) -> None:
        """Video.delete

        Deletes the video file. Will wait for the video to finish if necessary.
        """

        return mapping.from_maybe_impl(await self._impl_obj.delete())


mapping.register(VideoImpl, Video)


class Page(AsyncContextManager):

    @typing.overload
    def on(
        self,
        event: Literal["close"],
        f: typing.Callable[["Page"], "typing.Union[typing.Awaitable[None], None]"],
    ) -> None:
        """
        Emitted when the page closes."""

    @typing.overload
    def on(
        self,
        event: Literal["console"],
        f: typing.Callable[
            ["ConsoleMessage"], "typing.Union[typing.Awaitable[None], None]"
        ],
    ) -> None:
        """
        Emitted when JavaScript within the page calls one of console API methods, e.g. `console.log` or `console.dir`.

        The arguments passed into `console.log` are available on the `ConsoleMessage` event handler argument.

        **Usage**

        ```py
        async def print_args(msg):
            values = []
            for arg in msg.args:
                values.append(await arg.json_value())
            print(values)

        page.on(\"console\", print_args)
        await page.evaluate(\"console.log('hello', 5, { foo: 'bar' })\")
        ```"""

    @typing.overload
    def on(
        self,
        event: Literal["crash"],
        f: typing.Callable[["Page"], "typing.Union[typing.Awaitable[None], None]"],
    ) -> None:
        """
        Emitted when the page crashes. Browser pages might crash if they try to allocate too much memory. When the page
        crashes, ongoing and subsequent operations will throw.

        The most common way to deal with crashes is to catch an exception:

        ```py
        try:
            # crash might happen during a click.
            await page.click(\"button\")
            # or while waiting for an event.
            await page.wait_for_event(\"popup\")
        except Error as e:
            pass
            # when the page crashes, exception message contains \"crash\".
        ```"""

    @typing.overload
    def on(
        self,
        event: Literal["dialog"],
        f: typing.Callable[["Dialog"], "typing.Union[typing.Awaitable[None], None]"],
    ) -> None:
        """
        Emitted when a JavaScript dialog appears, such as `alert`, `prompt`, `confirm` or `beforeunload`. Listener **must**
        either `dialog.accept()` or `dialog.dismiss()` the dialog - otherwise the page will
        [freeze](https://developer.mozilla.org/en-US/docs/Web/JavaScript/EventLoop#never_blocking) waiting for the dialog,
        and actions like click will never finish.

        **Usage**

        ```python
        page.on(\"dialog\", lambda dialog: dialog.accept())
        ```

        **NOTE** When no `page.on('dialog')` or `browser_context.on('dialog')` listeners are present, all dialogs are
        automatically dismissed."""

    @typing.overload
    def on(
        self,
        event: Literal["domcontentloaded"],
        f: typing.Callable[["Page"], "typing.Union[typing.Awaitable[None], None]"],
    ) -> None:
        """
        Emitted when the JavaScript
        [`DOMContentLoaded`](https://developer.mozilla.org/en-US/docs/Web/Events/DOMContentLoaded) event is dispatched.
        """

    @typing.overload
    def on(
        self,
        event: Literal["download"],
        f: typing.Callable[["Download"], "typing.Union[typing.Awaitable[None], None]"],
    ) -> None:
        """
        Emitted when attachment download started. User can access basic file operations on downloaded content via the
        passed `Download` instance."""

    @typing.overload
    def on(
        self,
        event: Literal["filechooser"],
        f: typing.Callable[
            ["FileChooser"], "typing.Union[typing.Awaitable[None], None]"
        ],
    ) -> None:
        """
        Emitted when a file chooser is supposed to appear, such as after clicking the  `<input type=file>`. Playwright can
        respond to it via setting the input files using `file_chooser.set_files()` that can be uploaded after that.

        ```py
        page.on(\"filechooser\", lambda file_chooser: file_chooser.set_files(\"/tmp/myfile.pdf\"))
        ```"""

    @typing.overload
    def on(
        self,
        event: Literal["frameattached"],
        f: typing.Callable[["Frame"], "typing.Union[typing.Awaitable[None], None]"],
    ) -> None:
        """
        Emitted when a frame is attached."""

    @typing.overload
    def on(
        self,
        event: Literal["framedetached"],
        f: typing.Callable[["Frame"], "typing.Union[typing.Awaitable[None], None]"],
    ) -> None:
        """
        Emitted when a frame is detached."""

    @typing.overload
    def on(
        self,
        event: Literal["framenavigated"],
        f: typing.Callable[["Frame"], "typing.Union[typing.Awaitable[None], None]"],
    ) -> None:
        """
        Emitted when a frame is navigated to a new url."""

    @typing.overload
    def on(
        self,
        event: Literal["load"],
        f: typing.Callable[["Page"], "typing.Union[typing.Awaitable[None], None]"],
    ) -> None:
        """
        Emitted when the JavaScript [`load`](https://developer.mozilla.org/en-US/docs/Web/Events/load) event is dispatched.
        """

    @typing.overload
    def on(
        self,
        event: Literal["pageerror"],
        f: typing.Callable[["Error"], "typing.Union[typing.Awaitable[None], None]"],
    ) -> None:
        """
        Emitted when an uncaught exception happens within the page.

        ```py
        # Log all uncaught errors to the terminal
        page.on(\"pageerror\", lambda exc: print(f\"uncaught exception: {exc}\"))

        # Navigate to a page with an exception.
        await page.goto(\"data:text/html,<script>throw new Error('test')</script>\")
        ```"""

    @typing.overload
    def on(
        self,
        event: Literal["popup"],
        f: typing.Callable[["Page"], "typing.Union[typing.Awaitable[None], None]"],
    ) -> None:
        """
        Emitted when the page opens a new tab or window. This event is emitted in addition to the
        `browser_context.on('page')`, but only for popups relevant to this page.

        The earliest moment that page is available is when it has navigated to the initial url. For example, when opening a
        popup with `window.open('http://example.com')`, this event will fire when the network request to
        \"http://example.com\" is done and its response has started loading in the popup. If you would like to route/listen
        to this network request, use `browser_context.route()` and `browser_context.on('request')` respectively
        instead of similar methods on the `Page`.

        ```py
        async with page.expect_event(\"popup\") as page_info:
            await page.get_by_text(\"open the popup\").click()
        popup = await page_info.value
        print(await popup.evaluate(\"location.href\"))
        ```

        **NOTE** Use `page.wait_for_load_state()` to wait until the page gets to a particular state (you should not
        need it in most cases)."""

    @typing.overload
    def on(
        self,
        event: Literal["request"],
        f: typing.Callable[["Request"], "typing.Union[typing.Awaitable[None], None]"],
    ) -> None:
        """
        Emitted when a page issues a request. The [request] object is read-only. In order to intercept and mutate requests,
        see `page.route()` or `browser_context.route()`."""

    @typing.overload
    def on(
        self,
        event: Literal["requestfailed"],
        f: typing.Callable[["Request"], "typing.Union[typing.Awaitable[None], None]"],
    ) -> None:
        """
        Emitted when a request fails, for example by timing out.

        ```python
        page.on(\"requestfailed\", lambda request: print(request.url + \" \" + request.failure.error_text))
        ```

        **NOTE** HTTP Error responses, such as 404 or 503, are still successful responses from HTTP standpoint, so request
        will complete with `page.on('request_finished')` event and not with `page.on('request_failed')`. A request will
        only be considered failed when the client cannot get an HTTP response from the server, e.g. due to network error
        net::ERR_FAILED."""

    @typing.overload
    def on(
        self,
        event: Literal["requestfinished"],
        f: typing.Callable[["Request"], "typing.Union[typing.Awaitable[None], None]"],
    ) -> None:
        """
        Emitted when a request finishes successfully after downloading the response body. For a successful response, the
        sequence of events is `request`, `response` and `requestfinished`."""

    @typing.overload
    def on(
        self,
        event: Literal["response"],
        f: typing.Callable[["Response"], "typing.Union[typing.Awaitable[None], None]"],
    ) -> None:
        """
        Emitted when [response] status and headers are received for a request. For a successful response, the sequence of
        events is `request`, `response` and `requestfinished`."""

    @typing.overload
    def on(
        self,
        event: Literal["websocket"],
        f: typing.Callable[["WebSocket"], "typing.Union[typing.Awaitable[None], None]"],
    ) -> None:
        """
        Emitted when `WebSocket` request is sent."""

    @typing.overload
    def on(
        self,
        event: Literal["worker"],
        f: typing.Callable[["Worker"], "typing.Union[typing.Awaitable[None], None]"],
    ) -> None:
        """
        Emitted when a dedicated [WebWorker](https://developer.mozilla.org/en-US/docs/Web/API/Web_Workers_API) is spawned
        by the page."""

    def on(
        self,
        event: str,
        f: typing.Callable[..., typing.Union[typing.Awaitable[None], None]],
    ) -> None:
        return super().on(event=event, f=f)

    @typing.overload
    def once(
        self,
        event: Literal["close"],
        f: typing.Callable[["Page"], "typing.Union[typing.Awaitable[None], None]"],
    ) -> None:
        """
        Emitted when the page closes."""

    @typing.overload
    def once(
        self,
        event: Literal["console"],
        f: typing.Callable[
            ["ConsoleMessage"], "typing.Union[typing.Awaitable[None], None]"
        ],
    ) -> None:
        """
        Emitted when JavaScript within the page calls one of console API methods, e.g. `console.log` or `console.dir`.

        The arguments passed into `console.log` are available on the `ConsoleMessage` event handler argument.

        **Usage**

        ```py
        async def print_args(msg):
            values = []
            for arg in msg.args:
                values.append(await arg.json_value())
            print(values)

        page.on(\"console\", print_args)
        await page.evaluate(\"console.log('hello', 5, { foo: 'bar' })\")
        ```"""

    @typing.overload
    def once(
        self,
        event: Literal["crash"],
        f: typing.Callable[["Page"], "typing.Union[typing.Awaitable[None], None]"],
    ) -> None:
        """
        Emitted when the page crashes. Browser pages might crash if they try to allocate too much memory. When the page
        crashes, ongoing and subsequent operations will throw.

        The most common way to deal with crashes is to catch an exception:

        ```py
        try:
            # crash might happen during a click.
            await page.click(\"button\")
            # or while waiting for an event.
            await page.wait_for_event(\"popup\")
        except Error as e:
            pass
            # when the page crashes, exception message contains \"crash\".
        ```"""

    @typing.overload
    def once(
        self,
        event: Literal["dialog"],
        f: typing.Callable[["Dialog"], "typing.Union[typing.Awaitable[None], None]"],
    ) -> None:
        """
        Emitted when a JavaScript dialog appears, such as `alert`, `prompt`, `confirm` or `beforeunload`. Listener **must**
        either `dialog.accept()` or `dialog.dismiss()` the dialog - otherwise the page will
        [freeze](https://developer.mozilla.org/en-US/docs/Web/JavaScript/EventLoop#never_blocking) waiting for the dialog,
        and actions like click will never finish.

        **Usage**

        ```python
        page.on(\"dialog\", lambda dialog: dialog.accept())
        ```

        **NOTE** When no `page.on('dialog')` or `browser_context.on('dialog')` listeners are present, all dialogs are
        automatically dismissed."""

    @typing.overload
    def once(
        self,
        event: Literal["domcontentloaded"],
        f: typing.Callable[["Page"], "typing.Union[typing.Awaitable[None], None]"],
    ) -> None:
        """
        Emitted when the JavaScript
        [`DOMContentLoaded`](https://developer.mozilla.org/en-US/docs/Web/Events/DOMContentLoaded) event is dispatched.
        """

    @typing.overload
    def once(
        self,
        event: Literal["download"],
        f: typing.Callable[["Download"], "typing.Union[typing.Awaitable[None], None]"],
    ) -> None:
        """
        Emitted when attachment download started. User can access basic file operations on downloaded content via the
        passed `Download` instance."""

    @typing.overload
    def once(
        self,
        event: Literal["filechooser"],
        f: typing.Callable[
            ["FileChooser"], "typing.Union[typing.Awaitable[None], None]"
        ],
    ) -> None:
        """
        Emitted when a file chooser is supposed to appear, such as after clicking the  `<input type=file>`. Playwright can
        respond to it via setting the input files using `file_chooser.set_files()` that can be uploaded after that.

        ```py
        page.on(\"filechooser\", lambda file_chooser: file_chooser.set_files(\"/tmp/myfile.pdf\"))
        ```"""

    @typing.overload
    def once(
        self,
        event: Literal["frameattached"],
        f: typing.Callable[["Frame"], "typing.Union[typing.Awaitable[None], None]"],
    ) -> None:
        """
        Emitted when a frame is attached."""

    @typing.overload
    def once(
        self,
        event: Literal["framedetached"],
        f: typing.Callable[["Frame"], "typing.Union[typing.Awaitable[None], None]"],
    ) -> None:
        """
        Emitted when a frame is detached."""

    @typing.overload
    def once(
        self,
        event: Literal["framenavigated"],
        f: typing.Callable[["Frame"], "typing.Union[typing.Awaitable[None], None]"],
    ) -> None:
        """
        Emitted when a frame is navigated to a new url."""

    @typing.overload
    def once(
        self,
        event: Literal["load"],
        f: typing.Callable[["Page"], "typing.Union[typing.Awaitable[None], None]"],
    ) -> None:
        """
        Emitted when the JavaScript [`load`](https://developer.mozilla.org/en-US/docs/Web/Events/load) event is dispatched.
        """

    @typing.overload
    def once(
        self,
        event: Literal["pageerror"],
        f: typing.Callable[["Error"], "typing.Union[typing.Awaitable[None], None]"],
    ) -> None:
        """
        Emitted when an uncaught exception happens within the page.

        ```py
        # Log all uncaught errors to the terminal
        page.on(\"pageerror\", lambda exc: print(f\"uncaught exception: {exc}\"))

        # Navigate to a page with an exception.
        await page.goto(\"data:text/html,<script>throw new Error('test')</script>\")
        ```"""

    @typing.overload
    def once(
        self,
        event: Literal["popup"],
        f: typing.Callable[["Page"], "typing.Union[typing.Awaitable[None], None]"],
    ) -> None:
        """
        Emitted when the page opens a new tab or window. This event is emitted in addition to the
        `browser_context.on('page')`, but only for popups relevant to this page.

        The earliest moment that page is available is when it has navigated to the initial url. For example, when opening a
        popup with `window.open('http://example.com')`, this event will fire when the network request to
        \"http://example.com\" is done and its response has started loading in the popup. If you would like to route/listen
        to this network request, use `browser_context.route()` and `browser_context.on('request')` respectively
        instead of similar methods on the `Page`.

        ```py
        async with page.expect_event(\"popup\") as page_info:
            await page.get_by_text(\"open the popup\").click()
        popup = await page_info.value
        print(await popup.evaluate(\"location.href\"))
        ```

        **NOTE** Use `page.wait_for_load_state()` to wait until the page gets to a particular state (you should not
        need it in most cases)."""

    @typing.overload
    def once(
        self,
        event: Literal["request"],
        f: typing.Callable[["Request"], "typing.Union[typing.Awaitable[None], None]"],
    ) -> None:
        """
        Emitted when a page issues a request. The [request] object is read-only. In order to intercept and mutate requests,
        see `page.route()` or `browser_context.route()`."""

    @typing.overload
    def once(
        self,
        event: Literal["requestfailed"],
        f: typing.Callable[["Request"], "typing.Union[typing.Awaitable[None], None]"],
    ) -> None:
        """
        Emitted when a request fails, for example by timing out.

        ```python
        page.on(\"requestfailed\", lambda request: print(request.url + \" \" + request.failure.error_text))
        ```

        **NOTE** HTTP Error responses, such as 404 or 503, are still successful responses from HTTP standpoint, so request
        will complete with `page.on('request_finished')` event and not with `page.on('request_failed')`. A request will
        only be considered failed when the client cannot get an HTTP response from the server, e.g. due to network error
        net::ERR_FAILED."""

    @typing.overload
    def once(
        self,
        event: Literal["requestfinished"],
        f: typing.Callable[["Request"], "typing.Union[typing.Awaitable[None], None]"],
    ) -> None:
        """
        Emitted when a request finishes successfully after downloading the response body. For a successful response, the
        sequence of events is `request`, `response` and `requestfinished`."""

    @typing.overload
    def once(
        self,
        event: Literal["response"],
        f: typing.Callable[["Response"], "typing.Union[typing.Awaitable[None], None]"],
    ) -> None:
        """
        Emitted when [response] status and headers are received for a request. For a successful response, the sequence of
        events is `request`, `response` and `requestfinished`."""

    @typing.overload
    def once(
        self,
        event: Literal["websocket"],
        f: typing.Callable[["WebSocket"], "typing.Union[typing.Awaitable[None], None]"],
    ) -> None:
        """
        Emitted when `WebSocket` request is sent."""

    @typing.overload
    def once(
        self,
        event: Literal["worker"],
        f: typing.Callable[["Worker"], "typing.Union[typing.Awaitable[None], None]"],
    ) -> None:
        """
        Emitted when a dedicated [WebWorker](https://developer.mozilla.org/en-US/docs/Web/API/Web_Workers_API) is spawned
        by the page."""

    def once(
        self,
        event: str,
        f: typing.Callable[..., typing.Union[typing.Awaitable[None], None]],
    ) -> None:
        return super().once(event=event, f=f)

    @property
    def keyboard(self) -> "Keyboard":
        """Page.keyboard

        Returns
        -------
        Keyboard
        """
        return mapping.from_impl(self._impl_obj.keyboard)

    @property
    def mouse(self) -> "Mouse":
        """Page.mouse

        Returns
        -------
        Mouse
        """
        return mapping.from_impl(self._impl_obj.mouse)

    @property
    def touchscreen(self) -> "Touchscreen":
        """Page.touchscreen

        Returns
        -------
        Touchscreen
        """
        return mapping.from_impl(self._impl_obj.touchscreen)

    @property
    def context(self) -> "BrowserContext":
        """Page.context

        Get the browser context that the page belongs to.

        Returns
        -------
        BrowserContext
        """
        return mapping.from_impl(self._impl_obj.context)

    @property
    def clock(self) -> "Clock":
        """Page.clock

        Playwright has ability to mock clock and passage of time.

        Returns
        -------
        Clock
        """
        return mapping.from_impl(self._impl_obj.clock)

    @property
    def main_frame(self) -> "Frame":
        """Page.main_frame

        The page's main frame. Page is guaranteed to have a main frame which persists during navigations.

        Returns
        -------
        Frame
        """
        return mapping.from_impl(self._impl_obj.main_frame)

    @property
    def frames(self) -> typing.List["Frame"]:
        """Page.frames

        An array of all frames attached to the page.

        Returns
        -------
        List[Frame]
        """
        return mapping.from_impl_list(self._impl_obj.frames)

    @property
    def url(self) -> str:
        """Page.url

        Returns
        -------
        str
        """
        return mapping.from_maybe_impl(self._impl_obj.url)

    @property
    def viewport_size(self) -> typing.Optional[ViewportSize]:
        """Page.viewport_size

        Returns
        -------
        Union[{width: int, height: int}, None]
        """
        return mapping.from_impl_nullable(self._impl_obj.viewport_size)

    @property
    def workers(self) -> typing.List["Worker"]:
        """Page.workers

        This method returns all of the dedicated
        [WebWorkers](https://developer.mozilla.org/en-US/docs/Web/API/Web_Workers_API) associated with the page.

        **NOTE** This does not contain ServiceWorkers

        Returns
        -------
        List[Worker]
        """
        return mapping.from_impl_list(self._impl_obj.workers)

    @property
    def request(self) -> "APIRequestContext":
        """Page.request

        API testing helper associated with this page. This method returns the same instance as
        `browser_context.request` on the page's context. See `browser_context.request` for more
        details.

        Returns
        -------
        APIRequestContext
        """
        return mapping.from_impl(self._impl_obj.request)

    @property
    def video(self) -> typing.Optional["Video"]:
        """Page.video

        Video object associated with this page.

        Returns
        -------
        Union[Video, None]
        """
        return mapping.from_impl_nullable(self._impl_obj.video)

    async def opener(self) -> typing.Optional["Page"]:
        """Page.opener

        Returns the opener for popup pages and `null` for others. If the opener has been closed already the returns `null`.

        Returns
        -------
        Union[Page, None]
        """

        return mapping.from_impl_nullable(await self._impl_obj.opener())

    def frame(
        self,
        name: typing.Optional[str] = None,
        *,
        url: typing.Optional[
            typing.Union[str, typing.Pattern[str], typing.Callable[[str], bool]]
        ] = None,
    ) -> typing.Optional["Frame"]:
        """Page.frame

        Returns frame matching the specified criteria. Either `name` or `url` must be specified.

        **Usage**

        ```py
        frame = page.frame(name=\"frame-name\")
        ```

        Parameters
        ----------
        name : Union[str, None]
            Frame name specified in the `iframe`'s `name` attribute. Optional.
        url : Union[Callable[[str], bool], Pattern[str], str, None]
            A glob pattern, regex pattern or predicate receiving frame's `url` as a [URL] object. Optional.

        Returns
        -------
        Union[Frame, None]
        """

        return mapping.from_impl_nullable(
            self._impl_obj.frame(name=name, url=self._wrap_handler(url))
        )

    def set_default_navigation_timeout(self, timeout: float) -> None:
        """Page.set_default_navigation_timeout

        This setting will change the default maximum navigation time for the following methods and related shortcuts:
        - `page.go_back()`
        - `page.go_forward()`
        - `page.goto()`
        - `page.reload()`
        - `page.set_content()`
        - `page.expect_navigation()`
        - `page.wait_for_url()`

        **NOTE** `page.set_default_navigation_timeout()` takes priority over `page.set_default_timeout()`,
        `browser_context.set_default_timeout()` and `browser_context.set_default_navigation_timeout()`.

        Parameters
        ----------
        timeout : float
            Maximum navigation time in milliseconds
        """

        return mapping.from_maybe_impl(
            self._impl_obj.set_default_navigation_timeout(timeout=timeout)
        )

    def set_default_timeout(self, timeout: float) -> None:
        """Page.set_default_timeout

        This setting will change the default maximum time for all the methods accepting `timeout` option.

        **NOTE** `page.set_default_navigation_timeout()` takes priority over `page.set_default_timeout()`.

        Parameters
        ----------
        timeout : float
            Maximum time in milliseconds. Pass `0` to disable timeout.
        """

        return mapping.from_maybe_impl(
            self._impl_obj.set_default_timeout(timeout=timeout)
        )

    async def query_selector(
        self, selector: str, *, strict: typing.Optional[bool] = None
    ) -> typing.Optional["ElementHandle"]:
        """Page.query_selector

        The method finds an element matching the specified selector within the page. If no elements match the selector, the
        return value resolves to `null`. To wait for an element on the page, use `locator.wait_for()`.

        Parameters
        ----------
        selector : str
            A selector to query for.
        strict : Union[bool, None]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more than one
            element, the call throws an exception.

        Returns
        -------
        Union[ElementHandle, None]
        """

        return mapping.from_impl_nullable(
            await self._impl_obj.query_selector(selector=selector, strict=strict)
        )

    async def query_selector_all(self, selector: str) -> typing.List["ElementHandle"]:
        """Page.query_selector_all

        The method finds all elements matching the specified selector within the page. If no elements match the selector,
        the return value resolves to `[]`.

        Parameters
        ----------
        selector : str
            A selector to query for.

        Returns
        -------
        List[ElementHandle]
        """

        return mapping.from_impl_list(
            await self._impl_obj.query_selector_all(selector=selector)
        )

    async def wait_for_selector(
        self,
        selector: str,
        *,
        timeout: typing.Optional[float] = None,
        state: typing.Optional[
            Literal["attached", "detached", "hidden", "visible"]
        ] = None,
        strict: typing.Optional[bool] = None,
    ) -> typing.Optional["ElementHandle"]:
        """Page.wait_for_selector

        Returns when element specified by selector satisfies `state` option. Returns `null` if waiting for `hidden` or
        `detached`.

        **NOTE** Playwright automatically waits for element to be ready before performing an action. Using `Locator`
        objects and web-first assertions makes the code wait-for-selector-free.

        Wait for the `selector` to satisfy `state` option (either appear/disappear from dom, or become visible/hidden). If
        at the moment of calling the method `selector` already satisfies the condition, the method will return immediately.
        If the selector doesn't satisfy the condition for the `timeout` milliseconds, the function will throw.

        **Usage**

        This method works across navigations:

        ```py
        import asyncio
        from playwright.async_api import async_playwright, Playwright

        async def run(playwright: Playwright):
            chromium = playwright.chromium
            browser = await chromium.launch()
            page = await browser.new_page()
            for current_url in [\"https://google.com\", \"https://bbc.com\"]:
                await page.goto(current_url, wait_until=\"domcontentloaded\")
                element = await page.wait_for_selector(\"img\")
                print(\"Loaded image: \" + str(await element.get_attribute(\"src\")))
            await browser.close()

        async def main():
            async with async_playwright() as playwright:
                await run(playwright)
        asyncio.run(main())
        ```

        Parameters
        ----------
        selector : str
            A selector to query for.
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        state : Union["attached", "detached", "hidden", "visible", None]
            Defaults to `'visible'`. Can be either:
            - `'attached'` - wait for element to be present in DOM.
            - `'detached'` - wait for element to not be present in DOM.
            - `'visible'` - wait for element to have non-empty bounding box and no `visibility:hidden`. Note that element
              without any content or with `display:none` has an empty bounding box and is not considered visible.
            - `'hidden'` - wait for element to be either detached from DOM, or have an empty bounding box or
              `visibility:hidden`. This is opposite to the `'visible'` option.
        strict : Union[bool, None]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more than one
            element, the call throws an exception.

        Returns
        -------
        Union[ElementHandle, None]
        """

        return mapping.from_impl_nullable(
            await self._impl_obj.wait_for_selector(
                selector=selector, timeout=timeout, state=state, strict=strict
            )
        )

    async def is_checked(
        self,
        selector: str,
        *,
        strict: typing.Optional[bool] = None,
        timeout: typing.Optional[float] = None,
    ) -> bool:
        """Page.is_checked

        Returns whether the element is checked. Throws if the element is not a checkbox or radio input.

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be
            used.
        strict : Union[bool, None]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more than one
            element, the call throws an exception.
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.

        Returns
        -------
        bool
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.is_checked(
                selector=selector, strict=strict, timeout=timeout
            )
        )

    async def is_disabled(
        self,
        selector: str,
        *,
        strict: typing.Optional[bool] = None,
        timeout: typing.Optional[float] = None,
    ) -> bool:
        """Page.is_disabled

        Returns whether the element is disabled, the opposite of [enabled](https://playwright.dev/python/docs/actionability#enabled).

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be
            used.
        strict : Union[bool, None]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more than one
            element, the call throws an exception.
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.

        Returns
        -------
        bool
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.is_disabled(
                selector=selector, strict=strict, timeout=timeout
            )
        )

    async def is_editable(
        self,
        selector: str,
        *,
        strict: typing.Optional[bool] = None,
        timeout: typing.Optional[float] = None,
    ) -> bool:
        """Page.is_editable

        Returns whether the element is [editable](https://playwright.dev/python/docs/actionability#editable).

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be
            used.
        strict : Union[bool, None]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more than one
            element, the call throws an exception.
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.

        Returns
        -------
        bool
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.is_editable(
                selector=selector, strict=strict, timeout=timeout
            )
        )

    async def is_enabled(
        self,
        selector: str,
        *,
        strict: typing.Optional[bool] = None,
        timeout: typing.Optional[float] = None,
    ) -> bool:
        """Page.is_enabled

        Returns whether the element is [enabled](https://playwright.dev/python/docs/actionability#enabled).

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be
            used.
        strict : Union[bool, None]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more than one
            element, the call throws an exception.
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.

        Returns
        -------
        bool
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.is_enabled(
                selector=selector, strict=strict, timeout=timeout
            )
        )

    async def is_hidden(
        self,
        selector: str,
        *,
        strict: typing.Optional[bool] = None,
        timeout: typing.Optional[float] = None,
    ) -> bool:
        """Page.is_hidden

        Returns whether the element is hidden, the opposite of [visible](https://playwright.dev/python/docs/actionability#visible).  `selector` that
        does not match any elements is considered hidden.

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be
            used.
        strict : Union[bool, None]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more than one
            element, the call throws an exception.
        timeout : Union[float, None]
            Deprecated: This option is ignored. `page.is_hidden()` does not wait for the↵element to become hidden and returns immediately.

        Returns
        -------
        bool
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.is_hidden(
                selector=selector, strict=strict, timeout=timeout
            )
        )

    async def is_visible(
        self,
        selector: str,
        *,
        strict: typing.Optional[bool] = None,
        timeout: typing.Optional[float] = None,
    ) -> bool:
        """Page.is_visible

        Returns whether the element is [visible](https://playwright.dev/python/docs/actionability#visible). `selector` that does not match any elements
        is considered not visible.

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be
            used.
        strict : Union[bool, None]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more than one
            element, the call throws an exception.
        timeout : Union[float, None]
            Deprecated: This option is ignored. `page.is_visible()` does not wait↵for the element to become visible and returns immediately.

        Returns
        -------
        bool
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.is_visible(
                selector=selector, strict=strict, timeout=timeout
            )
        )

    async def dispatch_event(
        self,
        selector: str,
        type: str,
        event_init: typing.Optional[typing.Dict] = None,
        *,
        timeout: typing.Optional[float] = None,
        strict: typing.Optional[bool] = None,
    ) -> None:
        """Page.dispatch_event

        The snippet below dispatches the `click` event on the element. Regardless of the visibility state of the element,
        `click` is dispatched. This is equivalent to calling
        [element.click()](https://developer.mozilla.org/en-US/docs/Web/API/HTMLElement/click).

        **Usage**

        ```py
        await page.dispatch_event(\"button#submit\", \"click\")
        ```

        Under the hood, it creates an instance of an event based on the given `type`, initializes it with `eventInit`
        properties and dispatches it on the element. Events are `composed`, `cancelable` and bubble by default.

        Since `eventInit` is event-specific, please refer to the events documentation for the lists of initial properties:
        - [DeviceMotionEvent](https://developer.mozilla.org/en-US/docs/Web/API/DeviceMotionEvent/DeviceMotionEvent)
        - [DeviceOrientationEvent](https://developer.mozilla.org/en-US/docs/Web/API/DeviceOrientationEvent/DeviceOrientationEvent)
        - [DragEvent](https://developer.mozilla.org/en-US/docs/Web/API/DragEvent/DragEvent)
        - [Event](https://developer.mozilla.org/en-US/docs/Web/API/Event/Event)
        - [FocusEvent](https://developer.mozilla.org/en-US/docs/Web/API/FocusEvent/FocusEvent)
        - [KeyboardEvent](https://developer.mozilla.org/en-US/docs/Web/API/KeyboardEvent/KeyboardEvent)
        - [MouseEvent](https://developer.mozilla.org/en-US/docs/Web/API/MouseEvent/MouseEvent)
        - [PointerEvent](https://developer.mozilla.org/en-US/docs/Web/API/PointerEvent/PointerEvent)
        - [TouchEvent](https://developer.mozilla.org/en-US/docs/Web/API/TouchEvent/TouchEvent)
        - [WheelEvent](https://developer.mozilla.org/en-US/docs/Web/API/WheelEvent/WheelEvent)

        You can also specify `JSHandle` as the property value if you want live objects to be passed into the event:

        ```py
        # note you can only create data_transfer in chromium and firefox
        data_transfer = await page.evaluate_handle(\"new DataTransfer()\")
        await page.dispatch_event(\"#source\", \"dragstart\", { \"dataTransfer\": data_transfer })
        ```

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be
            used.
        type : str
            DOM event type: `"click"`, `"dragstart"`, etc.
        event_init : Union[Dict, None]
            Optional event-specific initialization properties.
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        strict : Union[bool, None]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more than one
            element, the call throws an exception.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.dispatch_event(
                selector=selector,
                type=type,
                eventInit=mapping.to_impl(event_init),
                timeout=timeout,
                strict=strict,
            )
        )

    async def evaluate(
        self, expression: str, arg: typing.Optional[typing.Any] = None
    ) -> typing.Any:
        """Page.evaluate

        Returns the value of the `expression` invocation.

        If the function passed to the `page.evaluate()` returns a [Promise], then `page.evaluate()` would
        wait for the promise to resolve and return its value.

        If the function passed to the `page.evaluate()` returns a non-[Serializable] value, then
        `page.evaluate()` resolves to `undefined`. Playwright also supports transferring some additional values
        that are not serializable by `JSON`: `-0`, `NaN`, `Infinity`, `-Infinity`.

        **Usage**

        Passing argument to `expression`:

        ```py
        result = await page.evaluate(\"([x, y]) => Promise.resolve(x * y)\", [7, 8])
        print(result) # prints \"56\"
        ```

        A string can also be passed in instead of a function:

        ```py
        print(await page.evaluate(\"1 + 2\")) # prints \"3\"
        x = 10
        print(await page.evaluate(f\"1 + {x}\")) # prints \"11\"
        ```

        `ElementHandle` instances can be passed as an argument to the `page.evaluate()`:

        ```py
        body_handle = await page.evaluate(\"document.body\")
        html = await page.evaluate(\"([body, suffix]) => body.innerHTML + suffix\", [body_handle, \"hello\"])
        await body_handle.dispose()
        ```

        Parameters
        ----------
        expression : str
            JavaScript expression to be evaluated in the browser context. If the expression evaluates to a function, the
            function is automatically invoked.
        arg : Union[Any, None]
            Optional argument to pass to `expression`.

        Returns
        -------
        Any
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.evaluate(
                expression=expression, arg=mapping.to_impl(arg)
            )
        )

    async def evaluate_handle(
        self, expression: str, arg: typing.Optional[typing.Any] = None
    ) -> "JSHandle":
        """Page.evaluate_handle

        Returns the value of the `expression` invocation as a `JSHandle`.

        The only difference between `page.evaluate()` and `page.evaluate_handle()` is that
        `page.evaluate_handle()` returns `JSHandle`.

        If the function passed to the `page.evaluate_handle()` returns a [Promise], then
        `page.evaluate_handle()` would wait for the promise to resolve and return its value.

        **Usage**

        ```py
        a_window_handle = await page.evaluate_handle(\"Promise.resolve(window)\")
        a_window_handle # handle for the window object.
        ```

        A string can also be passed in instead of a function:

        ```py
        a_handle = await page.evaluate_handle(\"document\") # handle for the \"document\"
        ```

        `JSHandle` instances can be passed as an argument to the `page.evaluate_handle()`:

        ```py
        a_handle = await page.evaluate_handle(\"document.body\")
        result_handle = await page.evaluate_handle(\"body => body.innerHTML\", a_handle)
        print(await result_handle.json_value())
        await result_handle.dispose()
        ```

        Parameters
        ----------
        expression : str
            JavaScript expression to be evaluated in the browser context. If the expression evaluates to a function, the
            function is automatically invoked.
        arg : Union[Any, None]
            Optional argument to pass to `expression`.

        Returns
        -------
        JSHandle
        """

        return mapping.from_impl(
            await self._impl_obj.evaluate_handle(
                expression=expression, arg=mapping.to_impl(arg)
            )
        )

    async def eval_on_selector(
        self,
        selector: str,
        expression: str,
        arg: typing.Optional[typing.Any] = None,
        *,
        strict: typing.Optional[bool] = None,
    ) -> typing.Any:
        """Page.eval_on_selector

        The method finds an element matching the specified selector within the page and passes it as a first argument to
        `expression`. If no elements match the selector, the method throws an error. Returns the value of `expression`.

        If `expression` returns a [Promise], then `page.eval_on_selector()` would wait for the promise to resolve and
        return its value.

        **Usage**

        ```py
        search_value = await page.eval_on_selector(\"#search\", \"el => el.value\")
        preload_href = await page.eval_on_selector(\"link[rel=preload]\", \"el => el.href\")
        html = await page.eval_on_selector(\".main-container\", \"(e, suffix) => e.outer_html + suffix\", \"hello\")
        ```

        Parameters
        ----------
        selector : str
            A selector to query for.
        expression : str
            JavaScript expression to be evaluated in the browser context. If the expression evaluates to a function, the
            function is automatically invoked.
        arg : Union[Any, None]
            Optional argument to pass to `expression`.
        strict : Union[bool, None]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more than one
            element, the call throws an exception.

        Returns
        -------
        Any
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.eval_on_selector(
                selector=selector,
                expression=expression,
                arg=mapping.to_impl(arg),
                strict=strict,
            )
        )

    async def eval_on_selector_all(
        self, selector: str, expression: str, arg: typing.Optional[typing.Any] = None
    ) -> typing.Any:
        """Page.eval_on_selector_all

        The method finds all elements matching the specified selector within the page and passes an array of matched
        elements as a first argument to `expression`. Returns the result of `expression` invocation.

        If `expression` returns a [Promise], then `page.eval_on_selector_all()` would wait for the promise to resolve
        and return its value.

        **Usage**

        ```py
        div_counts = await page.eval_on_selector_all(\"div\", \"(divs, min) => divs.length >= min\", 10)
        ```

        Parameters
        ----------
        selector : str
            A selector to query for.
        expression : str
            JavaScript expression to be evaluated in the browser context. If the expression evaluates to a function, the
            function is automatically invoked.
        arg : Union[Any, None]
            Optional argument to pass to `expression`.

        Returns
        -------
        Any
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.eval_on_selector_all(
                selector=selector, expression=expression, arg=mapping.to_impl(arg)
            )
        )

    async def add_script_tag(
        self,
        *,
        url: typing.Optional[str] = None,
        path: typing.Optional[typing.Union[pathlib.Path, str]] = None,
        content: typing.Optional[str] = None,
        type: typing.Optional[str] = None,
    ) -> "ElementHandle":
        """Page.add_script_tag

        Adds a `<script>` tag into the page with the desired url or content. Returns the added tag when the script's onload
        fires or when the script content was injected into frame.

        Parameters
        ----------
        url : Union[str, None]
            URL of a script to be added.
        path : Union[pathlib.Path, str, None]
            Path to the JavaScript file to be injected into frame. If `path` is a relative path, then it is resolved relative
            to the current working directory.
        content : Union[str, None]
            Raw JavaScript content to be injected into frame.
        type : Union[str, None]
            Script type. Use 'module' in order to load a JavaScript ES6 module. See
            [script](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/script) for more details.

        Returns
        -------
        ElementHandle
        """

        return mapping.from_impl(
            await self._impl_obj.add_script_tag(
                url=url, path=path, content=content, type=type
            )
        )

    async def add_style_tag(
        self,
        *,
        url: typing.Optional[str] = None,
        path: typing.Optional[typing.Union[pathlib.Path, str]] = None,
        content: typing.Optional[str] = None,
    ) -> "ElementHandle":
        """Page.add_style_tag

        Adds a `<link rel=\"stylesheet\">` tag into the page with the desired url or a `<style type=\"text/css\">` tag with the
        content. Returns the added tag when the stylesheet's onload fires or when the CSS content was injected into frame.

        Parameters
        ----------
        url : Union[str, None]
            URL of the `<link>` tag.
        path : Union[pathlib.Path, str, None]
            Path to the CSS file to be injected into frame. If `path` is a relative path, then it is resolved relative to the
            current working directory.
        content : Union[str, None]
            Raw CSS content to be injected into frame.

        Returns
        -------
        ElementHandle
        """

        return mapping.from_impl(
            await self._impl_obj.add_style_tag(url=url, path=path, content=content)
        )

    async def expose_function(self, name: str, callback: typing.Callable) -> None:
        """Page.expose_function

        The method adds a function called `name` on the `window` object of every frame in the page. When called, the
        function executes `callback` and returns a [Promise] which resolves to the return value of `callback`.

        If the `callback` returns a [Promise], it will be awaited.

        See `browser_context.expose_function()` for context-wide exposed function.

        **NOTE** Functions installed via `page.expose_function()` survive navigations.

        **Usage**

        An example of adding a `sha256` function to the page:

        ```py
        import asyncio
        import hashlib
        from playwright.async_api import async_playwright, Playwright

        def sha256(text):
            m = hashlib.sha256()
            m.update(bytes(text, \"utf8\"))
            return m.hexdigest()

        async def run(playwright: Playwright):
            webkit = playwright.webkit
            browser = await webkit.launch(headless=False)
            page = await browser.new_page()
            await page.expose_function(\"sha256\", sha256)
            await page.set_content(\"\"\"
                <script>
                  async function onClick() {
                    document.querySelector('div').textContent = await window.sha256('PLAYWRIGHT');
                  }
                </script>
                <button onclick=\"onClick()\">Click me</button>
                <div></div>
            \"\"\")
            await page.click(\"button\")

        async def main():
            async with async_playwright() as playwright:
                await run(playwright)
        asyncio.run(main())
        ```

        Parameters
        ----------
        name : str
            Name of the function on the window object
        callback : Callable
            Callback function which will be called in Playwright's context.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.expose_function(
                name=name, callback=self._wrap_handler(callback)
            )
        )

    async def expose_binding(
        self,
        name: str,
        callback: typing.Callable,
        *,
        handle: typing.Optional[bool] = None,
    ) -> None:
        """Page.expose_binding

        The method adds a function called `name` on the `window` object of every frame in this page. When called, the
        function executes `callback` and returns a [Promise] which resolves to the return value of `callback`. If the
        `callback` returns a [Promise], it will be awaited.

        The first argument of the `callback` function contains information about the caller: `{ browserContext:
        BrowserContext, page: Page, frame: Frame }`.

        See `browser_context.expose_binding()` for the context-wide version.

        **NOTE** Functions installed via `page.expose_binding()` survive navigations.

        **Usage**

        An example of exposing page URL to all frames in a page:

        ```py
        import asyncio
        from playwright.async_api import async_playwright, Playwright

        async def run(playwright: Playwright):
            webkit = playwright.webkit
            browser = await webkit.launch(headless=False)
            context = await browser.new_context()
            page = await context.new_page()
            await page.expose_binding(\"pageURL\", lambda source: source[\"page\"].url)
            await page.set_content(\"\"\"
            <script>
              async function onClick() {
                document.querySelector('div').textContent = await window.pageURL();
              }
            </script>
            <button onclick=\"onClick()\">Click me</button>
            <div></div>
            \"\"\")
            await page.click(\"button\")

        async def main():
            async with async_playwright() as playwright:
                await run(playwright)
        asyncio.run(main())
        ```

        Parameters
        ----------
        name : str
            Name of the function on the window object.
        callback : Callable
            Callback function that will be called in the Playwright's context.
        handle : Union[bool, None]
            Whether to pass the argument as a handle, instead of passing by value. When passing a handle, only one argument is
            supported. When passing by value, multiple arguments are supported.
            Deprecated: This option will be removed in the future.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.expose_binding(
                name=name, callback=self._wrap_handler(callback), handle=handle
            )
        )

    async def set_extra_http_headers(self, headers: typing.Dict[str, str]) -> None:
        """Page.set_extra_http_headers

        The extra HTTP headers will be sent with every request the page initiates.

        **NOTE** `page.set_extra_http_headers()` does not guarantee the order of headers in the outgoing requests.

        Parameters
        ----------
        headers : Dict[str, str]
            An object containing additional HTTP headers to be sent with every request. All header values must be strings.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.set_extra_http_headers(
                headers=mapping.to_impl(headers)
            )
        )

    async def content(self) -> str:
        """Page.content

        Gets the full HTML contents of the page, including the doctype.

        Returns
        -------
        str
        """

        return mapping.from_maybe_impl(await self._impl_obj.content())

    async def set_content(
        self,
        html: str,
        *,
        timeout: typing.Optional[float] = None,
        wait_until: typing.Optional[
            Literal["commit", "domcontentloaded", "load", "networkidle"]
        ] = None,
    ) -> None:
        """Page.set_content

        This method internally calls [document.write()](https://developer.mozilla.org/en-US/docs/Web/API/Document/write),
        inheriting all its specific characteristics and behaviors.

        Parameters
        ----------
        html : str
            HTML markup to assign to the page.
        timeout : Union[float, None]
            Maximum operation time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_navigation_timeout()`,
            `browser_context.set_default_timeout()`, `page.set_default_navigation_timeout()` or
            `page.set_default_timeout()` methods.
        wait_until : Union["commit", "domcontentloaded", "load", "networkidle", None]
            When to consider operation succeeded, defaults to `load`. Events can be either:
            - `'domcontentloaded'` - consider operation to be finished when the `DOMContentLoaded` event is fired.
            - `'load'` - consider operation to be finished when the `load` event is fired.
            - `'networkidle'` - **DISCOURAGED** consider operation to be finished when there are no network connections for
              at least `500` ms. Don't use this method for testing, rely on web assertions to assess readiness instead.
            - `'commit'` - consider operation to be finished when network response is received and the document started
              loading.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.set_content(
                html=html, timeout=timeout, waitUntil=wait_until
            )
        )

    async def goto(
        self,
        url: str,
        *,
        timeout: typing.Optional[float] = None,
        wait_until: typing.Optional[
            Literal["commit", "domcontentloaded", "load", "networkidle"]
        ] = None,
        referer: typing.Optional[str] = None,
    ) -> typing.Optional["Response"]:
        """Page.goto

        Returns the main resource response. In case of multiple redirects, the navigation will resolve with the first
        non-redirect response.

        The method will throw an error if:
        - there's an SSL error (e.g. in case of self-signed certificates).
        - target URL is invalid.
        - the `timeout` is exceeded during navigation.
        - the remote server does not respond or is unreachable.
        - the main resource failed to load.

        The method will not throw an error when any valid HTTP status code is returned by the remote server, including 404
        \"Not Found\" and 500 \"Internal Server Error\".  The status code for such responses can be retrieved by calling
        `response.status()`.

        **NOTE** The method either throws an error or returns a main resource response. The only exceptions are navigation
        to `about:blank` or navigation to the same URL with a different hash, which would succeed and return `null`.

        **NOTE** Headless mode doesn't support navigation to a PDF document. See the
        [upstream issue](https://bugs.chromium.org/p/chromium/issues/detail?id=761295).

        Parameters
        ----------
        url : str
            URL to navigate page to. The url should include scheme, e.g. `https://`. When a `baseURL` via the context options
            was provided and the passed URL is a path, it gets merged via the
            [`new URL()`](https://developer.mozilla.org/en-US/docs/Web/API/URL/URL) constructor.
        timeout : Union[float, None]
            Maximum operation time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_navigation_timeout()`,
            `browser_context.set_default_timeout()`, `page.set_default_navigation_timeout()` or
            `page.set_default_timeout()` methods.
        wait_until : Union["commit", "domcontentloaded", "load", "networkidle", None]
            When to consider operation succeeded, defaults to `load`. Events can be either:
            - `'domcontentloaded'` - consider operation to be finished when the `DOMContentLoaded` event is fired.
            - `'load'` - consider operation to be finished when the `load` event is fired.
            - `'networkidle'` - **DISCOURAGED** consider operation to be finished when there are no network connections for
              at least `500` ms. Don't use this method for testing, rely on web assertions to assess readiness instead.
            - `'commit'` - consider operation to be finished when network response is received and the document started
              loading.
        referer : Union[str, None]
            Referer header value. If provided it will take preference over the referer header value set by
            `page.set_extra_http_headers()`.

        Returns
        -------
        Union[Response, None]
        """

        return mapping.from_impl_nullable(
            await self._impl_obj.goto(
                url=url, timeout=timeout, waitUntil=wait_until, referer=referer
            )
        )

    async def reload(
        self,
        *,
        timeout: typing.Optional[float] = None,
        wait_until: typing.Optional[
            Literal["commit", "domcontentloaded", "load", "networkidle"]
        ] = None,
    ) -> typing.Optional["Response"]:
        """Page.reload

        This method reloads the current page, in the same way as if the user had triggered a browser refresh. Returns the
        main resource response. In case of multiple redirects, the navigation will resolve with the response of the last
        redirect.

        Parameters
        ----------
        timeout : Union[float, None]
            Maximum operation time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_navigation_timeout()`,
            `browser_context.set_default_timeout()`, `page.set_default_navigation_timeout()` or
            `page.set_default_timeout()` methods.
        wait_until : Union["commit", "domcontentloaded", "load", "networkidle", None]
            When to consider operation succeeded, defaults to `load`. Events can be either:
            - `'domcontentloaded'` - consider operation to be finished when the `DOMContentLoaded` event is fired.
            - `'load'` - consider operation to be finished when the `load` event is fired.
            - `'networkidle'` - **DISCOURAGED** consider operation to be finished when there are no network connections for
              at least `500` ms. Don't use this method for testing, rely on web assertions to assess readiness instead.
            - `'commit'` - consider operation to be finished when network response is received and the document started
              loading.

        Returns
        -------
        Union[Response, None]
        """

        return mapping.from_impl_nullable(
            await self._impl_obj.reload(timeout=timeout, waitUntil=wait_until)
        )

    async def wait_for_load_state(
        self,
        state: typing.Optional[
            Literal["domcontentloaded", "load", "networkidle"]
        ] = None,
        *,
        timeout: typing.Optional[float] = None,
    ) -> None:
        """Page.wait_for_load_state

        Returns when the required load state has been reached.

        This resolves when the page reaches a required load state, `load` by default. The navigation must have been
        committed when this method is called. If current document has already reached the required state, resolves
        immediately.

        **NOTE** Most of the time, this method is not needed because Playwright
        [auto-waits before every action](https://playwright.dev/python/docs/actionability).

        **Usage**

        ```py
        await page.get_by_role(\"button\").click() # click triggers navigation.
        await page.wait_for_load_state() # the promise resolves after \"load\" event.
        ```

        ```py
        async with page.expect_popup() as page_info:
            await page.get_by_role(\"button\").click() # click triggers a popup.
        popup = await page_info.value
        # Wait for the \"DOMContentLoaded\" event.
        await popup.wait_for_load_state(\"domcontentloaded\")
        print(await popup.title()) # popup is ready to use.
        ```

        Parameters
        ----------
        state : Union["domcontentloaded", "load", "networkidle", None]
            Optional load state to wait for, defaults to `load`. If the state has been already reached while loading current
            document, the method resolves immediately. Can be one of:
            - `'load'` - wait for the `load` event to be fired.
            - `'domcontentloaded'` - wait for the `DOMContentLoaded` event to be fired.
            - `'networkidle'` - **DISCOURAGED** wait until there are no network connections for at least `500` ms. Don't use
              this method for testing, rely on web assertions to assess readiness instead.
        timeout : Union[float, None]
            Maximum operation time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_navigation_timeout()`,
            `browser_context.set_default_timeout()`, `page.set_default_navigation_timeout()` or
            `page.set_default_timeout()` methods.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.wait_for_load_state(state=state, timeout=timeout)
        )

    async def wait_for_url(
        self,
        url: typing.Union[str, typing.Pattern[str], typing.Callable[[str], bool]],
        *,
        wait_until: typing.Optional[
            Literal["commit", "domcontentloaded", "load", "networkidle"]
        ] = None,
        timeout: typing.Optional[float] = None,
    ) -> None:
        """Page.wait_for_url

        Waits for the main frame to navigate to the given URL.

        **Usage**

        ```py
        await page.click(\"a.delayed-navigation\") # clicking the link will indirectly cause a navigation
        await page.wait_for_url(\"**/target.html\")
        ```

        Parameters
        ----------
        url : Union[Callable[[str], bool], Pattern[str], str]
            A glob pattern, regex pattern or predicate receiving [URL] to match while waiting for the navigation. Note that if
            the parameter is a string without wildcard characters, the method will wait for navigation to URL that is exactly
            equal to the string.
        wait_until : Union["commit", "domcontentloaded", "load", "networkidle", None]
            When to consider operation succeeded, defaults to `load`. Events can be either:
            - `'domcontentloaded'` - consider operation to be finished when the `DOMContentLoaded` event is fired.
            - `'load'` - consider operation to be finished when the `load` event is fired.
            - `'networkidle'` - **DISCOURAGED** consider operation to be finished when there are no network connections for
              at least `500` ms. Don't use this method for testing, rely on web assertions to assess readiness instead.
            - `'commit'` - consider operation to be finished when network response is received and the document started
              loading.
        timeout : Union[float, None]
            Maximum operation time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_navigation_timeout()`,
            `browser_context.set_default_timeout()`, `page.set_default_navigation_timeout()` or
            `page.set_default_timeout()` methods.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.wait_for_url(
                url=self._wrap_handler(url), waitUntil=wait_until, timeout=timeout
            )
        )

    async def wait_for_event(
        self,
        event: str,
        predicate: typing.Optional[typing.Callable] = None,
        *,
        timeout: typing.Optional[float] = None,
    ) -> typing.Any:
        """Page.wait_for_event

        **NOTE** In most cases, you should use `page.expect_event()`.

        Waits for given `event` to fire. If predicate is provided, it passes event's value into the `predicate` function
        and waits for `predicate(event)` to return a truthy value. Will throw an error if the page is closed before the
        `event` is fired.

        Parameters
        ----------
        event : str
            Event name, same one typically passed into `*.on(event)`.
        predicate : Union[Callable, None]
            Receives the event data and resolves to truthy value when the waiting should resolve.
        timeout : Union[float, None]
            Maximum time to wait for in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The
            default value can be changed by using the `browser_context.set_default_timeout()`.

        Returns
        -------
        Any
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.wait_for_event(
                event=event, predicate=self._wrap_handler(predicate), timeout=timeout
            )
        )

    async def go_back(
        self,
        *,
        timeout: typing.Optional[float] = None,
        wait_until: typing.Optional[
            Literal["commit", "domcontentloaded", "load", "networkidle"]
        ] = None,
    ) -> typing.Optional["Response"]:
        """Page.go_back

        Returns the main resource response. In case of multiple redirects, the navigation will resolve with the response of
        the last redirect. If cannot go back, returns `null`.

        Navigate to the previous page in history.

        Parameters
        ----------
        timeout : Union[float, None]
            Maximum operation time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_navigation_timeout()`,
            `browser_context.set_default_timeout()`, `page.set_default_navigation_timeout()` or
            `page.set_default_timeout()` methods.
        wait_until : Union["commit", "domcontentloaded", "load", "networkidle", None]
            When to consider operation succeeded, defaults to `load`. Events can be either:
            - `'domcontentloaded'` - consider operation to be finished when the `DOMContentLoaded` event is fired.
            - `'load'` - consider operation to be finished when the `load` event is fired.
            - `'networkidle'` - **DISCOURAGED** consider operation to be finished when there are no network connections for
              at least `500` ms. Don't use this method for testing, rely on web assertions to assess readiness instead.
            - `'commit'` - consider operation to be finished when network response is received and the document started
              loading.

        Returns
        -------
        Union[Response, None]
        """

        return mapping.from_impl_nullable(
            await self._impl_obj.go_back(timeout=timeout, waitUntil=wait_until)
        )

    async def go_forward(
        self,
        *,
        timeout: typing.Optional[float] = None,
        wait_until: typing.Optional[
            Literal["commit", "domcontentloaded", "load", "networkidle"]
        ] = None,
    ) -> typing.Optional["Response"]:
        """Page.go_forward

        Returns the main resource response. In case of multiple redirects, the navigation will resolve with the response of
        the last redirect. If cannot go forward, returns `null`.

        Navigate to the next page in history.

        Parameters
        ----------
        timeout : Union[float, None]
            Maximum operation time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_navigation_timeout()`,
            `browser_context.set_default_timeout()`, `page.set_default_navigation_timeout()` or
            `page.set_default_timeout()` methods.
        wait_until : Union["commit", "domcontentloaded", "load", "networkidle", None]
            When to consider operation succeeded, defaults to `load`. Events can be either:
            - `'domcontentloaded'` - consider operation to be finished when the `DOMContentLoaded` event is fired.
            - `'load'` - consider operation to be finished when the `load` event is fired.
            - `'networkidle'` - **DISCOURAGED** consider operation to be finished when there are no network connections for
              at least `500` ms. Don't use this method for testing, rely on web assertions to assess readiness instead.
            - `'commit'` - consider operation to be finished when network response is received and the document started
              loading.

        Returns
        -------
        Union[Response, None]
        """

        return mapping.from_impl_nullable(
            await self._impl_obj.go_forward(timeout=timeout, waitUntil=wait_until)
        )

    async def request_gc(self) -> None:
        """Page.request_gc

        Request the page to perform garbage collection. Note that there is no guarantee that all unreachable objects will
        be collected.

        This is useful to help detect memory leaks. For example, if your page has a large object `'suspect'` that might be
        leaked, you can check that it does not leak by using a
        [`WeakRef`](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/WeakRef).

        ```py
        # 1. In your page, save a WeakRef for the \"suspect\".
        await page.evaluate(\"globalThis.suspectWeakRef = new WeakRef(suspect)\")
        # 2. Request garbage collection.
        await page.request_gc()
        # 3. Check that weak ref does not deref to the original object.
        assert await page.evaluate(\"!globalThis.suspectWeakRef.deref()\")
        ```
        """

        return mapping.from_maybe_impl(await self._impl_obj.request_gc())

    async def emulate_media(
        self,
        *,
        media: typing.Optional[Literal["null", "print", "screen"]] = None,
        color_scheme: typing.Optional[
            Literal["dark", "light", "no-preference", "null"]
        ] = None,
        reduced_motion: typing.Optional[
            Literal["no-preference", "null", "reduce"]
        ] = None,
        forced_colors: typing.Optional[Literal["active", "none", "null"]] = None,
        contrast: typing.Optional[Literal["more", "no-preference", "null"]] = None,
    ) -> None:
        """Page.emulate_media

        This method changes the `CSS media type` through the `media` argument, and/or the `'prefers-colors-scheme'` media
        feature, using the `colorScheme` argument.

        **Usage**

        ```py
        await page.evaluate(\"matchMedia('screen').matches\")
        # → True
        await page.evaluate(\"matchMedia('print').matches\")
        # → False

        await page.emulate_media(media=\"print\")
        await page.evaluate(\"matchMedia('screen').matches\")
        # → False
        await page.evaluate(\"matchMedia('print').matches\")
        # → True

        await page.emulate_media()
        await page.evaluate(\"matchMedia('screen').matches\")
        # → True
        await page.evaluate(\"matchMedia('print').matches\")
        # → False
        ```

        ```py
        await page.emulate_media(color_scheme=\"dark\")
        await page.evaluate(\"matchMedia('(prefers-color-scheme: dark)').matches\")
        # → True
        await page.evaluate(\"matchMedia('(prefers-color-scheme: light)').matches\")
        # → False
        ```

        Parameters
        ----------
        media : Union["null", "print", "screen", None]
            Changes the CSS media type of the page. The only allowed values are `'Screen'`, `'Print'` and `'Null'`. Passing
            `'Null'` disables CSS media emulation.
        color_scheme : Union["dark", "light", "no-preference", "null", None]
            Emulates [prefers-colors-scheme](https://developer.mozilla.org/en-US/docs/Web/CSS/@media/prefers-color-scheme)
            media feature, supported values are `'light'` and `'dark'`. Passing `'Null'` disables color scheme emulation.
            `'no-preference'` is deprecated.
        reduced_motion : Union["no-preference", "null", "reduce", None]
            Emulates `'prefers-reduced-motion'` media feature, supported values are `'reduce'`, `'no-preference'`. Passing
            `null` disables reduced motion emulation.
        forced_colors : Union["active", "none", "null", None]
        contrast : Union["more", "no-preference", "null", None]
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.emulate_media(
                media=media,
                colorScheme=color_scheme,
                reducedMotion=reduced_motion,
                forcedColors=forced_colors,
                contrast=contrast,
            )
        )

    async def set_viewport_size(self, viewport_size: ViewportSize) -> None:
        """Page.set_viewport_size

        In the case of multiple pages in a single browser, each page can have its own viewport size. However,
        `browser.new_context()` allows to set viewport size (and more) for all pages in the context at once.

        `page.set_viewport_size()` will resize the page. A lot of websites don't expect phones to change size, so you
        should set the viewport size before navigating to the page. `page.set_viewport_size()` will also reset
        `screen` size, use `browser.new_context()` with `screen` and `viewport` parameters if you need better
        control of these properties.

        **Usage**

        ```py
        page = await browser.new_page()
        await page.set_viewport_size({\"width\": 640, \"height\": 480})
        await page.goto(\"https://example.com\")
        ```

        Parameters
        ----------
        viewport_size : {width: int, height: int}
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.set_viewport_size(viewportSize=viewport_size)
        )

    async def bring_to_front(self) -> None:
        """Page.bring_to_front

        Brings page to front (activates tab).
        """

        return mapping.from_maybe_impl(await self._impl_obj.bring_to_front())

    async def add_init_script(
        self,
        script: typing.Optional[str] = None,
        *,
        path: typing.Optional[typing.Union[pathlib.Path, str]] = None,
    ) -> None:
        """Page.add_init_script

        Adds a script which would be evaluated in one of the following scenarios:
        - Whenever the page is navigated.
        - Whenever the child frame is attached or navigated. In this case, the script is evaluated in the context of the
          newly attached frame.

        The script is evaluated after the document was created but before any of its scripts were run. This is useful to
        amend the JavaScript environment, e.g. to seed `Math.random`.

        **Usage**

        An example of overriding `Math.random` before the page loads:

        ```py
        # in your playwright script, assuming the preload.js file is in same directory
        await page.add_init_script(path=\"./preload.js\")
        ```

        **NOTE** The order of evaluation of multiple scripts installed via `browser_context.add_init_script()` and
        `page.add_init_script()` is not defined.

        Parameters
        ----------
        script : Union[str, None]
            Script to be evaluated in all pages in the browser context. Optional.
        path : Union[pathlib.Path, str, None]
            Path to the JavaScript file. If `path` is a relative path, then it is resolved relative to the current working
            directory. Optional.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.add_init_script(script=script, path=path)
        )

    async def route(
        self,
        url: typing.Union[str, typing.Pattern[str], typing.Callable[[str], bool]],
        handler: typing.Union[
            typing.Callable[["Route"], typing.Any],
            typing.Callable[["Route", "Request"], typing.Any],
        ],
        *,
        times: typing.Optional[int] = None,
    ) -> None:
        """Page.route

        Routing provides the capability to modify network requests that are made by a page.

        Once routing is enabled, every request matching the url pattern will stall unless it's continued, fulfilled or
        aborted.

        **NOTE** The handler will only be called for the first url if the response is a redirect.

        **NOTE** `page.route()` will not intercept requests intercepted by Service Worker. See
        [this](https://github.com/microsoft/playwright/issues/1090) issue. We recommend disabling Service Workers when
        using request interception by setting `serviceWorkers` to `'block'`.

        **NOTE** `page.route()` will not intercept the first request of a popup page. Use
        `browser_context.route()` instead.

        **Usage**

        An example of a naive handler that aborts all image requests:

        ```py
        page = await browser.new_page()
        await page.route(\"**/*.{png,jpg,jpeg}\", lambda route: route.abort())
        await page.goto(\"https://example.com\")
        await browser.close()
        ```

        or the same snippet using a regex pattern instead:

        ```py
        page = await browser.new_page()
        await page.route(re.compile(r\"(\\.png$)|(\\.jpg$)\"), lambda route: route.abort())
        await page.goto(\"https://example.com\")
        await browser.close()
        ```

        It is possible to examine the request to decide the route action. For example, mocking all requests that contain
        some post data, and leaving all other requests as is:

        ```py
        async def handle_route(route: Route):
          if (\"my-string\" in route.request.post_data):
            await route.fulfill(body=\"mocked-data\")
          else:
            await route.continue_()
        await page.route(\"/api/**\", handle_route)
        ```

        Page routes take precedence over browser context routes (set up with `browser_context.route()`) when request
        matches both handlers.

        To remove a route with its handler you can use `page.unroute()`.

        **NOTE** Enabling routing disables http cache.

        Parameters
        ----------
        url : Union[Callable[[str], bool], Pattern[str], str]
            A glob pattern, regex pattern, or predicate that receives a [URL] to match during routing. If `baseURL` is set in
            the context options and the provided URL is a string that does not start with `*`, it is resolved using the
            [`new URL()`](https://developer.mozilla.org/en-US/docs/Web/API/URL/URL) constructor.
        handler : Union[Callable[[Route, Request], Any], Callable[[Route], Any]]
            handler function to route the request.
        times : Union[int, None]
            How often a route should be used. By default it will be used every time.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.route(
                url=self._wrap_handler(url),
                handler=self._wrap_handler(handler),
                times=times,
            )
        )

    async def unroute(
        self,
        url: typing.Union[str, typing.Pattern[str], typing.Callable[[str], bool]],
        handler: typing.Optional[
            typing.Union[
                typing.Callable[["Route"], typing.Any],
                typing.Callable[["Route", "Request"], typing.Any],
            ]
        ] = None,
    ) -> None:
        """Page.unroute

        Removes a route created with `page.route()`. When `handler` is not specified, removes all routes for the
        `url`.

        Parameters
        ----------
        url : Union[Callable[[str], bool], Pattern[str], str]
            A glob pattern, regex pattern or predicate receiving [URL] to match while routing.
        handler : Union[Callable[[Route, Request], Any], Callable[[Route], Any], None]
            Optional handler function to route the request.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.unroute(
                url=self._wrap_handler(url), handler=self._wrap_handler(handler)
            )
        )

    async def route_web_socket(
        self,
        url: typing.Union[str, typing.Pattern[str], typing.Callable[[str], bool]],
        handler: typing.Callable[["WebSocketRoute"], typing.Any],
    ) -> None:
        """Page.route_web_socket

        This method allows to modify websocket connections that are made by the page.

        Note that only `WebSocket`s created after this method was called will be routed. It is recommended to call this
        method before navigating the page.

        **Usage**

        Below is an example of a simple mock that responds to a single message. See `WebSocketRoute` for more details and
        examples.

        ```py
        def message_handler(ws: WebSocketRoute, message: Union[str, bytes]):
          if message == \"request\":
            ws.send(\"response\")

        def handler(ws: WebSocketRoute):
          ws.on_message(lambda message: message_handler(ws, message))

        await page.route_web_socket(\"/ws\", handler)
        ```

        Parameters
        ----------
        url : Union[Callable[[str], bool], Pattern[str], str]
            Only WebSockets with the url matching this pattern will be routed. A string pattern can be relative to the
            `baseURL` context option.
        handler : Callable[[WebSocketRoute], Any]
            Handler function to route the WebSocket.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.route_web_socket(
                url=self._wrap_handler(url), handler=self._wrap_handler(handler)
            )
        )

    async def unroute_all(
        self,
        *,
        behavior: typing.Optional[Literal["default", "ignoreErrors", "wait"]] = None,
    ) -> None:
        """Page.unroute_all

        Removes all routes created with `page.route()` and `page.route_from_har()`.

        Parameters
        ----------
        behavior : Union["default", "ignoreErrors", "wait", None]
            Specifies whether to wait for already running handlers and what to do if they throw errors:
            - `'default'` - do not wait for current handler calls (if any) to finish, if unrouted handler throws, it may
              result in unhandled error
            - `'wait'` - wait for current handler calls (if any) to finish
            - `'ignoreErrors'` - do not wait for current handler calls (if any) to finish, all errors thrown by the handlers
              after unrouting are silently caught
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.unroute_all(behavior=behavior)
        )

    async def route_from_har(
        self,
        har: typing.Union[pathlib.Path, str],
        *,
        url: typing.Optional[typing.Union[typing.Pattern[str], str]] = None,
        not_found: typing.Optional[Literal["abort", "fallback"]] = None,
        update: typing.Optional[bool] = None,
        update_content: typing.Optional[Literal["attach", "embed"]] = None,
        update_mode: typing.Optional[Literal["full", "minimal"]] = None,
    ) -> None:
        """Page.route_from_har

        If specified the network requests that are made in the page will be served from the HAR file. Read more about
        [Replaying from HAR](https://playwright.dev/python/docs/mock#replaying-from-har).

        Playwright will not serve requests intercepted by Service Worker from the HAR file. See
        [this](https://github.com/microsoft/playwright/issues/1090) issue. We recommend disabling Service Workers when
        using request interception by setting `serviceWorkers` to `'block'`.

        Parameters
        ----------
        har : Union[pathlib.Path, str]
            Path to a [HAR](http://www.softwareishard.com/blog/har-12-spec) file with prerecorded network data. If `path` is a
            relative path, then it is resolved relative to the current working directory.
        url : Union[Pattern[str], str, None]
            A glob pattern, regular expression or predicate to match the request URL. Only requests with URL matching the
            pattern will be served from the HAR file. If not specified, all requests are served from the HAR file.
        not_found : Union["abort", "fallback", None]
            - If set to 'abort' any request not found in the HAR file will be aborted.
            - If set to 'fallback' missing requests will be sent to the network.

            Defaults to abort.
        update : Union[bool, None]
            If specified, updates the given HAR with the actual network information instead of serving from file. The file is
            written to disk when `browser_context.close()` is called.
        update_content : Union["attach", "embed", None]
            Optional setting to control resource content management. If `attach` is specified, resources are persisted as
            separate files or entries in the ZIP archive. If `embed` is specified, content is stored inline the HAR file.
        update_mode : Union["full", "minimal", None]
            When set to `minimal`, only record information necessary for routing from HAR. This omits sizes, timing, page,
            cookies, security and other types of HAR information that are not used when replaying from HAR. Defaults to
            `minimal`.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.route_from_har(
                har=har,
                url=url,
                notFound=not_found,
                update=update,
                updateContent=update_content,
                updateMode=update_mode,
            )
        )

    async def screenshot(
        self,
        *,
        timeout: typing.Optional[float] = None,
        type: typing.Optional[Literal["jpeg", "png"]] = None,
        path: typing.Optional[typing.Union[pathlib.Path, str]] = None,
        quality: typing.Optional[int] = None,
        omit_background: typing.Optional[bool] = None,
        full_page: typing.Optional[bool] = None,
        clip: typing.Optional[FloatRect] = None,
        animations: typing.Optional[Literal["allow", "disabled"]] = None,
        caret: typing.Optional[Literal["hide", "initial"]] = None,
        scale: typing.Optional[Literal["css", "device"]] = None,
        mask: typing.Optional[typing.Sequence["Locator"]] = None,
        mask_color: typing.Optional[str] = None,
        style: typing.Optional[str] = None,
    ) -> bytes:
        """Page.screenshot

        Returns the buffer with the captured screenshot.

        Parameters
        ----------
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        type : Union["jpeg", "png", None]
            Specify screenshot type, defaults to `png`.
        path : Union[pathlib.Path, str, None]
            The file path to save the image to. The screenshot type will be inferred from file extension. If `path` is a
            relative path, then it is resolved relative to the current working directory. If no path is provided, the image
            won't be saved to the disk.
        quality : Union[int, None]
            The quality of the image, between 0-100. Not applicable to `png` images.
        omit_background : Union[bool, None]
            Hides default white background and allows capturing screenshots with transparency. Not applicable to `jpeg` images.
            Defaults to `false`.
        full_page : Union[bool, None]
            When true, takes a screenshot of the full scrollable page, instead of the currently visible viewport. Defaults to
            `false`.
        clip : Union[{x: float, y: float, width: float, height: float}, None]
            An object which specifies clipping of the resulting image.
        animations : Union["allow", "disabled", None]
            When set to `"disabled"`, stops CSS animations, CSS transitions and Web Animations. Animations get different
            treatment depending on their duration:
            - finite animations are fast-forwarded to completion, so they'll fire `transitionend` event.
            - infinite animations are canceled to initial state, and then played over after the screenshot.

            Defaults to `"allow"` that leaves animations untouched.
        caret : Union["hide", "initial", None]
            When set to `"hide"`, screenshot will hide text caret. When set to `"initial"`, text caret behavior will not be
            changed.  Defaults to `"hide"`.
        scale : Union["css", "device", None]
            When set to `"css"`, screenshot will have a single pixel per each css pixel on the page. For high-dpi devices, this
            will keep screenshots small. Using `"device"` option will produce a single pixel per each device pixel, so
            screenshots of high-dpi devices will be twice as large or even larger.

            Defaults to `"device"`.
        mask : Union[Sequence[Locator], None]
            Specify locators that should be masked when the screenshot is taken. Masked elements will be overlaid with a pink
            box `#FF00FF` (customized by `maskColor`) that completely covers its bounding box. The mask is also applied to
            invisible elements, see [Matching only visible elements](../locators.md#matching-only-visible-elements) to disable
            that.
        mask_color : Union[str, None]
            Specify the color of the overlay box for masked elements, in
            [CSS color format](https://developer.mozilla.org/en-US/docs/Web/CSS/color_value). Default color is pink `#FF00FF`.
        style : Union[str, None]
            Text of the stylesheet to apply while making the screenshot. This is where you can hide dynamic elements, make
            elements invisible or change their properties to help you creating repeatable screenshots. This stylesheet pierces
            the Shadow DOM and applies to the inner frames.

        Returns
        -------
        bytes
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.screenshot(
                timeout=timeout,
                type=type,
                path=path,
                quality=quality,
                omitBackground=omit_background,
                fullPage=full_page,
                clip=clip,
                animations=animations,
                caret=caret,
                scale=scale,
                mask=mapping.to_impl(mask),
                maskColor=mask_color,
                style=style,
            )
        )

    async def title(self) -> str:
        """Page.title

        Returns the page's title.

        Returns
        -------
        str
        """

        return mapping.from_maybe_impl(await self._impl_obj.title())

    async def close(
        self,
        *,
        run_before_unload: typing.Optional[bool] = None,
        reason: typing.Optional[str] = None,
    ) -> None:
        """Page.close

        If `runBeforeUnload` is `false`, does not run any unload handlers and waits for the page to be closed. If
        `runBeforeUnload` is `true` the method will run unload handlers, but will **not** wait for the page to close.

        By default, `page.close()` **does not** run `beforeunload` handlers.

        **NOTE** if `runBeforeUnload` is passed as true, a `beforeunload` dialog might be summoned and should be handled
        manually via `page.on('dialog')` event.

        Parameters
        ----------
        run_before_unload : Union[bool, None]
            Defaults to `false`. Whether to run the
            [before unload](https://developer.mozilla.org/en-US/docs/Web/Events/beforeunload) page handlers.
        reason : Union[str, None]
            The reason to be reported to the operations interrupted by the page closure.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.close(runBeforeUnload=run_before_unload, reason=reason)
        )

    def is_closed(self) -> bool:
        """Page.is_closed

        Indicates that the page has been closed.

        Returns
        -------
        bool
        """

        return mapping.from_maybe_impl(self._impl_obj.is_closed())

    async def click(
        self,
        selector: str,
        *,
        modifiers: typing.Optional[
            typing.Sequence[Literal["Alt", "Control", "ControlOrMeta", "Meta", "Shift"]]
        ] = None,
        position: typing.Optional[Position] = None,
        delay: typing.Optional[float] = None,
        button: typing.Optional[Literal["left", "middle", "right"]] = None,
        click_count: typing.Optional[int] = None,
        timeout: typing.Optional[float] = None,
        force: typing.Optional[bool] = None,
        no_wait_after: typing.Optional[bool] = None,
        trial: typing.Optional[bool] = None,
        strict: typing.Optional[bool] = None,
    ) -> None:
        """Page.click

        This method clicks an element matching `selector` by performing the following steps:
        1. Find an element matching `selector`. If there is none, wait until a matching element is attached to the DOM.
        1. Wait for [actionability](https://playwright.dev/python/docs/actionability) checks on the matched element, unless `force` option is set. If
           the element is detached during the checks, the whole action is retried.
        1. Scroll the element into view if needed.
        1. Use `page.mouse` to click in the center of the element, or the specified `position`.
        1. Wait for initiated navigations to either succeed or fail, unless `noWaitAfter` option is set.

        When all steps combined have not finished during the specified `timeout`, this method throws a `TimeoutError`.
        Passing zero timeout disables this.

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be
            used.
        modifiers : Union[Sequence[Union["Alt", "Control", "ControlOrMeta", "Meta", "Shift"]], None]
            Modifier keys to press. Ensures that only these modifiers are pressed during the operation, and then restores
            current modifiers back. If not specified, currently pressed modifiers are used. "ControlOrMeta" resolves to
            "Control" on Windows and Linux and to "Meta" on macOS.
        position : Union[{x: float, y: float}, None]
            A point to use relative to the top-left corner of element padding box. If not specified, uses some visible point of
            the element.
        delay : Union[float, None]
            Time to wait between `mousedown` and `mouseup` in milliseconds. Defaults to 0.
        button : Union["left", "middle", "right", None]
            Defaults to `left`.
        click_count : Union[int, None]
            defaults to 1. See [UIEvent.detail].
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        force : Union[bool, None]
            Whether to bypass the [actionability](../actionability.md) checks. Defaults to `false`.
        no_wait_after : Union[bool, None]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You
            can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as
            navigating to inaccessible pages. Defaults to `false`.
            Deprecated: This option will default to `true` in the future.
        trial : Union[bool, None]
            When set, this method only performs the [actionability](../actionability.md) checks and skips the action. Defaults
            to `false`. Useful to wait until the element is ready for the action without performing it. Note that keyboard
            `modifiers` will be pressed regardless of `trial` to allow testing elements which are only visible when those keys
            are pressed.
        strict : Union[bool, None]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more than one
            element, the call throws an exception.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.click(
                selector=selector,
                modifiers=mapping.to_impl(modifiers),
                position=position,
                delay=delay,
                button=button,
                clickCount=click_count,
                timeout=timeout,
                force=force,
                noWaitAfter=no_wait_after,
                trial=trial,
                strict=strict,
            )
        )

    async def dblclick(
        self,
        selector: str,
        *,
        modifiers: typing.Optional[
            typing.Sequence[Literal["Alt", "Control", "ControlOrMeta", "Meta", "Shift"]]
        ] = None,
        position: typing.Optional[Position] = None,
        delay: typing.Optional[float] = None,
        button: typing.Optional[Literal["left", "middle", "right"]] = None,
        timeout: typing.Optional[float] = None,
        force: typing.Optional[bool] = None,
        no_wait_after: typing.Optional[bool] = None,
        strict: typing.Optional[bool] = None,
        trial: typing.Optional[bool] = None,
    ) -> None:
        """Page.dblclick

        This method double clicks an element matching `selector` by performing the following steps:
        1. Find an element matching `selector`. If there is none, wait until a matching element is attached to the DOM.
        1. Wait for [actionability](https://playwright.dev/python/docs/actionability) checks on the matched element, unless `force` option is set. If
           the element is detached during the checks, the whole action is retried.
        1. Scroll the element into view if needed.
        1. Use `page.mouse` to double click in the center of the element, or the specified `position`.

        When all steps combined have not finished during the specified `timeout`, this method throws a `TimeoutError`.
        Passing zero timeout disables this.

        **NOTE** `page.dblclick()` dispatches two `click` events and a single `dblclick` event.

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be
            used.
        modifiers : Union[Sequence[Union["Alt", "Control", "ControlOrMeta", "Meta", "Shift"]], None]
            Modifier keys to press. Ensures that only these modifiers are pressed during the operation, and then restores
            current modifiers back. If not specified, currently pressed modifiers are used. "ControlOrMeta" resolves to
            "Control" on Windows and Linux and to "Meta" on macOS.
        position : Union[{x: float, y: float}, None]
            A point to use relative to the top-left corner of element padding box. If not specified, uses some visible point of
            the element.
        delay : Union[float, None]
            Time to wait between `mousedown` and `mouseup` in milliseconds. Defaults to 0.
        button : Union["left", "middle", "right", None]
            Defaults to `left`.
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        force : Union[bool, None]
            Whether to bypass the [actionability](../actionability.md) checks. Defaults to `false`.
        no_wait_after : Union[bool, None]
            This option has no effect.
            Deprecated: This option has no effect.
        strict : Union[bool, None]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more than one
            element, the call throws an exception.
        trial : Union[bool, None]
            When set, this method only performs the [actionability](../actionability.md) checks and skips the action. Defaults
            to `false`. Useful to wait until the element is ready for the action without performing it. Note that keyboard
            `modifiers` will be pressed regardless of `trial` to allow testing elements which are only visible when those keys
            are pressed.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.dblclick(
                selector=selector,
                modifiers=mapping.to_impl(modifiers),
                position=position,
                delay=delay,
                button=button,
                timeout=timeout,
                force=force,
                noWaitAfter=no_wait_after,
                strict=strict,
                trial=trial,
            )
        )

    async def tap(
        self,
        selector: str,
        *,
        modifiers: typing.Optional[
            typing.Sequence[Literal["Alt", "Control", "ControlOrMeta", "Meta", "Shift"]]
        ] = None,
        position: typing.Optional[Position] = None,
        timeout: typing.Optional[float] = None,
        force: typing.Optional[bool] = None,
        no_wait_after: typing.Optional[bool] = None,
        strict: typing.Optional[bool] = None,
        trial: typing.Optional[bool] = None,
    ) -> None:
        """Page.tap

        This method taps an element matching `selector` by performing the following steps:
        1. Find an element matching `selector`. If there is none, wait until a matching element is attached to the DOM.
        1. Wait for [actionability](https://playwright.dev/python/docs/actionability) checks on the matched element, unless `force` option is set. If
           the element is detached during the checks, the whole action is retried.
        1. Scroll the element into view if needed.
        1. Use `page.touchscreen` to tap the center of the element, or the specified `position`.

        When all steps combined have not finished during the specified `timeout`, this method throws a `TimeoutError`.
        Passing zero timeout disables this.

        **NOTE** `page.tap()` the method will throw if `hasTouch` option of the browser context is false.

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be
            used.
        modifiers : Union[Sequence[Union["Alt", "Control", "ControlOrMeta", "Meta", "Shift"]], None]
            Modifier keys to press. Ensures that only these modifiers are pressed during the operation, and then restores
            current modifiers back. If not specified, currently pressed modifiers are used. "ControlOrMeta" resolves to
            "Control" on Windows and Linux and to "Meta" on macOS.
        position : Union[{x: float, y: float}, None]
            A point to use relative to the top-left corner of element padding box. If not specified, uses some visible point of
            the element.
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        force : Union[bool, None]
            Whether to bypass the [actionability](../actionability.md) checks. Defaults to `false`.
        no_wait_after : Union[bool, None]
            This option has no effect.
            Deprecated: This option has no effect.
        strict : Union[bool, None]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more than one
            element, the call throws an exception.
        trial : Union[bool, None]
            When set, this method only performs the [actionability](../actionability.md) checks and skips the action. Defaults
            to `false`. Useful to wait until the element is ready for the action without performing it. Note that keyboard
            `modifiers` will be pressed regardless of `trial` to allow testing elements which are only visible when those keys
            are pressed.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.tap(
                selector=selector,
                modifiers=mapping.to_impl(modifiers),
                position=position,
                timeout=timeout,
                force=force,
                noWaitAfter=no_wait_after,
                strict=strict,
                trial=trial,
            )
        )

    async def fill(
        self,
        selector: str,
        value: str,
        *,
        timeout: typing.Optional[float] = None,
        no_wait_after: typing.Optional[bool] = None,
        strict: typing.Optional[bool] = None,
        force: typing.Optional[bool] = None,
    ) -> None:
        """Page.fill

        This method waits for an element matching `selector`, waits for [actionability](https://playwright.dev/python/docs/actionability) checks,
        focuses the element, fills it and triggers an `input` event after filling. Note that you can pass an empty string
        to clear the input field.

        If the target element is not an `<input>`, `<textarea>` or `[contenteditable]` element, this method throws an
        error. However, if the element is inside the `<label>` element that has an associated
        [control](https://developer.mozilla.org/en-US/docs/Web/API/HTMLLabelElement/control), the control will be filled
        instead.

        To send fine-grained keyboard events, use `locator.press_sequentially()`.

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be
            used.
        value : str
            Value to fill for the `<input>`, `<textarea>` or `[contenteditable]` element.
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        no_wait_after : Union[bool, None]
            This option has no effect.
            Deprecated: This option has no effect.
        strict : Union[bool, None]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more than one
            element, the call throws an exception.
        force : Union[bool, None]
            Whether to bypass the [actionability](../actionability.md) checks. Defaults to `false`.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.fill(
                selector=selector,
                value=value,
                timeout=timeout,
                noWaitAfter=no_wait_after,
                strict=strict,
                force=force,
            )
        )

    def locator(
        self,
        selector: str,
        *,
        has_text: typing.Optional[typing.Union[typing.Pattern[str], str]] = None,
        has_not_text: typing.Optional[typing.Union[typing.Pattern[str], str]] = None,
        has: typing.Optional["Locator"] = None,
        has_not: typing.Optional["Locator"] = None,
    ) -> "Locator":
        """Page.locator

        The method returns an element locator that can be used to perform actions on this page / frame. Locator is resolved
        to the element immediately before performing an action, so a series of actions on the same locator can in fact be
        performed on different DOM elements. That would happen if the DOM structure between those actions has changed.

        [Learn more about locators](https://playwright.dev/python/docs/locators).

        Parameters
        ----------
        selector : str
            A selector to use when resolving DOM element.
        has_text : Union[Pattern[str], str, None]
            Matches elements containing specified text somewhere inside, possibly in a child or a descendant element. When
            passed a [string], matching is case-insensitive and searches for a substring. For example, `"Playwright"` matches
            `<article><div>Playwright</div></article>`.
        has_not_text : Union[Pattern[str], str, None]
            Matches elements that do not contain specified text somewhere inside, possibly in a child or a descendant element.
            When passed a [string], matching is case-insensitive and searches for a substring.
        has : Union[Locator, None]
            Narrows down the results of the method to those which contain elements matching this relative locator. For example,
            `article` that has `text=Playwright` matches `<article><div>Playwright</div></article>`.

            Inner locator **must be relative** to the outer locator and is queried starting with the outer locator match, not
            the document root. For example, you can find `content` that has `div` in
            `<article><content><div>Playwright</div></content></article>`. However, looking for `content` that has `article
            div` will fail, because the inner locator must be relative and should not use any elements outside the `content`.

            Note that outer and inner locators must belong to the same frame. Inner locator must not contain `FrameLocator`s.
        has_not : Union[Locator, None]
            Matches elements that do not contain an element that matches an inner locator. Inner locator is queried against the
            outer one. For example, `article` that does not have `div` matches `<article><span>Playwright</span></article>`.

            Note that outer and inner locators must belong to the same frame. Inner locator must not contain `FrameLocator`s.

        Returns
        -------
        Locator
        """

        return mapping.from_impl(
            self._impl_obj.locator(
                selector=selector,
                hasText=has_text,
                hasNotText=has_not_text,
                has=has._impl_obj if has else None,
                hasNot=has_not._impl_obj if has_not else None,
            )
        )

    def get_by_alt_text(
        self,
        text: typing.Union[str, typing.Pattern[str]],
        *,
        exact: typing.Optional[bool] = None,
    ) -> "Locator":
        """Page.get_by_alt_text

        Allows locating elements by their alt text.

        **Usage**

        For example, this method will find the image by alt text \"Playwright logo\":

        ```html
        <img alt='Playwright logo'>
        ```

        ```py
        await page.get_by_alt_text(\"Playwright logo\").click()
        ```

        Parameters
        ----------
        text : Union[Pattern[str], str]
            Text to locate the element for.
        exact : Union[bool, None]
            Whether to find an exact match: case-sensitive and whole-string. Default to false. Ignored when locating by a
            regular expression. Note that exact match still trims whitespace.

        Returns
        -------
        Locator
        """

        return mapping.from_impl(self._impl_obj.get_by_alt_text(text=text, exact=exact))

    def get_by_label(
        self,
        text: typing.Union[str, typing.Pattern[str]],
        *,
        exact: typing.Optional[bool] = None,
    ) -> "Locator":
        """Page.get_by_label

        Allows locating input elements by the text of the associated `<label>` or `aria-labelledby` element, or by the
        `aria-label` attribute.

        **Usage**

        For example, this method will find inputs by label \"Username\" and \"Password\" in the following DOM:

        ```html
        <input aria-label=\"Username\">
        <label for=\"password-input\">Password:</label>
        <input id=\"password-input\">
        ```

        ```py
        await page.get_by_label(\"Username\").fill(\"john\")
        await page.get_by_label(\"Password\").fill(\"secret\")
        ```

        Parameters
        ----------
        text : Union[Pattern[str], str]
            Text to locate the element for.
        exact : Union[bool, None]
            Whether to find an exact match: case-sensitive and whole-string. Default to false. Ignored when locating by a
            regular expression. Note that exact match still trims whitespace.

        Returns
        -------
        Locator
        """

        return mapping.from_impl(self._impl_obj.get_by_label(text=text, exact=exact))

    def get_by_placeholder(
        self,
        text: typing.Union[str, typing.Pattern[str]],
        *,
        exact: typing.Optional[bool] = None,
    ) -> "Locator":
        """Page.get_by_placeholder

        Allows locating input elements by the placeholder text.

        **Usage**

        For example, consider the following DOM structure.

        ```html
        <input type=\"email\" placeholder=\"name@example.com\" />
        ```

        You can fill the input after locating it by the placeholder text:

        ```py
        await page.get_by_placeholder(\"name@example.com\").fill(\"playwright@microsoft.com\")
        ```

        Parameters
        ----------
        text : Union[Pattern[str], str]
            Text to locate the element for.
        exact : Union[bool, None]
            Whether to find an exact match: case-sensitive and whole-string. Default to false. Ignored when locating by a
            regular expression. Note that exact match still trims whitespace.

        Returns
        -------
        Locator
        """

        return mapping.from_impl(
            self._impl_obj.get_by_placeholder(text=text, exact=exact)
        )

    def get_by_role(
        self,
        role: Literal[
            "alert",
            "alertdialog",
            "application",
            "article",
            "banner",
            "blockquote",
            "button",
            "caption",
            "cell",
            "checkbox",
            "code",
            "columnheader",
            "combobox",
            "complementary",
            "contentinfo",
            "definition",
            "deletion",
            "dialog",
            "directory",
            "document",
            "emphasis",
            "feed",
            "figure",
            "form",
            "generic",
            "grid",
            "gridcell",
            "group",
            "heading",
            "img",
            "insertion",
            "link",
            "list",
            "listbox",
            "listitem",
            "log",
            "main",
            "marquee",
            "math",
            "menu",
            "menubar",
            "menuitem",
            "menuitemcheckbox",
            "menuitemradio",
            "meter",
            "navigation",
            "none",
            "note",
            "option",
            "paragraph",
            "presentation",
            "progressbar",
            "radio",
            "radiogroup",
            "region",
            "row",
            "rowgroup",
            "rowheader",
            "scrollbar",
            "search",
            "searchbox",
            "separator",
            "slider",
            "spinbutton",
            "status",
            "strong",
            "subscript",
            "superscript",
            "switch",
            "tab",
            "table",
            "tablist",
            "tabpanel",
            "term",
            "textbox",
            "time",
            "timer",
            "toolbar",
            "tooltip",
            "tree",
            "treegrid",
            "treeitem",
        ],
        *,
        checked: typing.Optional[bool] = None,
        disabled: typing.Optional[bool] = None,
        expanded: typing.Optional[bool] = None,
        include_hidden: typing.Optional[bool] = None,
        level: typing.Optional[int] = None,
        name: typing.Optional[typing.Union[typing.Pattern[str], str]] = None,
        pressed: typing.Optional[bool] = None,
        selected: typing.Optional[bool] = None,
        exact: typing.Optional[bool] = None,
    ) -> "Locator":
        """Page.get_by_role

        Allows locating elements by their [ARIA role](https://www.w3.org/TR/wai-aria-1.2/#roles),
        [ARIA attributes](https://www.w3.org/TR/wai-aria-1.2/#aria-attributes) and
        [accessible name](https://w3c.github.io/accname/#dfn-accessible-name).

        **Usage**

        Consider the following DOM structure.

        ```html
        <h3>Sign up</h3>
        <label>
          <input type=\"checkbox\" /> Subscribe
        </label>
        <br/>
        <button>Submit</button>
        ```

        You can locate each element by it's implicit role:

        ```py
        await expect(page.get_by_role(\"heading\", name=\"Sign up\")).to_be_visible()

        await page.get_by_role(\"checkbox\", name=\"Subscribe\").check()

        await page.get_by_role(\"button\", name=re.compile(\"submit\", re.IGNORECASE)).click()
        ```

        **Details**

        Role selector **does not replace** accessibility audits and conformance tests, but rather gives early feedback
        about the ARIA guidelines.

        Many html elements have an implicitly [defined role](https://w3c.github.io/html-aam/#html-element-role-mappings)
        that is recognized by the role selector. You can find all the
        [supported roles here](https://www.w3.org/TR/wai-aria-1.2/#role_definitions). ARIA guidelines **do not recommend**
        duplicating implicit roles and attributes by setting `role` and/or `aria-*` attributes to default values.

        Parameters
        ----------
        role : Union["alert", "alertdialog", "application", "article", "banner", "blockquote", "button", "caption", "cell", "checkbox", "code", "columnheader", "combobox", "complementary", "contentinfo", "definition", "deletion", "dialog", "directory", "document", "emphasis", "feed", "figure", "form", "generic", "grid", "gridcell", "group", "heading", "img", "insertion", "link", "list", "listbox", "listitem", "log", "main", "marquee", "math", "menu", "menubar", "menuitem", "menuitemcheckbox", "menuitemradio", "meter", "navigation", "none", "note", "option", "paragraph", "presentation", "progressbar", "radio", "radiogroup", "region", "row", "rowgroup", "rowheader", "scrollbar", "search", "searchbox", "separator", "slider", "spinbutton", "status", "strong", "subscript", "superscript", "switch", "tab", "table", "tablist", "tabpanel", "term", "textbox", "time", "timer", "toolbar", "tooltip", "tree", "treegrid", "treeitem"]
            Required aria role.
        checked : Union[bool, None]
            An attribute that is usually set by `aria-checked` or native `<input type=checkbox>` controls.

            Learn more about [`aria-checked`](https://www.w3.org/TR/wai-aria-1.2/#aria-checked).
        disabled : Union[bool, None]
            An attribute that is usually set by `aria-disabled` or `disabled`.

            **NOTE** Unlike most other attributes, `disabled` is inherited through the DOM hierarchy. Learn more about
            [`aria-disabled`](https://www.w3.org/TR/wai-aria-1.2/#aria-disabled).

        expanded : Union[bool, None]
            An attribute that is usually set by `aria-expanded`.

            Learn more about [`aria-expanded`](https://www.w3.org/TR/wai-aria-1.2/#aria-expanded).
        include_hidden : Union[bool, None]
            Option that controls whether hidden elements are matched. By default, only non-hidden elements, as
            [defined by ARIA](https://www.w3.org/TR/wai-aria-1.2/#tree_exclusion), are matched by role selector.

            Learn more about [`aria-hidden`](https://www.w3.org/TR/wai-aria-1.2/#aria-hidden).
        level : Union[int, None]
            A number attribute that is usually present for roles `heading`, `listitem`, `row`, `treeitem`, with default values
            for `<h1>-<h6>` elements.

            Learn more about [`aria-level`](https://www.w3.org/TR/wai-aria-1.2/#aria-level).
        name : Union[Pattern[str], str, None]
            Option to match the [accessible name](https://w3c.github.io/accname/#dfn-accessible-name). By default, matching is
            case-insensitive and searches for a substring, use `exact` to control this behavior.

            Learn more about [accessible name](https://w3c.github.io/accname/#dfn-accessible-name).
        pressed : Union[bool, None]
            An attribute that is usually set by `aria-pressed`.

            Learn more about [`aria-pressed`](https://www.w3.org/TR/wai-aria-1.2/#aria-pressed).
        selected : Union[bool, None]
            An attribute that is usually set by `aria-selected`.

            Learn more about [`aria-selected`](https://www.w3.org/TR/wai-aria-1.2/#aria-selected).
        exact : Union[bool, None]
            Whether `name` is matched exactly: case-sensitive and whole-string. Defaults to false. Ignored when `name` is a
            regular expression. Note that exact match still trims whitespace.

        Returns
        -------
        Locator
        """

        return mapping.from_impl(
            self._impl_obj.get_by_role(
                role=role,
                checked=checked,
                disabled=disabled,
                expanded=expanded,
                includeHidden=include_hidden,
                level=level,
                name=name,
                pressed=pressed,
                selected=selected,
                exact=exact,
            )
        )

    def get_by_test_id(
        self, test_id: typing.Union[str, typing.Pattern[str]]
    ) -> "Locator":
        """Page.get_by_test_id

        Locate element by the test id.

        **Usage**

        Consider the following DOM structure.

        ```html
        <button data-testid=\"directions\">Itinéraire</button>
        ```

        You can locate the element by it's test id:

        ```py
        await page.get_by_test_id(\"directions\").click()
        ```

        **Details**

        By default, the `data-testid` attribute is used as a test id. Use `selectors.set_test_id_attribute()` to
        configure a different test id attribute if necessary.

        Parameters
        ----------
        test_id : Union[Pattern[str], str]
            Id to locate the element by.

        Returns
        -------
        Locator
        """

        return mapping.from_impl(self._impl_obj.get_by_test_id(testId=test_id))

    def get_by_text(
        self,
        text: typing.Union[str, typing.Pattern[str]],
        *,
        exact: typing.Optional[bool] = None,
    ) -> "Locator":
        """Page.get_by_text

        Allows locating elements that contain given text.

        See also `locator.filter()` that allows to match by another criteria, like an accessible role, and then
        filter by the text content.

        **Usage**

        Consider the following DOM structure:

        ```html
        <div>Hello <span>world</span></div>
        <div>Hello</div>
        ```

        You can locate by text substring, exact string, or a regular expression:

        ```py
        # Matches <span>
        page.get_by_text(\"world\")

        # Matches first <div>
        page.get_by_text(\"Hello world\")

        # Matches second <div>
        page.get_by_text(\"Hello\", exact=True)

        # Matches both <div>s
        page.get_by_text(re.compile(\"Hello\"))

        # Matches second <div>
        page.get_by_text(re.compile(\"^hello$\", re.IGNORECASE))
        ```

        **Details**

        Matching by text always normalizes whitespace, even with exact match. For example, it turns multiple spaces into
        one, turns line breaks into spaces and ignores leading and trailing whitespace.

        Input elements of the type `button` and `submit` are matched by their `value` instead of the text content. For
        example, locating by text `\"Log in\"` matches `<input type=button value=\"Log in\">`.

        Parameters
        ----------
        text : Union[Pattern[str], str]
            Text to locate the element for.
        exact : Union[bool, None]
            Whether to find an exact match: case-sensitive and whole-string. Default to false. Ignored when locating by a
            regular expression. Note that exact match still trims whitespace.

        Returns
        -------
        Locator
        """

        return mapping.from_impl(self._impl_obj.get_by_text(text=text, exact=exact))

    def get_by_title(
        self,
        text: typing.Union[str, typing.Pattern[str]],
        *,
        exact: typing.Optional[bool] = None,
    ) -> "Locator":
        """Page.get_by_title

        Allows locating elements by their title attribute.

        **Usage**

        Consider the following DOM structure.

        ```html
        <span title='Issues count'>25 issues</span>
        ```

        You can check the issues count after locating it by the title text:

        ```py
        await expect(page.get_by_title(\"Issues count\")).to_have_text(\"25 issues\")
        ```

        Parameters
        ----------
        text : Union[Pattern[str], str]
            Text to locate the element for.
        exact : Union[bool, None]
            Whether to find an exact match: case-sensitive and whole-string. Default to false. Ignored when locating by a
            regular expression. Note that exact match still trims whitespace.

        Returns
        -------
        Locator
        """

        return mapping.from_impl(self._impl_obj.get_by_title(text=text, exact=exact))

    def frame_locator(self, selector: str) -> "FrameLocator":
        """Page.frame_locator

        When working with iframes, you can create a frame locator that will enter the iframe and allow selecting elements
        in that iframe.

        **Usage**

        Following snippet locates element with text \"Submit\" in the iframe with id `my-frame`, like `<iframe
        id=\"my-frame\">`:

        ```py
        locator = page.frame_locator(\"#my-iframe\").get_by_text(\"Submit\")
        await locator.click()
        ```

        Parameters
        ----------
        selector : str
            A selector to use when resolving DOM element.

        Returns
        -------
        FrameLocator
        """

        return mapping.from_impl(self._impl_obj.frame_locator(selector=selector))

    async def focus(
        self,
        selector: str,
        *,
        strict: typing.Optional[bool] = None,
        timeout: typing.Optional[float] = None,
    ) -> None:
        """Page.focus

        This method fetches an element with `selector` and focuses it. If there's no element matching `selector`, the
        method waits until a matching element appears in the DOM.

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be
            used.
        strict : Union[bool, None]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more than one
            element, the call throws an exception.
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.focus(
                selector=selector, strict=strict, timeout=timeout
            )
        )

    async def text_content(
        self,
        selector: str,
        *,
        strict: typing.Optional[bool] = None,
        timeout: typing.Optional[float] = None,
    ) -> typing.Optional[str]:
        """Page.text_content

        Returns `element.textContent`.

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be
            used.
        strict : Union[bool, None]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more than one
            element, the call throws an exception.
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.

        Returns
        -------
        Union[str, None]
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.text_content(
                selector=selector, strict=strict, timeout=timeout
            )
        )

    async def inner_text(
        self,
        selector: str,
        *,
        strict: typing.Optional[bool] = None,
        timeout: typing.Optional[float] = None,
    ) -> str:
        """Page.inner_text

        Returns `element.innerText`.

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be
            used.
        strict : Union[bool, None]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more than one
            element, the call throws an exception.
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.

        Returns
        -------
        str
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.inner_text(
                selector=selector, strict=strict, timeout=timeout
            )
        )

    async def inner_html(
        self,
        selector: str,
        *,
        strict: typing.Optional[bool] = None,
        timeout: typing.Optional[float] = None,
    ) -> str:
        """Page.inner_html

        Returns `element.innerHTML`.

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be
            used.
        strict : Union[bool, None]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more than one
            element, the call throws an exception.
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.

        Returns
        -------
        str
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.inner_html(
                selector=selector, strict=strict, timeout=timeout
            )
        )

    async def get_attribute(
        self,
        selector: str,
        name: str,
        *,
        strict: typing.Optional[bool] = None,
        timeout: typing.Optional[float] = None,
    ) -> typing.Optional[str]:
        """Page.get_attribute

        Returns element attribute value.

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be
            used.
        name : str
            Attribute name to get the value for.
        strict : Union[bool, None]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more than one
            element, the call throws an exception.
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.

        Returns
        -------
        Union[str, None]
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.get_attribute(
                selector=selector, name=name, strict=strict, timeout=timeout
            )
        )

    async def hover(
        self,
        selector: str,
        *,
        modifiers: typing.Optional[
            typing.Sequence[Literal["Alt", "Control", "ControlOrMeta", "Meta", "Shift"]]
        ] = None,
        position: typing.Optional[Position] = None,
        timeout: typing.Optional[float] = None,
        no_wait_after: typing.Optional[bool] = None,
        force: typing.Optional[bool] = None,
        strict: typing.Optional[bool] = None,
        trial: typing.Optional[bool] = None,
    ) -> None:
        """Page.hover

        This method hovers over an element matching `selector` by performing the following steps:
        1. Find an element matching `selector`. If there is none, wait until a matching element is attached to the DOM.
        1. Wait for [actionability](https://playwright.dev/python/docs/actionability) checks on the matched element, unless `force` option is set. If
           the element is detached during the checks, the whole action is retried.
        1. Scroll the element into view if needed.
        1. Use `page.mouse` to hover over the center of the element, or the specified `position`.

        When all steps combined have not finished during the specified `timeout`, this method throws a `TimeoutError`.
        Passing zero timeout disables this.

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be
            used.
        modifiers : Union[Sequence[Union["Alt", "Control", "ControlOrMeta", "Meta", "Shift"]], None]
            Modifier keys to press. Ensures that only these modifiers are pressed during the operation, and then restores
            current modifiers back. If not specified, currently pressed modifiers are used. "ControlOrMeta" resolves to
            "Control" on Windows and Linux and to "Meta" on macOS.
        position : Union[{x: float, y: float}, None]
            A point to use relative to the top-left corner of element padding box. If not specified, uses some visible point of
            the element.
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        no_wait_after : Union[bool, None]
            This option has no effect.
            Deprecated: This option has no effect.
        force : Union[bool, None]
            Whether to bypass the [actionability](../actionability.md) checks. Defaults to `false`.
        strict : Union[bool, None]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more than one
            element, the call throws an exception.
        trial : Union[bool, None]
            When set, this method only performs the [actionability](../actionability.md) checks and skips the action. Defaults
            to `false`. Useful to wait until the element is ready for the action without performing it. Note that keyboard
            `modifiers` will be pressed regardless of `trial` to allow testing elements which are only visible when those keys
            are pressed.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.hover(
                selector=selector,
                modifiers=mapping.to_impl(modifiers),
                position=position,
                timeout=timeout,
                noWaitAfter=no_wait_after,
                force=force,
                strict=strict,
                trial=trial,
            )
        )

    async def drag_and_drop(
        self,
        source: str,
        target: str,
        *,
        source_position: typing.Optional[Position] = None,
        target_position: typing.Optional[Position] = None,
        force: typing.Optional[bool] = None,
        no_wait_after: typing.Optional[bool] = None,
        timeout: typing.Optional[float] = None,
        strict: typing.Optional[bool] = None,
        trial: typing.Optional[bool] = None,
        steps: typing.Optional[int] = None,
    ) -> None:
        """Page.drag_and_drop

        This method drags the source element to the target element. It will first move to the source element, perform a
        `mousedown`, then move to the target element and perform a `mouseup`.

        **Usage**

        ```py
        await page.drag_and_drop(\"#source\", \"#target\")
        # or specify exact positions relative to the top-left corners of the elements:
        await page.drag_and_drop(
          \"#source\",
          \"#target\",
          source_position={\"x\": 34, \"y\": 7},
          target_position={\"x\": 10, \"y\": 20}
        )
        ```

        Parameters
        ----------
        source : str
            A selector to search for an element to drag. If there are multiple elements satisfying the selector, the first will
            be used.
        target : str
            A selector to search for an element to drop onto. If there are multiple elements satisfying the selector, the first
            will be used.
        source_position : Union[{x: float, y: float}, None]
            Clicks on the source element at this point relative to the top-left corner of the element's padding box. If not
            specified, some visible point of the element is used.
        target_position : Union[{x: float, y: float}, None]
            Drops on the target element at this point relative to the top-left corner of the element's padding box. If not
            specified, some visible point of the element is used.
        force : Union[bool, None]
            Whether to bypass the [actionability](../actionability.md) checks. Defaults to `false`.
        no_wait_after : Union[bool, None]
            This option has no effect.
            Deprecated: This option has no effect.
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        strict : Union[bool, None]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more than one
            element, the call throws an exception.
        trial : Union[bool, None]
            When set, this method only performs the [actionability](../actionability.md) checks and skips the action. Defaults
            to `false`. Useful to wait until the element is ready for the action without performing it.
        steps : Union[int, None]
            Defaults to 1. Sends `n` interpolated `mousemove` events to represent travel between the `mousedown` and `mouseup`
            of the drag. When set to 1, emits a single `mousemove` event at the destination location.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.drag_and_drop(
                source=source,
                target=target,
                sourcePosition=source_position,
                targetPosition=target_position,
                force=force,
                noWaitAfter=no_wait_after,
                timeout=timeout,
                strict=strict,
                trial=trial,
                steps=steps,
            )
        )

    async def select_option(
        self,
        selector: str,
        value: typing.Optional[typing.Union[str, typing.Sequence[str]]] = None,
        *,
        index: typing.Optional[typing.Union[int, typing.Sequence[int]]] = None,
        label: typing.Optional[typing.Union[str, typing.Sequence[str]]] = None,
        element: typing.Optional[
            typing.Union["ElementHandle", typing.Sequence["ElementHandle"]]
        ] = None,
        timeout: typing.Optional[float] = None,
        no_wait_after: typing.Optional[bool] = None,
        force: typing.Optional[bool] = None,
        strict: typing.Optional[bool] = None,
    ) -> typing.List[str]:
        """Page.select_option

        This method waits for an element matching `selector`, waits for [actionability](https://playwright.dev/python/docs/actionability) checks, waits
        until all specified options are present in the `<select>` element and selects these options.

        If the target element is not a `<select>` element, this method throws an error. However, if the element is inside
        the `<label>` element that has an associated
        [control](https://developer.mozilla.org/en-US/docs/Web/API/HTMLLabelElement/control), the control will be used
        instead.

        Returns the array of option values that have been successfully selected.

        Triggers a `change` and `input` event once all the provided options have been selected.

        **Usage**

        ```py
        # Single selection matching the value or label
        await page.select_option(\"select#colors\", \"blue\")
        # single selection matching the label
        await page.select_option(\"select#colors\", label=\"blue\")
        # multiple selection
        await page.select_option(\"select#colors\", value=[\"red\", \"green\", \"blue\"])
        ```

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be
            used.
        value : Union[Sequence[str], str, None]
            Options to select by value. If the `<select>` has the `multiple` attribute, all given options are selected,
            otherwise only the first option matching one of the passed options is selected. Optional.
        index : Union[Sequence[int], int, None]
            Options to select by index. Optional.
        label : Union[Sequence[str], str, None]
            Options to select by label. If the `<select>` has the `multiple` attribute, all given options are selected,
            otherwise only the first option matching one of the passed options is selected. Optional.
        element : Union[ElementHandle, Sequence[ElementHandle], None]
            Option elements to select. Optional.
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        no_wait_after : Union[bool, None]
            This option has no effect.
            Deprecated: This option has no effect.
        force : Union[bool, None]
            Whether to bypass the [actionability](../actionability.md) checks. Defaults to `false`.
        strict : Union[bool, None]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more than one
            element, the call throws an exception.

        Returns
        -------
        List[str]
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.select_option(
                selector=selector,
                value=mapping.to_impl(value),
                index=mapping.to_impl(index),
                label=mapping.to_impl(label),
                element=mapping.to_impl(element),
                timeout=timeout,
                noWaitAfter=no_wait_after,
                force=force,
                strict=strict,
            )
        )

    async def input_value(
        self,
        selector: str,
        *,
        strict: typing.Optional[bool] = None,
        timeout: typing.Optional[float] = None,
    ) -> str:
        """Page.input_value

        Returns `input.value` for the selected `<input>` or `<textarea>` or `<select>` element.

        Throws for non-input elements. However, if the element is inside the `<label>` element that has an associated
        [control](https://developer.mozilla.org/en-US/docs/Web/API/HTMLLabelElement/control), returns the value of the
        control.

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be
            used.
        strict : Union[bool, None]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more than one
            element, the call throws an exception.
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.

        Returns
        -------
        str
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.input_value(
                selector=selector, strict=strict, timeout=timeout
            )
        )

    async def set_input_files(
        self,
        selector: str,
        files: typing.Union[
            str,
            pathlib.Path,
            FilePayload,
            typing.Sequence[typing.Union[str, pathlib.Path]],
            typing.Sequence[FilePayload],
        ],
        *,
        timeout: typing.Optional[float] = None,
        strict: typing.Optional[bool] = None,
        no_wait_after: typing.Optional[bool] = None,
    ) -> None:
        """Page.set_input_files

        Sets the value of the file input to these file paths or files. If some of the `filePaths` are relative paths, then
        they are resolved relative to the current working directory. For empty array, clears the selected files. For inputs
        with a `[webkitdirectory]` attribute, only a single directory path is supported.

        This method expects `selector` to point to an
        [input element](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/input). However, if the element is inside
        the `<label>` element that has an associated
        [control](https://developer.mozilla.org/en-US/docs/Web/API/HTMLLabelElement/control), targets the control instead.

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be
            used.
        files : Union[Sequence[Union[pathlib.Path, str]], Sequence[{name: str, mimeType: str, buffer: bytes}], pathlib.Path, str, {name: str, mimeType: str, buffer: bytes}]
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        strict : Union[bool, None]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more than one
            element, the call throws an exception.
        no_wait_after : Union[bool, None]
            This option has no effect.
            Deprecated: This option has no effect.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.set_input_files(
                selector=selector,
                files=mapping.to_impl(files),
                timeout=timeout,
                strict=strict,
                noWaitAfter=no_wait_after,
            )
        )

    async def type(
        self,
        selector: str,
        text: str,
        *,
        delay: typing.Optional[float] = None,
        timeout: typing.Optional[float] = None,
        no_wait_after: typing.Optional[bool] = None,
        strict: typing.Optional[bool] = None,
    ) -> None:
        """Page.type

        Sends a `keydown`, `keypress`/`input`, and `keyup` event for each character in the text. `page.type` can be used to
        send fine-grained keyboard events. To fill values in form fields, use `page.fill()`.

        To press a special key, like `Control` or `ArrowDown`, use `keyboard.press()`.

        **Usage**

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be
            used.
        text : str
            A text to type into a focused element.
        delay : Union[float, None]
            Time to wait between key presses in milliseconds. Defaults to 0.
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        no_wait_after : Union[bool, None]
            This option has no effect.
            Deprecated: This option has no effect.
        strict : Union[bool, None]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more than one
            element, the call throws an exception.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.type(
                selector=selector,
                text=text,
                delay=delay,
                timeout=timeout,
                noWaitAfter=no_wait_after,
                strict=strict,
            )
        )

    async def press(
        self,
        selector: str,
        key: str,
        *,
        delay: typing.Optional[float] = None,
        timeout: typing.Optional[float] = None,
        no_wait_after: typing.Optional[bool] = None,
        strict: typing.Optional[bool] = None,
    ) -> None:
        """Page.press

        Focuses the element, and then uses `keyboard.down()` and `keyboard.up()`.

        `key` can specify the intended
        [keyboardEvent.key](https://developer.mozilla.org/en-US/docs/Web/API/KeyboardEvent/key) value or a single character
        to generate the text for. A superset of the `key` values can be found
        [here](https://developer.mozilla.org/en-US/docs/Web/API/KeyboardEvent/key/Key_Values). Examples of the keys are:

        `F1` - `F12`, `Digit0`- `Digit9`, `KeyA`- `KeyZ`, `Backquote`, `Minus`, `Equal`, `Backslash`, `Backspace`, `Tab`,
        `Delete`, `Escape`, `ArrowDown`, `End`, `Enter`, `Home`, `Insert`, `PageDown`, `PageUp`, `ArrowRight`, `ArrowUp`,
        etc.

        Following modification shortcuts are also supported: `Shift`, `Control`, `Alt`, `Meta`, `ShiftLeft`,
        `ControlOrMeta`. `ControlOrMeta` resolves to `Control` on Windows and Linux and to `Meta` on macOS.

        Holding down `Shift` will type the text that corresponds to the `key` in the upper case.

        If `key` is a single character, it is case-sensitive, so the values `a` and `A` will generate different respective
        texts.

        Shortcuts such as `key: \"Control+o\"`, `key: \"Control++` or `key: \"Control+Shift+T\"` are supported as well. When
        specified with the modifier, modifier is pressed and being held while the subsequent key is being pressed.

        **Usage**

        ```py
        page = await browser.new_page()
        await page.goto(\"https://keycode.info\")
        await page.press(\"body\", \"A\")
        await page.screenshot(path=\"a.png\")
        await page.press(\"body\", \"ArrowLeft\")
        await page.screenshot(path=\"arrow_left.png\")
        await page.press(\"body\", \"Shift+O\")
        await page.screenshot(path=\"o.png\")
        await browser.close()
        ```

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be
            used.
        key : str
            Name of the key to press or a character to generate, such as `ArrowLeft` or `a`.
        delay : Union[float, None]
            Time to wait between `keydown` and `keyup` in milliseconds. Defaults to 0.
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        no_wait_after : Union[bool, None]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You
            can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as
            navigating to inaccessible pages. Defaults to `false`.
            Deprecated: This option will default to `true` in the future.
        strict : Union[bool, None]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more than one
            element, the call throws an exception.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.press(
                selector=selector,
                key=key,
                delay=delay,
                timeout=timeout,
                noWaitAfter=no_wait_after,
                strict=strict,
            )
        )

    async def check(
        self,
        selector: str,
        *,
        position: typing.Optional[Position] = None,
        timeout: typing.Optional[float] = None,
        force: typing.Optional[bool] = None,
        no_wait_after: typing.Optional[bool] = None,
        strict: typing.Optional[bool] = None,
        trial: typing.Optional[bool] = None,
    ) -> None:
        """Page.check

        This method checks an element matching `selector` by performing the following steps:
        1. Find an element matching `selector`. If there is none, wait until a matching element is attached to the DOM.
        1. Ensure that matched element is a checkbox or a radio input. If not, this method throws. If the element is
           already checked, this method returns immediately.
        1. Wait for [actionability](https://playwright.dev/python/docs/actionability) checks on the matched element, unless `force` option is set. If
           the element is detached during the checks, the whole action is retried.
        1. Scroll the element into view if needed.
        1. Use `page.mouse` to click in the center of the element.
        1. Ensure that the element is now checked. If not, this method throws.

        When all steps combined have not finished during the specified `timeout`, this method throws a `TimeoutError`.
        Passing zero timeout disables this.

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be
            used.
        position : Union[{x: float, y: float}, None]
            A point to use relative to the top-left corner of element padding box. If not specified, uses some visible point of
            the element.
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        force : Union[bool, None]
            Whether to bypass the [actionability](../actionability.md) checks. Defaults to `false`.
        no_wait_after : Union[bool, None]
            This option has no effect.
            Deprecated: This option has no effect.
        strict : Union[bool, None]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more than one
            element, the call throws an exception.
        trial : Union[bool, None]
            When set, this method only performs the [actionability](../actionability.md) checks and skips the action. Defaults
            to `false`. Useful to wait until the element is ready for the action without performing it.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.check(
                selector=selector,
                position=position,
                timeout=timeout,
                force=force,
                noWaitAfter=no_wait_after,
                strict=strict,
                trial=trial,
            )
        )

    async def uncheck(
        self,
        selector: str,
        *,
        position: typing.Optional[Position] = None,
        timeout: typing.Optional[float] = None,
        force: typing.Optional[bool] = None,
        no_wait_after: typing.Optional[bool] = None,
        strict: typing.Optional[bool] = None,
        trial: typing.Optional[bool] = None,
    ) -> None:
        """Page.uncheck

        This method unchecks an element matching `selector` by performing the following steps:
        1. Find an element matching `selector`. If there is none, wait until a matching element is attached to the DOM.
        1. Ensure that matched element is a checkbox or a radio input. If not, this method throws. If the element is
           already unchecked, this method returns immediately.
        1. Wait for [actionability](https://playwright.dev/python/docs/actionability) checks on the matched element, unless `force` option is set. If
           the element is detached during the checks, the whole action is retried.
        1. Scroll the element into view if needed.
        1. Use `page.mouse` to click in the center of the element.
        1. Ensure that the element is now unchecked. If not, this method throws.

        When all steps combined have not finished during the specified `timeout`, this method throws a `TimeoutError`.
        Passing zero timeout disables this.

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be
            used.
        position : Union[{x: float, y: float}, None]
            A point to use relative to the top-left corner of element padding box. If not specified, uses some visible point of
            the element.
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        force : Union[bool, None]
            Whether to bypass the [actionability](../actionability.md) checks. Defaults to `false`.
        no_wait_after : Union[bool, None]
            This option has no effect.
            Deprecated: This option has no effect.
        strict : Union[bool, None]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more than one
            element, the call throws an exception.
        trial : Union[bool, None]
            When set, this method only performs the [actionability](../actionability.md) checks and skips the action. Defaults
            to `false`. Useful to wait until the element is ready for the action without performing it.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.uncheck(
                selector=selector,
                position=position,
                timeout=timeout,
                force=force,
                noWaitAfter=no_wait_after,
                strict=strict,
                trial=trial,
            )
        )

    async def wait_for_timeout(self, timeout: float) -> None:
        """Page.wait_for_timeout

        Waits for the given `timeout` in milliseconds.

        Note that `page.waitForTimeout()` should only be used for debugging. Tests using the timer in production are going
        to be flaky. Use signals such as network events, selectors becoming visible and others instead.

        **Usage**

        ```py
        # wait for 1 second
        await page.wait_for_timeout(1000)
        ```

        Parameters
        ----------
        timeout : float
            A timeout to wait for
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.wait_for_timeout(timeout=timeout)
        )

    async def wait_for_function(
        self,
        expression: str,
        *,
        arg: typing.Optional[typing.Any] = None,
        timeout: typing.Optional[float] = None,
        polling: typing.Optional[typing.Union[float, Literal["raf"]]] = None,
    ) -> "JSHandle":
        """Page.wait_for_function

        Returns when the `expression` returns a truthy value. It resolves to a JSHandle of the truthy value.

        **Usage**

        The `page.wait_for_function()` can be used to observe viewport size change:

        ```py
        import asyncio
        from playwright.async_api import async_playwright, Playwright

        async def run(playwright: Playwright):
            webkit = playwright.webkit
            browser = await webkit.launch()
            page = await browser.new_page()
            await page.evaluate(\"window.x = 0; setTimeout(() => { window.x = 100 }, 1000);\")
            await page.wait_for_function(\"() => window.x > 0\")
            await browser.close()

        async def main():
            async with async_playwright() as playwright:
                await run(playwright)
        asyncio.run(main())
        ```

        To pass an argument to the predicate of `page.wait_for_function()` function:

        ```py
        selector = \".foo\"
        await page.wait_for_function(\"selector => !!document.querySelector(selector)\", selector)
        ```

        Parameters
        ----------
        expression : str
            JavaScript expression to be evaluated in the browser context. If the expression evaluates to a function, the
            function is automatically invoked.
        arg : Union[Any, None]
            Optional argument to pass to `expression`.
        timeout : Union[float, None]
            Maximum time to wait for in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The
            default value can be changed by using the `browser_context.set_default_timeout()` or
            `page.set_default_timeout()` methods.
        polling : Union["raf", float, None]
            If `polling` is `'raf'`, then `expression` is constantly executed in `requestAnimationFrame` callback. If `polling`
            is a number, then it is treated as an interval in milliseconds at which the function would be executed. Defaults to
            `raf`.

        Returns
        -------
        JSHandle
        """

        return mapping.from_impl(
            await self._impl_obj.wait_for_function(
                expression=expression,
                arg=mapping.to_impl(arg),
                timeout=timeout,
                polling=polling,
            )
        )

    async def pause(self) -> None:
        """Page.pause

        Pauses script execution. Playwright will stop executing the script and wait for the user to either press the
        'Resume' button in the page overlay or to call `playwright.resume()` in the DevTools console.

        User can inspect selectors or perform manual steps while paused. Resume will continue running the original script
        from the place it was paused.

        **NOTE** This method requires Playwright to be started in a headed mode, with a falsy `headless` option.
        """

        return mapping.from_maybe_impl(await self._impl_obj.pause())

    async def pdf(
        self,
        *,
        scale: typing.Optional[float] = None,
        display_header_footer: typing.Optional[bool] = None,
        header_template: typing.Optional[str] = None,
        footer_template: typing.Optional[str] = None,
        print_background: typing.Optional[bool] = None,
        landscape: typing.Optional[bool] = None,
        page_ranges: typing.Optional[str] = None,
        format: typing.Optional[str] = None,
        width: typing.Optional[typing.Union[str, float]] = None,
        height: typing.Optional[typing.Union[str, float]] = None,
        prefer_css_page_size: typing.Optional[bool] = None,
        margin: typing.Optional[PdfMargins] = None,
        path: typing.Optional[typing.Union[pathlib.Path, str]] = None,
        outline: typing.Optional[bool] = None,
        tagged: typing.Optional[bool] = None,
    ) -> bytes:
        """Page.pdf

        Returns the PDF buffer.

        `page.pdf()` generates a pdf of the page with `print` css media. To generate a pdf with `screen` media, call
        `page.emulate_media()` before calling `page.pdf()`:

        **NOTE** By default, `page.pdf()` generates a pdf with modified colors for printing. Use the
        [`-webkit-print-color-adjust`](https://developer.mozilla.org/en-US/docs/Web/CSS/-webkit-print-color-adjust)
        property to force rendering of exact colors.

        **Usage**

        ```py
        # generates a pdf with \"screen\" media type.
        await page.emulate_media(media=\"screen\")
        await page.pdf(path=\"page.pdf\")
        ```

        The `width`, `height`, and `margin` options accept values labeled with units. Unlabeled values are treated as
        pixels.

        A few examples:
        - `page.pdf({width: 100})` - prints with width set to 100 pixels
        - `page.pdf({width: '100px'})` - prints with width set to 100 pixels
        - `page.pdf({width: '10cm'})` - prints with width set to 10 centimeters.

        All possible units are:
        - `px` - pixel
        - `in` - inch
        - `cm` - centimeter
        - `mm` - millimeter

        The `format` options are:
        - `Letter`: 8.5in x 11in
        - `Legal`: 8.5in x 14in
        - `Tabloid`: 11in x 17in
        - `Ledger`: 17in x 11in
        - `A0`: 33.1in x 46.8in
        - `A1`: 23.4in x 33.1in
        - `A2`: 16.54in x 23.4in
        - `A3`: 11.7in x 16.54in
        - `A4`: 8.27in x 11.7in
        - `A5`: 5.83in x 8.27in
        - `A6`: 4.13in x 5.83in

        **NOTE** `headerTemplate` and `footerTemplate` markup have the following limitations: > 1. Script tags inside
        templates are not evaluated. > 2. Page styles are not visible inside templates.

        Parameters
        ----------
        scale : Union[float, None]
            Scale of the webpage rendering. Defaults to `1`. Scale amount must be between 0.1 and 2.
        display_header_footer : Union[bool, None]
            Display header and footer. Defaults to `false`.
        header_template : Union[str, None]
            HTML template for the print header. Should be valid HTML markup with following classes used to inject printing
            values into them:
            - `'date'` formatted print date
            - `'title'` document title
            - `'url'` document location
            - `'pageNumber'` current page number
            - `'totalPages'` total pages in the document
        footer_template : Union[str, None]
            HTML template for the print footer. Should use the same format as the `headerTemplate`.
        print_background : Union[bool, None]
            Print background graphics. Defaults to `false`.
        landscape : Union[bool, None]
            Paper orientation. Defaults to `false`.
        page_ranges : Union[str, None]
            Paper ranges to print, e.g., '1-5, 8, 11-13'. Defaults to the empty string, which means print all pages.
        format : Union[str, None]
            Paper format. If set, takes priority over `width` or `height` options. Defaults to 'Letter'.
        width : Union[float, str, None]
            Paper width, accepts values labeled with units.
        height : Union[float, str, None]
            Paper height, accepts values labeled with units.
        prefer_css_page_size : Union[bool, None]
            Give any CSS `@page` size declared in the page priority over what is declared in `width` and `height` or `format`
            options. Defaults to `false`, which will scale the content to fit the paper size.
        margin : Union[{top: Union[float, str, None], right: Union[float, str, None], bottom: Union[float, str, None], left: Union[float, str, None]}, None]
            Paper margins, defaults to none.
        path : Union[pathlib.Path, str, None]
            The file path to save the PDF to. If `path` is a relative path, then it is resolved relative to the current working
            directory. If no path is provided, the PDF won't be saved to the disk.
        outline : Union[bool, None]
            Whether or not to embed the document outline into the PDF. Defaults to `false`.
        tagged : Union[bool, None]
            Whether or not to generate tagged (accessible) PDF. Defaults to `false`.

        Returns
        -------
        bytes
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.pdf(
                scale=scale,
                displayHeaderFooter=display_header_footer,
                headerTemplate=header_template,
                footerTemplate=footer_template,
                printBackground=print_background,
                landscape=landscape,
                pageRanges=page_ranges,
                format=format,
                width=width,
                height=height,
                preferCSSPageSize=prefer_css_page_size,
                margin=margin,
                path=path,
                outline=outline,
                tagged=tagged,
            )
        )

    def expect_event(
        self,
        event: str,
        predicate: typing.Optional[typing.Callable] = None,
        *,
        timeout: typing.Optional[float] = None,
    ) -> AsyncEventContextManager:
        """Page.expect_event

        Waits for event to fire and passes its value into the predicate function. Returns when the predicate returns truthy
        value. Will throw an error if the page is closed before the event is fired. Returns the event data value.

        **Usage**

        ```py
        async with page.expect_event(\"framenavigated\") as event_info:
            await page.get_by_role(\"button\")
        frame = await event_info.value
        ```

        Parameters
        ----------
        event : str
            Event name, same one typically passed into `*.on(event)`.
        predicate : Union[Callable, None]
            Receives the event data and resolves to truthy value when the waiting should resolve.
        timeout : Union[float, None]
            Maximum time to wait for in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The
            default value can be changed by using the `browser_context.set_default_timeout()`.

        Returns
        -------
        EventContextManager
        """

        return AsyncEventContextManager(
            self._impl_obj.expect_event(
                event=event, predicate=self._wrap_handler(predicate), timeout=timeout
            ).future
        )

    def expect_console_message(
        self,
        predicate: typing.Optional[typing.Callable[["ConsoleMessage"], bool]] = None,
        *,
        timeout: typing.Optional[float] = None,
    ) -> AsyncEventContextManager["ConsoleMessage"]:
        """Page.expect_console_message

        Performs action and waits for a `ConsoleMessage` to be logged by in the page. If predicate is provided, it passes
        `ConsoleMessage` value into the `predicate` function and waits for `predicate(message)` to return a truthy value.
        Will throw an error if the page is closed before the `page.on('console')` event is fired.

        Parameters
        ----------
        predicate : Union[Callable[[ConsoleMessage], bool], None]
            Receives the `ConsoleMessage` object and resolves to truthy value when the waiting should resolve.
        timeout : Union[float, None]
            Maximum time to wait for in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The
            default value can be changed by using the `browser_context.set_default_timeout()`.

        Returns
        -------
        EventContextManager[ConsoleMessage]
        """

        return AsyncEventContextManager(
            self._impl_obj.expect_console_message(
                predicate=self._wrap_handler(predicate), timeout=timeout
            ).future
        )

    def expect_download(
        self,
        predicate: typing.Optional[typing.Callable[["Download"], bool]] = None,
        *,
        timeout: typing.Optional[float] = None,
    ) -> AsyncEventContextManager["Download"]:
        """Page.expect_download

        Performs action and waits for a new `Download`. If predicate is provided, it passes `Download` value into the
        `predicate` function and waits for `predicate(download)` to return a truthy value. Will throw an error if the page
        is closed before the download event is fired.

        Parameters
        ----------
        predicate : Union[Callable[[Download], bool], None]
            Receives the `Download` object and resolves to truthy value when the waiting should resolve.
        timeout : Union[float, None]
            Maximum time to wait for in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The
            default value can be changed by using the `browser_context.set_default_timeout()`.

        Returns
        -------
        EventContextManager[Download]
        """

        return AsyncEventContextManager(
            self._impl_obj.expect_download(
                predicate=self._wrap_handler(predicate), timeout=timeout
            ).future
        )

    def expect_file_chooser(
        self,
        predicate: typing.Optional[typing.Callable[["FileChooser"], bool]] = None,
        *,
        timeout: typing.Optional[float] = None,
    ) -> AsyncEventContextManager["FileChooser"]:
        """Page.expect_file_chooser

        Performs action and waits for a new `FileChooser` to be created. If predicate is provided, it passes `FileChooser`
        value into the `predicate` function and waits for `predicate(fileChooser)` to return a truthy value. Will throw an
        error if the page is closed before the file chooser is opened.

        Parameters
        ----------
        predicate : Union[Callable[[FileChooser], bool], None]
            Receives the `FileChooser` object and resolves to truthy value when the waiting should resolve.
        timeout : Union[float, None]
            Maximum time to wait for in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The
            default value can be changed by using the `browser_context.set_default_timeout()`.

        Returns
        -------
        EventContextManager[FileChooser]
        """

        return AsyncEventContextManager(
            self._impl_obj.expect_file_chooser(
                predicate=self._wrap_handler(predicate), timeout=timeout
            ).future
        )

    def expect_navigation(
        self,
        *,
        url: typing.Optional[
            typing.Union[str, typing.Pattern[str], typing.Callable[[str], bool]]
        ] = None,
        wait_until: typing.Optional[
            Literal["commit", "domcontentloaded", "load", "networkidle"]
        ] = None,
        timeout: typing.Optional[float] = None,
    ) -> AsyncEventContextManager["Response"]:
        """Page.expect_navigation

        Waits for the main frame navigation and returns the main resource response. In case of multiple redirects, the
        navigation will resolve with the response of the last redirect. In case of navigation to a different anchor or
        navigation due to History API usage, the navigation will resolve with `null`.

        **Usage**

        This resolves when the page navigates to a new URL or reloads. It is useful for when you run code which will
        indirectly cause the page to navigate. e.g. The click target has an `onclick` handler that triggers navigation from
        a `setTimeout`. Consider this example:

        ```py
        async with page.expect_navigation():
            # This action triggers the navigation after a timeout.
            await page.get_by_text(\"Navigate after timeout\").click()
        # Resolves after navigation has finished
        ```

        **NOTE** Usage of the [History API](https://developer.mozilla.org/en-US/docs/Web/API/History_API) to change the URL
        is considered a navigation.

        Parameters
        ----------
        url : Union[Callable[[str], bool], Pattern[str], str, None]
            A glob pattern, regex pattern or predicate receiving [URL] to match while waiting for the navigation. Note that if
            the parameter is a string without wildcard characters, the method will wait for navigation to URL that is exactly
            equal to the string.
        wait_until : Union["commit", "domcontentloaded", "load", "networkidle", None]
            When to consider operation succeeded, defaults to `load`. Events can be either:
            - `'domcontentloaded'` - consider operation to be finished when the `DOMContentLoaded` event is fired.
            - `'load'` - consider operation to be finished when the `load` event is fired.
            - `'networkidle'` - **DISCOURAGED** consider operation to be finished when there are no network connections for
              at least `500` ms. Don't use this method for testing, rely on web assertions to assess readiness instead.
            - `'commit'` - consider operation to be finished when network response is received and the document started
              loading.
        timeout : Union[float, None]
            Maximum operation time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_navigation_timeout()`,
            `browser_context.set_default_timeout()`, `page.set_default_navigation_timeout()` or
            `page.set_default_timeout()` methods.

        Returns
        -------
        EventContextManager[Response]
        """

        return AsyncEventContextManager(
            self._impl_obj.expect_navigation(
                url=self._wrap_handler(url), waitUntil=wait_until, timeout=timeout
            ).future
        )

    def expect_popup(
        self,
        predicate: typing.Optional[typing.Callable[["Page"], bool]] = None,
        *,
        timeout: typing.Optional[float] = None,
    ) -> AsyncEventContextManager["Page"]:
        """Page.expect_popup

        Performs action and waits for a popup `Page`. If predicate is provided, it passes [Popup] value into the
        `predicate` function and waits for `predicate(page)` to return a truthy value. Will throw an error if the page is
        closed before the popup event is fired.

        Parameters
        ----------
        predicate : Union[Callable[[Page], bool], None]
            Receives the `Page` object and resolves to truthy value when the waiting should resolve.
        timeout : Union[float, None]
            Maximum time to wait for in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The
            default value can be changed by using the `browser_context.set_default_timeout()`.

        Returns
        -------
        EventContextManager[Page]
        """

        return AsyncEventContextManager(
            self._impl_obj.expect_popup(
                predicate=self._wrap_handler(predicate), timeout=timeout
            ).future
        )

    def expect_request(
        self,
        url_or_predicate: typing.Union[
            str, typing.Pattern[str], typing.Callable[["Request"], bool]
        ],
        *,
        timeout: typing.Optional[float] = None,
    ) -> AsyncEventContextManager["Request"]:
        """Page.expect_request

        Waits for the matching request and returns it. See [waiting for event](https://playwright.dev/python/docs/events#waiting-for-event) for more
        details about events.

        **Usage**

        ```py
        async with page.expect_request(\"http://example.com/resource\") as first:
            await page.get_by_text(\"trigger request\").click()
        first_request = await first.value

        # or with a lambda
        async with page.expect_request(lambda request: request.url == \"http://example.com\" and request.method == \"get\") as second:
            await page.get_by_text(\"trigger request\").click()
        second_request = await second.value
        ```

        Parameters
        ----------
        url_or_predicate : Union[Callable[[Request], bool], Pattern[str], str]
            Request URL string, regex or predicate receiving `Request` object. When a `baseURL` via the context options was
            provided and the passed URL is a path, it gets merged via the
            [`new URL()`](https://developer.mozilla.org/en-US/docs/Web/API/URL/URL) constructor.
        timeout : Union[float, None]
            Maximum wait time in milliseconds, defaults to 30 seconds, pass `0` to disable the timeout. The default value can
            be changed by using the `page.set_default_timeout()` method.

        Returns
        -------
        EventContextManager[Request]
        """

        return AsyncEventContextManager(
            self._impl_obj.expect_request(
                urlOrPredicate=self._wrap_handler(url_or_predicate), timeout=timeout
            ).future
        )

    def expect_request_finished(
        self,
        predicate: typing.Optional[typing.Callable[["Request"], bool]] = None,
        *,
        timeout: typing.Optional[float] = None,
    ) -> AsyncEventContextManager["Request"]:
        """Page.expect_request_finished

        Performs action and waits for a `Request` to finish loading. If predicate is provided, it passes `Request` value
        into the `predicate` function and waits for `predicate(request)` to return a truthy value. Will throw an error if
        the page is closed before the `page.on('request_finished')` event is fired.

        Parameters
        ----------
        predicate : Union[Callable[[Request], bool], None]
            Receives the `Request` object and resolves to truthy value when the waiting should resolve.
        timeout : Union[float, None]
            Maximum time to wait for in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The
            default value can be changed by using the `browser_context.set_default_timeout()`.

        Returns
        -------
        EventContextManager[Request]
        """

        return AsyncEventContextManager(
            self._impl_obj.expect_request_finished(
                predicate=self._wrap_handler(predicate), timeout=timeout
            ).future
        )

    def expect_response(
        self,
        url_or_predicate: typing.Union[
            str, typing.Pattern[str], typing.Callable[["Response"], bool]
        ],
        *,
        timeout: typing.Optional[float] = None,
    ) -> AsyncEventContextManager["Response"]:
        """Page.expect_response

        Returns the matched response. See [waiting for event](https://playwright.dev/python/docs/events#waiting-for-event) for more details about
        events.

        **Usage**

        ```py
        async with page.expect_response(\"https://example.com/resource\") as response_info:
            await page.get_by_text(\"trigger response\").click()
        response = await response_info.value
        return response.ok

        # or with a lambda
        async with page.expect_response(lambda response: response.url == \"https://example.com\" and response.status == 200 and response.request.method == \"get\") as response_info:
            await page.get_by_text(\"trigger response\").click()
        response = await response_info.value
        return response.ok
        ```

        Parameters
        ----------
        url_or_predicate : Union[Callable[[Response], bool], Pattern[str], str]
            Request URL string, regex or predicate receiving `Response` object. When a `baseURL` via the context options was
            provided and the passed URL is a path, it gets merged via the
            [`new URL()`](https://developer.mozilla.org/en-US/docs/Web/API/URL/URL) constructor.
        timeout : Union[float, None]
            Maximum wait time in milliseconds, defaults to 30 seconds, pass `0` to disable the timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.

        Returns
        -------
        EventContextManager[Response]
        """

        return AsyncEventContextManager(
            self._impl_obj.expect_response(
                urlOrPredicate=self._wrap_handler(url_or_predicate), timeout=timeout
            ).future
        )

    def expect_websocket(
        self,
        predicate: typing.Optional[typing.Callable[["WebSocket"], bool]] = None,
        *,
        timeout: typing.Optional[float] = None,
    ) -> AsyncEventContextManager["WebSocket"]:
        """Page.expect_websocket

        Performs action and waits for a new `WebSocket`. If predicate is provided, it passes `WebSocket` value into the
        `predicate` function and waits for `predicate(webSocket)` to return a truthy value. Will throw an error if the page
        is closed before the WebSocket event is fired.

        Parameters
        ----------
        predicate : Union[Callable[[WebSocket], bool], None]
            Receives the `WebSocket` object and resolves to truthy value when the waiting should resolve.
        timeout : Union[float, None]
            Maximum time to wait for in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The
            default value can be changed by using the `browser_context.set_default_timeout()`.

        Returns
        -------
        EventContextManager[WebSocket]
        """

        return AsyncEventContextManager(
            self._impl_obj.expect_websocket(
                predicate=self._wrap_handler(predicate), timeout=timeout
            ).future
        )

    def expect_worker(
        self,
        predicate: typing.Optional[typing.Callable[["Worker"], bool]] = None,
        *,
        timeout: typing.Optional[float] = None,
    ) -> AsyncEventContextManager["Worker"]:
        """Page.expect_worker

        Performs action and waits for a new `Worker`. If predicate is provided, it passes `Worker` value into the
        `predicate` function and waits for `predicate(worker)` to return a truthy value. Will throw an error if the page is
        closed before the worker event is fired.

        Parameters
        ----------
        predicate : Union[Callable[[Worker], bool], None]
            Receives the `Worker` object and resolves to truthy value when the waiting should resolve.
        timeout : Union[float, None]
            Maximum time to wait for in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The
            default value can be changed by using the `browser_context.set_default_timeout()`.

        Returns
        -------
        EventContextManager[Worker]
        """

        return AsyncEventContextManager(
            self._impl_obj.expect_worker(
                predicate=self._wrap_handler(predicate), timeout=timeout
            ).future
        )

    async def set_checked(
        self,
        selector: str,
        checked: bool,
        *,
        position: typing.Optional[Position] = None,
        timeout: typing.Optional[float] = None,
        force: typing.Optional[bool] = None,
        no_wait_after: typing.Optional[bool] = None,
        strict: typing.Optional[bool] = None,
        trial: typing.Optional[bool] = None,
    ) -> None:
        """Page.set_checked

        This method checks or unchecks an element matching `selector` by performing the following steps:
        1. Find an element matching `selector`. If there is none, wait until a matching element is attached to the DOM.
        1. Ensure that matched element is a checkbox or a radio input. If not, this method throws.
        1. If the element already has the right checked state, this method returns immediately.
        1. Wait for [actionability](https://playwright.dev/python/docs/actionability) checks on the matched element, unless `force` option is set. If
           the element is detached during the checks, the whole action is retried.
        1. Scroll the element into view if needed.
        1. Use `page.mouse` to click in the center of the element.
        1. Ensure that the element is now checked or unchecked. If not, this method throws.

        When all steps combined have not finished during the specified `timeout`, this method throws a `TimeoutError`.
        Passing zero timeout disables this.

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be
            used.
        checked : bool
            Whether to check or uncheck the checkbox.
        position : Union[{x: float, y: float}, None]
            A point to use relative to the top-left corner of element padding box. If not specified, uses some visible point of
            the element.
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        force : Union[bool, None]
            Whether to bypass the [actionability](../actionability.md) checks. Defaults to `false`.
        no_wait_after : Union[bool, None]
            This option has no effect.
            Deprecated: This option has no effect.
        strict : Union[bool, None]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more than one
            element, the call throws an exception.
        trial : Union[bool, None]
            When set, this method only performs the [actionability](../actionability.md) checks and skips the action. Defaults
            to `false`. Useful to wait until the element is ready for the action without performing it.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.set_checked(
                selector=selector,
                checked=checked,
                position=position,
                timeout=timeout,
                force=force,
                noWaitAfter=no_wait_after,
                strict=strict,
                trial=trial,
            )
        )

    async def add_locator_handler(
        self,
        locator: "Locator",
        handler: typing.Union[
            typing.Callable[["Locator"], typing.Any], typing.Callable[[], typing.Any]
        ],
        *,
        no_wait_after: typing.Optional[bool] = None,
        times: typing.Optional[int] = None,
    ) -> None:
        """Page.add_locator_handler

        When testing a web page, sometimes unexpected overlays like a \"Sign up\" dialog appear and block actions you want to
        automate, e.g. clicking a button. These overlays don't always show up in the same way or at the same time, making
        them tricky to handle in automated tests.

        This method lets you set up a special function, called a handler, that activates when it detects that overlay is
        visible. The handler's job is to remove the overlay, allowing your test to continue as if the overlay wasn't there.

        Things to keep in mind:
        - When an overlay is shown predictably, we recommend explicitly waiting for it in your test and dismissing it as
          a part of your normal test flow, instead of using `page.add_locator_handler()`.
        - Playwright checks for the overlay every time before executing or retrying an action that requires an
          [actionability check](https://playwright.dev/python/docs/actionability), or before performing an auto-waiting assertion check. When overlay
          is visible, Playwright calls the handler first, and then proceeds with the action/assertion. Note that the
          handler is only called when you perform an action/assertion - if the overlay becomes visible but you don't
          perform any actions, the handler will not be triggered.
        - After executing the handler, Playwright will ensure that overlay that triggered the handler is not visible
          anymore. You can opt-out of this behavior with `noWaitAfter`.
        - The execution time of the handler counts towards the timeout of the action/assertion that executed the handler.
          If your handler takes too long, it might cause timeouts.
        - You can register multiple handlers. However, only a single handler will be running at a time. Make sure the
          actions within a handler don't depend on another handler.

        **NOTE** Running the handler will alter your page state mid-test. For example it will change the currently focused
        element and move the mouse. Make sure that actions that run after the handler are self-contained and do not rely on
        the focus and mouse state being unchanged.

        For example, consider a test that calls `locator.focus()` followed by `keyboard.press()`. If your
        handler clicks a button between these two actions, the focused element most likely will be wrong, and key press
        will happen on the unexpected element. Use `locator.press()` instead to avoid this problem.

        Another example is a series of mouse actions, where `mouse.move()` is followed by `mouse.down()`.
        Again, when the handler runs between these two actions, the mouse position will be wrong during the mouse down.
        Prefer self-contained actions like `locator.click()` that do not rely on the state being unchanged by a
        handler.

        **Usage**

        An example that closes a \"Sign up to the newsletter\" dialog when it appears:

        ```py
        # Setup the handler.
        def handler():
          page.get_by_role(\"button\", name=\"No thanks\").click()
        page.add_locator_handler(page.get_by_text(\"Sign up to the newsletter\"), handler)

        # Write the test as usual.
        page.goto(\"https://example.com\")
        page.get_by_role(\"button\", name=\"Start here\").click()
        ```

        An example that skips the \"Confirm your security details\" page when it is shown:

        ```py
        # Setup the handler.
        def handler():
          page.get_by_role(\"button\", name=\"Remind me later\").click()
        page.add_locator_handler(page.get_by_text(\"Confirm your security details\"), handler)

        # Write the test as usual.
        page.goto(\"https://example.com\")
        page.get_by_role(\"button\", name=\"Start here\").click()
        ```

        An example with a custom callback on every actionability check. It uses a `<body>` locator that is always visible,
        so the handler is called before every actionability check. It is important to specify `noWaitAfter`, because the
        handler does not hide the `<body>` element.

        ```py
        # Setup the handler.
        def handler():
          page.evaluate(\"window.removeObstructionsForTestIfNeeded()\")
        page.add_locator_handler(page.locator(\"body\"), handler, no_wait_after=True)

        # Write the test as usual.
        page.goto(\"https://example.com\")
        page.get_by_role(\"button\", name=\"Start here\").click()
        ```

        Handler takes the original locator as an argument. You can also automatically remove the handler after a number of
        invocations by setting `times`:

        ```py
        def handler(locator):
          locator.click()
        page.add_locator_handler(page.get_by_label(\"Close\"), handler, times=1)
        ```

        Parameters
        ----------
        locator : Locator
            Locator that triggers the handler.
        handler : Union[Callable[[Locator], Any], Callable[[], Any]]
            Function that should be run once `locator` appears. This function should get rid of the element that blocks actions
            like click.
        no_wait_after : Union[bool, None]
            By default, after calling the handler Playwright will wait until the overlay becomes hidden, and only then
            Playwright will continue with the action/assertion that triggered the handler. This option allows to opt-out of
            this behavior, so that overlay can stay visible after the handler has run.
        times : Union[int, None]
            Specifies the maximum number of times this handler should be called. Unlimited by default.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.add_locator_handler(
                locator=locator._impl_obj,
                handler=self._wrap_handler(handler),
                noWaitAfter=no_wait_after,
                times=times,
            )
        )

    async def remove_locator_handler(self, locator: "Locator") -> None:
        """Page.remove_locator_handler

        Removes all locator handlers added by `page.add_locator_handler()` for a specific locator.

        Parameters
        ----------
        locator : Locator
            Locator passed to `page.add_locator_handler()`.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.remove_locator_handler(locator=locator._impl_obj)
        )

    async def requests(self) -> typing.List["Request"]:
        """Page.requests

        Returns up to (currently) 100 last network request from this page. See `page.on('request')` for more details.

        Returned requests should be accessed immediately, otherwise they might be collected to prevent unbounded memory
        growth as new requests come in. Once collected, retrieving most information about the request is impossible.

        Note that requests reported through the `page.on('request')` request are not collected, so there is a trade off
        between efficient memory usage with `page.requests()` and the amount of available information reported
        through `page.on('request')`.

        Returns
        -------
        List[Request]
        """

        return mapping.from_impl_list(await self._impl_obj.requests())

    async def console_messages(self) -> typing.List["ConsoleMessage"]:
        """Page.console_messages

        Returns up to (currently) 200 last console messages from this page. See `page.on('console')` for more details.

        Returns
        -------
        List[ConsoleMessage]
        """

        return mapping.from_impl_list(await self._impl_obj.console_messages())

    async def page_errors(self) -> typing.List["Error"]:
        """Page.page_errors

        Returns up to (currently) 200 last page errors from this page. See `page.on('page_error')` for more details.

        Returns
        -------
        List[Error]
        """

        return mapping.from_impl_list(await self._impl_obj.page_errors())


mapping.register(PageImpl, Page)


class WebError(AsyncBase):

    @property
    def page(self) -> typing.Optional["Page"]:
        """WebError.page

        The page that produced this unhandled exception, if any.

        Returns
        -------
        Union[Page, None]
        """
        return mapping.from_impl_nullable(self._impl_obj.page)

    @property
    def error(self) -> "Error":
        """WebError.error

        Unhandled error that was thrown.

        Returns
        -------
        Error
        """
        return mapping.from_impl(self._impl_obj.error)


mapping.register(WebErrorImpl, WebError)


class BrowserContext(AsyncContextManager):

    @typing.overload
    def on(
        self,
        event: Literal["backgroundpage"],
        f: typing.Callable[["Page"], "typing.Union[typing.Awaitable[None], None]"],
    ) -> None:
        """
        This event is not emitted."""

    @typing.overload
    def on(
        self,
        event: Literal["close"],
        f: typing.Callable[
            ["BrowserContext"], "typing.Union[typing.Awaitable[None], None]"
        ],
    ) -> None:
        """
        Emitted when Browser context gets closed. This might happen because of one of the following:
        - Browser context is closed.
        - Browser application is closed or crashed.
        - The `browser.close()` method was called."""

    @typing.overload
    def on(
        self,
        event: Literal["console"],
        f: typing.Callable[
            ["ConsoleMessage"], "typing.Union[typing.Awaitable[None], None]"
        ],
    ) -> None:
        """
        Emitted when JavaScript within the page calls one of console API methods, e.g. `console.log` or `console.dir`.

        The arguments passed into `console.log` and the page are available on the `ConsoleMessage` event handler argument.

        **Usage**

        ```py
        async def print_args(msg):
            values = []
            for arg in msg.args:
                values.append(await arg.json_value())
            print(values)

        context.on(\"console\", print_args)
        await page.evaluate(\"console.log('hello', 5, { foo: 'bar' })\")
        ```"""

    @typing.overload
    def on(
        self,
        event: Literal["dialog"],
        f: typing.Callable[["Dialog"], "typing.Union[typing.Awaitable[None], None]"],
    ) -> None:
        """
        Emitted when a JavaScript dialog appears, such as `alert`, `prompt`, `confirm` or `beforeunload`. Listener **must**
        either `dialog.accept()` or `dialog.dismiss()` the dialog - otherwise the page will
        [freeze](https://developer.mozilla.org/en-US/docs/Web/JavaScript/EventLoop#never_blocking) waiting for the dialog,
        and actions like click will never finish.

        **Usage**

        ```python
        context.on(\"dialog\", lambda dialog: dialog.accept())
        ```

        **NOTE** When no `page.on('dialog')` or `browser_context.on('dialog')` listeners are present, all dialogs are
        automatically dismissed."""

    @typing.overload
    def on(
        self,
        event: Literal["page"],
        f: typing.Callable[["Page"], "typing.Union[typing.Awaitable[None], None]"],
    ) -> None:
        """
        The event is emitted when a new Page is created in the BrowserContext. The page may still be loading. The event
        will also fire for popup pages. See also `page.on('popup')` to receive events about popups relevant to a
        specific page.

        The earliest moment that page is available is when it has navigated to the initial url. For example, when opening a
        popup with `window.open('http://example.com')`, this event will fire when the network request to
        \"http://example.com\" is done and its response has started loading in the popup. If you would like to route/listen
        to this network request, use `browser_context.route()` and `browser_context.on('request')` respectively
        instead of similar methods on the `Page`.

        ```py
        async with context.expect_page() as page_info:
            await page.get_by_text(\"open new page\").click(),
        page = await page_info.value
        print(await page.evaluate(\"location.href\"))
        ```

        **NOTE** Use `page.wait_for_load_state()` to wait until the page gets to a particular state (you should not
        need it in most cases)."""

    @typing.overload
    def on(
        self,
        event: Literal["weberror"],
        f: typing.Callable[["WebError"], "typing.Union[typing.Awaitable[None], None]"],
    ) -> None:
        """
        Emitted when exception is unhandled in any of the pages in this context. To listen for errors from a particular
        page, use `page.on('page_error')` instead."""

    @typing.overload
    def on(
        self,
        event: Literal["request"],
        f: typing.Callable[["Request"], "typing.Union[typing.Awaitable[None], None]"],
    ) -> None:
        """
        Emitted when a request is issued from any pages created through this context. The [request] object is read-only. To
        only listen for requests from a particular page, use `page.on('request')`.

        In order to intercept and mutate requests, see `browser_context.route()` or `page.route()`.
        """

    @typing.overload
    def on(
        self,
        event: Literal["requestfailed"],
        f: typing.Callable[["Request"], "typing.Union[typing.Awaitable[None], None]"],
    ) -> None:
        """
        Emitted when a request fails, for example by timing out. To only listen for failed requests from a particular page,
        use `page.on('request_failed')`.

        **NOTE** HTTP Error responses, such as 404 or 503, are still successful responses from HTTP standpoint, so request
        will complete with `browser_context.on('request_finished')` event and not with
        `browser_context.on('request_failed')`."""

    @typing.overload
    def on(
        self,
        event: Literal["requestfinished"],
        f: typing.Callable[["Request"], "typing.Union[typing.Awaitable[None], None]"],
    ) -> None:
        """
        Emitted when a request finishes successfully after downloading the response body. For a successful response, the
        sequence of events is `request`, `response` and `requestfinished`. To listen for successful requests from a
        particular page, use `page.on('request_finished')`."""

    @typing.overload
    def on(
        self,
        event: Literal["response"],
        f: typing.Callable[["Response"], "typing.Union[typing.Awaitable[None], None]"],
    ) -> None:
        """
        Emitted when [response] status and headers are received for a request. For a successful response, the sequence of
        events is `request`, `response` and `requestfinished`. To listen for response events from a particular page, use
        `page.on('response')`."""

    @typing.overload
    def on(
        self,
        event: Literal["serviceworker"],
        f: typing.Callable[["Worker"], "typing.Union[typing.Awaitable[None], None]"],
    ) -> None:
        """
        **NOTE** Service workers are only supported on Chromium-based browsers.

        Emitted when new service worker is created in the context."""

    def on(
        self,
        event: str,
        f: typing.Callable[..., typing.Union[typing.Awaitable[None], None]],
    ) -> None:
        return super().on(event=event, f=f)

    @typing.overload
    def once(
        self,
        event: Literal["backgroundpage"],
        f: typing.Callable[["Page"], "typing.Union[typing.Awaitable[None], None]"],
    ) -> None:
        """
        This event is not emitted."""

    @typing.overload
    def once(
        self,
        event: Literal["close"],
        f: typing.Callable[
            ["BrowserContext"], "typing.Union[typing.Awaitable[None], None]"
        ],
    ) -> None:
        """
        Emitted when Browser context gets closed. This might happen because of one of the following:
        - Browser context is closed.
        - Browser application is closed or crashed.
        - The `browser.close()` method was called."""

    @typing.overload
    def once(
        self,
        event: Literal["console"],
        f: typing.Callable[
            ["ConsoleMessage"], "typing.Union[typing.Awaitable[None], None]"
        ],
    ) -> None:
        """
        Emitted when JavaScript within the page calls one of console API methods, e.g. `console.log` or `console.dir`.

        The arguments passed into `console.log` and the page are available on the `ConsoleMessage` event handler argument.

        **Usage**

        ```py
        async def print_args(msg):
            values = []
            for arg in msg.args:
                values.append(await arg.json_value())
            print(values)

        context.on(\"console\", print_args)
        await page.evaluate(\"console.log('hello', 5, { foo: 'bar' })\")
        ```"""

    @typing.overload
    def once(
        self,
        event: Literal["dialog"],
        f: typing.Callable[["Dialog"], "typing.Union[typing.Awaitable[None], None]"],
    ) -> None:
        """
        Emitted when a JavaScript dialog appears, such as `alert`, `prompt`, `confirm` or `beforeunload`. Listener **must**
        either `dialog.accept()` or `dialog.dismiss()` the dialog - otherwise the page will
        [freeze](https://developer.mozilla.org/en-US/docs/Web/JavaScript/EventLoop#never_blocking) waiting for the dialog,
        and actions like click will never finish.

        **Usage**

        ```python
        context.on(\"dialog\", lambda dialog: dialog.accept())
        ```

        **NOTE** When no `page.on('dialog')` or `browser_context.on('dialog')` listeners are present, all dialogs are
        automatically dismissed."""

    @typing.overload
    def once(
        self,
        event: Literal["page"],
        f: typing.Callable[["Page"], "typing.Union[typing.Awaitable[None], None]"],
    ) -> None:
        """
        The event is emitted when a new Page is created in the BrowserContext. The page may still be loading. The event
        will also fire for popup pages. See also `page.on('popup')` to receive events about popups relevant to a
        specific page.

        The earliest moment that page is available is when it has navigated to the initial url. For example, when opening a
        popup with `window.open('http://example.com')`, this event will fire when the network request to
        \"http://example.com\" is done and its response has started loading in the popup. If you would like to route/listen
        to this network request, use `browser_context.route()` and `browser_context.on('request')` respectively
        instead of similar methods on the `Page`.

        ```py
        async with context.expect_page() as page_info:
            await page.get_by_text(\"open new page\").click(),
        page = await page_info.value
        print(await page.evaluate(\"location.href\"))
        ```

        **NOTE** Use `page.wait_for_load_state()` to wait until the page gets to a particular state (you should not
        need it in most cases)."""

    @typing.overload
    def once(
        self,
        event: Literal["weberror"],
        f: typing.Callable[["WebError"], "typing.Union[typing.Awaitable[None], None]"],
    ) -> None:
        """
        Emitted when exception is unhandled in any of the pages in this context. To listen for errors from a particular
        page, use `page.on('page_error')` instead."""

    @typing.overload
    def once(
        self,
        event: Literal["request"],
        f: typing.Callable[["Request"], "typing.Union[typing.Awaitable[None], None]"],
    ) -> None:
        """
        Emitted when a request is issued from any pages created through this context. The [request] object is read-only. To
        only listen for requests from a particular page, use `page.on('request')`.

        In order to intercept and mutate requests, see `browser_context.route()` or `page.route()`.
        """

    @typing.overload
    def once(
        self,
        event: Literal["requestfailed"],
        f: typing.Callable[["Request"], "typing.Union[typing.Awaitable[None], None]"],
    ) -> None:
        """
        Emitted when a request fails, for example by timing out. To only listen for failed requests from a particular page,
        use `page.on('request_failed')`.

        **NOTE** HTTP Error responses, such as 404 or 503, are still successful responses from HTTP standpoint, so request
        will complete with `browser_context.on('request_finished')` event and not with
        `browser_context.on('request_failed')`."""

    @typing.overload
    def once(
        self,
        event: Literal["requestfinished"],
        f: typing.Callable[["Request"], "typing.Union[typing.Awaitable[None], None]"],
    ) -> None:
        """
        Emitted when a request finishes successfully after downloading the response body. For a successful response, the
        sequence of events is `request`, `response` and `requestfinished`. To listen for successful requests from a
        particular page, use `page.on('request_finished')`."""

    @typing.overload
    def once(
        self,
        event: Literal["response"],
        f: typing.Callable[["Response"], "typing.Union[typing.Awaitable[None], None]"],
    ) -> None:
        """
        Emitted when [response] status and headers are received for a request. For a successful response, the sequence of
        events is `request`, `response` and `requestfinished`. To listen for response events from a particular page, use
        `page.on('response')`."""

    @typing.overload
    def once(
        self,
        event: Literal["serviceworker"],
        f: typing.Callable[["Worker"], "typing.Union[typing.Awaitable[None], None]"],
    ) -> None:
        """
        **NOTE** Service workers are only supported on Chromium-based browsers.

        Emitted when new service worker is created in the context."""

    def once(
        self,
        event: str,
        f: typing.Callable[..., typing.Union[typing.Awaitable[None], None]],
    ) -> None:
        return super().once(event=event, f=f)

    @property
    def pages(self) -> typing.List["Page"]:
        """BrowserContext.pages

        Returns all open pages in the context.

        Returns
        -------
        List[Page]
        """
        return mapping.from_impl_list(self._impl_obj.pages)

    @property
    def browser(self) -> typing.Optional["Browser"]:
        """BrowserContext.browser

        Gets the browser instance that owns the context. Returns `null` if the context is created outside of normal
        browser, e.g. Android or Electron.

        Returns
        -------
        Union[Browser, None]
        """
        return mapping.from_impl_nullable(self._impl_obj.browser)

    @property
    def background_pages(self) -> typing.List["Page"]:
        """BrowserContext.background_pages

        Returns an empty list.

        Returns
        -------
        List[Page]
        """
        return mapping.from_impl_list(self._impl_obj.background_pages)

    @property
    def service_workers(self) -> typing.List["Worker"]:
        """BrowserContext.service_workers

        **NOTE** Service workers are only supported on Chromium-based browsers.

        All existing service workers in the context.

        Returns
        -------
        List[Worker]
        """
        return mapping.from_impl_list(self._impl_obj.service_workers)

    @property
    def tracing(self) -> "Tracing":
        """BrowserContext.tracing

        Returns
        -------
        Tracing
        """
        return mapping.from_impl(self._impl_obj.tracing)

    @property
    def request(self) -> "APIRequestContext":
        """BrowserContext.request

        API testing helper associated with this context. Requests made with this API will use context cookies.

        Returns
        -------
        APIRequestContext
        """
        return mapping.from_impl(self._impl_obj.request)

    @property
    def clock(self) -> "Clock":
        """BrowserContext.clock

        Playwright has ability to mock clock and passage of time.

        Returns
        -------
        Clock
        """
        return mapping.from_impl(self._impl_obj.clock)

    def set_default_navigation_timeout(self, timeout: float) -> None:
        """BrowserContext.set_default_navigation_timeout

        This setting will change the default maximum navigation time for the following methods and related shortcuts:
        - `page.go_back()`
        - `page.go_forward()`
        - `page.goto()`
        - `page.reload()`
        - `page.set_content()`
        - `page.expect_navigation()`

        **NOTE** `page.set_default_navigation_timeout()` and `page.set_default_timeout()` take priority over
        `browser_context.set_default_navigation_timeout()`.

        Parameters
        ----------
        timeout : float
            Maximum navigation time in milliseconds
        """

        return mapping.from_maybe_impl(
            self._impl_obj.set_default_navigation_timeout(timeout=timeout)
        )

    def set_default_timeout(self, timeout: float) -> None:
        """BrowserContext.set_default_timeout

        This setting will change the default maximum time for all the methods accepting `timeout` option.

        **NOTE** `page.set_default_navigation_timeout()`, `page.set_default_timeout()` and
        `browser_context.set_default_navigation_timeout()` take priority over
        `browser_context.set_default_timeout()`.

        Parameters
        ----------
        timeout : float
            Maximum time in milliseconds. Pass `0` to disable timeout.
        """

        return mapping.from_maybe_impl(
            self._impl_obj.set_default_timeout(timeout=timeout)
        )

    async def new_page(self) -> "Page":
        """BrowserContext.new_page

        Creates a new page in the browser context.

        Returns
        -------
        Page
        """

        return mapping.from_impl(await self._impl_obj.new_page())

    async def cookies(
        self, urls: typing.Optional[typing.Union[str, typing.Sequence[str]]] = None
    ) -> typing.List[Cookie]:
        """BrowserContext.cookies

        If no URLs are specified, this method returns all cookies. If URLs are specified, only cookies that affect those
        URLs are returned.

        Parameters
        ----------
        urls : Union[Sequence[str], str, None]
            Optional list of URLs.

        Returns
        -------
        List[{name: str, value: str, domain: str, path: str, expires: float, httpOnly: bool, secure: bool, sameSite: Union["Lax", "None", "Strict"], partitionKey: Union[str, None]}]
        """

        return mapping.from_impl_list(
            await self._impl_obj.cookies(urls=mapping.to_impl(urls))
        )

    async def add_cookies(self, cookies: typing.Sequence[SetCookieParam]) -> None:
        """BrowserContext.add_cookies

        Adds cookies into this browser context. All pages within this context will have these cookies installed. Cookies
        can be obtained via `browser_context.cookies()`.

        **Usage**

        ```py
        await browser_context.add_cookies([cookie_object1, cookie_object2])
        ```

        Parameters
        ----------
        cookies : Sequence[{name: str, value: str, url: Union[str, None], domain: Union[str, None], path: Union[str, None], expires: Union[float, None], httpOnly: Union[bool, None], secure: Union[bool, None], sameSite: Union["Lax", "None", "Strict", None], partitionKey: Union[str, None]}]
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.add_cookies(cookies=mapping.to_impl(cookies))
        )

    async def clear_cookies(
        self,
        *,
        name: typing.Optional[typing.Union[typing.Pattern[str], str]] = None,
        domain: typing.Optional[typing.Union[typing.Pattern[str], str]] = None,
        path: typing.Optional[typing.Union[typing.Pattern[str], str]] = None,
    ) -> None:
        """BrowserContext.clear_cookies

        Removes cookies from context. Accepts optional filter.

        **Usage**

        ```py
        await context.clear_cookies()
        await context.clear_cookies(name=\"session-id\")
        await context.clear_cookies(domain=\"my-origin.com\")
        await context.clear_cookies(path=\"/api/v1\")
        await context.clear_cookies(name=\"session-id\", domain=\"my-origin.com\")
        ```

        Parameters
        ----------
        name : Union[Pattern[str], str, None]
            Only removes cookies with the given name.
        domain : Union[Pattern[str], str, None]
            Only removes cookies with the given domain.
        path : Union[Pattern[str], str, None]
            Only removes cookies with the given path.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.clear_cookies(name=name, domain=domain, path=path)
        )

    async def grant_permissions(
        self, permissions: typing.Sequence[str], *, origin: typing.Optional[str] = None
    ) -> None:
        """BrowserContext.grant_permissions

        Grants specified permissions to the browser context. Only grants corresponding permissions to the given origin if
        specified.

        Parameters
        ----------
        permissions : Sequence[str]
            A list of permissions to grant.

            **NOTE** Supported permissions differ between browsers, and even between different versions of the same browser.
            Any permission may stop working after an update.

            Here are some permissions that may be supported by some browsers:
            - `'accelerometer'`
            - `'ambient-light-sensor'`
            - `'background-sync'`
            - `'camera'`
            - `'clipboard-read'`
            - `'clipboard-write'`
            - `'geolocation'`
            - `'gyroscope'`
            - `'local-fonts'`
            - `'local-network-access'`
            - `'magnetometer'`
            - `'microphone'`
            - `'midi-sysex'` (system-exclusive midi)
            - `'midi'`
            - `'notifications'`
            - `'payment-handler'`
            - `'storage-access'`
        origin : Union[str, None]
            The [origin] to grant permissions to, e.g. "https://example.com".
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.grant_permissions(
                permissions=mapping.to_impl(permissions), origin=origin
            )
        )

    async def clear_permissions(self) -> None:
        """BrowserContext.clear_permissions

        Clears all permission overrides for the browser context.

        **Usage**

        ```py
        context = await browser.new_context()
        await context.grant_permissions([\"clipboard-read\"])
        # do stuff ..
        context.clear_permissions()
        ```
        """

        return mapping.from_maybe_impl(await self._impl_obj.clear_permissions())

    async def set_geolocation(
        self, geolocation: typing.Optional[Geolocation] = None
    ) -> None:
        """BrowserContext.set_geolocation

        Sets the context's geolocation. Passing `null` or `undefined` emulates position unavailable.

        **Usage**

        ```py
        await browser_context.set_geolocation({\"latitude\": 59.95, \"longitude\": 30.31667})
        ```

        **NOTE** Consider using `browser_context.grant_permissions()` to grant permissions for the browser context
        pages to read its geolocation.

        Parameters
        ----------
        geolocation : Union[{latitude: float, longitude: float, accuracy: Union[float, None]}, None]
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.set_geolocation(geolocation=geolocation)
        )

    async def set_extra_http_headers(self, headers: typing.Dict[str, str]) -> None:
        """BrowserContext.set_extra_http_headers

        The extra HTTP headers will be sent with every request initiated by any page in the context. These headers are
        merged with page-specific extra HTTP headers set with `page.set_extra_http_headers()`. If page overrides a
        particular header, page-specific header value will be used instead of the browser context header value.

        **NOTE** `browser_context.set_extra_http_headers()` does not guarantee the order of headers in the outgoing
        requests.

        Parameters
        ----------
        headers : Dict[str, str]
            An object containing additional HTTP headers to be sent with every request. All header values must be strings.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.set_extra_http_headers(
                headers=mapping.to_impl(headers)
            )
        )

    async def set_offline(self, offline: bool) -> None:
        """BrowserContext.set_offline

        Parameters
        ----------
        offline : bool
            Whether to emulate network being offline for the browser context.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.set_offline(offline=offline)
        )

    async def add_init_script(
        self,
        script: typing.Optional[str] = None,
        *,
        path: typing.Optional[typing.Union[pathlib.Path, str]] = None,
    ) -> None:
        """BrowserContext.add_init_script

        Adds a script which would be evaluated in one of the following scenarios:
        - Whenever a page is created in the browser context or is navigated.
        - Whenever a child frame is attached or navigated in any page in the browser context. In this case, the script is
          evaluated in the context of the newly attached frame.

        The script is evaluated after the document was created but before any of its scripts were run. This is useful to
        amend the JavaScript environment, e.g. to seed `Math.random`.

        **Usage**

        An example of overriding `Math.random` before the page loads:

        ```py
        # in your playwright script, assuming the preload.js file is in same directory.
        await browser_context.add_init_script(path=\"preload.js\")
        ```

        **NOTE** The order of evaluation of multiple scripts installed via `browser_context.add_init_script()` and
        `page.add_init_script()` is not defined.

        Parameters
        ----------
        script : Union[str, None]
            Script to be evaluated in all pages in the browser context. Optional.
        path : Union[pathlib.Path, str, None]
            Path to the JavaScript file. If `path` is a relative path, then it is resolved relative to the current working
            directory. Optional.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.add_init_script(script=script, path=path)
        )

    async def expose_binding(
        self,
        name: str,
        callback: typing.Callable,
        *,
        handle: typing.Optional[bool] = None,
    ) -> None:
        """BrowserContext.expose_binding

        The method adds a function called `name` on the `window` object of every frame in every page in the context. When
        called, the function executes `callback` and returns a [Promise] which resolves to the return value of `callback`.
        If the `callback` returns a [Promise], it will be awaited.

        The first argument of the `callback` function contains information about the caller: `{ browserContext:
        BrowserContext, page: Page, frame: Frame }`.

        See `page.expose_binding()` for page-only version.

        **Usage**

        An example of exposing page URL to all frames in all pages in the context:

        ```py
        import asyncio
        from playwright.async_api import async_playwright, Playwright

        async def run(playwright: Playwright):
            webkit = playwright.webkit
            browser = await webkit.launch(headless=False)
            context = await browser.new_context()
            await context.expose_binding(\"pageURL\", lambda source: source[\"page\"].url)
            page = await context.new_page()
            await page.set_content(\"\"\"
            <script>
              async function onClick() {
                document.querySelector('div').textContent = await window.pageURL();
              }
            </script>
            <button onclick=\"onClick()\">Click me</button>
            <div></div>
            \"\"\")
            await page.get_by_role(\"button\").click()

        async def main():
            async with async_playwright() as playwright:
                await run(playwright)
        asyncio.run(main())
        ```

        Parameters
        ----------
        name : str
            Name of the function on the window object.
        callback : Callable
            Callback function that will be called in the Playwright's context.
        handle : Union[bool, None]
            Whether to pass the argument as a handle, instead of passing by value. When passing a handle, only one argument is
            supported. When passing by value, multiple arguments are supported.
            Deprecated: This option will be removed in the future.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.expose_binding(
                name=name, callback=self._wrap_handler(callback), handle=handle
            )
        )

    async def expose_function(self, name: str, callback: typing.Callable) -> None:
        """BrowserContext.expose_function

        The method adds a function called `name` on the `window` object of every frame in every page in the context. When
        called, the function executes `callback` and returns a [Promise] which resolves to the return value of `callback`.

        If the `callback` returns a [Promise], it will be awaited.

        See `page.expose_function()` for page-only version.

        **Usage**

        An example of adding a `sha256` function to all pages in the context:

        ```py
        import asyncio
        import hashlib
        from playwright.async_api import async_playwright, Playwright

        def sha256(text: str) -> str:
            m = hashlib.sha256()
            m.update(bytes(text, \"utf8\"))
            return m.hexdigest()

        async def run(playwright: Playwright):
            webkit = playwright.webkit
            browser = await webkit.launch(headless=False)
            context = await browser.new_context()
            await context.expose_function(\"sha256\", sha256)
            page = await context.new_page()
            await page.set_content(\"\"\"
                <script>
                  async function onClick() {
                    document.querySelector('div').textContent = await window.sha256('PLAYWRIGHT');
                  }
                </script>
                <button onclick=\"onClick()\">Click me</button>
                <div></div>
            \"\"\")
            await page.get_by_role(\"button\").click()

        async def main():
            async with async_playwright() as playwright:
                await run(playwright)
        asyncio.run(main())
        ```

        Parameters
        ----------
        name : str
            Name of the function on the window object.
        callback : Callable
            Callback function that will be called in the Playwright's context.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.expose_function(
                name=name, callback=self._wrap_handler(callback)
            )
        )

    async def route(
        self,
        url: typing.Union[str, typing.Pattern[str], typing.Callable[[str], bool]],
        handler: typing.Union[
            typing.Callable[["Route"], typing.Any],
            typing.Callable[["Route", "Request"], typing.Any],
        ],
        *,
        times: typing.Optional[int] = None,
    ) -> None:
        """BrowserContext.route

        Routing provides the capability to modify network requests that are made by any page in the browser context. Once
        route is enabled, every request matching the url pattern will stall unless it's continued, fulfilled or aborted.

        **NOTE** `browser_context.route()` will not intercept requests intercepted by Service Worker. See
        [this](https://github.com/microsoft/playwright/issues/1090) issue. We recommend disabling Service Workers when
        using request interception by setting `serviceWorkers` to `'block'`.

        **Usage**

        An example of a naive handler that aborts all image requests:

        ```py
        context = await browser.new_context()
        page = await context.new_page()
        await context.route(\"**/*.{png,jpg,jpeg}\", lambda route: route.abort())
        await page.goto(\"https://example.com\")
        await browser.close()
        ```

        or the same snippet using a regex pattern instead:

        ```py
        context = await browser.new_context()
        page = await context.new_page()
        await context.route(re.compile(r\"(\\.png$)|(\\.jpg$)\"), lambda route: route.abort())
        page = await context.new_page()
        await page.goto(\"https://example.com\")
        await browser.close()
        ```

        It is possible to examine the request to decide the route action. For example, mocking all requests that contain
        some post data, and leaving all other requests as is:

        ```py
        async def handle_route(route: Route):
          if (\"my-string\" in route.request.post_data):
            await route.fulfill(body=\"mocked-data\")
          else:
            await route.continue_()
        await context.route(\"/api/**\", handle_route)
        ```

        Page routes (set up with `page.route()`) take precedence over browser context routes when request matches
        both handlers.

        To remove a route with its handler you can use `browser_context.unroute()`.

        **NOTE** Enabling routing disables http cache.

        Parameters
        ----------
        url : Union[Callable[[str], bool], Pattern[str], str]
            A glob pattern, regex pattern, or predicate that receives a [URL] to match during routing. If `baseURL` is set in
            the context options and the provided URL is a string that does not start with `*`, it is resolved using the
            [`new URL()`](https://developer.mozilla.org/en-US/docs/Web/API/URL/URL) constructor.
        handler : Union[Callable[[Route, Request], Any], Callable[[Route], Any]]
            handler function to route the request.
        times : Union[int, None]
            How often a route should be used. By default it will be used every time.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.route(
                url=self._wrap_handler(url),
                handler=self._wrap_handler(handler),
                times=times,
            )
        )

    async def unroute(
        self,
        url: typing.Union[str, typing.Pattern[str], typing.Callable[[str], bool]],
        handler: typing.Optional[
            typing.Union[
                typing.Callable[["Route"], typing.Any],
                typing.Callable[["Route", "Request"], typing.Any],
            ]
        ] = None,
    ) -> None:
        """BrowserContext.unroute

        Removes a route created with `browser_context.route()`. When `handler` is not specified, removes all routes
        for the `url`.

        Parameters
        ----------
        url : Union[Callable[[str], bool], Pattern[str], str]
            A glob pattern, regex pattern or predicate receiving [URL] used to register a routing with
            `browser_context.route()`.
        handler : Union[Callable[[Route, Request], Any], Callable[[Route], Any], None]
            Optional handler function used to register a routing with `browser_context.route()`.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.unroute(
                url=self._wrap_handler(url), handler=self._wrap_handler(handler)
            )
        )

    async def route_web_socket(
        self,
        url: typing.Union[str, typing.Pattern[str], typing.Callable[[str], bool]],
        handler: typing.Callable[["WebSocketRoute"], typing.Any],
    ) -> None:
        """BrowserContext.route_web_socket

        This method allows to modify websocket connections that are made by any page in the browser context.

        Note that only `WebSocket`s created after this method was called will be routed. It is recommended to call this
        method before creating any pages.

        **Usage**

        Below is an example of a simple handler that blocks some websocket messages. See `WebSocketRoute` for more details
        and examples.

        ```py
        def message_handler(ws: WebSocketRoute, message: Union[str, bytes]):
          if message == \"to-be-blocked\":
            return
          ws.send(message)

        async def handler(ws: WebSocketRoute):
          ws.route_send(lambda message: message_handler(ws, message))
          await ws.connect()

        await context.route_web_socket(\"/ws\", handler)
        ```

        Parameters
        ----------
        url : Union[Callable[[str], bool], Pattern[str], str]
            Only WebSockets with the url matching this pattern will be routed. A string pattern can be relative to the
            `baseURL` context option.
        handler : Callable[[WebSocketRoute], Any]
            Handler function to route the WebSocket.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.route_web_socket(
                url=self._wrap_handler(url), handler=self._wrap_handler(handler)
            )
        )

    async def unroute_all(
        self,
        *,
        behavior: typing.Optional[Literal["default", "ignoreErrors", "wait"]] = None,
    ) -> None:
        """BrowserContext.unroute_all

        Removes all routes created with `browser_context.route()` and `browser_context.route_from_har()`.

        Parameters
        ----------
        behavior : Union["default", "ignoreErrors", "wait", None]
            Specifies whether to wait for already running handlers and what to do if they throw errors:
            - `'default'` - do not wait for current handler calls (if any) to finish, if unrouted handler throws, it may
              result in unhandled error
            - `'wait'` - wait for current handler calls (if any) to finish
            - `'ignoreErrors'` - do not wait for current handler calls (if any) to finish, all errors thrown by the handlers
              after unrouting are silently caught
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.unroute_all(behavior=behavior)
        )

    async def route_from_har(
        self,
        har: typing.Union[pathlib.Path, str],
        *,
        url: typing.Optional[typing.Union[typing.Pattern[str], str]] = None,
        not_found: typing.Optional[Literal["abort", "fallback"]] = None,
        update: typing.Optional[bool] = None,
        update_content: typing.Optional[Literal["attach", "embed"]] = None,
        update_mode: typing.Optional[Literal["full", "minimal"]] = None,
    ) -> None:
        """BrowserContext.route_from_har

        If specified the network requests that are made in the context will be served from the HAR file. Read more about
        [Replaying from HAR](https://playwright.dev/python/docs/mock#replaying-from-har).

        Playwright will not serve requests intercepted by Service Worker from the HAR file. See
        [this](https://github.com/microsoft/playwright/issues/1090) issue. We recommend disabling Service Workers when
        using request interception by setting `serviceWorkers` to `'block'`.

        Parameters
        ----------
        har : Union[pathlib.Path, str]
            Path to a [HAR](http://www.softwareishard.com/blog/har-12-spec) file with prerecorded network data. If `path` is a
            relative path, then it is resolved relative to the current working directory.
        url : Union[Pattern[str], str, None]
            A glob pattern, regular expression or predicate to match the request URL. Only requests with URL matching the
            pattern will be served from the HAR file. If not specified, all requests are served from the HAR file.
        not_found : Union["abort", "fallback", None]
            - If set to 'abort' any request not found in the HAR file will be aborted.
            - If set to 'fallback' falls through to the next route handler in the handler chain.

            Defaults to abort.
        update : Union[bool, None]
            If specified, updates the given HAR with the actual network information instead of serving from file. The file is
            written to disk when `browser_context.close()` is called.
        update_content : Union["attach", "embed", None]
            Optional setting to control resource content management. If `attach` is specified, resources are persisted as
            separate files or entries in the ZIP archive. If `embed` is specified, content is stored inline the HAR file.
        update_mode : Union["full", "minimal", None]
            When set to `minimal`, only record information necessary for routing from HAR. This omits sizes, timing, page,
            cookies, security and other types of HAR information that are not used when replaying from HAR. Defaults to
            `minimal`.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.route_from_har(
                har=har,
                url=url,
                notFound=not_found,
                update=update,
                updateContent=update_content,
                updateMode=update_mode,
            )
        )

    def expect_event(
        self,
        event: str,
        predicate: typing.Optional[typing.Callable] = None,
        *,
        timeout: typing.Optional[float] = None,
    ) -> AsyncEventContextManager:
        """BrowserContext.expect_event

        Waits for event to fire and passes its value into the predicate function. Returns when the predicate returns truthy
        value. Will throw an error if the context closes before the event is fired. Returns the event data value.

        **Usage**

        ```py
        async with context.expect_event(\"page\") as event_info:
            await page.get_by_role(\"button\").click()
        page = await event_info.value
        ```

        Parameters
        ----------
        event : str
            Event name, same one would pass into `browserContext.on(event)`.
        predicate : Union[Callable, None]
            Receives the event data and resolves to truthy value when the waiting should resolve.
        timeout : Union[float, None]
            Maximum time to wait for in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The
            default value can be changed by using the `browser_context.set_default_timeout()`.

        Returns
        -------
        EventContextManager
        """

        return AsyncEventContextManager(
            self._impl_obj.expect_event(
                event=event, predicate=self._wrap_handler(predicate), timeout=timeout
            ).future
        )

    async def close(self, *, reason: typing.Optional[str] = None) -> None:
        """BrowserContext.close

        Closes the browser context. All the pages that belong to the browser context will be closed.

        **NOTE** The default browser context cannot be closed.

        Parameters
        ----------
        reason : Union[str, None]
            The reason to be reported to the operations interrupted by the context closure.
        """

        return mapping.from_maybe_impl(await self._impl_obj.close(reason=reason))

    async def storage_state(
        self,
        *,
        path: typing.Optional[typing.Union[pathlib.Path, str]] = None,
        indexed_db: typing.Optional[bool] = None,
    ) -> StorageState:
        """BrowserContext.storage_state

        Returns storage state for this browser context, contains current cookies, local storage snapshot and IndexedDB
        snapshot.

        Parameters
        ----------
        path : Union[pathlib.Path, str, None]
            The file path to save the storage state to. If `path` is a relative path, then it is resolved relative to current
            working directory. If no path is provided, storage state is still returned, but won't be saved to the disk.
        indexed_db : Union[bool, None]
            Set to `true` to include [IndexedDB](https://developer.mozilla.org/en-US/docs/Web/API/IndexedDB_API) in the storage
            state snapshot. If your application uses IndexedDB to store authentication tokens, like Firebase Authentication,
            enable this.

        Returns
        -------
        {cookies: List[{name: str, value: str, domain: str, path: str, expires: float, httpOnly: bool, secure: bool, sameSite: Union["Lax", "None", "Strict"]}], origins: List[{origin: str, localStorage: List[{name: str, value: str}]}]}
        """

        return mapping.from_impl(
            await self._impl_obj.storage_state(path=path, indexedDB=indexed_db)
        )

    async def wait_for_event(
        self,
        event: str,
        predicate: typing.Optional[typing.Callable] = None,
        *,
        timeout: typing.Optional[float] = None,
    ) -> typing.Any:
        """BrowserContext.wait_for_event

        **NOTE** In most cases, you should use `browser_context.expect_event()`.

        Waits for given `event` to fire. If predicate is provided, it passes event's value into the `predicate` function
        and waits for `predicate(event)` to return a truthy value. Will throw an error if the browser context is closed
        before the `event` is fired.

        Parameters
        ----------
        event : str
            Event name, same one typically passed into `*.on(event)`.
        predicate : Union[Callable, None]
            Receives the event data and resolves to truthy value when the waiting should resolve.
        timeout : Union[float, None]
            Maximum time to wait for in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The
            default value can be changed by using the `browser_context.set_default_timeout()`.

        Returns
        -------
        Any
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.wait_for_event(
                event=event, predicate=self._wrap_handler(predicate), timeout=timeout
            )
        )

    def expect_console_message(
        self,
        predicate: typing.Optional[typing.Callable[["ConsoleMessage"], bool]] = None,
        *,
        timeout: typing.Optional[float] = None,
    ) -> AsyncEventContextManager["ConsoleMessage"]:
        """BrowserContext.expect_console_message

        Performs action and waits for a `ConsoleMessage` to be logged by in the pages in the context. If predicate is
        provided, it passes `ConsoleMessage` value into the `predicate` function and waits for `predicate(message)` to
        return a truthy value. Will throw an error if the page is closed before the `browser_context.on('console')` event
        is fired.

        Parameters
        ----------
        predicate : Union[Callable[[ConsoleMessage], bool], None]
            Receives the `ConsoleMessage` object and resolves to truthy value when the waiting should resolve.
        timeout : Union[float, None]
            Maximum time to wait for in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The
            default value can be changed by using the `browser_context.set_default_timeout()`.

        Returns
        -------
        EventContextManager[ConsoleMessage]
        """

        return AsyncEventContextManager(
            self._impl_obj.expect_console_message(
                predicate=self._wrap_handler(predicate), timeout=timeout
            ).future
        )

    def expect_page(
        self,
        predicate: typing.Optional[typing.Callable[["Page"], bool]] = None,
        *,
        timeout: typing.Optional[float] = None,
    ) -> AsyncEventContextManager["Page"]:
        """BrowserContext.expect_page

        Performs action and waits for a new `Page` to be created in the context. If predicate is provided, it passes `Page`
        value into the `predicate` function and waits for `predicate(event)` to return a truthy value. Will throw an error
        if the context closes before new `Page` is created.

        Parameters
        ----------
        predicate : Union[Callable[[Page], bool], None]
            Receives the `Page` object and resolves to truthy value when the waiting should resolve.
        timeout : Union[float, None]
            Maximum time to wait for in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The
            default value can be changed by using the `browser_context.set_default_timeout()`.

        Returns
        -------
        EventContextManager[Page]
        """

        return AsyncEventContextManager(
            self._impl_obj.expect_page(
                predicate=self._wrap_handler(predicate), timeout=timeout
            ).future
        )

    async def new_cdp_session(
        self, page: typing.Union["Page", "Frame"]
    ) -> "CDPSession":
        """BrowserContext.new_cdp_session

        **NOTE** CDP sessions are only supported on Chromium-based browsers.

        Returns the newly created session.

        Parameters
        ----------
        page : Union[Frame, Page]
            Target to create new session for. For backwards-compatibility, this parameter is named `page`, but it can be a
            `Page` or `Frame` type.

        Returns
        -------
        CDPSession
        """

        return mapping.from_impl(await self._impl_obj.new_cdp_session(page=page))


mapping.register(BrowserContextImpl, BrowserContext)


class CDPSession(AsyncBase):

    async def send(
        self, method: str, params: typing.Optional[typing.Dict] = None
    ) -> typing.Dict:
        """CDPSession.send

        Parameters
        ----------
        method : str
            Protocol method name.
        params : Union[Dict, None]
            Optional method parameters.

        Returns
        -------
        Dict
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.send(method=method, params=mapping.to_impl(params))
        )

    async def detach(self) -> None:
        """CDPSession.detach

        Detaches the CDPSession from the target. Once detached, the CDPSession object won't emit any events and can't be
        used to send messages.
        """

        return mapping.from_maybe_impl(await self._impl_obj.detach())


mapping.register(CDPSessionImpl, CDPSession)


class Browser(AsyncContextManager):

    def on(
        self,
        event: Literal["disconnected"],
        f: typing.Callable[["Browser"], "typing.Union[typing.Awaitable[None], None]"],
    ) -> None:
        """
        Emitted when Browser gets disconnected from the browser application. This might happen because of one of the
        following:
        - Browser application is closed or crashed.
        - The `browser.close()` method was called."""
        return super().on(event=event, f=f)

    def once(
        self,
        event: Literal["disconnected"],
        f: typing.Callable[["Browser"], "typing.Union[typing.Awaitable[None], None]"],
    ) -> None:
        """
        Emitted when Browser gets disconnected from the browser application. This might happen because of one of the
        following:
        - Browser application is closed or crashed.
        - The `browser.close()` method was called."""
        return super().once(event=event, f=f)

    @property
    def contexts(self) -> typing.List["BrowserContext"]:
        """Browser.contexts

        Returns an array of all open browser contexts. In a newly created browser, this will return zero browser contexts.

        **Usage**

        ```py
        browser = await pw.webkit.launch()
        print(len(browser.contexts)) # prints `0`
        context = await browser.new_context()
        print(len(browser.contexts)) # prints `1`
        ```

        Returns
        -------
        List[BrowserContext]
        """
        return mapping.from_impl_list(self._impl_obj.contexts)

    @property
    def browser_type(self) -> "BrowserType":
        """Browser.browser_type

        Get the browser type (chromium, firefox or webkit) that the browser belongs to.

        Returns
        -------
        BrowserType
        """
        return mapping.from_impl(self._impl_obj.browser_type)

    @property
    def version(self) -> str:
        """Browser.version

        Returns the browser version.

        Returns
        -------
        str
        """
        return mapping.from_maybe_impl(self._impl_obj.version)

    def is_connected(self) -> bool:
        """Browser.is_connected

        Indicates that the browser is connected.

        Returns
        -------
        bool
        """

        return mapping.from_maybe_impl(self._impl_obj.is_connected())

    async def new_context(
        self,
        *,
        viewport: typing.Optional[ViewportSize] = None,
        screen: typing.Optional[ViewportSize] = None,
        no_viewport: typing.Optional[bool] = None,
        ignore_https_errors: typing.Optional[bool] = None,
        java_script_enabled: typing.Optional[bool] = None,
        bypass_csp: typing.Optional[bool] = None,
        user_agent: typing.Optional[str] = None,
        locale: typing.Optional[str] = None,
        timezone_id: typing.Optional[str] = None,
        geolocation: typing.Optional[Geolocation] = None,
        permissions: typing.Optional[typing.Sequence[str]] = None,
        extra_http_headers: typing.Optional[typing.Dict[str, str]] = None,
        offline: typing.Optional[bool] = None,
        http_credentials: typing.Optional[HttpCredentials] = None,
        device_scale_factor: typing.Optional[float] = None,
        is_mobile: typing.Optional[bool] = None,
        has_touch: typing.Optional[bool] = None,
        color_scheme: typing.Optional[
            Literal["dark", "light", "no-preference", "null"]
        ] = None,
        reduced_motion: typing.Optional[
            Literal["no-preference", "null", "reduce"]
        ] = None,
        forced_colors: typing.Optional[Literal["active", "none", "null"]] = None,
        contrast: typing.Optional[Literal["more", "no-preference", "null"]] = None,
        accept_downloads: typing.Optional[bool] = None,
        default_browser_type: typing.Optional[str] = None,
        proxy: typing.Optional[ProxySettings] = None,
        record_har_path: typing.Optional[typing.Union[pathlib.Path, str]] = None,
        record_har_omit_content: typing.Optional[bool] = None,
        record_video_dir: typing.Optional[typing.Union[pathlib.Path, str]] = None,
        record_video_size: typing.Optional[ViewportSize] = None,
        storage_state: typing.Optional[
            typing.Union[StorageState, str, pathlib.Path]
        ] = None,
        base_url: typing.Optional[str] = None,
        strict_selectors: typing.Optional[bool] = None,
        service_workers: typing.Optional[Literal["allow", "block"]] = None,
        record_har_url_filter: typing.Optional[
            typing.Union[typing.Pattern[str], str]
        ] = None,
        record_har_mode: typing.Optional[Literal["full", "minimal"]] = None,
        record_har_content: typing.Optional[Literal["attach", "embed", "omit"]] = None,
        client_certificates: typing.Optional[typing.List[ClientCertificate]] = None,
    ) -> "BrowserContext":
        """Browser.new_context

        Creates a new browser context. It won't share cookies/cache with other browser contexts.

        **NOTE** If directly using this method to create `BrowserContext`s, it is best practice to explicitly close the
        returned context via `browser_context.close()` when your code is done with the `BrowserContext`, and before
        calling `browser.close()`. This will ensure the `context` is closed gracefully and any artifacts—like HARs
        and videos—are fully flushed and saved.

        **Usage**

        ```py
        browser = await playwright.firefox.launch() # or \"chromium\" or \"webkit\".
        # create a new incognito browser context.
        context = await browser.new_context()
        # create a new page in a pristine context.
        page = await context.new_page()
        await page.goto(\"https://example.com\")

        # gracefully close up everything
        await context.close()
        await browser.close()
        ```

        Parameters
        ----------
        viewport : Union[{width: int, height: int}, None]
            Sets a consistent viewport for each page. Defaults to an 1280x720 viewport. `no_viewport` disables the fixed
            viewport. Learn more about [viewport emulation](../emulation.md#viewport).
        screen : Union[{width: int, height: int}, None]
            Emulates consistent window screen size available inside web page via `window.screen`. Is only used when the
            `viewport` is set.
        no_viewport : Union[bool, None]
            Does not enforce fixed viewport, allows resizing window in the headed mode.
        ignore_https_errors : Union[bool, None]
            Whether to ignore HTTPS errors when sending network requests. Defaults to `false`.
        java_script_enabled : Union[bool, None]
            Whether or not to enable JavaScript in the context. Defaults to `true`. Learn more about
            [disabling JavaScript](../emulation.md#javascript-enabled).
        bypass_csp : Union[bool, None]
            Toggles bypassing page's Content-Security-Policy. Defaults to `false`.
        user_agent : Union[str, None]
            Specific user agent to use in this context.
        locale : Union[str, None]
            Specify user locale, for example `en-GB`, `de-DE`, etc. Locale will affect `navigator.language` value,
            `Accept-Language` request header value as well as number and date formatting rules. Defaults to the system default
            locale. Learn more about emulation in our [emulation guide](../emulation.md#locale--timezone).
        timezone_id : Union[str, None]
            Changes the timezone of the context. See
            [ICU's metaZones.txt](https://cs.chromium.org/chromium/src/third_party/icu/source/data/misc/metaZones.txt?rcl=faee8bc70570192d82d2978a71e2a615788597d1)
            for a list of supported timezone IDs. Defaults to the system timezone.
        geolocation : Union[{latitude: float, longitude: float, accuracy: Union[float, None]}, None]
        permissions : Union[Sequence[str], None]
            A list of permissions to grant to all pages in this context. See `browser_context.grant_permissions()` for
            more details. Defaults to none.
        extra_http_headers : Union[Dict[str, str], None]
            An object containing additional HTTP headers to be sent with every request. Defaults to none.
        offline : Union[bool, None]
            Whether to emulate network being offline. Defaults to `false`. Learn more about
            [network emulation](../emulation.md#offline).
        http_credentials : Union[{username: str, password: str, origin: Union[str, None], send: Union["always", "unauthorized", None]}, None]
            Credentials for [HTTP authentication](https://developer.mozilla.org/en-US/docs/Web/HTTP/Authentication). If no
            origin is specified, the username and password are sent to any servers upon unauthorized responses.
        device_scale_factor : Union[float, None]
            Specify device scale factor (can be thought of as dpr). Defaults to `1`. Learn more about
            [emulating devices with device scale factor](../emulation.md#devices).
        is_mobile : Union[bool, None]
            Whether the `meta viewport` tag is taken into account and touch events are enabled. isMobile is a part of device,
            so you don't actually need to set it manually. Defaults to `false` and is not supported in Firefox. Learn more
            about [mobile emulation](../emulation.md#ismobile).
        has_touch : Union[bool, None]
            Specifies if viewport supports touch events. Defaults to false. Learn more about
            [mobile emulation](../emulation.md#devices).
        color_scheme : Union["dark", "light", "no-preference", "null", None]
            Emulates [prefers-colors-scheme](https://developer.mozilla.org/en-US/docs/Web/CSS/@media/prefers-color-scheme)
            media feature, supported values are `'light'` and `'dark'`. See `page.emulate_media()` for more details.
            Passing `'null'` resets emulation to system defaults. Defaults to `'light'`.
        reduced_motion : Union["no-preference", "null", "reduce", None]
            Emulates `'prefers-reduced-motion'` media feature, supported values are `'reduce'`, `'no-preference'`. See
            `page.emulate_media()` for more details. Passing `'null'` resets emulation to system defaults. Defaults to
            `'no-preference'`.
        forced_colors : Union["active", "none", "null", None]
            Emulates `'forced-colors'` media feature, supported values are `'active'`, `'none'`. See
            `page.emulate_media()` for more details. Passing `'null'` resets emulation to system defaults. Defaults to
            `'none'`.
        contrast : Union["more", "no-preference", "null", None]
            Emulates `'prefers-contrast'` media feature, supported values are `'no-preference'`, `'more'`. See
            `page.emulate_media()` for more details. Passing `'null'` resets emulation to system defaults. Defaults to
            `'no-preference'`.
        accept_downloads : Union[bool, None]
            Whether to automatically download all the attachments. Defaults to `true` where all the downloads are accepted.
        proxy : Union[{server: str, bypass: Union[str, None], username: Union[str, None], password: Union[str, None]}, None]
            Network proxy settings to use with this context. Defaults to none.
        record_har_path : Union[pathlib.Path, str, None]
            Enables [HAR](http://www.softwareishard.com/blog/har-12-spec) recording for all pages into the specified HAR file
            on the filesystem. If not specified, the HAR is not recorded. Make sure to call `browser_context.close()`
            for the HAR to be saved.
        record_har_omit_content : Union[bool, None]
            Optional setting to control whether to omit request content from the HAR. Defaults to `false`.
        record_video_dir : Union[pathlib.Path, str, None]
            Enables video recording for all pages into the specified directory. If not specified videos are not recorded. Make
            sure to call `browser_context.close()` for videos to be saved.
        record_video_size : Union[{width: int, height: int}, None]
            Dimensions of the recorded videos. If not specified the size will be equal to `viewport` scaled down to fit into
            800x800. If `viewport` is not configured explicitly the video size defaults to 800x450. Actual picture of each page
            will be scaled down if necessary to fit the specified size.
        storage_state : Union[pathlib.Path, str, {cookies: Sequence[{name: str, value: str, domain: str, path: str, expires: float, httpOnly: bool, secure: bool, sameSite: Union["Lax", "None", "Strict"]}], origins: Sequence[{origin: str, localStorage: Sequence[{name: str, value: str}]}]}, None]
            Learn more about [storage state and auth](../auth.md).

            Populates context with given storage state. This option can be used to initialize context with logged-in
            information obtained via `browser_context.storage_state()`.
        base_url : Union[str, None]
            When using `page.goto()`, `page.route()`, `page.wait_for_url()`,
            `page.expect_request()`, or `page.expect_response()` it takes the base URL in consideration by
            using the [`URL()`](https://developer.mozilla.org/en-US/docs/Web/API/URL/URL) constructor for building the
            corresponding URL. Unset by default. Examples:
            - baseURL: `http://localhost:3000` and navigating to `/bar.html` results in `http://localhost:3000/bar.html`
            - baseURL: `http://localhost:3000/foo/` and navigating to `./bar.html` results in
              `http://localhost:3000/foo/bar.html`
            - baseURL: `http://localhost:3000/foo` (without trailing slash) and navigating to `./bar.html` results in
              `http://localhost:3000/bar.html`
        strict_selectors : Union[bool, None]
            If set to true, enables strict selectors mode for this context. In the strict selectors mode all operations on
            selectors that imply single target DOM element will throw when more than one element matches the selector. This
            option does not affect any Locator APIs (Locators are always strict). Defaults to `false`. See `Locator` to learn
            more about the strict mode.
        service_workers : Union["allow", "block", None]
            Whether to allow sites to register Service workers. Defaults to `'allow'`.
            - `'allow'`: [Service Workers](https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API) can be
              registered.
            - `'block'`: Playwright will block all registration of Service Workers.
        record_har_url_filter : Union[Pattern[str], str, None]
        record_har_mode : Union["full", "minimal", None]
            When set to `minimal`, only record information necessary for routing from HAR. This omits sizes, timing, page,
            cookies, security and other types of HAR information that are not used when replaying from HAR. Defaults to `full`.
        record_har_content : Union["attach", "embed", "omit", None]
            Optional setting to control resource content management. If `omit` is specified, content is not persisted. If
            `attach` is specified, resources are persisted as separate files and all of these files are archived along with the
            HAR file. Defaults to `embed`, which stores content inline the HAR file as per HAR specification.
        client_certificates : Union[Sequence[{origin: str, certPath: Union[pathlib.Path, str, None], cert: Union[bytes, None], keyPath: Union[pathlib.Path, str, None], key: Union[bytes, None], pfxPath: Union[pathlib.Path, str, None], pfx: Union[bytes, None], passphrase: Union[str, None]}], None]
            TLS Client Authentication allows the server to request a client certificate and verify it.

            **Details**

            An array of client certificates to be used. Each certificate object must have either both `certPath` and `keyPath`,
            a single `pfxPath`, or their corresponding direct value equivalents (`cert` and `key`, or `pfx`). Optionally,
            `passphrase` property should be provided if the certificate is encrypted. The `origin` property should be provided
            with an exact match to the request origin that the certificate is valid for.

            Client certificate authentication is only active when at least one client certificate is provided. If you want to
            reject all client certificates sent by the server, you need to provide a client certificate with an `origin` that
            does not match any of the domains you plan to visit.

            **NOTE** When using WebKit on macOS, accessing `localhost` will not pick up client certificates. You can make it
            work by replacing `localhost` with `local.playwright`.


        Returns
        -------
        BrowserContext
        """

        return mapping.from_impl(
            await self._impl_obj.new_context(
                viewport=viewport,
                screen=screen,
                noViewport=no_viewport,
                ignoreHTTPSErrors=ignore_https_errors,
                javaScriptEnabled=java_script_enabled,
                bypassCSP=bypass_csp,
                userAgent=user_agent,
                locale=locale,
                timezoneId=timezone_id,
                geolocation=geolocation,
                permissions=mapping.to_impl(permissions),
                extraHTTPHeaders=mapping.to_impl(extra_http_headers),
                offline=offline,
                httpCredentials=http_credentials,
                deviceScaleFactor=device_scale_factor,
                isMobile=is_mobile,
                hasTouch=has_touch,
                colorScheme=color_scheme,
                reducedMotion=reduced_motion,
                forcedColors=forced_colors,
                contrast=contrast,
                acceptDownloads=accept_downloads,
                defaultBrowserType=default_browser_type,
                proxy=proxy,
                recordHarPath=record_har_path,
                recordHarOmitContent=record_har_omit_content,
                recordVideoDir=record_video_dir,
                recordVideoSize=record_video_size,
                storageState=storage_state,
                baseURL=base_url,
                strictSelectors=strict_selectors,
                serviceWorkers=service_workers,
                recordHarUrlFilter=record_har_url_filter,
                recordHarMode=record_har_mode,
                recordHarContent=record_har_content,
                clientCertificates=client_certificates,
            )
        )

    async def new_page(
        self,
        *,
        viewport: typing.Optional[ViewportSize] = None,
        screen: typing.Optional[ViewportSize] = None,
        no_viewport: typing.Optional[bool] = None,
        ignore_https_errors: typing.Optional[bool] = None,
        java_script_enabled: typing.Optional[bool] = None,
        bypass_csp: typing.Optional[bool] = None,
        user_agent: typing.Optional[str] = None,
        locale: typing.Optional[str] = None,
        timezone_id: typing.Optional[str] = None,
        geolocation: typing.Optional[Geolocation] = None,
        permissions: typing.Optional[typing.Sequence[str]] = None,
        extra_http_headers: typing.Optional[typing.Dict[str, str]] = None,
        offline: typing.Optional[bool] = None,
        http_credentials: typing.Optional[HttpCredentials] = None,
        device_scale_factor: typing.Optional[float] = None,
        is_mobile: typing.Optional[bool] = None,
        has_touch: typing.Optional[bool] = None,
        color_scheme: typing.Optional[
            Literal["dark", "light", "no-preference", "null"]
        ] = None,
        forced_colors: typing.Optional[Literal["active", "none", "null"]] = None,
        contrast: typing.Optional[Literal["more", "no-preference", "null"]] = None,
        reduced_motion: typing.Optional[
            Literal["no-preference", "null", "reduce"]
        ] = None,
        accept_downloads: typing.Optional[bool] = None,
        default_browser_type: typing.Optional[str] = None,
        proxy: typing.Optional[ProxySettings] = None,
        record_har_path: typing.Optional[typing.Union[pathlib.Path, str]] = None,
        record_har_omit_content: typing.Optional[bool] = None,
        record_video_dir: typing.Optional[typing.Union[pathlib.Path, str]] = None,
        record_video_size: typing.Optional[ViewportSize] = None,
        storage_state: typing.Optional[
            typing.Union[StorageState, str, pathlib.Path]
        ] = None,
        base_url: typing.Optional[str] = None,
        strict_selectors: typing.Optional[bool] = None,
        service_workers: typing.Optional[Literal["allow", "block"]] = None,
        record_har_url_filter: typing.Optional[
            typing.Union[typing.Pattern[str], str]
        ] = None,
        record_har_mode: typing.Optional[Literal["full", "minimal"]] = None,
        record_har_content: typing.Optional[Literal["attach", "embed", "omit"]] = None,
        client_certificates: typing.Optional[typing.List[ClientCertificate]] = None,
    ) -> "Page":
        """Browser.new_page

        Creates a new page in a new browser context. Closing this page will close the context as well.

        This is a convenience API that should only be used for the single-page scenarios and short snippets. Production
        code and testing frameworks should explicitly create `browser.new_context()` followed by the
        `browser_context.new_page()` to control their exact life times.

        Parameters
        ----------
        viewport : Union[{width: int, height: int}, None]
            Sets a consistent viewport for each page. Defaults to an 1280x720 viewport. `no_viewport` disables the fixed
            viewport. Learn more about [viewport emulation](../emulation.md#viewport).
        screen : Union[{width: int, height: int}, None]
            Emulates consistent window screen size available inside web page via `window.screen`. Is only used when the
            `viewport` is set.
        no_viewport : Union[bool, None]
            Does not enforce fixed viewport, allows resizing window in the headed mode.
        ignore_https_errors : Union[bool, None]
            Whether to ignore HTTPS errors when sending network requests. Defaults to `false`.
        java_script_enabled : Union[bool, None]
            Whether or not to enable JavaScript in the context. Defaults to `true`. Learn more about
            [disabling JavaScript](../emulation.md#javascript-enabled).
        bypass_csp : Union[bool, None]
            Toggles bypassing page's Content-Security-Policy. Defaults to `false`.
        user_agent : Union[str, None]
            Specific user agent to use in this context.
        locale : Union[str, None]
            Specify user locale, for example `en-GB`, `de-DE`, etc. Locale will affect `navigator.language` value,
            `Accept-Language` request header value as well as number and date formatting rules. Defaults to the system default
            locale. Learn more about emulation in our [emulation guide](../emulation.md#locale--timezone).
        timezone_id : Union[str, None]
            Changes the timezone of the context. See
            [ICU's metaZones.txt](https://cs.chromium.org/chromium/src/third_party/icu/source/data/misc/metaZones.txt?rcl=faee8bc70570192d82d2978a71e2a615788597d1)
            for a list of supported timezone IDs. Defaults to the system timezone.
        geolocation : Union[{latitude: float, longitude: float, accuracy: Union[float, None]}, None]
        permissions : Union[Sequence[str], None]
            A list of permissions to grant to all pages in this context. See `browser_context.grant_permissions()` for
            more details. Defaults to none.
        extra_http_headers : Union[Dict[str, str], None]
            An object containing additional HTTP headers to be sent with every request. Defaults to none.
        offline : Union[bool, None]
            Whether to emulate network being offline. Defaults to `false`. Learn more about
            [network emulation](../emulation.md#offline).
        http_credentials : Union[{username: str, password: str, origin: Union[str, None], send: Union["always", "unauthorized", None]}, None]
            Credentials for [HTTP authentication](https://developer.mozilla.org/en-US/docs/Web/HTTP/Authentication). If no
            origin is specified, the username and password are sent to any servers upon unauthorized responses.
        device_scale_factor : Union[float, None]
            Specify device scale factor (can be thought of as dpr). Defaults to `1`. Learn more about
            [emulating devices with device scale factor](../emulation.md#devices).
        is_mobile : Union[bool, None]
            Whether the `meta viewport` tag is taken into account and touch events are enabled. isMobile is a part of device,
            so you don't actually need to set it manually. Defaults to `false` and is not supported in Firefox. Learn more
            about [mobile emulation](../emulation.md#ismobile).
        has_touch : Union[bool, None]
            Specifies if viewport supports touch events. Defaults to false. Learn more about
            [mobile emulation](../emulation.md#devices).
        color_scheme : Union["dark", "light", "no-preference", "null", None]
            Emulates [prefers-colors-scheme](https://developer.mozilla.org/en-US/docs/Web/CSS/@media/prefers-color-scheme)
            media feature, supported values are `'light'` and `'dark'`. See `page.emulate_media()` for more details.
            Passing `'null'` resets emulation to system defaults. Defaults to `'light'`.
        forced_colors : Union["active", "none", "null", None]
            Emulates `'forced-colors'` media feature, supported values are `'active'`, `'none'`. See
            `page.emulate_media()` for more details. Passing `'null'` resets emulation to system defaults. Defaults to
            `'none'`.
        contrast : Union["more", "no-preference", "null", None]
            Emulates `'prefers-contrast'` media feature, supported values are `'no-preference'`, `'more'`. See
            `page.emulate_media()` for more details. Passing `'null'` resets emulation to system defaults. Defaults to
            `'no-preference'`.
        reduced_motion : Union["no-preference", "null", "reduce", None]
            Emulates `'prefers-reduced-motion'` media feature, supported values are `'reduce'`, `'no-preference'`. See
            `page.emulate_media()` for more details. Passing `'null'` resets emulation to system defaults. Defaults to
            `'no-preference'`.
        accept_downloads : Union[bool, None]
            Whether to automatically download all the attachments. Defaults to `true` where all the downloads are accepted.
        proxy : Union[{server: str, bypass: Union[str, None], username: Union[str, None], password: Union[str, None]}, None]
            Network proxy settings to use with this context. Defaults to none.
        record_har_path : Union[pathlib.Path, str, None]
            Enables [HAR](http://www.softwareishard.com/blog/har-12-spec) recording for all pages into the specified HAR file
            on the filesystem. If not specified, the HAR is not recorded. Make sure to call `browser_context.close()`
            for the HAR to be saved.
        record_har_omit_content : Union[bool, None]
            Optional setting to control whether to omit request content from the HAR. Defaults to `false`.
        record_video_dir : Union[pathlib.Path, str, None]
            Enables video recording for all pages into the specified directory. If not specified videos are not recorded. Make
            sure to call `browser_context.close()` for videos to be saved.
        record_video_size : Union[{width: int, height: int}, None]
            Dimensions of the recorded videos. If not specified the size will be equal to `viewport` scaled down to fit into
            800x800. If `viewport` is not configured explicitly the video size defaults to 800x450. Actual picture of each page
            will be scaled down if necessary to fit the specified size.
        storage_state : Union[pathlib.Path, str, {cookies: Sequence[{name: str, value: str, domain: str, path: str, expires: float, httpOnly: bool, secure: bool, sameSite: Union["Lax", "None", "Strict"]}], origins: Sequence[{origin: str, localStorage: Sequence[{name: str, value: str}]}]}, None]
            Learn more about [storage state and auth](../auth.md).

            Populates context with given storage state. This option can be used to initialize context with logged-in
            information obtained via `browser_context.storage_state()`.
        base_url : Union[str, None]
            When using `page.goto()`, `page.route()`, `page.wait_for_url()`,
            `page.expect_request()`, or `page.expect_response()` it takes the base URL in consideration by
            using the [`URL()`](https://developer.mozilla.org/en-US/docs/Web/API/URL/URL) constructor for building the
            corresponding URL. Unset by default. Examples:
            - baseURL: `http://localhost:3000` and navigating to `/bar.html` results in `http://localhost:3000/bar.html`
            - baseURL: `http://localhost:3000/foo/` and navigating to `./bar.html` results in
              `http://localhost:3000/foo/bar.html`
            - baseURL: `http://localhost:3000/foo` (without trailing slash) and navigating to `./bar.html` results in
              `http://localhost:3000/bar.html`
        strict_selectors : Union[bool, None]
            If set to true, enables strict selectors mode for this context. In the strict selectors mode all operations on
            selectors that imply single target DOM element will throw when more than one element matches the selector. This
            option does not affect any Locator APIs (Locators are always strict). Defaults to `false`. See `Locator` to learn
            more about the strict mode.
        service_workers : Union["allow", "block", None]
            Whether to allow sites to register Service workers. Defaults to `'allow'`.
            - `'allow'`: [Service Workers](https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API) can be
              registered.
            - `'block'`: Playwright will block all registration of Service Workers.
        record_har_url_filter : Union[Pattern[str], str, None]
        record_har_mode : Union["full", "minimal", None]
            When set to `minimal`, only record information necessary for routing from HAR. This omits sizes, timing, page,
            cookies, security and other types of HAR information that are not used when replaying from HAR. Defaults to `full`.
        record_har_content : Union["attach", "embed", "omit", None]
            Optional setting to control resource content management. If `omit` is specified, content is not persisted. If
            `attach` is specified, resources are persisted as separate files and all of these files are archived along with the
            HAR file. Defaults to `embed`, which stores content inline the HAR file as per HAR specification.
        client_certificates : Union[Sequence[{origin: str, certPath: Union[pathlib.Path, str, None], cert: Union[bytes, None], keyPath: Union[pathlib.Path, str, None], key: Union[bytes, None], pfxPath: Union[pathlib.Path, str, None], pfx: Union[bytes, None], passphrase: Union[str, None]}], None]
            TLS Client Authentication allows the server to request a client certificate and verify it.

            **Details**

            An array of client certificates to be used. Each certificate object must have either both `certPath` and `keyPath`,
            a single `pfxPath`, or their corresponding direct value equivalents (`cert` and `key`, or `pfx`). Optionally,
            `passphrase` property should be provided if the certificate is encrypted. The `origin` property should be provided
            with an exact match to the request origin that the certificate is valid for.

            Client certificate authentication is only active when at least one client certificate is provided. If you want to
            reject all client certificates sent by the server, you need to provide a client certificate with an `origin` that
            does not match any of the domains you plan to visit.

            **NOTE** When using WebKit on macOS, accessing `localhost` will not pick up client certificates. You can make it
            work by replacing `localhost` with `local.playwright`.


        Returns
        -------
        Page
        """

        return mapping.from_impl(
            await self._impl_obj.new_page(
                viewport=viewport,
                screen=screen,
                noViewport=no_viewport,
                ignoreHTTPSErrors=ignore_https_errors,
                javaScriptEnabled=java_script_enabled,
                bypassCSP=bypass_csp,
                userAgent=user_agent,
                locale=locale,
                timezoneId=timezone_id,
                geolocation=geolocation,
                permissions=mapping.to_impl(permissions),
                extraHTTPHeaders=mapping.to_impl(extra_http_headers),
                offline=offline,
                httpCredentials=http_credentials,
                deviceScaleFactor=device_scale_factor,
                isMobile=is_mobile,
                hasTouch=has_touch,
                colorScheme=color_scheme,
                forcedColors=forced_colors,
                contrast=contrast,
                reducedMotion=reduced_motion,
                acceptDownloads=accept_downloads,
                defaultBrowserType=default_browser_type,
                proxy=proxy,
                recordHarPath=record_har_path,
                recordHarOmitContent=record_har_omit_content,
                recordVideoDir=record_video_dir,
                recordVideoSize=record_video_size,
                storageState=storage_state,
                baseURL=base_url,
                strictSelectors=strict_selectors,
                serviceWorkers=service_workers,
                recordHarUrlFilter=record_har_url_filter,
                recordHarMode=record_har_mode,
                recordHarContent=record_har_content,
                clientCertificates=client_certificates,
            )
        )

    async def close(self, *, reason: typing.Optional[str] = None) -> None:
        """Browser.close

        In case this browser is obtained using `browser_type.launch()`, closes the browser and all of its pages (if
        any were opened).

        In case this browser is connected to, clears all created contexts belonging to this browser and disconnects from
        the browser server.

        **NOTE** This is similar to force-quitting the browser. To close pages gracefully and ensure you receive page close
        events, call `browser_context.close()` on any `BrowserContext` instances you explicitly created earlier
        using `browser.new_context()` **before** calling `browser.close()`.

        The `Browser` object itself is considered to be disposed and cannot be used anymore.

        Parameters
        ----------
        reason : Union[str, None]
            The reason to be reported to the operations interrupted by the browser closure.
        """

        return mapping.from_maybe_impl(await self._impl_obj.close(reason=reason))

    async def new_browser_cdp_session(self) -> "CDPSession":
        """Browser.new_browser_cdp_session

        **NOTE** CDP Sessions are only supported on Chromium-based browsers.

        Returns the newly created browser session.

        Returns
        -------
        CDPSession
        """

        return mapping.from_impl(await self._impl_obj.new_browser_cdp_session())

    async def start_tracing(
        self,
        *,
        page: typing.Optional["Page"] = None,
        path: typing.Optional[typing.Union[pathlib.Path, str]] = None,
        screenshots: typing.Optional[bool] = None,
        categories: typing.Optional[typing.Sequence[str]] = None,
    ) -> None:
        """Browser.start_tracing

        **NOTE** This API controls
        [Chromium Tracing](https://www.chromium.org/developers/how-tos/trace-event-profiling-tool) which is a low-level
        chromium-specific debugging tool. API to control [Playwright Tracing](https://playwright.dev/python/docs/trace-viewer) could be found
        [here](https://playwright.dev/python/docs/api/class-tracing).

        You can use `browser.start_tracing()` and `browser.stop_tracing()` to create a trace file that can be
        opened in Chrome DevTools performance panel.

        **Usage**

        ```py
        await browser.start_tracing(page, path=\"trace.json\")
        await page.goto(\"https://www.google.com\")
        await browser.stop_tracing()
        ```

        Parameters
        ----------
        page : Union[Page, None]
            Optional, if specified, tracing includes screenshots of the given page.
        path : Union[pathlib.Path, str, None]
            A path to write the trace file to.
        screenshots : Union[bool, None]
            captures screenshots in the trace.
        categories : Union[Sequence[str], None]
            specify custom categories to use instead of default.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.start_tracing(
                page=page._impl_obj if page else None,
                path=path,
                screenshots=screenshots,
                categories=mapping.to_impl(categories),
            )
        )

    async def stop_tracing(self) -> bytes:
        """Browser.stop_tracing

        **NOTE** This API controls
        [Chromium Tracing](https://www.chromium.org/developers/how-tos/trace-event-profiling-tool) which is a low-level
        chromium-specific debugging tool. API to control [Playwright Tracing](https://playwright.dev/python/docs/trace-viewer) could be found
        [here](https://playwright.dev/python/docs/api/class-tracing).

        Returns the buffer with trace data.

        Returns
        -------
        bytes
        """

        return mapping.from_maybe_impl(await self._impl_obj.stop_tracing())


mapping.register(BrowserImpl, Browser)


class BrowserType(AsyncBase):

    @property
    def name(self) -> str:
        """BrowserType.name

        Returns browser name. For example: `'chromium'`, `'webkit'` or `'firefox'`.

        Returns
        -------
        str
        """
        return mapping.from_maybe_impl(self._impl_obj.name)

    @property
    def executable_path(self) -> str:
        """BrowserType.executable_path

        A path where Playwright expects to find a bundled browser executable.

        Returns
        -------
        str
        """
        return mapping.from_maybe_impl(self._impl_obj.executable_path)

    async def launch(
        self,
        *,
        executable_path: typing.Optional[typing.Union[pathlib.Path, str]] = None,
        channel: typing.Optional[str] = None,
        args: typing.Optional[typing.Sequence[str]] = None,
        ignore_default_args: typing.Optional[
            typing.Union[bool, typing.Sequence[str]]
        ] = None,
        handle_sigint: typing.Optional[bool] = None,
        handle_sigterm: typing.Optional[bool] = None,
        handle_sighup: typing.Optional[bool] = None,
        timeout: typing.Optional[float] = None,
        env: typing.Optional[typing.Dict[str, typing.Union[str, float, bool]]] = None,
        headless: typing.Optional[bool] = None,
        proxy: typing.Optional[ProxySettings] = None,
        downloads_path: typing.Optional[typing.Union[pathlib.Path, str]] = None,
        slow_mo: typing.Optional[float] = None,
        traces_dir: typing.Optional[typing.Union[pathlib.Path, str]] = None,
        chromium_sandbox: typing.Optional[bool] = None,
        firefox_user_prefs: typing.Optional[
            typing.Dict[str, typing.Union[str, float, bool]]
        ] = None,
    ) -> "Browser":
        """BrowserType.launch

        Returns the browser instance.

        **Usage**

        You can use `ignoreDefaultArgs` to filter out `--mute-audio` from default arguments:

        ```py
        browser = await playwright.chromium.launch( # or \"firefox\" or \"webkit\".
            ignore_default_args=[\"--mute-audio\"]
        )
        ```

        > **Chromium-only** Playwright can also be used to control the Google Chrome or Microsoft Edge browsers, but it
        works best with the version of Chromium it is bundled with. There is no guarantee it will work with any other
        version. Use `executablePath` option with extreme caution.
        >
        > If Google Chrome (rather than Chromium) is preferred, a
        [Chrome Canary](https://www.google.com/chrome/browser/canary.html) or
        [Dev Channel](https://www.chromium.org/getting-involved/dev-channel) build is suggested.
        >
        > Stock browsers like Google Chrome and Microsoft Edge are suitable for tests that require proprietary media codecs
        for video playback. See
        [this article](https://www.howtogeek.com/202825/what%E2%80%99s-the-difference-between-chromium-and-chrome/) for
        other differences between Chromium and Chrome.
        [This article](https://chromium.googlesource.com/chromium/src/+/lkgr/docs/chromium_browser_vs_google_chrome.md)
        describes some differences for Linux users.

        Parameters
        ----------
        executable_path : Union[pathlib.Path, str, None]
            Path to a browser executable to run instead of the bundled one. If `executablePath` is a relative path, then it is
            resolved relative to the current working directory. Note that Playwright only works with the bundled Chromium,
            Firefox or WebKit, use at your own risk.
        channel : Union[str, None]
            Browser distribution channel.

            Use "chromium" to [opt in to new headless mode](../browsers.md#chromium-new-headless-mode).

            Use "chrome", "chrome-beta", "chrome-dev", "chrome-canary", "msedge", "msedge-beta", "msedge-dev", or
            "msedge-canary" to use branded [Google Chrome and Microsoft Edge](../browsers.md#google-chrome--microsoft-edge).
        args : Union[Sequence[str], None]
            **NOTE** Use custom browser args at your own risk, as some of them may break Playwright functionality.

            Additional arguments to pass to the browser instance. The list of Chromium flags can be found
            [here](https://peter.sh/experiments/chromium-command-line-switches/).
        ignore_default_args : Union[Sequence[str], bool, None]
            If `true`, Playwright does not pass its own configurations args and only uses the ones from `args`. If an array is
            given, then filters out the given default arguments. Dangerous option; use with care. Defaults to `false`.
        handle_sigint : Union[bool, None]
            Close the browser process on Ctrl-C. Defaults to `true`.
        handle_sigterm : Union[bool, None]
            Close the browser process on SIGTERM. Defaults to `true`.
        handle_sighup : Union[bool, None]
            Close the browser process on SIGHUP. Defaults to `true`.
        timeout : Union[float, None]
            Maximum time in milliseconds to wait for the browser instance to start. Defaults to `30000` (30 seconds). Pass `0`
            to disable timeout.
        env : Union[Dict[str, Union[bool, float, str]], None]
            Specify environment variables that will be visible to the browser. Defaults to `process.env`.
        headless : Union[bool, None]
            Whether to run browser in headless mode. More details for
            [Chromium](https://developers.google.com/web/updates/2017/04/headless-chrome) and
            [Firefox](https://hacks.mozilla.org/2017/12/using-headless-mode-in-firefox/). Defaults to `true`.
        proxy : Union[{server: str, bypass: Union[str, None], username: Union[str, None], password: Union[str, None]}, None]
            Network proxy settings.
        downloads_path : Union[pathlib.Path, str, None]
            If specified, accepted downloads are downloaded into this directory. Otherwise, temporary directory is created and
            is deleted when browser is closed. In either case, the downloads are deleted when the browser context they were
            created in is closed.
        slow_mo : Union[float, None]
            Slows down Playwright operations by the specified amount of milliseconds. Useful so that you can see what is going
            on.
        traces_dir : Union[pathlib.Path, str, None]
            If specified, traces are saved into this directory.
        chromium_sandbox : Union[bool, None]
            Enable Chromium sandboxing. Defaults to `false`.
        firefox_user_prefs : Union[Dict[str, Union[bool, float, str]], None]
            Firefox user preferences. Learn more about the Firefox user preferences at
            [`about:config`](https://support.mozilla.org/en-US/kb/about-config-editor-firefox).

            You can also provide a path to a custom [`policies.json` file](https://mozilla.github.io/policy-templates/) via
            `PLAYWRIGHT_FIREFOX_POLICIES_JSON` environment variable.

        Returns
        -------
        Browser
        """

        return mapping.from_impl(
            await self._impl_obj.launch(
                executablePath=executable_path,
                channel=channel,
                args=mapping.to_impl(args),
                ignoreDefaultArgs=mapping.to_impl(ignore_default_args),
                handleSIGINT=handle_sigint,
                handleSIGTERM=handle_sigterm,
                handleSIGHUP=handle_sighup,
                timeout=timeout,
                env=mapping.to_impl(env),
                headless=headless,
                proxy=proxy,
                downloadsPath=downloads_path,
                slowMo=slow_mo,
                tracesDir=traces_dir,
                chromiumSandbox=chromium_sandbox,
                firefoxUserPrefs=mapping.to_impl(firefox_user_prefs),
            )
        )

    async def launch_persistent_context(
        self,
        user_data_dir: typing.Union[str, pathlib.Path],
        *,
        channel: typing.Optional[str] = None,
        executable_path: typing.Optional[typing.Union[pathlib.Path, str]] = None,
        args: typing.Optional[typing.Sequence[str]] = None,
        ignore_default_args: typing.Optional[
            typing.Union[bool, typing.Sequence[str]]
        ] = None,
        handle_sigint: typing.Optional[bool] = None,
        handle_sigterm: typing.Optional[bool] = None,
        handle_sighup: typing.Optional[bool] = None,
        timeout: typing.Optional[float] = None,
        env: typing.Optional[typing.Dict[str, typing.Union[str, float, bool]]] = None,
        headless: typing.Optional[bool] = None,
        proxy: typing.Optional[ProxySettings] = None,
        downloads_path: typing.Optional[typing.Union[pathlib.Path, str]] = None,
        slow_mo: typing.Optional[float] = None,
        viewport: typing.Optional[ViewportSize] = None,
        screen: typing.Optional[ViewportSize] = None,
        no_viewport: typing.Optional[bool] = None,
        ignore_https_errors: typing.Optional[bool] = None,
        java_script_enabled: typing.Optional[bool] = None,
        bypass_csp: typing.Optional[bool] = None,
        user_agent: typing.Optional[str] = None,
        locale: typing.Optional[str] = None,
        timezone_id: typing.Optional[str] = None,
        geolocation: typing.Optional[Geolocation] = None,
        permissions: typing.Optional[typing.Sequence[str]] = None,
        extra_http_headers: typing.Optional[typing.Dict[str, str]] = None,
        offline: typing.Optional[bool] = None,
        http_credentials: typing.Optional[HttpCredentials] = None,
        device_scale_factor: typing.Optional[float] = None,
        is_mobile: typing.Optional[bool] = None,
        has_touch: typing.Optional[bool] = None,
        color_scheme: typing.Optional[
            Literal["dark", "light", "no-preference", "null"]
        ] = None,
        reduced_motion: typing.Optional[
            Literal["no-preference", "null", "reduce"]
        ] = None,
        forced_colors: typing.Optional[Literal["active", "none", "null"]] = None,
        contrast: typing.Optional[Literal["more", "no-preference", "null"]] = None,
        accept_downloads: typing.Optional[bool] = None,
        traces_dir: typing.Optional[typing.Union[pathlib.Path, str]] = None,
        chromium_sandbox: typing.Optional[bool] = None,
        firefox_user_prefs: typing.Optional[
            typing.Dict[str, typing.Union[str, float, bool]]
        ] = None,
        record_har_path: typing.Optional[typing.Union[pathlib.Path, str]] = None,
        record_har_omit_content: typing.Optional[bool] = None,
        record_video_dir: typing.Optional[typing.Union[pathlib.Path, str]] = None,
        record_video_size: typing.Optional[ViewportSize] = None,
        base_url: typing.Optional[str] = None,
        strict_selectors: typing.Optional[bool] = None,
        service_workers: typing.Optional[Literal["allow", "block"]] = None,
        record_har_url_filter: typing.Optional[
            typing.Union[typing.Pattern[str], str]
        ] = None,
        record_har_mode: typing.Optional[Literal["full", "minimal"]] = None,
        record_har_content: typing.Optional[Literal["attach", "embed", "omit"]] = None,
        client_certificates: typing.Optional[typing.List[ClientCertificate]] = None,
    ) -> "BrowserContext":
        """BrowserType.launch_persistent_context

        Returns the persistent browser context instance.

        Launches browser that uses persistent storage located at `userDataDir` and returns the only context. Closing this
        context will automatically close the browser.

        Parameters
        ----------
        user_data_dir : Union[pathlib.Path, str]
            Path to a User Data Directory, which stores browser session data like cookies and local storage. Pass an empty
            string to create a temporary directory.

            More details for
            [Chromium](https://chromium.googlesource.com/chromium/src/+/master/docs/user_data_dir.md#introduction) and
            [Firefox](https://wiki.mozilla.org/Firefox/CommandLineOptions#User_profile). Chromium's user data directory is the
            **parent** directory of the "Profile Path" seen at `chrome://version`.

            Note that browsers do not allow launching multiple instances with the same User Data Directory.

            **NOTE** Chromium/Chrome: Due to recent Chrome policy changes, automating the default Chrome user profile is not
            supported. Pointing `userDataDir` to Chrome's main "User Data" directory (the profile used for your regular
            browsing) may result in pages not loading or the browser exiting. Create and use a separate directory (for example,
            an empty folder) as your automation profile instead. See https://developer.chrome.com/blog/remote-debugging-port
            for details.

        channel : Union[str, None]
            Browser distribution channel.

            Use "chromium" to [opt in to new headless mode](../browsers.md#chromium-new-headless-mode).

            Use "chrome", "chrome-beta", "chrome-dev", "chrome-canary", "msedge", "msedge-beta", "msedge-dev", or
            "msedge-canary" to use branded [Google Chrome and Microsoft Edge](../browsers.md#google-chrome--microsoft-edge).
        executable_path : Union[pathlib.Path, str, None]
            Path to a browser executable to run instead of the bundled one. If `executablePath` is a relative path, then it is
            resolved relative to the current working directory. Note that Playwright only works with the bundled Chromium,
            Firefox or WebKit, use at your own risk.
        args : Union[Sequence[str], None]
            **NOTE** Use custom browser args at your own risk, as some of them may break Playwright functionality.

            Additional arguments to pass to the browser instance. The list of Chromium flags can be found
            [here](https://peter.sh/experiments/chromium-command-line-switches/).
        ignore_default_args : Union[Sequence[str], bool, None]
            If `true`, Playwright does not pass its own configurations args and only uses the ones from `args`. If an array is
            given, then filters out the given default arguments. Dangerous option; use with care. Defaults to `false`.
        handle_sigint : Union[bool, None]
            Close the browser process on Ctrl-C. Defaults to `true`.
        handle_sigterm : Union[bool, None]
            Close the browser process on SIGTERM. Defaults to `true`.
        handle_sighup : Union[bool, None]
            Close the browser process on SIGHUP. Defaults to `true`.
        timeout : Union[float, None]
            Maximum time in milliseconds to wait for the browser instance to start. Defaults to `30000` (30 seconds). Pass `0`
            to disable timeout.
        env : Union[Dict[str, Union[bool, float, str]], None]
            Specify environment variables that will be visible to the browser. Defaults to `process.env`.
        headless : Union[bool, None]
            Whether to run browser in headless mode. More details for
            [Chromium](https://developers.google.com/web/updates/2017/04/headless-chrome) and
            [Firefox](https://hacks.mozilla.org/2017/12/using-headless-mode-in-firefox/). Defaults to `true`.
        proxy : Union[{server: str, bypass: Union[str, None], username: Union[str, None], password: Union[str, None]}, None]
            Network proxy settings.
        downloads_path : Union[pathlib.Path, str, None]
            If specified, accepted downloads are downloaded into this directory. Otherwise, temporary directory is created and
            is deleted when browser is closed. In either case, the downloads are deleted when the browser context they were
            created in is closed.
        slow_mo : Union[float, None]
            Slows down Playwright operations by the specified amount of milliseconds. Useful so that you can see what is going
            on.
        viewport : Union[{width: int, height: int}, None]
            Sets a consistent viewport for each page. Defaults to an 1280x720 viewport. `no_viewport` disables the fixed
            viewport. Learn more about [viewport emulation](../emulation.md#viewport).
        screen : Union[{width: int, height: int}, None]
            Emulates consistent window screen size available inside web page via `window.screen`. Is only used when the
            `viewport` is set.
        no_viewport : Union[bool, None]
            Does not enforce fixed viewport, allows resizing window in the headed mode.
        ignore_https_errors : Union[bool, None]
            Whether to ignore HTTPS errors when sending network requests. Defaults to `false`.
        java_script_enabled : Union[bool, None]
            Whether or not to enable JavaScript in the context. Defaults to `true`. Learn more about
            [disabling JavaScript](../emulation.md#javascript-enabled).
        bypass_csp : Union[bool, None]
            Toggles bypassing page's Content-Security-Policy. Defaults to `false`.
        user_agent : Union[str, None]
            Specific user agent to use in this context.
        locale : Union[str, None]
            Specify user locale, for example `en-GB`, `de-DE`, etc. Locale will affect `navigator.language` value,
            `Accept-Language` request header value as well as number and date formatting rules. Defaults to the system default
            locale. Learn more about emulation in our [emulation guide](../emulation.md#locale--timezone).
        timezone_id : Union[str, None]
            Changes the timezone of the context. See
            [ICU's metaZones.txt](https://cs.chromium.org/chromium/src/third_party/icu/source/data/misc/metaZones.txt?rcl=faee8bc70570192d82d2978a71e2a615788597d1)
            for a list of supported timezone IDs. Defaults to the system timezone.
        geolocation : Union[{latitude: float, longitude: float, accuracy: Union[float, None]}, None]
        permissions : Union[Sequence[str], None]
            A list of permissions to grant to all pages in this context. See `browser_context.grant_permissions()` for
            more details. Defaults to none.
        extra_http_headers : Union[Dict[str, str], None]
            An object containing additional HTTP headers to be sent with every request. Defaults to none.
        offline : Union[bool, None]
            Whether to emulate network being offline. Defaults to `false`. Learn more about
            [network emulation](../emulation.md#offline).
        http_credentials : Union[{username: str, password: str, origin: Union[str, None], send: Union["always", "unauthorized", None]}, None]
            Credentials for [HTTP authentication](https://developer.mozilla.org/en-US/docs/Web/HTTP/Authentication). If no
            origin is specified, the username and password are sent to any servers upon unauthorized responses.
        device_scale_factor : Union[float, None]
            Specify device scale factor (can be thought of as dpr). Defaults to `1`. Learn more about
            [emulating devices with device scale factor](../emulation.md#devices).
        is_mobile : Union[bool, None]
            Whether the `meta viewport` tag is taken into account and touch events are enabled. isMobile is a part of device,
            so you don't actually need to set it manually. Defaults to `false` and is not supported in Firefox. Learn more
            about [mobile emulation](../emulation.md#ismobile).
        has_touch : Union[bool, None]
            Specifies if viewport supports touch events. Defaults to false. Learn more about
            [mobile emulation](../emulation.md#devices).
        color_scheme : Union["dark", "light", "no-preference", "null", None]
            Emulates [prefers-colors-scheme](https://developer.mozilla.org/en-US/docs/Web/CSS/@media/prefers-color-scheme)
            media feature, supported values are `'light'` and `'dark'`. See `page.emulate_media()` for more details.
            Passing `'null'` resets emulation to system defaults. Defaults to `'light'`.
        reduced_motion : Union["no-preference", "null", "reduce", None]
            Emulates `'prefers-reduced-motion'` media feature, supported values are `'reduce'`, `'no-preference'`. See
            `page.emulate_media()` for more details. Passing `'null'` resets emulation to system defaults. Defaults to
            `'no-preference'`.
        forced_colors : Union["active", "none", "null", None]
            Emulates `'forced-colors'` media feature, supported values are `'active'`, `'none'`. See
            `page.emulate_media()` for more details. Passing `'null'` resets emulation to system defaults. Defaults to
            `'none'`.
        contrast : Union["more", "no-preference", "null", None]
            Emulates `'prefers-contrast'` media feature, supported values are `'no-preference'`, `'more'`. See
            `page.emulate_media()` for more details. Passing `'null'` resets emulation to system defaults. Defaults to
            `'no-preference'`.
        accept_downloads : Union[bool, None]
            Whether to automatically download all the attachments. Defaults to `true` where all the downloads are accepted.
        traces_dir : Union[pathlib.Path, str, None]
            If specified, traces are saved into this directory.
        chromium_sandbox : Union[bool, None]
            Enable Chromium sandboxing. Defaults to `false`.
        firefox_user_prefs : Union[Dict[str, Union[bool, float, str]], None]
            Firefox user preferences. Learn more about the Firefox user preferences at
            [`about:config`](https://support.mozilla.org/en-US/kb/about-config-editor-firefox).

            You can also provide a path to a custom [`policies.json` file](https://mozilla.github.io/policy-templates/) via
            `PLAYWRIGHT_FIREFOX_POLICIES_JSON` environment variable.
        record_har_path : Union[pathlib.Path, str, None]
            Enables [HAR](http://www.softwareishard.com/blog/har-12-spec) recording for all pages into the specified HAR file
            on the filesystem. If not specified, the HAR is not recorded. Make sure to call `browser_context.close()`
            for the HAR to be saved.
        record_har_omit_content : Union[bool, None]
            Optional setting to control whether to omit request content from the HAR. Defaults to `false`.
        record_video_dir : Union[pathlib.Path, str, None]
            Enables video recording for all pages into the specified directory. If not specified videos are not recorded. Make
            sure to call `browser_context.close()` for videos to be saved.
        record_video_size : Union[{width: int, height: int}, None]
            Dimensions of the recorded videos. If not specified the size will be equal to `viewport` scaled down to fit into
            800x800. If `viewport` is not configured explicitly the video size defaults to 800x450. Actual picture of each page
            will be scaled down if necessary to fit the specified size.
        base_url : Union[str, None]
            When using `page.goto()`, `page.route()`, `page.wait_for_url()`,
            `page.expect_request()`, or `page.expect_response()` it takes the base URL in consideration by
            using the [`URL()`](https://developer.mozilla.org/en-US/docs/Web/API/URL/URL) constructor for building the
            corresponding URL. Unset by default. Examples:
            - baseURL: `http://localhost:3000` and navigating to `/bar.html` results in `http://localhost:3000/bar.html`
            - baseURL: `http://localhost:3000/foo/` and navigating to `./bar.html` results in
              `http://localhost:3000/foo/bar.html`
            - baseURL: `http://localhost:3000/foo` (without trailing slash) and navigating to `./bar.html` results in
              `http://localhost:3000/bar.html`
        strict_selectors : Union[bool, None]
            If set to true, enables strict selectors mode for this context. In the strict selectors mode all operations on
            selectors that imply single target DOM element will throw when more than one element matches the selector. This
            option does not affect any Locator APIs (Locators are always strict). Defaults to `false`. See `Locator` to learn
            more about the strict mode.
        service_workers : Union["allow", "block", None]
            Whether to allow sites to register Service workers. Defaults to `'allow'`.
            - `'allow'`: [Service Workers](https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API) can be
              registered.
            - `'block'`: Playwright will block all registration of Service Workers.
        record_har_url_filter : Union[Pattern[str], str, None]
        record_har_mode : Union["full", "minimal", None]
            When set to `minimal`, only record information necessary for routing from HAR. This omits sizes, timing, page,
            cookies, security and other types of HAR information that are not used when replaying from HAR. Defaults to `full`.
        record_har_content : Union["attach", "embed", "omit", None]
            Optional setting to control resource content management. If `omit` is specified, content is not persisted. If
            `attach` is specified, resources are persisted as separate files and all of these files are archived along with the
            HAR file. Defaults to `embed`, which stores content inline the HAR file as per HAR specification.
        client_certificates : Union[Sequence[{origin: str, certPath: Union[pathlib.Path, str, None], cert: Union[bytes, None], keyPath: Union[pathlib.Path, str, None], key: Union[bytes, None], pfxPath: Union[pathlib.Path, str, None], pfx: Union[bytes, None], passphrase: Union[str, None]}], None]
            TLS Client Authentication allows the server to request a client certificate and verify it.

            **Details**

            An array of client certificates to be used. Each certificate object must have either both `certPath` and `keyPath`,
            a single `pfxPath`, or their corresponding direct value equivalents (`cert` and `key`, or `pfx`). Optionally,
            `passphrase` property should be provided if the certificate is encrypted. The `origin` property should be provided
            with an exact match to the request origin that the certificate is valid for.

            Client certificate authentication is only active when at least one client certificate is provided. If you want to
            reject all client certificates sent by the server, you need to provide a client certificate with an `origin` that
            does not match any of the domains you plan to visit.

            **NOTE** When using WebKit on macOS, accessing `localhost` will not pick up client certificates. You can make it
            work by replacing `localhost` with `local.playwright`.


        Returns
        -------
        BrowserContext
        """

        return mapping.from_impl(
            await self._impl_obj.launch_persistent_context(
                userDataDir=user_data_dir,
                channel=channel,
                executablePath=executable_path,
                args=mapping.to_impl(args),
                ignoreDefaultArgs=mapping.to_impl(ignore_default_args),
                handleSIGINT=handle_sigint,
                handleSIGTERM=handle_sigterm,
                handleSIGHUP=handle_sighup,
                timeout=timeout,
                env=mapping.to_impl(env),
                headless=headless,
                proxy=proxy,
                downloadsPath=downloads_path,
                slowMo=slow_mo,
                viewport=viewport,
                screen=screen,
                noViewport=no_viewport,
                ignoreHTTPSErrors=ignore_https_errors,
                javaScriptEnabled=java_script_enabled,
                bypassCSP=bypass_csp,
                userAgent=user_agent,
                locale=locale,
                timezoneId=timezone_id,
                geolocation=geolocation,
                permissions=mapping.to_impl(permissions),
                extraHTTPHeaders=mapping.to_impl(extra_http_headers),
                offline=offline,
                httpCredentials=http_credentials,
                deviceScaleFactor=device_scale_factor,
                isMobile=is_mobile,
                hasTouch=has_touch,
                colorScheme=color_scheme,
                reducedMotion=reduced_motion,
                forcedColors=forced_colors,
                contrast=contrast,
                acceptDownloads=accept_downloads,
                tracesDir=traces_dir,
                chromiumSandbox=chromium_sandbox,
                firefoxUserPrefs=mapping.to_impl(firefox_user_prefs),
                recordHarPath=record_har_path,
                recordHarOmitContent=record_har_omit_content,
                recordVideoDir=record_video_dir,
                recordVideoSize=record_video_size,
                baseURL=base_url,
                strictSelectors=strict_selectors,
                serviceWorkers=service_workers,
                recordHarUrlFilter=record_har_url_filter,
                recordHarMode=record_har_mode,
                recordHarContent=record_har_content,
                clientCertificates=client_certificates,
            )
        )

    async def connect_over_cdp(
        self,
        endpoint_url: str,
        *,
        timeout: typing.Optional[float] = None,
        slow_mo: typing.Optional[float] = None,
        headers: typing.Optional[typing.Dict[str, str]] = None,
        is_local: typing.Optional[bool] = None,
    ) -> "Browser":
        """BrowserType.connect_over_cdp

        This method attaches Playwright to an existing browser instance using the Chrome DevTools Protocol.

        The default browser context is accessible via `browser.contexts()`.

        **NOTE** Connecting over the Chrome DevTools Protocol is only supported for Chromium-based browsers.

        **NOTE** This connection is significantly lower fidelity than the Playwright protocol connection via
        `browser_type.connect()`. If you are experiencing issues or attempting to use advanced functionality, you
        probably want to use `browser_type.connect()`.

        **Usage**

        ```py
        browser = await playwright.chromium.connect_over_cdp(\"http://localhost:9222\")
        default_context = browser.contexts[0]
        page = default_context.pages[0]
        ```

        Parameters
        ----------
        endpoint_url : str
            A CDP websocket endpoint or http url to connect to. For example `http://localhost:9222/` or
            `ws://127.0.0.1:9222/devtools/browser/387adf4c-243f-4051-a181-46798f4a46f4`.
        timeout : Union[float, None]
            Maximum time in milliseconds to wait for the connection to be established. Defaults to `30000` (30 seconds). Pass
            `0` to disable timeout.
        slow_mo : Union[float, None]
            Slows down Playwright operations by the specified amount of milliseconds. Useful so that you can see what is going
            on. Defaults to 0.
        headers : Union[Dict[str, str], None]
            Additional HTTP headers to be sent with connect request. Optional.
        is_local : Union[bool, None]
            Tells Playwright that it runs on the same host as the CDP server. It will enable certain optimizations that rely
            upon the file system being the same between Playwright and the Browser.

        Returns
        -------
        Browser
        """

        return mapping.from_impl(
            await self._impl_obj.connect_over_cdp(
                endpointURL=endpoint_url,
                timeout=timeout,
                slowMo=slow_mo,
                headers=mapping.to_impl(headers),
                isLocal=is_local,
            )
        )

    async def connect(
        self,
        ws_endpoint: str,
        *,
        timeout: typing.Optional[float] = None,
        slow_mo: typing.Optional[float] = None,
        headers: typing.Optional[typing.Dict[str, str]] = None,
        expose_network: typing.Optional[str] = None,
    ) -> "Browser":
        """BrowserType.connect

        This method attaches Playwright to an existing browser instance created via `BrowserType.launchServer` in Node.js.

        **NOTE** The major and minor version of the Playwright instance that connects needs to match the version of
        Playwright that launches the browser (1.2.3 → is compatible with 1.2.x).

        Parameters
        ----------
        ws_endpoint : str
            A Playwright browser websocket endpoint to connect to. You obtain this endpoint via `BrowserServer.wsEndpoint`.
        timeout : Union[float, None]
            Maximum time in milliseconds to wait for the connection to be established. Defaults to `0` (no timeout).
        slow_mo : Union[float, None]
            Slows down Playwright operations by the specified amount of milliseconds. Useful so that you can see what is going
            on. Defaults to 0.
        headers : Union[Dict[str, str], None]
            Additional HTTP headers to be sent with web socket connect request. Optional.
        expose_network : Union[str, None]
            This option exposes network available on the connecting client to the browser being connected to. Consists of a
            list of rules separated by comma.

            Available rules:
            1. Hostname pattern, for example: `example.com`, `*.org:99`, `x.*.y.com`, `*foo.org`.
            1. IP literal, for example: `127.0.0.1`, `0.0.0.0:99`, `[::1]`, `[0:0::1]:99`.
            1. `<loopback>` that matches local loopback interfaces: `localhost`, `*.localhost`, `127.0.0.1`, `[::1]`.

            Some common examples:
            1. `"*"` to expose all network.
            1. `"<loopback>"` to expose localhost network.
            1. `"*.test.internal-domain,*.staging.internal-domain,<loopback>"` to expose test/staging deployments and
               localhost.

        Returns
        -------
        Browser
        """

        return mapping.from_impl(
            await self._impl_obj.connect(
                wsEndpoint=ws_endpoint,
                timeout=timeout,
                slowMo=slow_mo,
                headers=mapping.to_impl(headers),
                exposeNetwork=expose_network,
            )
        )


mapping.register(BrowserTypeImpl, BrowserType)


class Playwright(AsyncBase):

    @property
    def devices(self) -> typing.Dict:
        """Playwright.devices

        Returns a dictionary of devices to be used with `browser.new_context()` or `browser.new_page()`.

        ```py
        import asyncio
        from playwright.async_api import async_playwright, Playwright

        async def run(playwright: Playwright):
            webkit = playwright.webkit
            iphone = playwright.devices[\"iPhone 6\"]
            browser = await webkit.launch()
            context = await browser.new_context(**iphone)
            page = await context.new_page()
            await page.goto(\"http://example.com\")
            # other actions...
            await browser.close()

        async def main():
            async with async_playwright() as playwright:
                await run(playwright)
        asyncio.run(main())
        ```

        Returns
        -------
        Dict
        """
        return mapping.from_maybe_impl(self._impl_obj.devices)

    @property
    def selectors(self) -> "Selectors":
        """Playwright.selectors

        Selectors can be used to install custom selector engines. See [extensibility](https://playwright.dev/python/docs/extensibility) for more
        information.

        Returns
        -------
        Selectors
        """
        return mapping.from_impl(self._impl_obj.selectors)

    @property
    def chromium(self) -> "BrowserType":
        """Playwright.chromium

        This object can be used to launch or connect to Chromium, returning instances of `Browser`.

        Returns
        -------
        BrowserType
        """
        return mapping.from_impl(self._impl_obj.chromium)

    @property
    def firefox(self) -> "BrowserType":
        """Playwright.firefox

        This object can be used to launch or connect to Firefox, returning instances of `Browser`.

        Returns
        -------
        BrowserType
        """
        return mapping.from_impl(self._impl_obj.firefox)

    @property
    def webkit(self) -> "BrowserType":
        """Playwright.webkit

        This object can be used to launch or connect to WebKit, returning instances of `Browser`.

        Returns
        -------
        BrowserType
        """
        return mapping.from_impl(self._impl_obj.webkit)

    @property
    def request(self) -> "APIRequest":
        """Playwright.request

        Exposes API that can be used for the Web API testing.

        Returns
        -------
        APIRequest
        """
        return mapping.from_impl(self._impl_obj.request)

    def __getitem__(self, value: str) -> "BrowserType":

        return mapping.from_impl(self._impl_obj.__getitem__(value=value))

    async def stop(self) -> None:
        """Playwright.stop

        Terminates this instance of Playwright in case it was created bypassing the Python context manager. This is useful
        in REPL applications.

        ```py
        from playwright.sync_api import sync_playwright

        playwright = sync_playwright().start()

        browser = playwright.chromium.launch()
        page = browser.new_page()
        page.goto(\"https://playwright.dev/\")
        page.screenshot(path=\"example.png\")
        browser.close()

        playwright.stop()
        ```
        """

        return mapping.from_maybe_impl(await self._impl_obj.stop())


mapping.register(PlaywrightImpl, Playwright)


class Tracing(AsyncBase):

    async def start(
        self,
        *,
        name: typing.Optional[str] = None,
        title: typing.Optional[str] = None,
        snapshots: typing.Optional[bool] = None,
        screenshots: typing.Optional[bool] = None,
        sources: typing.Optional[bool] = None,
    ) -> None:
        """Tracing.start

        Start tracing.

        **NOTE** You probably want to
        [enable tracing in your config file](https://playwright.dev/docs/api/class-testoptions#test-options-trace) instead
        of using `Tracing.start`.

        The `context.tracing` API captures browser operations and network activity, but it doesn't record test assertions
        (like `expect` calls). We recommend
        [enabling tracing through Playwright Test configuration](https://playwright.dev/docs/api/class-testoptions#test-options-trace),
        which includes those assertions and provides a more complete trace for debugging test failures.

        **Usage**

        ```py
        await context.tracing.start(screenshots=True, snapshots=True)
        page = await context.new_page()
        await page.goto(\"https://playwright.dev\")
        await context.tracing.stop(path = \"trace.zip\")
        ```

        Parameters
        ----------
        name : Union[str, None]
            If specified, intermediate trace files are going to be saved into the files with the given name prefix inside the
            `tracesDir` directory specified in `browser_type.launch()`. To specify the final trace zip file name, you
            need to pass `path` option to `tracing.stop()` instead.
        title : Union[str, None]
            Trace name to be shown in the Trace Viewer.
        snapshots : Union[bool, None]
            If this option is true tracing will
            - capture DOM snapshot on every action
            - record network activity
        screenshots : Union[bool, None]
            Whether to capture screenshots during tracing. Screenshots are used to build a timeline preview.
        sources : Union[bool, None]
            Whether to include source files for trace actions.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.start(
                name=name,
                title=title,
                snapshots=snapshots,
                screenshots=screenshots,
                sources=sources,
            )
        )

    async def start_chunk(
        self, *, title: typing.Optional[str] = None, name: typing.Optional[str] = None
    ) -> None:
        """Tracing.start_chunk

        Start a new trace chunk. If you'd like to record multiple traces on the same `BrowserContext`, use
        `tracing.start()` once, and then create multiple trace chunks with `tracing.start_chunk()` and
        `tracing.stop_chunk()`.

        **Usage**

        ```py
        await context.tracing.start(screenshots=True, snapshots=True)
        page = await context.new_page()
        await page.goto(\"https://playwright.dev\")

        await context.tracing.start_chunk()
        await page.get_by_text(\"Get Started\").click()
        # Everything between start_chunk and stop_chunk will be recorded in the trace.
        await context.tracing.stop_chunk(path = \"trace1.zip\")

        await context.tracing.start_chunk()
        await page.goto(\"http://example.com\")
        # Save a second trace file with different actions.
        await context.tracing.stop_chunk(path = \"trace2.zip\")
        ```

        Parameters
        ----------
        title : Union[str, None]
            Trace name to be shown in the Trace Viewer.
        name : Union[str, None]
            If specified, intermediate trace files are going to be saved into the files with the given name prefix inside the
            `tracesDir` directory specified in `browser_type.launch()`. To specify the final trace zip file name, you
            need to pass `path` option to `tracing.stop_chunk()` instead.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.start_chunk(title=title, name=name)
        )

    async def stop_chunk(
        self, *, path: typing.Optional[typing.Union[pathlib.Path, str]] = None
    ) -> None:
        """Tracing.stop_chunk

        Stop the trace chunk. See `tracing.start_chunk()` for more details about multiple trace chunks.

        Parameters
        ----------
        path : Union[pathlib.Path, str, None]
            Export trace collected since the last `tracing.start_chunk()` call into the file with the given path.
        """

        return mapping.from_maybe_impl(await self._impl_obj.stop_chunk(path=path))

    async def stop(
        self, *, path: typing.Optional[typing.Union[pathlib.Path, str]] = None
    ) -> None:
        """Tracing.stop

        Stop tracing.

        Parameters
        ----------
        path : Union[pathlib.Path, str, None]
            Export trace into the file with the given path.
        """

        return mapping.from_maybe_impl(await self._impl_obj.stop(path=path))

    async def group(
        self, name: str, *, location: typing.Optional[TracingGroupLocation] = None
    ) -> None:
        """Tracing.group

        **NOTE** Use `test.step` instead when available.

        Creates a new group within the trace, assigning any subsequent API calls to this group, until
        `tracing.group_end()` is called. Groups can be nested and will be visible in the trace viewer.

        **Usage**

        ```py
        # All actions between group and group_end
        # will be shown in the trace viewer as a group.
        page.context.tracing.group(\"Open Playwright.dev > API\")
        page.goto(\"https://playwright.dev/\")
        page.get_by_role(\"link\", name=\"API\").click()
        page.context.tracing.group_end()
        ```

        Parameters
        ----------
        name : str
            Group name shown in the trace viewer.
        location : Union[{file: str, line: Union[int, None], column: Union[int, None]}, None]
            Specifies a custom location for the group to be shown in the trace viewer. Defaults to the location of the
            `tracing.group()` call.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.group(name=name, location=location)
        )

    async def group_end(self) -> None:
        """Tracing.group_end

        Closes the last group created by `tracing.group()`.
        """

        return mapping.from_maybe_impl(await self._impl_obj.group_end())


mapping.register(TracingImpl, Tracing)


class Locator(AsyncBase):

    @property
    def page(self) -> "Page":
        """Locator.page

        A page this locator belongs to.

        Returns
        -------
        Page
        """
        return mapping.from_impl(self._impl_obj.page)

    @property
    def first(self) -> "Locator":
        """Locator.first

        Returns locator to the first matching element.

        Returns
        -------
        Locator
        """
        return mapping.from_impl(self._impl_obj.first)

    @property
    def last(self) -> "Locator":
        """Locator.last

        Returns locator to the last matching element.

        **Usage**

        ```py
        banana = await page.get_by_role(\"listitem\").last
        ```

        Returns
        -------
        Locator
        """
        return mapping.from_impl(self._impl_obj.last)

    @property
    def content_frame(self) -> "FrameLocator":
        """Locator.content_frame

        Returns a `FrameLocator` object pointing to the same `iframe` as this locator.

        Useful when you have a `Locator` object obtained somewhere, and later on would like to interact with the content
        inside the frame.

        For a reverse operation, use `frame_locator.owner()`.

        **Usage**

        ```py
        locator = page.locator(\"iframe[name=\\\"embedded\\\"]\")
        # ...
        frame_locator = locator.content_frame
        await frame_locator.get_by_role(\"button\").click()
        ```

        Returns
        -------
        FrameLocator
        """
        return mapping.from_impl(self._impl_obj.content_frame)

    @property
    def description(self) -> typing.Optional[str]:
        """Locator.description

        Returns locator description previously set with `locator.describe()`. Returns `null` if no custom
        description has been set.

        **Usage**

        ```py
        button = page.get_by_role(\"button\").describe(\"Subscribe button\")
        print(button.description())  # \"Subscribe button\"

        input = page.get_by_role(\"textbox\")
        print(input.description())  # None
        ```

        Returns
        -------
        Union[str, None]
        """
        return mapping.from_maybe_impl(self._impl_obj.description)

    async def bounding_box(
        self, *, timeout: typing.Optional[float] = None
    ) -> typing.Optional[FloatRect]:
        """Locator.bounding_box

        This method returns the bounding box of the element matching the locator, or `null` if the element is not visible.
        The bounding box is calculated relative to the main frame viewport - which is usually the same as the browser
        window.

        **Details**

        Scrolling affects the returned bounding box, similarly to
        [Element.getBoundingClientRect](https://developer.mozilla.org/en-US/docs/Web/API/Element/getBoundingClientRect).
        That means `x` and/or `y` may be negative.

        Elements from child frames return the bounding box relative to the main frame, unlike the
        [Element.getBoundingClientRect](https://developer.mozilla.org/en-US/docs/Web/API/Element/getBoundingClientRect).

        Assuming the page is static, it is safe to use bounding box coordinates to perform input. For example, the
        following snippet should click the center of the element.

        **Usage**

        ```py
        box = await page.get_by_role(\"button\").bounding_box()
        await page.mouse.click(box[\"x\"] + box[\"width\"] / 2, box[\"y\"] + box[\"height\"] / 2)
        ```

        Parameters
        ----------
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.

        Returns
        -------
        Union[{x: float, y: float, width: float, height: float}, None]
        """

        return mapping.from_impl_nullable(
            await self._impl_obj.bounding_box(timeout=timeout)
        )

    async def check(
        self,
        *,
        position: typing.Optional[Position] = None,
        timeout: typing.Optional[float] = None,
        force: typing.Optional[bool] = None,
        no_wait_after: typing.Optional[bool] = None,
        trial: typing.Optional[bool] = None,
    ) -> None:
        """Locator.check

        Ensure that checkbox or radio element is checked.

        **Details**

        Performs the following steps:
        1. Ensure that element is a checkbox or a radio input. If not, this method throws. If the element is already
           checked, this method returns immediately.
        1. Wait for [actionability](https://playwright.dev/python/docs/actionability) checks on the element, unless `force` option is set.
        1. Scroll the element into view if needed.
        1. Use `page.mouse` to click in the center of the element.
        1. Ensure that the element is now checked. If not, this method throws.

        If the element is detached from the DOM at any moment during the action, this method throws.

        When all steps combined have not finished during the specified `timeout`, this method throws a `TimeoutError`.
        Passing zero timeout disables this.

        **Usage**

        ```py
        await page.get_by_role(\"checkbox\").check()
        ```

        Parameters
        ----------
        position : Union[{x: float, y: float}, None]
            A point to use relative to the top-left corner of element padding box. If not specified, uses some visible point of
            the element.
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        force : Union[bool, None]
            Whether to bypass the [actionability](../actionability.md) checks. Defaults to `false`.
        no_wait_after : Union[bool, None]
            This option has no effect.
            Deprecated: This option has no effect.
        trial : Union[bool, None]
            When set, this method only performs the [actionability](../actionability.md) checks and skips the action. Defaults
            to `false`. Useful to wait until the element is ready for the action without performing it.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.check(
                position=position,
                timeout=timeout,
                force=force,
                noWaitAfter=no_wait_after,
                trial=trial,
            )
        )

    async def click(
        self,
        *,
        modifiers: typing.Optional[
            typing.Sequence[Literal["Alt", "Control", "ControlOrMeta", "Meta", "Shift"]]
        ] = None,
        position: typing.Optional[Position] = None,
        delay: typing.Optional[float] = None,
        button: typing.Optional[Literal["left", "middle", "right"]] = None,
        click_count: typing.Optional[int] = None,
        timeout: typing.Optional[float] = None,
        force: typing.Optional[bool] = None,
        no_wait_after: typing.Optional[bool] = None,
        trial: typing.Optional[bool] = None,
        steps: typing.Optional[int] = None,
    ) -> None:
        """Locator.click

        Click an element.

        **Details**

        This method clicks the element by performing the following steps:
        1. Wait for [actionability](https://playwright.dev/python/docs/actionability) checks on the element, unless `force` option is set.
        1. Scroll the element into view if needed.
        1. Use `page.mouse` to click in the center of the element, or the specified `position`.
        1. Wait for initiated navigations to either succeed or fail, unless `noWaitAfter` option is set.

        If the element is detached from the DOM at any moment during the action, this method throws.

        When all steps combined have not finished during the specified `timeout`, this method throws a `TimeoutError`.
        Passing zero timeout disables this.

        **Usage**

        Click a button:

        ```py
        await page.get_by_role(\"button\").click()
        ```

        Shift-right-click at a specific position on a canvas:

        ```py
        await page.locator(\"canvas\").click(
            button=\"right\", modifiers=[\"Shift\"], position={\"x\": 23, \"y\": 32}
        )
        ```

        Parameters
        ----------
        modifiers : Union[Sequence[Union["Alt", "Control", "ControlOrMeta", "Meta", "Shift"]], None]
            Modifier keys to press. Ensures that only these modifiers are pressed during the operation, and then restores
            current modifiers back. If not specified, currently pressed modifiers are used. "ControlOrMeta" resolves to
            "Control" on Windows and Linux and to "Meta" on macOS.
        position : Union[{x: float, y: float}, None]
            A point to use relative to the top-left corner of element padding box. If not specified, uses some visible point of
            the element.
        delay : Union[float, None]
            Time to wait between `mousedown` and `mouseup` in milliseconds. Defaults to 0.
        button : Union["left", "middle", "right", None]
            Defaults to `left`.
        click_count : Union[int, None]
            defaults to 1. See [UIEvent.detail].
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        force : Union[bool, None]
            Whether to bypass the [actionability](../actionability.md) checks. Defaults to `false`.
        no_wait_after : Union[bool, None]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You
            can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as
            navigating to inaccessible pages. Defaults to `false`.
            Deprecated: This option will default to `true` in the future.
        trial : Union[bool, None]
            When set, this method only performs the [actionability](../actionability.md) checks and skips the action. Defaults
            to `false`. Useful to wait until the element is ready for the action without performing it. Note that keyboard
            `modifiers` will be pressed regardless of `trial` to allow testing elements which are only visible when those keys
            are pressed.
        steps : Union[int, None]
            Defaults to 1. Sends `n` interpolated `mousemove` events to represent travel between Playwright's current cursor
            position and the provided destination. When set to 1, emits a single `mousemove` event at the destination location.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.click(
                modifiers=mapping.to_impl(modifiers),
                position=position,
                delay=delay,
                button=button,
                clickCount=click_count,
                timeout=timeout,
                force=force,
                noWaitAfter=no_wait_after,
                trial=trial,
                steps=steps,
            )
        )

    async def dblclick(
        self,
        *,
        modifiers: typing.Optional[
            typing.Sequence[Literal["Alt", "Control", "ControlOrMeta", "Meta", "Shift"]]
        ] = None,
        position: typing.Optional[Position] = None,
        delay: typing.Optional[float] = None,
        button: typing.Optional[Literal["left", "middle", "right"]] = None,
        timeout: typing.Optional[float] = None,
        force: typing.Optional[bool] = None,
        no_wait_after: typing.Optional[bool] = None,
        trial: typing.Optional[bool] = None,
        steps: typing.Optional[int] = None,
    ) -> None:
        """Locator.dblclick

        Double-click an element.

        **Details**

        This method double clicks the element by performing the following steps:
        1. Wait for [actionability](https://playwright.dev/python/docs/actionability) checks on the element, unless `force` option is set.
        1. Scroll the element into view if needed.
        1. Use `page.mouse` to double click in the center of the element, or the specified `position`.

        If the element is detached from the DOM at any moment during the action, this method throws.

        When all steps combined have not finished during the specified `timeout`, this method throws a `TimeoutError`.
        Passing zero timeout disables this.

        **NOTE** `element.dblclick()` dispatches two `click` events and a single `dblclick` event.

        Parameters
        ----------
        modifiers : Union[Sequence[Union["Alt", "Control", "ControlOrMeta", "Meta", "Shift"]], None]
            Modifier keys to press. Ensures that only these modifiers are pressed during the operation, and then restores
            current modifiers back. If not specified, currently pressed modifiers are used. "ControlOrMeta" resolves to
            "Control" on Windows and Linux and to "Meta" on macOS.
        position : Union[{x: float, y: float}, None]
            A point to use relative to the top-left corner of element padding box. If not specified, uses some visible point of
            the element.
        delay : Union[float, None]
            Time to wait between `mousedown` and `mouseup` in milliseconds. Defaults to 0.
        button : Union["left", "middle", "right", None]
            Defaults to `left`.
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        force : Union[bool, None]
            Whether to bypass the [actionability](../actionability.md) checks. Defaults to `false`.
        no_wait_after : Union[bool, None]
            This option has no effect.
            Deprecated: This option has no effect.
        trial : Union[bool, None]
            When set, this method only performs the [actionability](../actionability.md) checks and skips the action. Defaults
            to `false`. Useful to wait until the element is ready for the action without performing it. Note that keyboard
            `modifiers` will be pressed regardless of `trial` to allow testing elements which are only visible when those keys
            are pressed.
        steps : Union[int, None]
            Defaults to 1. Sends `n` interpolated `mousemove` events to represent travel between Playwright's current cursor
            position and the provided destination. When set to 1, emits a single `mousemove` event at the destination location.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.dblclick(
                modifiers=mapping.to_impl(modifiers),
                position=position,
                delay=delay,
                button=button,
                timeout=timeout,
                force=force,
                noWaitAfter=no_wait_after,
                trial=trial,
                steps=steps,
            )
        )

    async def dispatch_event(
        self,
        type: str,
        event_init: typing.Optional[typing.Dict] = None,
        *,
        timeout: typing.Optional[float] = None,
    ) -> None:
        """Locator.dispatch_event

        Programmatically dispatch an event on the matching element.

        **Usage**

        ```py
        await locator.dispatch_event(\"click\")
        ```

        **Details**

        The snippet above dispatches the `click` event on the element. Regardless of the visibility state of the element,
        `click` is dispatched. This is equivalent to calling
        [element.click()](https://developer.mozilla.org/en-US/docs/Web/API/HTMLElement/click).

        Under the hood, it creates an instance of an event based on the given `type`, initializes it with `eventInit`
        properties and dispatches it on the element. Events are `composed`, `cancelable` and bubble by default.

        Since `eventInit` is event-specific, please refer to the events documentation for the lists of initial properties:
        - [DeviceMotionEvent](https://developer.mozilla.org/en-US/docs/Web/API/DeviceMotionEvent/DeviceMotionEvent)
        - [DeviceOrientationEvent](https://developer.mozilla.org/en-US/docs/Web/API/DeviceOrientationEvent/DeviceOrientationEvent)
        - [DragEvent](https://developer.mozilla.org/en-US/docs/Web/API/DragEvent/DragEvent)
        - [Event](https://developer.mozilla.org/en-US/docs/Web/API/Event/Event)
        - [FocusEvent](https://developer.mozilla.org/en-US/docs/Web/API/FocusEvent/FocusEvent)
        - [KeyboardEvent](https://developer.mozilla.org/en-US/docs/Web/API/KeyboardEvent/KeyboardEvent)
        - [MouseEvent](https://developer.mozilla.org/en-US/docs/Web/API/MouseEvent/MouseEvent)
        - [PointerEvent](https://developer.mozilla.org/en-US/docs/Web/API/PointerEvent/PointerEvent)
        - [TouchEvent](https://developer.mozilla.org/en-US/docs/Web/API/TouchEvent/TouchEvent)
        - [WheelEvent](https://developer.mozilla.org/en-US/docs/Web/API/WheelEvent/WheelEvent)

        You can also specify `JSHandle` as the property value if you want live objects to be passed into the event:

        ```py
        data_transfer = await page.evaluate_handle(\"new DataTransfer()\")
        await locator.dispatch_event(\"#source\", \"dragstart\", {\"dataTransfer\": data_transfer})
        ```

        Parameters
        ----------
        type : str
            DOM event type: `"click"`, `"dragstart"`, etc.
        event_init : Union[Dict, None]
            Optional event-specific initialization properties.
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.dispatch_event(
                type=type, eventInit=mapping.to_impl(event_init), timeout=timeout
            )
        )

    async def evaluate(
        self,
        expression: str,
        arg: typing.Optional[typing.Any] = None,
        *,
        timeout: typing.Optional[float] = None,
    ) -> typing.Any:
        """Locator.evaluate

        Execute JavaScript code in the page, taking the matching element as an argument.

        **Details**

        Returns the return value of `expression`, called with the matching element as a first argument, and `arg` as a
        second argument.

        If `expression` returns a [Promise], this method will wait for the promise to resolve and return its value.

        If `expression` throws or rejects, this method throws.

        **Usage**

        Passing argument to `expression`:

        ```py
        result = await page.get_by_testid(\"myId\").evaluate(\"(element, [x, y]) => element.textContent + ' ' + x * y\", [7, 8])
        print(result) # prints \"myId text 56\"
        ```

        Parameters
        ----------
        expression : str
            JavaScript expression to be evaluated in the browser context. If the expression evaluates to a function, the
            function is automatically invoked.
        arg : Union[Any, None]
            Optional argument to pass to `expression`.
        timeout : Union[float, None]
            Maximum time in milliseconds to wait for the locator before evaluating. Note that after locator is resolved,
            evaluation itself is not limited by the timeout. Defaults to `30000` (30 seconds). Pass `0` to disable timeout.

        Returns
        -------
        Any
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.evaluate(
                expression=expression, arg=mapping.to_impl(arg), timeout=timeout
            )
        )

    async def evaluate_all(
        self, expression: str, arg: typing.Optional[typing.Any] = None
    ) -> typing.Any:
        """Locator.evaluate_all

        Execute JavaScript code in the page, taking all matching elements as an argument.

        **Details**

        Returns the return value of `expression`, called with an array of all matching elements as a first argument, and
        `arg` as a second argument.

        If `expression` returns a [Promise], this method will wait for the promise to resolve and return its value.

        If `expression` throws or rejects, this method throws.

        **Usage**

        ```py
        locator = page.locator(\"div\")
        more_than_ten = await locator.evaluate_all(\"(divs, min) => divs.length > min\", 10)
        ```

        Parameters
        ----------
        expression : str
            JavaScript expression to be evaluated in the browser context. If the expression evaluates to a function, the
            function is automatically invoked.
        arg : Union[Any, None]
            Optional argument to pass to `expression`.

        Returns
        -------
        Any
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.evaluate_all(
                expression=expression, arg=mapping.to_impl(arg)
            )
        )

    async def evaluate_handle(
        self,
        expression: str,
        arg: typing.Optional[typing.Any] = None,
        *,
        timeout: typing.Optional[float] = None,
    ) -> "JSHandle":
        """Locator.evaluate_handle

        Execute JavaScript code in the page, taking the matching element as an argument, and return a `JSHandle` with the
        result.

        **Details**

        Returns the return value of `expression` as a`JSHandle`, called with the matching element as a first argument, and
        `arg` as a second argument.

        The only difference between `locator.evaluate()` and `locator.evaluate_handle()` is that
        `locator.evaluate_handle()` returns `JSHandle`.

        If `expression` returns a [Promise], this method will wait for the promise to resolve and return its value.

        If `expression` throws or rejects, this method throws.

        See `page.evaluate_handle()` for more details.

        Parameters
        ----------
        expression : str
            JavaScript expression to be evaluated in the browser context. If the expression evaluates to a function, the
            function is automatically invoked.
        arg : Union[Any, None]
            Optional argument to pass to `expression`.
        timeout : Union[float, None]
            Maximum time in milliseconds to wait for the locator before evaluating. Note that after locator is resolved,
            evaluation itself is not limited by the timeout. Defaults to `30000` (30 seconds). Pass `0` to disable timeout.

        Returns
        -------
        JSHandle
        """

        return mapping.from_impl(
            await self._impl_obj.evaluate_handle(
                expression=expression, arg=mapping.to_impl(arg), timeout=timeout
            )
        )

    async def fill(
        self,
        value: str,
        *,
        timeout: typing.Optional[float] = None,
        no_wait_after: typing.Optional[bool] = None,
        force: typing.Optional[bool] = None,
    ) -> None:
        """Locator.fill

        Set a value to the input field.

        **Usage**

        ```py
        await page.get_by_role(\"textbox\").fill(\"example value\")
        ```

        **Details**

        This method waits for [actionability](https://playwright.dev/python/docs/actionability) checks, focuses the element, fills it and triggers an
        `input` event after filling. Note that you can pass an empty string to clear the input field.

        If the target element is not an `<input>`, `<textarea>` or `[contenteditable]` element, this method throws an
        error. However, if the element is inside the `<label>` element that has an associated
        [control](https://developer.mozilla.org/en-US/docs/Web/API/HTMLLabelElement/control), the control will be filled
        instead.

        To send fine-grained keyboard events, use `locator.press_sequentially()`.

        Parameters
        ----------
        value : str
            Value to set for the `<input>`, `<textarea>` or `[contenteditable]` element.
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        no_wait_after : Union[bool, None]
            This option has no effect.
            Deprecated: This option has no effect.
        force : Union[bool, None]
            Whether to bypass the [actionability](../actionability.md) checks. Defaults to `false`.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.fill(
                value=value, timeout=timeout, noWaitAfter=no_wait_after, force=force
            )
        )

    async def clear(
        self,
        *,
        timeout: typing.Optional[float] = None,
        no_wait_after: typing.Optional[bool] = None,
        force: typing.Optional[bool] = None,
    ) -> None:
        """Locator.clear

        Clear the input field.

        **Details**

        This method waits for [actionability](https://playwright.dev/python/docs/actionability) checks, focuses the element, clears it and triggers an
        `input` event after clearing.

        If the target element is not an `<input>`, `<textarea>` or `[contenteditable]` element, this method throws an
        error. However, if the element is inside the `<label>` element that has an associated
        [control](https://developer.mozilla.org/en-US/docs/Web/API/HTMLLabelElement/control), the control will be cleared
        instead.

        **Usage**

        ```py
        await page.get_by_role(\"textbox\").clear()
        ```

        Parameters
        ----------
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        no_wait_after : Union[bool, None]
            This option has no effect.
            Deprecated: This option has no effect.
        force : Union[bool, None]
            Whether to bypass the [actionability](../actionability.md) checks. Defaults to `false`.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.clear(
                timeout=timeout, noWaitAfter=no_wait_after, force=force
            )
        )

    def locator(
        self,
        selector_or_locator: typing.Union[str, "Locator"],
        *,
        has_text: typing.Optional[typing.Union[typing.Pattern[str], str]] = None,
        has_not_text: typing.Optional[typing.Union[typing.Pattern[str], str]] = None,
        has: typing.Optional["Locator"] = None,
        has_not: typing.Optional["Locator"] = None,
    ) -> "Locator":
        """Locator.locator

        The method finds an element matching the specified selector in the locator's subtree. It also accepts filter
        options, similar to `locator.filter()` method.

        [Learn more about locators](https://playwright.dev/python/docs/locators).

        Parameters
        ----------
        selector_or_locator : Union[Locator, str]
            A selector or locator to use when resolving DOM element.
        has_text : Union[Pattern[str], str, None]
            Matches elements containing specified text somewhere inside, possibly in a child or a descendant element. When
            passed a [string], matching is case-insensitive and searches for a substring. For example, `"Playwright"` matches
            `<article><div>Playwright</div></article>`.
        has_not_text : Union[Pattern[str], str, None]
            Matches elements that do not contain specified text somewhere inside, possibly in a child or a descendant element.
            When passed a [string], matching is case-insensitive and searches for a substring.
        has : Union[Locator, None]
            Narrows down the results of the method to those which contain elements matching this relative locator. For example,
            `article` that has `text=Playwright` matches `<article><div>Playwright</div></article>`.

            Inner locator **must be relative** to the outer locator and is queried starting with the outer locator match, not
            the document root. For example, you can find `content` that has `div` in
            `<article><content><div>Playwright</div></content></article>`. However, looking for `content` that has `article
            div` will fail, because the inner locator must be relative and should not use any elements outside the `content`.

            Note that outer and inner locators must belong to the same frame. Inner locator must not contain `FrameLocator`s.
        has_not : Union[Locator, None]
            Matches elements that do not contain an element that matches an inner locator. Inner locator is queried against the
            outer one. For example, `article` that does not have `div` matches `<article><span>Playwright</span></article>`.

            Note that outer and inner locators must belong to the same frame. Inner locator must not contain `FrameLocator`s.

        Returns
        -------
        Locator
        """

        return mapping.from_impl(
            self._impl_obj.locator(
                selectorOrLocator=selector_or_locator,
                hasText=has_text,
                hasNotText=has_not_text,
                has=has._impl_obj if has else None,
                hasNot=has_not._impl_obj if has_not else None,
            )
        )

    def get_by_alt_text(
        self,
        text: typing.Union[str, typing.Pattern[str]],
        *,
        exact: typing.Optional[bool] = None,
    ) -> "Locator":
        """Locator.get_by_alt_text

        Allows locating elements by their alt text.

        **Usage**

        For example, this method will find the image by alt text \"Playwright logo\":

        ```html
        <img alt='Playwright logo'>
        ```

        ```py
        await page.get_by_alt_text(\"Playwright logo\").click()
        ```

        Parameters
        ----------
        text : Union[Pattern[str], str]
            Text to locate the element for.
        exact : Union[bool, None]
            Whether to find an exact match: case-sensitive and whole-string. Default to false. Ignored when locating by a
            regular expression. Note that exact match still trims whitespace.

        Returns
        -------
        Locator
        """

        return mapping.from_impl(self._impl_obj.get_by_alt_text(text=text, exact=exact))

    def get_by_label(
        self,
        text: typing.Union[str, typing.Pattern[str]],
        *,
        exact: typing.Optional[bool] = None,
    ) -> "Locator":
        """Locator.get_by_label

        Allows locating input elements by the text of the associated `<label>` or `aria-labelledby` element, or by the
        `aria-label` attribute.

        **Usage**

        For example, this method will find inputs by label \"Username\" and \"Password\" in the following DOM:

        ```html
        <input aria-label=\"Username\">
        <label for=\"password-input\">Password:</label>
        <input id=\"password-input\">
        ```

        ```py
        await page.get_by_label(\"Username\").fill(\"john\")
        await page.get_by_label(\"Password\").fill(\"secret\")
        ```

        Parameters
        ----------
        text : Union[Pattern[str], str]
            Text to locate the element for.
        exact : Union[bool, None]
            Whether to find an exact match: case-sensitive and whole-string. Default to false. Ignored when locating by a
            regular expression. Note that exact match still trims whitespace.

        Returns
        -------
        Locator
        """

        return mapping.from_impl(self._impl_obj.get_by_label(text=text, exact=exact))

    def get_by_placeholder(
        self,
        text: typing.Union[str, typing.Pattern[str]],
        *,
        exact: typing.Optional[bool] = None,
    ) -> "Locator":
        """Locator.get_by_placeholder

        Allows locating input elements by the placeholder text.

        **Usage**

        For example, consider the following DOM structure.

        ```html
        <input type=\"email\" placeholder=\"name@example.com\" />
        ```

        You can fill the input after locating it by the placeholder text:

        ```py
        await page.get_by_placeholder(\"name@example.com\").fill(\"playwright@microsoft.com\")
        ```

        Parameters
        ----------
        text : Union[Pattern[str], str]
            Text to locate the element for.
        exact : Union[bool, None]
            Whether to find an exact match: case-sensitive and whole-string. Default to false. Ignored when locating by a
            regular expression. Note that exact match still trims whitespace.

        Returns
        -------
        Locator
        """

        return mapping.from_impl(
            self._impl_obj.get_by_placeholder(text=text, exact=exact)
        )

    def get_by_role(
        self,
        role: Literal[
            "alert",
            "alertdialog",
            "application",
            "article",
            "banner",
            "blockquote",
            "button",
            "caption",
            "cell",
            "checkbox",
            "code",
            "columnheader",
            "combobox",
            "complementary",
            "contentinfo",
            "definition",
            "deletion",
            "dialog",
            "directory",
            "document",
            "emphasis",
            "feed",
            "figure",
            "form",
            "generic",
            "grid",
            "gridcell",
            "group",
            "heading",
            "img",
            "insertion",
            "link",
            "list",
            "listbox",
            "listitem",
            "log",
            "main",
            "marquee",
            "math",
            "menu",
            "menubar",
            "menuitem",
            "menuitemcheckbox",
            "menuitemradio",
            "meter",
            "navigation",
            "none",
            "note",
            "option",
            "paragraph",
            "presentation",
            "progressbar",
            "radio",
            "radiogroup",
            "region",
            "row",
            "rowgroup",
            "rowheader",
            "scrollbar",
            "search",
            "searchbox",
            "separator",
            "slider",
            "spinbutton",
            "status",
            "strong",
            "subscript",
            "superscript",
            "switch",
            "tab",
            "table",
            "tablist",
            "tabpanel",
            "term",
            "textbox",
            "time",
            "timer",
            "toolbar",
            "tooltip",
            "tree",
            "treegrid",
            "treeitem",
        ],
        *,
        checked: typing.Optional[bool] = None,
        disabled: typing.Optional[bool] = None,
        expanded: typing.Optional[bool] = None,
        include_hidden: typing.Optional[bool] = None,
        level: typing.Optional[int] = None,
        name: typing.Optional[typing.Union[typing.Pattern[str], str]] = None,
        pressed: typing.Optional[bool] = None,
        selected: typing.Optional[bool] = None,
        exact: typing.Optional[bool] = None,
    ) -> "Locator":
        """Locator.get_by_role

        Allows locating elements by their [ARIA role](https://www.w3.org/TR/wai-aria-1.2/#roles),
        [ARIA attributes](https://www.w3.org/TR/wai-aria-1.2/#aria-attributes) and
        [accessible name](https://w3c.github.io/accname/#dfn-accessible-name).

        **Usage**

        Consider the following DOM structure.

        ```html
        <h3>Sign up</h3>
        <label>
          <input type=\"checkbox\" /> Subscribe
        </label>
        <br/>
        <button>Submit</button>
        ```

        You can locate each element by it's implicit role:

        ```py
        await expect(page.get_by_role(\"heading\", name=\"Sign up\")).to_be_visible()

        await page.get_by_role(\"checkbox\", name=\"Subscribe\").check()

        await page.get_by_role(\"button\", name=re.compile(\"submit\", re.IGNORECASE)).click()
        ```

        **Details**

        Role selector **does not replace** accessibility audits and conformance tests, but rather gives early feedback
        about the ARIA guidelines.

        Many html elements have an implicitly [defined role](https://w3c.github.io/html-aam/#html-element-role-mappings)
        that is recognized by the role selector. You can find all the
        [supported roles here](https://www.w3.org/TR/wai-aria-1.2/#role_definitions). ARIA guidelines **do not recommend**
        duplicating implicit roles and attributes by setting `role` and/or `aria-*` attributes to default values.

        Parameters
        ----------
        role : Union["alert", "alertdialog", "application", "article", "banner", "blockquote", "button", "caption", "cell", "checkbox", "code", "columnheader", "combobox", "complementary", "contentinfo", "definition", "deletion", "dialog", "directory", "document", "emphasis", "feed", "figure", "form", "generic", "grid", "gridcell", "group", "heading", "img", "insertion", "link", "list", "listbox", "listitem", "log", "main", "marquee", "math", "menu", "menubar", "menuitem", "menuitemcheckbox", "menuitemradio", "meter", "navigation", "none", "note", "option", "paragraph", "presentation", "progressbar", "radio", "radiogroup", "region", "row", "rowgroup", "rowheader", "scrollbar", "search", "searchbox", "separator", "slider", "spinbutton", "status", "strong", "subscript", "superscript", "switch", "tab", "table", "tablist", "tabpanel", "term", "textbox", "time", "timer", "toolbar", "tooltip", "tree", "treegrid", "treeitem"]
            Required aria role.
        checked : Union[bool, None]
            An attribute that is usually set by `aria-checked` or native `<input type=checkbox>` controls.

            Learn more about [`aria-checked`](https://www.w3.org/TR/wai-aria-1.2/#aria-checked).
        disabled : Union[bool, None]
            An attribute that is usually set by `aria-disabled` or `disabled`.

            **NOTE** Unlike most other attributes, `disabled` is inherited through the DOM hierarchy. Learn more about
            [`aria-disabled`](https://www.w3.org/TR/wai-aria-1.2/#aria-disabled).

        expanded : Union[bool, None]
            An attribute that is usually set by `aria-expanded`.

            Learn more about [`aria-expanded`](https://www.w3.org/TR/wai-aria-1.2/#aria-expanded).
        include_hidden : Union[bool, None]
            Option that controls whether hidden elements are matched. By default, only non-hidden elements, as
            [defined by ARIA](https://www.w3.org/TR/wai-aria-1.2/#tree_exclusion), are matched by role selector.

            Learn more about [`aria-hidden`](https://www.w3.org/TR/wai-aria-1.2/#aria-hidden).
        level : Union[int, None]
            A number attribute that is usually present for roles `heading`, `listitem`, `row`, `treeitem`, with default values
            for `<h1>-<h6>` elements.

            Learn more about [`aria-level`](https://www.w3.org/TR/wai-aria-1.2/#aria-level).
        name : Union[Pattern[str], str, None]
            Option to match the [accessible name](https://w3c.github.io/accname/#dfn-accessible-name). By default, matching is
            case-insensitive and searches for a substring, use `exact` to control this behavior.

            Learn more about [accessible name](https://w3c.github.io/accname/#dfn-accessible-name).
        pressed : Union[bool, None]
            An attribute that is usually set by `aria-pressed`.

            Learn more about [`aria-pressed`](https://www.w3.org/TR/wai-aria-1.2/#aria-pressed).
        selected : Union[bool, None]
            An attribute that is usually set by `aria-selected`.

            Learn more about [`aria-selected`](https://www.w3.org/TR/wai-aria-1.2/#aria-selected).
        exact : Union[bool, None]
            Whether `name` is matched exactly: case-sensitive and whole-string. Defaults to false. Ignored when `name` is a
            regular expression. Note that exact match still trims whitespace.

        Returns
        -------
        Locator
        """

        return mapping.from_impl(
            self._impl_obj.get_by_role(
                role=role,
                checked=checked,
                disabled=disabled,
                expanded=expanded,
                includeHidden=include_hidden,
                level=level,
                name=name,
                pressed=pressed,
                selected=selected,
                exact=exact,
            )
        )

    def get_by_test_id(
        self, test_id: typing.Union[str, typing.Pattern[str]]
    ) -> "Locator":
        """Locator.get_by_test_id

        Locate element by the test id.

        **Usage**

        Consider the following DOM structure.

        ```html
        <button data-testid=\"directions\">Itinéraire</button>
        ```

        You can locate the element by it's test id:

        ```py
        await page.get_by_test_id(\"directions\").click()
        ```

        **Details**

        By default, the `data-testid` attribute is used as a test id. Use `selectors.set_test_id_attribute()` to
        configure a different test id attribute if necessary.

        Parameters
        ----------
        test_id : Union[Pattern[str], str]
            Id to locate the element by.

        Returns
        -------
        Locator
        """

        return mapping.from_impl(self._impl_obj.get_by_test_id(testId=test_id))

    def get_by_text(
        self,
        text: typing.Union[str, typing.Pattern[str]],
        *,
        exact: typing.Optional[bool] = None,
    ) -> "Locator":
        """Locator.get_by_text

        Allows locating elements that contain given text.

        See also `locator.filter()` that allows to match by another criteria, like an accessible role, and then
        filter by the text content.

        **Usage**

        Consider the following DOM structure:

        ```html
        <div>Hello <span>world</span></div>
        <div>Hello</div>
        ```

        You can locate by text substring, exact string, or a regular expression:

        ```py
        # Matches <span>
        page.get_by_text(\"world\")

        # Matches first <div>
        page.get_by_text(\"Hello world\")

        # Matches second <div>
        page.get_by_text(\"Hello\", exact=True)

        # Matches both <div>s
        page.get_by_text(re.compile(\"Hello\"))

        # Matches second <div>
        page.get_by_text(re.compile(\"^hello$\", re.IGNORECASE))
        ```

        **Details**

        Matching by text always normalizes whitespace, even with exact match. For example, it turns multiple spaces into
        one, turns line breaks into spaces and ignores leading and trailing whitespace.

        Input elements of the type `button` and `submit` are matched by their `value` instead of the text content. For
        example, locating by text `\"Log in\"` matches `<input type=button value=\"Log in\">`.

        Parameters
        ----------
        text : Union[Pattern[str], str]
            Text to locate the element for.
        exact : Union[bool, None]
            Whether to find an exact match: case-sensitive and whole-string. Default to false. Ignored when locating by a
            regular expression. Note that exact match still trims whitespace.

        Returns
        -------
        Locator
        """

        return mapping.from_impl(self._impl_obj.get_by_text(text=text, exact=exact))

    def get_by_title(
        self,
        text: typing.Union[str, typing.Pattern[str]],
        *,
        exact: typing.Optional[bool] = None,
    ) -> "Locator":
        """Locator.get_by_title

        Allows locating elements by their title attribute.

        **Usage**

        Consider the following DOM structure.

        ```html
        <span title='Issues count'>25 issues</span>
        ```

        You can check the issues count after locating it by the title text:

        ```py
        await expect(page.get_by_title(\"Issues count\")).to_have_text(\"25 issues\")
        ```

        Parameters
        ----------
        text : Union[Pattern[str], str]
            Text to locate the element for.
        exact : Union[bool, None]
            Whether to find an exact match: case-sensitive and whole-string. Default to false. Ignored when locating by a
            regular expression. Note that exact match still trims whitespace.

        Returns
        -------
        Locator
        """

        return mapping.from_impl(self._impl_obj.get_by_title(text=text, exact=exact))

    def frame_locator(self, selector: str) -> "FrameLocator":
        """Locator.frame_locator

        When working with iframes, you can create a frame locator that will enter the iframe and allow locating elements in
        that iframe:

        **Usage**

        ```py
        locator = page.frame_locator(\"iframe\").get_by_text(\"Submit\")
        await locator.click()
        ```

        Parameters
        ----------
        selector : str
            A selector to use when resolving DOM element.

        Returns
        -------
        FrameLocator
        """

        return mapping.from_impl(self._impl_obj.frame_locator(selector=selector))

    async def element_handle(
        self, *, timeout: typing.Optional[float] = None
    ) -> "ElementHandle":
        """Locator.element_handle

        Resolves given locator to the first matching DOM element. If there are no matching elements, waits for one. If
        multiple elements match the locator, throws.

        Parameters
        ----------
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.

        Returns
        -------
        ElementHandle
        """

        return mapping.from_impl(await self._impl_obj.element_handle(timeout=timeout))

    async def element_handles(self) -> typing.List["ElementHandle"]:
        """Locator.element_handles

        Resolves given locator to all matching DOM elements. If there are no matching elements, returns an empty list.

        Returns
        -------
        List[ElementHandle]
        """

        return mapping.from_impl_list(await self._impl_obj.element_handles())

    def nth(self, index: int) -> "Locator":
        """Locator.nth

        Returns locator to the n-th matching element. It's zero based, `nth(0)` selects the first element.

        **Usage**

        ```py
        banana = await page.get_by_role(\"listitem\").nth(2)
        ```

        Parameters
        ----------
        index : int

        Returns
        -------
        Locator
        """

        return mapping.from_impl(self._impl_obj.nth(index=index))

    def describe(self, description: str) -> "Locator":
        """Locator.describe

        Describes the locator, description is used in the trace viewer and reports. Returns the locator pointing to the
        same element.

        **Usage**

        ```py
        button = page.get_by_test_id(\"btn-sub\").describe(\"Subscribe button\")
        await button.click()
        ```

        Parameters
        ----------
        description : str
            Locator description.

        Returns
        -------
        Locator
        """

        return mapping.from_impl(self._impl_obj.describe(description=description))

    def filter(
        self,
        *,
        has_text: typing.Optional[typing.Union[typing.Pattern[str], str]] = None,
        has_not_text: typing.Optional[typing.Union[typing.Pattern[str], str]] = None,
        has: typing.Optional["Locator"] = None,
        has_not: typing.Optional["Locator"] = None,
        visible: typing.Optional[bool] = None,
    ) -> "Locator":
        """Locator.filter

        This method narrows existing locator according to the options, for example filters by text. It can be chained to
        filter multiple times.

        **Usage**

        ```py
        row_locator = page.locator(\"tr\")
        # ...
        await row_locator.filter(has_text=\"text in column 1\").filter(
            has=page.get_by_role(\"button\", name=\"column 2 button\")
        ).screenshot()

        ```

        Parameters
        ----------
        has_text : Union[Pattern[str], str, None]
            Matches elements containing specified text somewhere inside, possibly in a child or a descendant element. When
            passed a [string], matching is case-insensitive and searches for a substring. For example, `"Playwright"` matches
            `<article><div>Playwright</div></article>`.
        has_not_text : Union[Pattern[str], str, None]
            Matches elements that do not contain specified text somewhere inside, possibly in a child or a descendant element.
            When passed a [string], matching is case-insensitive and searches for a substring.
        has : Union[Locator, None]
            Narrows down the results of the method to those which contain elements matching this relative locator. For example,
            `article` that has `text=Playwright` matches `<article><div>Playwright</div></article>`.

            Inner locator **must be relative** to the outer locator and is queried starting with the outer locator match, not
            the document root. For example, you can find `content` that has `div` in
            `<article><content><div>Playwright</div></content></article>`. However, looking for `content` that has `article
            div` will fail, because the inner locator must be relative and should not use any elements outside the `content`.

            Note that outer and inner locators must belong to the same frame. Inner locator must not contain `FrameLocator`s.
        has_not : Union[Locator, None]
            Matches elements that do not contain an element that matches an inner locator. Inner locator is queried against the
            outer one. For example, `article` that does not have `div` matches `<article><span>Playwright</span></article>`.

            Note that outer and inner locators must belong to the same frame. Inner locator must not contain `FrameLocator`s.
        visible : Union[bool, None]
            Only matches visible or invisible elements.

        Returns
        -------
        Locator
        """

        return mapping.from_impl(
            self._impl_obj.filter(
                hasText=has_text,
                hasNotText=has_not_text,
                has=has._impl_obj if has else None,
                hasNot=has_not._impl_obj if has_not else None,
                visible=visible,
            )
        )

    def or_(self, locator: "Locator") -> "Locator":
        """Locator.or_

        Creates a locator matching all elements that match one or both of the two locators.

        Note that when both locators match something, the resulting locator will have multiple matches, potentially causing
        a [locator strictness](https://playwright.dev/python/docs/locators#strictness) violation.

        **Usage**

        Consider a scenario where you'd like to click on a \"New email\" button, but sometimes a security settings dialog
        shows up instead. In this case, you can wait for either a \"New email\" button, or a dialog and act accordingly.

        **NOTE** If both \"New email\" button and security dialog appear on screen, the \"or\" locator will match both of them,
        possibly throwing the [\"strict mode violation\" error](https://playwright.dev/python/docs/locators#strictness). In this case, you can use
        `locator.first()` to only match one of them.

        ```py
        new_email = page.get_by_role(\"button\", name=\"New\")
        dialog = page.get_by_text(\"Confirm security settings\")
        await expect(new_email.or_(dialog).first).to_be_visible()
        if (await dialog.is_visible()):
          await page.get_by_role(\"button\", name=\"Dismiss\").click()
        await new_email.click()
        ```

        Parameters
        ----------
        locator : Locator
            Alternative locator to match.

        Returns
        -------
        Locator
        """

        return mapping.from_impl(self._impl_obj.or_(locator=locator._impl_obj))

    def and_(self, locator: "Locator") -> "Locator":
        """Locator.and_

        Creates a locator that matches both this locator and the argument locator.

        **Usage**

        The following example finds a button with a specific title.

        ```py
        button = page.get_by_role(\"button\").and_(page.get_by_title(\"Subscribe\"))
        ```

        Parameters
        ----------
        locator : Locator
            Additional locator to match.

        Returns
        -------
        Locator
        """

        return mapping.from_impl(self._impl_obj.and_(locator=locator._impl_obj))

    async def focus(self, *, timeout: typing.Optional[float] = None) -> None:
        """Locator.focus

        Calls [focus](https://developer.mozilla.org/en-US/docs/Web/API/HTMLElement/focus) on the matching element.

        Parameters
        ----------
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        """

        return mapping.from_maybe_impl(await self._impl_obj.focus(timeout=timeout))

    async def blur(self, *, timeout: typing.Optional[float] = None) -> None:
        """Locator.blur

        Calls [blur](https://developer.mozilla.org/en-US/docs/Web/API/HTMLElement/blur) on the element.

        Parameters
        ----------
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        """

        return mapping.from_maybe_impl(await self._impl_obj.blur(timeout=timeout))

    async def all(self) -> typing.List["Locator"]:
        """Locator.all

        When the locator points to a list of elements, this returns an array of locators, pointing to their respective
        elements.

        **NOTE** `locator.all()` does not wait for elements to match the locator, and instead immediately returns
        whatever is present in the page.

        When the list of elements changes dynamically, `locator.all()` will produce unpredictable and flaky
        results.

        When the list of elements is stable, but loaded dynamically, wait for the full list to finish loading before
        calling `locator.all()`.

        **Usage**

        ```py
        for li in await page.get_by_role('listitem').all():
          await li.click();
        ```

        Returns
        -------
        List[Locator]
        """

        return mapping.from_impl_list(await self._impl_obj.all())

    async def count(self) -> int:
        """Locator.count

        Returns the number of elements matching the locator.

        **NOTE** If you need to assert the number of elements on the page, prefer `locator_assertions.to_have_count()`
        to avoid flakiness. See [assertions guide](https://playwright.dev/python/docs/test-assertions) for more details.

        **Usage**

        ```py
        count = await page.get_by_role(\"listitem\").count()
        ```

        Returns
        -------
        int
        """

        return mapping.from_maybe_impl(await self._impl_obj.count())

    async def drag_to(
        self,
        target: "Locator",
        *,
        force: typing.Optional[bool] = None,
        no_wait_after: typing.Optional[bool] = None,
        timeout: typing.Optional[float] = None,
        trial: typing.Optional[bool] = None,
        source_position: typing.Optional[Position] = None,
        target_position: typing.Optional[Position] = None,
        steps: typing.Optional[int] = None,
    ) -> None:
        """Locator.drag_to

        Drag the source element towards the target element and drop it.

        **Details**

        This method drags the locator to another target locator or target position. It will first move to the source
        element, perform a `mousedown`, then move to the target element or position and perform a `mouseup`.

        **Usage**

        ```py
        source = page.locator(\"#source\")
        target = page.locator(\"#target\")

        await source.drag_to(target)
        # or specify exact positions relative to the top-left corners of the elements:
        await source.drag_to(
          target,
          source_position={\"x\": 34, \"y\": 7},
          target_position={\"x\": 10, \"y\": 20}
        )
        ```

        Parameters
        ----------
        target : Locator
            Locator of the element to drag to.
        force : Union[bool, None]
            Whether to bypass the [actionability](../actionability.md) checks. Defaults to `false`.
        no_wait_after : Union[bool, None]
            This option has no effect.
            Deprecated: This option has no effect.
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        trial : Union[bool, None]
            When set, this method only performs the [actionability](../actionability.md) checks and skips the action. Defaults
            to `false`. Useful to wait until the element is ready for the action without performing it.
        source_position : Union[{x: float, y: float}, None]
            Clicks on the source element at this point relative to the top-left corner of the element's padding box. If not
            specified, some visible point of the element is used.
        target_position : Union[{x: float, y: float}, None]
            Drops on the target element at this point relative to the top-left corner of the element's padding box. If not
            specified, some visible point of the element is used.
        steps : Union[int, None]
            Defaults to 1. Sends `n` interpolated `mousemove` events to represent travel between the `mousedown` and `mouseup`
            of the drag. When set to 1, emits a single `mousemove` event at the destination location.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.drag_to(
                target=target._impl_obj,
                force=force,
                noWaitAfter=no_wait_after,
                timeout=timeout,
                trial=trial,
                sourcePosition=source_position,
                targetPosition=target_position,
                steps=steps,
            )
        )

    async def get_attribute(
        self, name: str, *, timeout: typing.Optional[float] = None
    ) -> typing.Optional[str]:
        """Locator.get_attribute

        Returns the matching element's attribute value.

        **NOTE** If you need to assert an element's attribute, prefer `locator_assertions.to_have_attribute()` to
        avoid flakiness. See [assertions guide](https://playwright.dev/python/docs/test-assertions) for more details.

        Parameters
        ----------
        name : str
            Attribute name to get the value for.
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.

        Returns
        -------
        Union[str, None]
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.get_attribute(name=name, timeout=timeout)
        )

    async def hover(
        self,
        *,
        modifiers: typing.Optional[
            typing.Sequence[Literal["Alt", "Control", "ControlOrMeta", "Meta", "Shift"]]
        ] = None,
        position: typing.Optional[Position] = None,
        timeout: typing.Optional[float] = None,
        no_wait_after: typing.Optional[bool] = None,
        force: typing.Optional[bool] = None,
        trial: typing.Optional[bool] = None,
    ) -> None:
        """Locator.hover

        Hover over the matching element.

        **Usage**

        ```py
        await page.get_by_role(\"link\").hover()
        ```

        **Details**

        This method hovers over the element by performing the following steps:
        1. Wait for [actionability](https://playwright.dev/python/docs/actionability) checks on the element, unless `force` option is set.
        1. Scroll the element into view if needed.
        1. Use `page.mouse` to hover over the center of the element, or the specified `position`.

        If the element is detached from the DOM at any moment during the action, this method throws.

        When all steps combined have not finished during the specified `timeout`, this method throws a `TimeoutError`.
        Passing zero timeout disables this.

        Parameters
        ----------
        modifiers : Union[Sequence[Union["Alt", "Control", "ControlOrMeta", "Meta", "Shift"]], None]
            Modifier keys to press. Ensures that only these modifiers are pressed during the operation, and then restores
            current modifiers back. If not specified, currently pressed modifiers are used. "ControlOrMeta" resolves to
            "Control" on Windows and Linux and to "Meta" on macOS.
        position : Union[{x: float, y: float}, None]
            A point to use relative to the top-left corner of element padding box. If not specified, uses some visible point of
            the element.
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        no_wait_after : Union[bool, None]
            This option has no effect.
            Deprecated: This option has no effect.
        force : Union[bool, None]
            Whether to bypass the [actionability](../actionability.md) checks. Defaults to `false`.
        trial : Union[bool, None]
            When set, this method only performs the [actionability](../actionability.md) checks and skips the action. Defaults
            to `false`. Useful to wait until the element is ready for the action without performing it. Note that keyboard
            `modifiers` will be pressed regardless of `trial` to allow testing elements which are only visible when those keys
            are pressed.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.hover(
                modifiers=mapping.to_impl(modifiers),
                position=position,
                timeout=timeout,
                noWaitAfter=no_wait_after,
                force=force,
                trial=trial,
            )
        )

    async def inner_html(self, *, timeout: typing.Optional[float] = None) -> str:
        """Locator.inner_html

        Returns the [`element.innerHTML`](https://developer.mozilla.org/en-US/docs/Web/API/Element/innerHTML).

        Parameters
        ----------
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.

        Returns
        -------
        str
        """

        return mapping.from_maybe_impl(await self._impl_obj.inner_html(timeout=timeout))

    async def inner_text(self, *, timeout: typing.Optional[float] = None) -> str:
        """Locator.inner_text

        Returns the [`element.innerText`](https://developer.mozilla.org/en-US/docs/Web/API/HTMLElement/innerText).

        **NOTE** If you need to assert text on the page, prefer `locator_assertions.to_have_text()` with
        `useInnerText` option to avoid flakiness. See [assertions guide](https://playwright.dev/python/docs/test-assertions) for more details.

        Parameters
        ----------
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.

        Returns
        -------
        str
        """

        return mapping.from_maybe_impl(await self._impl_obj.inner_text(timeout=timeout))

    async def input_value(self, *, timeout: typing.Optional[float] = None) -> str:
        """Locator.input_value

        Returns the value for the matching `<input>` or `<textarea>` or `<select>` element.

        **NOTE** If you need to assert input value, prefer `locator_assertions.to_have_value()` to avoid flakiness.
        See [assertions guide](https://playwright.dev/python/docs/test-assertions) for more details.

        **Usage**

        ```py
        value = await page.get_by_role(\"textbox\").input_value()
        ```

        **Details**

        Throws elements that are not an input, textarea or a select. However, if the element is inside the `<label>`
        element that has an associated
        [control](https://developer.mozilla.org/en-US/docs/Web/API/HTMLLabelElement/control), returns the value of the
        control.

        Parameters
        ----------
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.

        Returns
        -------
        str
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.input_value(timeout=timeout)
        )

    async def is_checked(self, *, timeout: typing.Optional[float] = None) -> bool:
        """Locator.is_checked

        Returns whether the element is checked. Throws if the element is not a checkbox or radio input.

        **NOTE** If you need to assert that checkbox is checked, prefer `locator_assertions.to_be_checked()` to avoid
        flakiness. See [assertions guide](https://playwright.dev/python/docs/test-assertions) for more details.

        **Usage**

        ```py
        checked = await page.get_by_role(\"checkbox\").is_checked()
        ```

        Parameters
        ----------
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.

        Returns
        -------
        bool
        """

        return mapping.from_maybe_impl(await self._impl_obj.is_checked(timeout=timeout))

    async def is_disabled(self, *, timeout: typing.Optional[float] = None) -> bool:
        """Locator.is_disabled

        Returns whether the element is disabled, the opposite of [enabled](https://playwright.dev/python/docs/actionability#enabled).

        **NOTE** If you need to assert that an element is disabled, prefer `locator_assertions.to_be_disabled()` to
        avoid flakiness. See [assertions guide](https://playwright.dev/python/docs/test-assertions) for more details.

        **Usage**

        ```py
        disabled = await page.get_by_role(\"button\").is_disabled()
        ```

        Parameters
        ----------
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.

        Returns
        -------
        bool
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.is_disabled(timeout=timeout)
        )

    async def is_editable(self, *, timeout: typing.Optional[float] = None) -> bool:
        """Locator.is_editable

        Returns whether the element is [editable](https://playwright.dev/python/docs/actionability#editable). If the target element is not an `<input>`,
        `<textarea>`, `<select>`, `[contenteditable]` and does not have a role allowing `[aria-readonly]`, this method
        throws an error.

        **NOTE** If you need to assert that an element is editable, prefer `locator_assertions.to_be_editable()` to
        avoid flakiness. See [assertions guide](https://playwright.dev/python/docs/test-assertions) for more details.

        **Usage**

        ```py
        editable = await page.get_by_role(\"textbox\").is_editable()
        ```

        Parameters
        ----------
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.

        Returns
        -------
        bool
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.is_editable(timeout=timeout)
        )

    async def is_enabled(self, *, timeout: typing.Optional[float] = None) -> bool:
        """Locator.is_enabled

        Returns whether the element is [enabled](https://playwright.dev/python/docs/actionability#enabled).

        **NOTE** If you need to assert that an element is enabled, prefer `locator_assertions.to_be_enabled()` to
        avoid flakiness. See [assertions guide](https://playwright.dev/python/docs/test-assertions) for more details.

        **Usage**

        ```py
        enabled = await page.get_by_role(\"button\").is_enabled()
        ```

        Parameters
        ----------
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.

        Returns
        -------
        bool
        """

        return mapping.from_maybe_impl(await self._impl_obj.is_enabled(timeout=timeout))

    async def is_hidden(self, *, timeout: typing.Optional[float] = None) -> bool:
        """Locator.is_hidden

        Returns whether the element is hidden, the opposite of [visible](https://playwright.dev/python/docs/actionability#visible).

        **NOTE** If you need to assert that element is hidden, prefer `locator_assertions.to_be_hidden()` to avoid
        flakiness. See [assertions guide](https://playwright.dev/python/docs/test-assertions) for more details.

        **Usage**

        ```py
        hidden = await page.get_by_role(\"button\").is_hidden()
        ```

        Parameters
        ----------
        timeout : Union[float, None]
            Deprecated: This option is ignored. `locator.is_hidden()` does not wait for the element to become hidden and returns immediately.

        Returns
        -------
        bool
        """

        return mapping.from_maybe_impl(await self._impl_obj.is_hidden(timeout=timeout))

    async def is_visible(self, *, timeout: typing.Optional[float] = None) -> bool:
        """Locator.is_visible

        Returns whether the element is [visible](https://playwright.dev/python/docs/actionability#visible).

        **NOTE** If you need to assert that element is visible, prefer `locator_assertions.to_be_visible()` to avoid
        flakiness. See [assertions guide](https://playwright.dev/python/docs/test-assertions) for more details.

        **Usage**

        ```py
        visible = await page.get_by_role(\"button\").is_visible()
        ```

        Parameters
        ----------
        timeout : Union[float, None]
            Deprecated: This option is ignored. `locator.is_visible()` does not wait for the element to become visible and returns immediately.

        Returns
        -------
        bool
        """

        return mapping.from_maybe_impl(await self._impl_obj.is_visible(timeout=timeout))

    async def press(
        self,
        key: str,
        *,
        delay: typing.Optional[float] = None,
        timeout: typing.Optional[float] = None,
        no_wait_after: typing.Optional[bool] = None,
    ) -> None:
        """Locator.press

        Focuses the matching element and presses a combination of the keys.

        **Usage**

        ```py
        await page.get_by_role(\"textbox\").press(\"Backspace\")
        ```

        **Details**

        Focuses the element, and then uses `keyboard.down()` and `keyboard.up()`.

        `key` can specify the intended
        [keyboardEvent.key](https://developer.mozilla.org/en-US/docs/Web/API/KeyboardEvent/key) value or a single character
        to generate the text for. A superset of the `key` values can be found
        [here](https://developer.mozilla.org/en-US/docs/Web/API/KeyboardEvent/key/Key_Values). Examples of the keys are:

        `F1` - `F12`, `Digit0`- `Digit9`, `KeyA`- `KeyZ`, `Backquote`, `Minus`, `Equal`, `Backslash`, `Backspace`, `Tab`,
        `Delete`, `Escape`, `ArrowDown`, `End`, `Enter`, `Home`, `Insert`, `PageDown`, `PageUp`, `ArrowRight`, `ArrowUp`,
        etc.

        Following modification shortcuts are also supported: `Shift`, `Control`, `Alt`, `Meta`, `ShiftLeft`,
        `ControlOrMeta`. `ControlOrMeta` resolves to `Control` on Windows and Linux and to `Meta` on macOS.

        Holding down `Shift` will type the text that corresponds to the `key` in the upper case.

        If `key` is a single character, it is case-sensitive, so the values `a` and `A` will generate different respective
        texts.

        Shortcuts such as `key: \"Control+o\"`, `key: \"Control++` or `key: \"Control+Shift+T\"` are supported as well. When
        specified with the modifier, modifier is pressed and being held while the subsequent key is being pressed.

        Parameters
        ----------
        key : str
            Name of the key to press or a character to generate, such as `ArrowLeft` or `a`.
        delay : Union[float, None]
            Time to wait between `keydown` and `keyup` in milliseconds. Defaults to 0.
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        no_wait_after : Union[bool, None]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You
            can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as
            navigating to inaccessible pages. Defaults to `false`.
            Deprecated: This option will default to `true` in the future.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.press(
                key=key, delay=delay, timeout=timeout, noWaitAfter=no_wait_after
            )
        )

    async def screenshot(
        self,
        *,
        timeout: typing.Optional[float] = None,
        type: typing.Optional[Literal["jpeg", "png"]] = None,
        path: typing.Optional[typing.Union[pathlib.Path, str]] = None,
        quality: typing.Optional[int] = None,
        omit_background: typing.Optional[bool] = None,
        animations: typing.Optional[Literal["allow", "disabled"]] = None,
        caret: typing.Optional[Literal["hide", "initial"]] = None,
        scale: typing.Optional[Literal["css", "device"]] = None,
        mask: typing.Optional[typing.Sequence["Locator"]] = None,
        mask_color: typing.Optional[str] = None,
        style: typing.Optional[str] = None,
    ) -> bytes:
        """Locator.screenshot

        Take a screenshot of the element matching the locator.

        **Usage**

        ```py
        await page.get_by_role(\"link\").screenshot()
        ```

        Disable animations and save screenshot to a file:

        ```py
        await page.get_by_role(\"link\").screenshot(animations=\"disabled\", path=\"link.png\")
        ```

        **Details**

        This method captures a screenshot of the page, clipped to the size and position of a particular element matching
        the locator. If the element is covered by other elements, it will not be actually visible on the screenshot. If the
        element is a scrollable container, only the currently scrolled content will be visible on the screenshot.

        This method waits for the [actionability](https://playwright.dev/python/docs/actionability) checks, then scrolls element into view before taking
        a screenshot. If the element is detached from DOM, the method throws an error.

        Returns the buffer with the captured screenshot.

        Parameters
        ----------
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        type : Union["jpeg", "png", None]
            Specify screenshot type, defaults to `png`.
        path : Union[pathlib.Path, str, None]
            The file path to save the image to. The screenshot type will be inferred from file extension. If `path` is a
            relative path, then it is resolved relative to the current working directory. If no path is provided, the image
            won't be saved to the disk.
        quality : Union[int, None]
            The quality of the image, between 0-100. Not applicable to `png` images.
        omit_background : Union[bool, None]
            Hides default white background and allows capturing screenshots with transparency. Not applicable to `jpeg` images.
            Defaults to `false`.
        animations : Union["allow", "disabled", None]
            When set to `"disabled"`, stops CSS animations, CSS transitions and Web Animations. Animations get different
            treatment depending on their duration:
            - finite animations are fast-forwarded to completion, so they'll fire `transitionend` event.
            - infinite animations are canceled to initial state, and then played over after the screenshot.

            Defaults to `"allow"` that leaves animations untouched.
        caret : Union["hide", "initial", None]
            When set to `"hide"`, screenshot will hide text caret. When set to `"initial"`, text caret behavior will not be
            changed.  Defaults to `"hide"`.
        scale : Union["css", "device", None]
            When set to `"css"`, screenshot will have a single pixel per each css pixel on the page. For high-dpi devices, this
            will keep screenshots small. Using `"device"` option will produce a single pixel per each device pixel, so
            screenshots of high-dpi devices will be twice as large or even larger.

            Defaults to `"device"`.
        mask : Union[Sequence[Locator], None]
            Specify locators that should be masked when the screenshot is taken. Masked elements will be overlaid with a pink
            box `#FF00FF` (customized by `maskColor`) that completely covers its bounding box. The mask is also applied to
            invisible elements, see [Matching only visible elements](../locators.md#matching-only-visible-elements) to disable
            that.
        mask_color : Union[str, None]
            Specify the color of the overlay box for masked elements, in
            [CSS color format](https://developer.mozilla.org/en-US/docs/Web/CSS/color_value). Default color is pink `#FF00FF`.
        style : Union[str, None]
            Text of the stylesheet to apply while making the screenshot. This is where you can hide dynamic elements, make
            elements invisible or change their properties to help you creating repeatable screenshots. This stylesheet pierces
            the Shadow DOM and applies to the inner frames.

        Returns
        -------
        bytes
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.screenshot(
                timeout=timeout,
                type=type,
                path=path,
                quality=quality,
                omitBackground=omit_background,
                animations=animations,
                caret=caret,
                scale=scale,
                mask=mapping.to_impl(mask),
                maskColor=mask_color,
                style=style,
            )
        )

    async def aria_snapshot(self, *, timeout: typing.Optional[float] = None) -> str:
        """Locator.aria_snapshot

        Captures the aria snapshot of the given element. Read more about [aria snapshots](https://playwright.dev/python/docs/aria-snapshots) and
        `locator_assertions.to_match_aria_snapshot()` for the corresponding assertion.

        **Usage**

        ```py
        await page.get_by_role(\"link\").aria_snapshot()
        ```

        **Details**

        This method captures the aria snapshot of the given element. The snapshot is a string that represents the state of
        the element and its children. The snapshot can be used to assert the state of the element in the test, or to
        compare it to state in the future.

        The ARIA snapshot is represented using [YAML](https://yaml.org/spec/1.2.2/) markup language:
        - The keys of the objects are the roles and optional accessible names of the elements.
        - The values are either text content or an array of child elements.
        - Generic static text can be represented with the `text` key.

        Below is the HTML markup and the respective ARIA snapshot:

        ```html
        <ul aria-label=\"Links\">
          <li><a href=\"/\">Home</a></li>
          <li><a href=\"/about\">About</a></li>
        <ul>
        ```

        ```yml
        - list \"Links\":
          - listitem:
            - link \"Home\"
          - listitem:
            - link \"About\"
        ```

        Parameters
        ----------
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.

        Returns
        -------
        str
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.aria_snapshot(timeout=timeout)
        )

    async def scroll_into_view_if_needed(
        self, *, timeout: typing.Optional[float] = None
    ) -> None:
        """Locator.scroll_into_view_if_needed

        This method waits for [actionability](https://playwright.dev/python/docs/actionability) checks, then tries to scroll element into view, unless
        it is completely visible as defined by
        [IntersectionObserver](https://developer.mozilla.org/en-US/docs/Web/API/Intersection_Observer_API)'s `ratio`.

        See [scrolling](https://playwright.dev/python/docs/input#scrolling) for alternative ways to scroll.

        Parameters
        ----------
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.scroll_into_view_if_needed(timeout=timeout)
        )

    async def select_option(
        self,
        value: typing.Optional[typing.Union[str, typing.Sequence[str]]] = None,
        *,
        index: typing.Optional[typing.Union[int, typing.Sequence[int]]] = None,
        label: typing.Optional[typing.Union[str, typing.Sequence[str]]] = None,
        element: typing.Optional[
            typing.Union["ElementHandle", typing.Sequence["ElementHandle"]]
        ] = None,
        timeout: typing.Optional[float] = None,
        no_wait_after: typing.Optional[bool] = None,
        force: typing.Optional[bool] = None,
    ) -> typing.List[str]:
        """Locator.select_option

        Selects option or options in `<select>`.

        **Details**

        This method waits for [actionability](https://playwright.dev/python/docs/actionability) checks, waits until all specified options are present in
        the `<select>` element and selects these options.

        If the target element is not a `<select>` element, this method throws an error. However, if the element is inside
        the `<label>` element that has an associated
        [control](https://developer.mozilla.org/en-US/docs/Web/API/HTMLLabelElement/control), the control will be used
        instead.

        Returns the array of option values that have been successfully selected.

        Triggers a `change` and `input` event once all the provided options have been selected.

        **Usage**

        ```html
        <select multiple>
          <option value=\"red\">Red</option>
          <option value=\"green\">Green</option>
          <option value=\"blue\">Blue</option>
        </select>
        ```

        ```py
        # single selection matching the value or label
        await element.select_option(\"blue\")
        # single selection matching the label
        await element.select_option(label=\"blue\")
        # multiple selection for blue, red and second option
        await element.select_option(value=[\"red\", \"green\", \"blue\"])
        ```

        Parameters
        ----------
        value : Union[Sequence[str], str, None]
            Options to select by value. If the `<select>` has the `multiple` attribute, all given options are selected,
            otherwise only the first option matching one of the passed options is selected. Optional.
        index : Union[Sequence[int], int, None]
            Options to select by index. Optional.
        label : Union[Sequence[str], str, None]
            Options to select by label. If the `<select>` has the `multiple` attribute, all given options are selected,
            otherwise only the first option matching one of the passed options is selected. Optional.
        element : Union[ElementHandle, Sequence[ElementHandle], None]
            Option elements to select. Optional.
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        no_wait_after : Union[bool, None]
            This option has no effect.
            Deprecated: This option has no effect.
        force : Union[bool, None]
            Whether to bypass the [actionability](../actionability.md) checks. Defaults to `false`.

        Returns
        -------
        List[str]
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.select_option(
                value=mapping.to_impl(value),
                index=mapping.to_impl(index),
                label=mapping.to_impl(label),
                element=mapping.to_impl(element),
                timeout=timeout,
                noWaitAfter=no_wait_after,
                force=force,
            )
        )

    async def select_text(
        self,
        *,
        force: typing.Optional[bool] = None,
        timeout: typing.Optional[float] = None,
    ) -> None:
        """Locator.select_text

        This method waits for [actionability](https://playwright.dev/python/docs/actionability) checks, then focuses the element and selects all its
        text content.

        If the element is inside the `<label>` element that has an associated
        [control](https://developer.mozilla.org/en-US/docs/Web/API/HTMLLabelElement/control), focuses and selects text in
        the control instead.

        Parameters
        ----------
        force : Union[bool, None]
            Whether to bypass the [actionability](../actionability.md) checks. Defaults to `false`.
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.select_text(force=force, timeout=timeout)
        )

    async def set_input_files(
        self,
        files: typing.Union[
            str,
            pathlib.Path,
            FilePayload,
            typing.Sequence[typing.Union[str, pathlib.Path]],
            typing.Sequence[FilePayload],
        ],
        *,
        timeout: typing.Optional[float] = None,
        no_wait_after: typing.Optional[bool] = None,
    ) -> None:
        """Locator.set_input_files

        Upload file or multiple files into `<input type=file>`. For inputs with a `[webkitdirectory]` attribute, only a
        single directory path is supported.

        **Usage**

        ```py
        # Select one file
        await page.get_by_label(\"Upload file\").set_input_files('myfile.pdf')

        # Select multiple files
        await page.get_by_label(\"Upload files\").set_input_files(['file1.txt', 'file2.txt'])

        # Select a directory
        await page.get_by_label(\"Upload directory\").set_input_files('mydir')

        # Remove all the selected files
        await page.get_by_label(\"Upload file\").set_input_files([])

        # Upload buffer from memory
        await page.get_by_label(\"Upload file\").set_input_files(
            files=[
                {\"name\": \"test.txt\", \"mimeType\": \"text/plain\", \"buffer\": b\"this is a test\"}
            ],
        )
        ```

        **Details**

        Sets the value of the file input to these file paths or files. If some of the `filePaths` are relative paths, then
        they are resolved relative to the current working directory. For empty array, clears the selected files.

        This method expects `Locator` to point to an
        [input element](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/input). However, if the element is inside
        the `<label>` element that has an associated
        [control](https://developer.mozilla.org/en-US/docs/Web/API/HTMLLabelElement/control), targets the control instead.

        Parameters
        ----------
        files : Union[Sequence[Union[pathlib.Path, str]], Sequence[{name: str, mimeType: str, buffer: bytes}], pathlib.Path, str, {name: str, mimeType: str, buffer: bytes}]
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        no_wait_after : Union[bool, None]
            This option has no effect.
            Deprecated: This option has no effect.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.set_input_files(
                files=mapping.to_impl(files), timeout=timeout, noWaitAfter=no_wait_after
            )
        )

    async def tap(
        self,
        *,
        modifiers: typing.Optional[
            typing.Sequence[Literal["Alt", "Control", "ControlOrMeta", "Meta", "Shift"]]
        ] = None,
        position: typing.Optional[Position] = None,
        timeout: typing.Optional[float] = None,
        force: typing.Optional[bool] = None,
        no_wait_after: typing.Optional[bool] = None,
        trial: typing.Optional[bool] = None,
    ) -> None:
        """Locator.tap

        Perform a tap gesture on the element matching the locator. For examples of emulating other gestures by manually
        dispatching touch events, see the [emulating legacy touch events](https://playwright.dev/python/docs/touch-events) page.

        **Details**

        This method taps the element by performing the following steps:
        1. Wait for [actionability](https://playwright.dev/python/docs/actionability) checks on the element, unless `force` option is set.
        1. Scroll the element into view if needed.
        1. Use `page.touchscreen` to tap the center of the element, or the specified `position`.

        If the element is detached from the DOM at any moment during the action, this method throws.

        When all steps combined have not finished during the specified `timeout`, this method throws a `TimeoutError`.
        Passing zero timeout disables this.

        **NOTE** `element.tap()` requires that the `hasTouch` option of the browser context be set to true.

        Parameters
        ----------
        modifiers : Union[Sequence[Union["Alt", "Control", "ControlOrMeta", "Meta", "Shift"]], None]
            Modifier keys to press. Ensures that only these modifiers are pressed during the operation, and then restores
            current modifiers back. If not specified, currently pressed modifiers are used. "ControlOrMeta" resolves to
            "Control" on Windows and Linux and to "Meta" on macOS.
        position : Union[{x: float, y: float}, None]
            A point to use relative to the top-left corner of element padding box. If not specified, uses some visible point of
            the element.
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        force : Union[bool, None]
            Whether to bypass the [actionability](../actionability.md) checks. Defaults to `false`.
        no_wait_after : Union[bool, None]
            This option has no effect.
            Deprecated: This option has no effect.
        trial : Union[bool, None]
            When set, this method only performs the [actionability](../actionability.md) checks and skips the action. Defaults
            to `false`. Useful to wait until the element is ready for the action without performing it. Note that keyboard
            `modifiers` will be pressed regardless of `trial` to allow testing elements which are only visible when those keys
            are pressed.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.tap(
                modifiers=mapping.to_impl(modifiers),
                position=position,
                timeout=timeout,
                force=force,
                noWaitAfter=no_wait_after,
                trial=trial,
            )
        )

    async def text_content(
        self, *, timeout: typing.Optional[float] = None
    ) -> typing.Optional[str]:
        """Locator.text_content

        Returns the [`node.textContent`](https://developer.mozilla.org/en-US/docs/Web/API/Node/textContent).

        **NOTE** If you need to assert text on the page, prefer `locator_assertions.to_have_text()` to avoid
        flakiness. See [assertions guide](https://playwright.dev/python/docs/test-assertions) for more details.

        Parameters
        ----------
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.

        Returns
        -------
        Union[str, None]
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.text_content(timeout=timeout)
        )

    async def type(
        self,
        text: str,
        *,
        delay: typing.Optional[float] = None,
        timeout: typing.Optional[float] = None,
        no_wait_after: typing.Optional[bool] = None,
    ) -> None:
        """Locator.type

        Focuses the element, and then sends a `keydown`, `keypress`/`input`, and `keyup` event for each character in the
        text.

        To press a special key, like `Control` or `ArrowDown`, use `locator.press()`.

        **Usage**

        Parameters
        ----------
        text : str
            A text to type into a focused element.
        delay : Union[float, None]
            Time to wait between key presses in milliseconds. Defaults to 0.
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        no_wait_after : Union[bool, None]
            This option has no effect.
            Deprecated: This option has no effect.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.type(
                text=text, delay=delay, timeout=timeout, noWaitAfter=no_wait_after
            )
        )

    async def press_sequentially(
        self,
        text: str,
        *,
        delay: typing.Optional[float] = None,
        timeout: typing.Optional[float] = None,
        no_wait_after: typing.Optional[bool] = None,
    ) -> None:
        """Locator.press_sequentially

        **NOTE** In most cases, you should use `locator.fill()` instead. You only need to press keys one by one if
        there is special keyboard handling on the page.

        Focuses the element, and then sends a `keydown`, `keypress`/`input`, and `keyup` event for each character in the
        text.

        To press a special key, like `Control` or `ArrowDown`, use `locator.press()`.

        **Usage**

        ```py
        await locator.press_sequentially(\"hello\") # types instantly
        await locator.press_sequentially(\"world\", delay=100) # types slower, like a user
        ```

        An example of typing into a text field and then submitting the form:

        ```py
        locator = page.get_by_label(\"Password\")
        await locator.press_sequentially(\"my password\")
        await locator.press(\"Enter\")
        ```

        Parameters
        ----------
        text : str
            String of characters to sequentially press into a focused element.
        delay : Union[float, None]
            Time to wait between key presses in milliseconds. Defaults to 0.
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        no_wait_after : Union[bool, None]
            This option has no effect.
            Deprecated: This option has no effect.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.press_sequentially(
                text=text, delay=delay, timeout=timeout, noWaitAfter=no_wait_after
            )
        )

    async def uncheck(
        self,
        *,
        position: typing.Optional[Position] = None,
        timeout: typing.Optional[float] = None,
        force: typing.Optional[bool] = None,
        no_wait_after: typing.Optional[bool] = None,
        trial: typing.Optional[bool] = None,
    ) -> None:
        """Locator.uncheck

        Ensure that checkbox or radio element is unchecked.

        **Usage**

        ```py
        await page.get_by_role(\"checkbox\").uncheck()
        ```

        **Details**

        This method unchecks the element by performing the following steps:
        1. Ensure that element is a checkbox or a radio input. If not, this method throws. If the element is already
           unchecked, this method returns immediately.
        1. Wait for [actionability](https://playwright.dev/python/docs/actionability) checks on the element, unless `force` option is set.
        1. Scroll the element into view if needed.
        1. Use `page.mouse` to click in the center of the element.
        1. Ensure that the element is now unchecked. If not, this method throws.

        If the element is detached from the DOM at any moment during the action, this method throws.

        When all steps combined have not finished during the specified `timeout`, this method throws a `TimeoutError`.
        Passing zero timeout disables this.

        Parameters
        ----------
        position : Union[{x: float, y: float}, None]
            A point to use relative to the top-left corner of element padding box. If not specified, uses some visible point of
            the element.
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        force : Union[bool, None]
            Whether to bypass the [actionability](../actionability.md) checks. Defaults to `false`.
        no_wait_after : Union[bool, None]
            This option has no effect.
            Deprecated: This option has no effect.
        trial : Union[bool, None]
            When set, this method only performs the [actionability](../actionability.md) checks and skips the action. Defaults
            to `false`. Useful to wait until the element is ready for the action without performing it.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.uncheck(
                position=position,
                timeout=timeout,
                force=force,
                noWaitAfter=no_wait_after,
                trial=trial,
            )
        )

    async def all_inner_texts(self) -> typing.List[str]:
        """Locator.all_inner_texts

        Returns an array of `node.innerText` values for all matching nodes.

        **NOTE** If you need to assert text on the page, prefer `locator_assertions.to_have_text()` with
        `useInnerText` option to avoid flakiness. See [assertions guide](https://playwright.dev/python/docs/test-assertions) for more details.

        **Usage**

        ```py
        texts = await page.get_by_role(\"link\").all_inner_texts()
        ```

        Returns
        -------
        List[str]
        """

        return mapping.from_maybe_impl(await self._impl_obj.all_inner_texts())

    async def all_text_contents(self) -> typing.List[str]:
        """Locator.all_text_contents

        Returns an array of `node.textContent` values for all matching nodes.

        **NOTE** If you need to assert text on the page, prefer `locator_assertions.to_have_text()` to avoid
        flakiness. See [assertions guide](https://playwright.dev/python/docs/test-assertions) for more details.

        **Usage**

        ```py
        texts = await page.get_by_role(\"link\").all_text_contents()
        ```

        Returns
        -------
        List[str]
        """

        return mapping.from_maybe_impl(await self._impl_obj.all_text_contents())

    async def wait_for(
        self,
        *,
        timeout: typing.Optional[float] = None,
        state: typing.Optional[
            Literal["attached", "detached", "hidden", "visible"]
        ] = None,
    ) -> None:
        """Locator.wait_for

        Returns when element specified by locator satisfies the `state` option.

        If target element already satisfies the condition, the method returns immediately. Otherwise, waits for up to
        `timeout` milliseconds until the condition is met.

        **Usage**

        ```py
        order_sent = page.locator(\"#order-sent\")
        await order_sent.wait_for()
        ```

        Parameters
        ----------
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        state : Union["attached", "detached", "hidden", "visible", None]
            Defaults to `'visible'`. Can be either:
            - `'attached'` - wait for element to be present in DOM.
            - `'detached'` - wait for element to not be present in DOM.
            - `'visible'` - wait for element to have non-empty bounding box and no `visibility:hidden`. Note that element
              without any content or with `display:none` has an empty bounding box and is not considered visible.
            - `'hidden'` - wait for element to be either detached from DOM, or have an empty bounding box or
              `visibility:hidden`. This is opposite to the `'visible'` option.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.wait_for(timeout=timeout, state=state)
        )

    async def set_checked(
        self,
        checked: bool,
        *,
        position: typing.Optional[Position] = None,
        timeout: typing.Optional[float] = None,
        force: typing.Optional[bool] = None,
        no_wait_after: typing.Optional[bool] = None,
        trial: typing.Optional[bool] = None,
    ) -> None:
        """Locator.set_checked

        Set the state of a checkbox or a radio element.

        **Usage**

        ```py
        await page.get_by_role(\"checkbox\").set_checked(True)
        ```

        **Details**

        This method checks or unchecks an element by performing the following steps:
        1. Ensure that matched element is a checkbox or a radio input. If not, this method throws.
        1. If the element already has the right checked state, this method returns immediately.
        1. Wait for [actionability](https://playwright.dev/python/docs/actionability) checks on the matched element, unless `force` option is set. If
           the element is detached during the checks, the whole action is retried.
        1. Scroll the element into view if needed.
        1. Use `page.mouse` to click in the center of the element.
        1. Ensure that the element is now checked or unchecked. If not, this method throws.

        When all steps combined have not finished during the specified `timeout`, this method throws a `TimeoutError`.
        Passing zero timeout disables this.

        Parameters
        ----------
        checked : bool
            Whether to check or uncheck the checkbox.
        position : Union[{x: float, y: float}, None]
            A point to use relative to the top-left corner of element padding box. If not specified, uses some visible point of
            the element.
        timeout : Union[float, None]
            Maximum time in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can
            be changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        force : Union[bool, None]
            Whether to bypass the [actionability](../actionability.md) checks. Defaults to `false`.
        no_wait_after : Union[bool, None]
            This option has no effect.
            Deprecated: This option has no effect.
        trial : Union[bool, None]
            When set, this method only performs the [actionability](../actionability.md) checks and skips the action. Defaults
            to `false`. Useful to wait until the element is ready for the action without performing it.
        """

        return mapping.from_maybe_impl(
            await self._impl_obj.set_checked(
                checked=checked,
                position=position,
                timeout=timeout,
                force=force,
                noWaitAfter=no_wait_after,
                trial=trial,
            )
        )

    async def highlight(self) -> None:
        """Locator.highlight

        Highlight the corresponding element(s) on the screen. Useful for debugging, don't commit the code that uses
        `locator.highlight()`.
        """

        return mapping.from_maybe_impl(await self._impl_obj.highlight())


mapping.register(LocatorImpl, Locator)


class APIResponse(AsyncBase):

    @property
    def ok(self) -> bool:
        """APIResponse.ok

        Contains a boolean stating whether the response was successful (status in the range 200-299) or not.

        Returns
        -------
        bool
        """
        return mapping.from_maybe_impl(self._impl_obj.ok)

    @property
    def url(self) -> str:
        """APIResponse.url

        Contains the URL of the response.

        Returns
        -------
        str
        """
        return mapping.from_maybe_impl(self._impl_obj.url)

    @property
    def status(self) -> int:
        """APIResponse.status

        Contains the status code of the response (e.g., 200 for a success).

        Returns
        -------
        int
        """
        return mapping.from_maybe_impl(self._impl_obj.status)

    @property
    def status_text(self) -> str:
        """APIResponse.status_text

        Contains the status text of the response (e.g. usually an \"OK\" for a success).

        Returns
        -------
        str
        """
        return mapping.from_maybe_impl(self._impl_obj.status_text)

    @property
    def headers(self) -> typing.Dict[str, str]:
        """APIResponse.headers

        An object with all the response HTTP headers associated with this response.

        Returns
        -------
        Dict[str, str]
        """
        return mapping.from_maybe_impl(self._impl_obj.headers)

    @property
    def headers_array(self) -> typing.List[NameValue]:
        """APIResponse.headers_array

        An array with all the response HTTP headers associated with this response. Header names are not lower-cased.
        Headers with multiple entries, such as `Set-Cookie`, appear in the array multiple times.

        Returns
        -------
        List[{name: str, value: str}]
        """
        return mapping.from_impl_list(self._impl_obj.headers_array)

    async def body(self) -> bytes:
        """APIResponse.body

        Returns the buffer with response body.

        Returns
        -------
        bytes
        """

        return mapping.from_maybe_impl(await self._impl_obj.body())

    async def text(self) -> str:
        """APIResponse.text

        Returns the text representation of response body.

        Returns
        -------
        str
        """

        return mapping.from_maybe_impl(await self._impl_obj.text())

    async def json(self) -> typing.Any:
        """APIResponse.json

        Returns the JSON representation of response body.

        This method will throw if the response body is not parsable via `JSON.parse`.

        Returns
        -------
        Any
        """

        return mapping.from_maybe_impl(await self._impl_obj.json())

    async def dispose(self) -> None:
        """APIResponse.dispose

        Disposes the body of this response. If not called then the body will stay in memory until the context closes.
        """

        return mapping.from_maybe_impl(await self._impl_obj.dispose())


mapping.register(APIResponseImpl, APIResponse)


class APIRequestContext(AsyncBase):

    async def dispose(self, *, reason: typing.Optional[str] = None) -> None:
        """APIRequestContext.dispose

        All responses returned by `a_pi_request_context.get()` and similar methods are stored in the memory, so that
        you can later call `a_pi_response.body()`.This method discards all its resources, calling any method on
        disposed `APIRequestContext` will throw an exception.

        Parameters
        ----------
        reason : Union[str, None]
            The reason to be reported to the operations interrupted by the context disposal.
        """

        return mapping.from_maybe_impl(await self._impl_obj.dispose(reason=reason))

    async def delete(
        self,
        url: str,
        *,
        params: typing.Optional[
            typing.Union[typing.Dict[str, typing.Union[str, float, bool]], str]
        ] = None,
        headers: typing.Optional[typing.Dict[str, str]] = None,
        data: typing.Optional[typing.Union[typing.Any, str, bytes]] = None,
        form: typing.Optional[typing.Dict[str, typing.Union[str, float, bool]]] = None,
        multipart: typing.Optional[
            typing.Dict[str, typing.Union[bytes, bool, float, str, FilePayload]]
        ] = None,
        timeout: typing.Optional[float] = None,
        fail_on_status_code: typing.Optional[bool] = None,
        ignore_https_errors: typing.Optional[bool] = None,
        max_redirects: typing.Optional[int] = None,
        max_retries: typing.Optional[int] = None,
    ) -> "APIResponse":
        """APIRequestContext.delete

        Sends HTTP(S) [DELETE](https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods/DELETE) request and returns its
        response. The method will populate request cookies from the context and update context cookies from the response.
        The method will automatically follow redirects.

        Parameters
        ----------
        url : str
            Target URL.
        params : Union[Dict[str, Union[bool, float, str]], str, None]
            Query parameters to be sent with the URL.
        headers : Union[Dict[str, str], None]
            Allows to set HTTP headers. These headers will apply to the fetched request as well as any redirects initiated by
            it.
        data : Union[Any, bytes, str, None]
            Allows to set post data of the request. If the data parameter is an object, it will be serialized to json string
            and `content-type` header will be set to `application/json` if not explicitly set. Otherwise the `content-type`
            header will be set to `application/octet-stream` if not explicitly set.
        form : Union[Dict[str, Union[bool, float, str]], None]
            Provides an object that will be serialized as html form using `application/x-www-form-urlencoded` encoding and sent
            as this request body. If this parameter is specified `content-type` header will be set to
            `application/x-www-form-urlencoded` unless explicitly provided.
        multipart : Union[Dict[str, Union[bool, bytes, float, str, {name: str, mimeType: str, buffer: bytes}]], None]
            Provides an object that will be serialized as html form using `multipart/form-data` encoding and sent as this
            request body. If this parameter is specified `content-type` header will be set to `multipart/form-data` unless
            explicitly provided. File values can be passed as file-like object containing file name, mime-type and its content.
        timeout : Union[float, None]
            Request timeout in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout.
        fail_on_status_code : Union[bool, None]
            Whether to throw on response codes other than 2xx and 3xx. By default response object is returned for all status
            codes.
        ignore_https_errors : Union[bool, None]
            Whether to ignore HTTPS errors when sending network requests. Defaults to `false`.
        max_redirects : Union[int, None]
            Maximum number of request redirects that will be followed automatically. An error will be thrown if the number is
            exceeded. Defaults to `20`. Pass `0` to not follow redirects.
        max_retries : Union[int, None]
            Maximum number of times network errors should be retried. Currently only `ECONNRESET` error is retried. Does not
            retry based on HTTP response codes. An error will be thrown if the limit is exceeded. Defaults to `0` - no retries.

        Returns
        -------
        APIResponse
        """

        return mapping.from_impl(
            await self._impl_obj.delete(
                url=url,
                params=mapping.to_impl(params),
                headers=mapping.to_impl(headers),
                data=mapping.to_impl(data),
                form=mapping.to_impl(form),
                multipart=mapping.to_impl(multipart),
                timeout=timeout,
                failOnStatusCode=fail_on_status_code,
                ignoreHTTPSErrors=ignore_https_errors,
                maxRedirects=max_redirects,
                maxRetries=max_retries,
            )
        )

    async def head(
        self,
        url: str,
        *,
        params: typing.Optional[
            typing.Union[typing.Dict[str, typing.Union[str, float, bool]], str]
        ] = None,
        headers: typing.Optional[typing.Dict[str, str]] = None,
        data: typing.Optional[typing.Union[typing.Any, str, bytes]] = None,
        form: typing.Optional[typing.Dict[str, typing.Union[str, float, bool]]] = None,
        multipart: typing.Optional[
            typing.Dict[str, typing.Union[bytes, bool, float, str, FilePayload]]
        ] = None,
        timeout: typing.Optional[float] = None,
        fail_on_status_code: typing.Optional[bool] = None,
        ignore_https_errors: typing.Optional[bool] = None,
        max_redirects: typing.Optional[int] = None,
        max_retries: typing.Optional[int] = None,
    ) -> "APIResponse":
        """APIRequestContext.head

        Sends HTTP(S) [HEAD](https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods/HEAD) request and returns its
        response. The method will populate request cookies from the context and update context cookies from the response.
        The method will automatically follow redirects.

        Parameters
        ----------
        url : str
            Target URL.
        params : Union[Dict[str, Union[bool, float, str]], str, None]
            Query parameters to be sent with the URL.
        headers : Union[Dict[str, str], None]
            Allows to set HTTP headers. These headers will apply to the fetched request as well as any redirects initiated by
            it.
        data : Union[Any, bytes, str, None]
            Allows to set post data of the request. If the data parameter is an object, it will be serialized to json string
            and `content-type` header will be set to `application/json` if not explicitly set. Otherwise the `content-type`
            header will be set to `application/octet-stream` if not explicitly set.
        form : Union[Dict[str, Union[bool, float, str]], None]
            Provides an object that will be serialized as html form using `application/x-www-form-urlencoded` encoding and sent
            as this request body. If this parameter is specified `content-type` header will be set to
            `application/x-www-form-urlencoded` unless explicitly provided.
        multipart : Union[Dict[str, Union[bool, bytes, float, str, {name: str, mimeType: str, buffer: bytes}]], None]
            Provides an object that will be serialized as html form using `multipart/form-data` encoding and sent as this
            request body. If this parameter is specified `content-type` header will be set to `multipart/form-data` unless
            explicitly provided. File values can be passed as file-like object containing file name, mime-type and its content.
        timeout : Union[float, None]
            Request timeout in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout.
        fail_on_status_code : Union[bool, None]
            Whether to throw on response codes other than 2xx and 3xx. By default response object is returned for all status
            codes.
        ignore_https_errors : Union[bool, None]
            Whether to ignore HTTPS errors when sending network requests. Defaults to `false`.
        max_redirects : Union[int, None]
            Maximum number of request redirects that will be followed automatically. An error will be thrown if the number is
            exceeded. Defaults to `20`. Pass `0` to not follow redirects.
        max_retries : Union[int, None]
            Maximum number of times network errors should be retried. Currently only `ECONNRESET` error is retried. Does not
            retry based on HTTP response codes. An error will be thrown if the limit is exceeded. Defaults to `0` - no retries.

        Returns
        -------
        APIResponse
        """

        return mapping.from_impl(
            await self._impl_obj.head(
                url=url,
                params=mapping.to_impl(params),
                headers=mapping.to_impl(headers),
                data=mapping.to_impl(data),
                form=mapping.to_impl(form),
                multipart=mapping.to_impl(multipart),
                timeout=timeout,
                failOnStatusCode=fail_on_status_code,
                ignoreHTTPSErrors=ignore_https_errors,
                maxRedirects=max_redirects,
                maxRetries=max_retries,
            )
        )

    async def get(
        self,
        url: str,
        *,
        params: typing.Optional[
            typing.Union[typing.Dict[str, typing.Union[str, float, bool]], str]
        ] = None,
        headers: typing.Optional[typing.Dict[str, str]] = None,
        data: typing.Optional[typing.Union[typing.Any, str, bytes]] = None,
        form: typing.Optional[typing.Dict[str, typing.Union[str, float, bool]]] = None,
        multipart: typing.Optional[
            typing.Dict[str, typing.Union[bytes, bool, float, str, FilePayload]]
        ] = None,
        timeout: typing.Optional[float] = None,
        fail_on_status_code: typing.Optional[bool] = None,
        ignore_https_errors: typing.Optional[bool] = None,
        max_redirects: typing.Optional[int] = None,
        max_retries: typing.Optional[int] = None,
    ) -> "APIResponse":
        """APIRequestContext.get

        Sends HTTP(S) [GET](https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods/GET) request and returns its
        response. The method will populate request cookies from the context and update context cookies from the response.
        The method will automatically follow redirects.

        **Usage**

        Request parameters can be configured with `params` option, they will be serialized into the URL search parameters:

        ```python
        query_params = {
          \"isbn\": \"1234\",
          \"page\": \"23\"
        }
        api_request_context.get(\"https://example.com/api/getText\", params=query_params)
        ```

        Parameters
        ----------
        url : str
            Target URL.
        params : Union[Dict[str, Union[bool, float, str]], str, None]
            Query parameters to be sent with the URL.
        headers : Union[Dict[str, str], None]
            Allows to set HTTP headers. These headers will apply to the fetched request as well as any redirects initiated by
            it.
        data : Union[Any, bytes, str, None]
            Allows to set post data of the request. If the data parameter is an object, it will be serialized to json string
            and `content-type` header will be set to `application/json` if not explicitly set. Otherwise the `content-type`
            header will be set to `application/octet-stream` if not explicitly set.
        form : Union[Dict[str, Union[bool, float, str]], None]
            Provides an object that will be serialized as html form using `application/x-www-form-urlencoded` encoding and sent
            as this request body. If this parameter is specified `content-type` header will be set to
            `application/x-www-form-urlencoded` unless explicitly provided.
        multipart : Union[Dict[str, Union[bool, bytes, float, str, {name: str, mimeType: str, buffer: bytes}]], None]
            Provides an object that will be serialized as html form using `multipart/form-data` encoding and sent as this
            request body. If this parameter is specified `content-type` header will be set to `multipart/form-data` unless
            explicitly provided. File values can be passed as file-like object containing file name, mime-type and its content.
        timeout : Union[float, None]
            Request timeout in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout.
        fail_on_status_code : Union[bool, None]
            Whether to throw on response codes other than 2xx and 3xx. By default response object is returned for all status
            codes.
        ignore_https_errors : Union[bool, None]
            Whether to ignore HTTPS errors when sending network requests. Defaults to `false`.
        max_redirects : Union[int, None]
            Maximum number of request redirects that will be followed automatically. An error will be thrown if the number is
            exceeded. Defaults to `20`. Pass `0` to not follow redirects.
        max_retries : Union[int, None]
            Maximum number of times network errors should be retried. Currently only `ECONNRESET` error is retried. Does not
            retry based on HTTP response codes. An error will be thrown if the limit is exceeded. Defaults to `0` - no retries.

        Returns
        -------
        APIResponse
        """

        return mapping.from_impl(
            await self._impl_obj.get(
                url=url,
                params=mapping.to_impl(params),
                headers=mapping.to_impl(headers),
                data=mapping.to_impl(data),
                form=mapping.to_impl(form),
                multipart=mapping.to_impl(multipart),
                timeout=timeout,
                failOnStatusCode=fail_on_status_code,
                ignoreHTTPSErrors=ignore_https_errors,
                maxRedirects=max_redirects,
                maxRetries=max_retries,
            )
        )

    async def patch(
        self,
        url: str,
        *,
        params: typing.Optional[
            typing.Union[typing.Dict[str, typing.Union[str, float, bool]], str]
        ] = None,
        headers: typing.Optional[typing.Dict[str, str]] = None,
        data: typing.Optional[typing.Union[typing.Any, str, bytes]] = None,
        form: typing.Optional[typing.Dict[str, typing.Union[str, float, bool]]] = None,
        multipart: typing.Optional[
            typing.Dict[str, typing.Union[bytes, bool, float, str, FilePayload]]
        ] = None,
        timeout: typing.Optional[float] = None,
        fail_on_status_code: typing.Optional[bool] = None,
        ignore_https_errors: typing.Optional[bool] = None,
        max_redirects: typing.Optional[int] = None,
        max_retries: typing.Optional[int] = None,
    ) -> "APIResponse":
        """APIRequestContext.patch

        Sends HTTP(S) [PATCH](https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods/PATCH) request and returns its
        response. The method will populate request cookies from the context and update context cookies from the response.
        The method will automatically follow redirects.

        Parameters
        ----------
        url : str
            Target URL.
        params : Union[Dict[str, Union[bool, float, str]], str, None]
            Query parameters to be sent with the URL.
        headers : Union[Dict[str, str], None]
            Allows to set HTTP headers. These headers will apply to the fetched request as well as any redirects initiated by
            it.
        data : Union[Any, bytes, str, None]
            Allows to set post data of the request. If the data parameter is an object, it will be serialized to json string
            and `content-type` header will be set to `application/json` if not explicitly set. Otherwise the `content-type`
            header will be set to `application/octet-stream` if not explicitly set.
        form : Union[Dict[str, Union[bool, float, str]], None]
            Provides an object that will be serialized as html form using `application/x-www-form-urlencoded` encoding and sent
            as this request body. If this parameter is specified `content-type` header will be set to
            `application/x-www-form-urlencoded` unless explicitly provided.
        multipart : Union[Dict[str, Union[bool, bytes, float, str, {name: str, mimeType: str, buffer: bytes}]], None]
            Provides an object that will be serialized as html form using `multipart/form-data` encoding and sent as this
            request body. If this parameter is specified `content-type` header will be set to `multipart/form-data` unless
            explicitly provided. File values can be passed as file-like object containing file name, mime-type and its content.
        timeout : Union[float, None]
            Request timeout in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout.
        fail_on_status_code : Union[bool, None]
            Whether to throw on response codes other than 2xx and 3xx. By default response object is returned for all status
            codes.
        ignore_https_errors : Union[bool, None]
            Whether to ignore HTTPS errors when sending network requests. Defaults to `false`.
        max_redirects : Union[int, None]
            Maximum number of request redirects that will be followed automatically. An error will be thrown if the number is
            exceeded. Defaults to `20`. Pass `0` to not follow redirects.
        max_retries : Union[int, None]
            Maximum number of times network errors should be retried. Currently only `ECONNRESET` error is retried. Does not
            retry based on HTTP response codes. An error will be thrown if the limit is exceeded. Defaults to `0` - no retries.

        Returns
        -------
        APIResponse
        """

        return mapping.from_impl(
            await self._impl_obj.patch(
                url=url,
                params=mapping.to_impl(params),
                headers=mapping.to_impl(headers),
                data=mapping.to_impl(data),
                form=mapping.to_impl(form),
                multipart=mapping.to_impl(multipart),
                timeout=timeout,
                failOnStatusCode=fail_on_status_code,
                ignoreHTTPSErrors=ignore_https_errors,
                maxRedirects=max_redirects,
                maxRetries=max_retries,
            )
        )

    async def put(
        self,
        url: str,
        *,
        params: typing.Optional[
            typing.Union[typing.Dict[str, typing.Union[str, float, bool]], str]
        ] = None,
        headers: typing.Optional[typing.Dict[str, str]] = None,
        data: typing.Optional[typing.Union[typing.Any, str, bytes]] = None,
        form: typing.Optional[typing.Dict[str, typing.Union[str, float, bool]]] = None,
        multipart: typing.Optional[
            typing.Dict[str, typing.Union[bytes, bool, float, str, FilePayload]]
        ] = None,
        timeout: typing.Optional[float] = None,
        fail_on_status_code: typing.Optional[bool] = None,
        ignore_https_errors: typing.Optional[bool] = None,
        max_redirects: typing.Optional[int] = None,
        max_retries: typing.Optional[int] = None,
    ) -> "APIResponse":
        """APIRequestContext.put

        Sends HTTP(S) [PUT](https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods/PUT) request and returns its
        response. The method will populate request cookies from the context and update context cookies from the response.
        The method will automatically follow redirects.

        Parameters
        ----------
        url : str
            Target URL.
        params : Union[Dict[str, Union[bool, float, str]], str, None]
            Query parameters to be sent with the URL.
        headers : Union[Dict[str, str], None]
            Allows to set HTTP headers. These headers will apply to the fetched request as well as any redirects initiated by
            it.
        data : Union[Any, bytes, str, None]
            Allows to set post data of the request. If the data parameter is an object, it will be serialized to json string
            and `content-type` header will be set to `application/json` if not explicitly set. Otherwise the `content-type`
            header will be set to `application/octet-stream` if not explicitly set.
        form : Union[Dict[str, Union[bool, float, str]], None]
            Provides an object that will be serialized as html form using `application/x-www-form-urlencoded` encoding and sent
            as this request body. If this parameter is specified `content-type` header will be set to
            `application/x-www-form-urlencoded` unless explicitly provided.
        multipart : Union[Dict[str, Union[bool, bytes, float, str, {name: str, mimeType: str, buffer: bytes}]], None]
            Provides an object that will be serialized as html form using `multipart/form-data` encoding and sent as this
            request body. If this parameter is specified `content-type` header will be set to `multipart/form-data` unless
            explicitly provided. File values can be passed as file-like object containing file name, mime-type and its content.
        timeout : Union[float, None]
            Request timeout in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout.
        fail_on_status_code : Union[bool, None]
            Whether to throw on response codes other than 2xx and 3xx. By default response object is returned for all status
            codes.
        ignore_https_errors : Union[bool, None]
            Whether to ignore HTTPS errors when sending network requests. Defaults to `false`.
        max_redirects : Union[int, None]
            Maximum number of request redirects that will be followed automatically. An error will be thrown if the number is
            exceeded. Defaults to `20`. Pass `0` to not follow redirects.
        max_retries : Union[int, None]
            Maximum number of times network errors should be retried. Currently only `ECONNRESET` error is retried. Does not
            retry based on HTTP response codes. An error will be thrown if the limit is exceeded. Defaults to `0` - no retries.

        Returns
        -------
        APIResponse
        """

        return mapping.from_impl(
            await self._impl_obj.put(
                url=url,
                params=mapping.to_impl(params),
                headers=mapping.to_impl(headers),
                data=mapping.to_impl(data),
                form=mapping.to_impl(form),
                multipart=mapping.to_impl(multipart),
                timeout=timeout,
                failOnStatusCode=fail_on_status_code,
                ignoreHTTPSErrors=ignore_https_errors,
                maxRedirects=max_redirects,
                maxRetries=max_retries,
            )
        )

    async def post(
        self,
        url: str,
        *,
        params: typing.Optional[
            typing.Union[typing.Dict[str, typing.Union[str, float, bool]], str]
        ] = None,
        headers: typing.Optional[typing.Dict[str, str]] = None,
        data: typing.Optional[typing.Union[typing.Any, str, bytes]] = None,
        form: typing.Optional[typing.Dict[str, typing.Union[str, float, bool]]] = None,
        multipart: typing.Optional[
            typing.Dict[str, typing.Union[bytes, bool, float, str, FilePayload]]
        ] = None,
        timeout: typing.Optional[float] = None,
        fail_on_status_code: typing.Optional[bool] = None,
        ignore_https_errors: typing.Optional[bool] = None,
        max_redirects: typing.Optional[int] = None,
        max_retries: typing.Optional[int] = None,
    ) -> "APIResponse":
        """APIRequestContext.post

        Sends HTTP(S) [POST](https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods/POST) request and returns its
        response. The method will populate request cookies from the context and update context cookies from the response.
        The method will automatically follow redirects.

        **Usage**

        JSON objects can be passed directly to the request:

        ```python
        data = {
            \"title\": \"Book Title\",
            \"body\": \"John Doe\",
        }
        api_request_context.post(\"https://example.com/api/createBook\", data=data)
        ```

        To send form data to the server use `form` option. Its value will be encoded into the request body with
        `application/x-www-form-urlencoded` encoding (see below how to use `multipart/form-data` form encoding to send
        files):

        The common way to send file(s) in the body of a request is to upload them as form fields with `multipart/form-data`
        encoding. Use `FormData` to construct request body and pass it to the request as `multipart` parameter:

        ```python
        api_request_context.post(
          \"https://example.com/api/uploadScript'\",
          multipart={
            \"fileField\": {
              \"name\": \"f.js\",
              \"mimeType\": \"text/javascript\",
              \"buffer\": b\"console.log(2022);\",
            },
          })
        ```

        Parameters
        ----------
        url : str
            Target URL.
        params : Union[Dict[str, Union[bool, float, str]], str, None]
            Query parameters to be sent with the URL.
        headers : Union[Dict[str, str], None]
            Allows to set HTTP headers. These headers will apply to the fetched request as well as any redirects initiated by
            it.
        data : Union[Any, bytes, str, None]
            Allows to set post data of the request. If the data parameter is an object, it will be serialized to json string
            and `content-type` header will be set to `application/json` if not explicitly set. Otherwise the `content-type`
            header will be set to `application/octet-stream` if not explicitly set.
        form : Union[Dict[str, Union[bool, float, str]], None]
            Provides an object that will be serialized as html form using `application/x-www-form-urlencoded` encoding and sent
            as this request body. If this parameter is specified `content-type` header will be set to
            `application/x-www-form-urlencoded` unless explicitly provided.
        multipart : Union[Dict[str, Union[bool, bytes, float, str, {name: str, mimeType: str, buffer: bytes}]], None]
            Provides an object that will be serialized as html form using `multipart/form-data` encoding and sent as this
            request body. If this parameter is specified `content-type` header will be set to `multipart/form-data` unless
            explicitly provided. File values can be passed as file-like object containing file name, mime-type and its content.
        timeout : Union[float, None]
            Request timeout in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout.
        fail_on_status_code : Union[bool, None]
            Whether to throw on response codes other than 2xx and 3xx. By default response object is returned for all status
            codes.
        ignore_https_errors : Union[bool, None]
            Whether to ignore HTTPS errors when sending network requests. Defaults to `false`.
        max_redirects : Union[int, None]
            Maximum number of request redirects that will be followed automatically. An error will be thrown if the number is
            exceeded. Defaults to `20`. Pass `0` to not follow redirects.
        max_retries : Union[int, None]
            Maximum number of times network errors should be retried. Currently only `ECONNRESET` error is retried. Does not
            retry based on HTTP response codes. An error will be thrown if the limit is exceeded. Defaults to `0` - no retries.

        Returns
        -------
        APIResponse
        """

        return mapping.from_impl(
            await self._impl_obj.post(
                url=url,
                params=mapping.to_impl(params),
                headers=mapping.to_impl(headers),
                data=mapping.to_impl(data),
                form=mapping.to_impl(form),
                multipart=mapping.to_impl(multipart),
                timeout=timeout,
                failOnStatusCode=fail_on_status_code,
                ignoreHTTPSErrors=ignore_https_errors,
                maxRedirects=max_redirects,
                maxRetries=max_retries,
            )
        )

    async def fetch(
        self,
        url_or_request: typing.Union[str, "Request"],
        *,
        params: typing.Optional[
            typing.Union[typing.Dict[str, typing.Union[str, float, bool]], str]
        ] = None,
        method: typing.Optional[str] = None,
        headers: typing.Optional[typing.Dict[str, str]] = None,
        data: typing.Optional[typing.Union[typing.Any, str, bytes]] = None,
        form: typing.Optional[typing.Dict[str, typing.Union[str, float, bool]]] = None,
        multipart: typing.Optional[
            typing.Dict[str, typing.Union[bytes, bool, float, str, FilePayload]]
        ] = None,
        timeout: typing.Optional[float] = None,
        fail_on_status_code: typing.Optional[bool] = None,
        ignore_https_errors: typing.Optional[bool] = None,
        max_redirects: typing.Optional[int] = None,
        max_retries: typing.Optional[int] = None,
    ) -> "APIResponse":
        """APIRequestContext.fetch

        Sends HTTP(S) request and returns its response. The method will populate request cookies from the context and
        update context cookies from the response. The method will automatically follow redirects.

        **Usage**

        JSON objects can be passed directly to the request:

        ```python
        data = {
            \"title\": \"Book Title\",
            \"body\": \"John Doe\",
        }
        api_request_context.fetch(\"https://example.com/api/createBook\", method=\"post\", data=data)
        ```

        The common way to send file(s) in the body of a request is to upload them as form fields with `multipart/form-data`
        encoding, by specifiying the `multipart` parameter:

        Parameters
        ----------
        url_or_request : Union[Request, str]
            Target URL or Request to get all parameters from.
        params : Union[Dict[str, Union[bool, float, str]], str, None]
            Query parameters to be sent with the URL.
        method : Union[str, None]
            If set changes the fetch method (e.g. [PUT](https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods/PUT) or
            [POST](https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods/POST)). If not specified, GET method is used.
        headers : Union[Dict[str, str], None]
            Allows to set HTTP headers. These headers will apply to the fetched request as well as any redirects initiated by
            it.
        data : Union[Any, bytes, str, None]
            Allows to set post data of the request. If the data parameter is an object, it will be serialized to json string
            and `content-type` header will be set to `application/json` if not explicitly set. Otherwise the `content-type`
            header will be set to `application/octet-stream` if not explicitly set.
        form : Union[Dict[str, Union[bool, float, str]], None]
            Provides an object that will be serialized as html form using `application/x-www-form-urlencoded` encoding and sent
            as this request body. If this parameter is specified `content-type` header will be set to
            `application/x-www-form-urlencoded` unless explicitly provided.
        multipart : Union[Dict[str, Union[bool, bytes, float, str, {name: str, mimeType: str, buffer: bytes}]], None]
            Provides an object that will be serialized as html form using `multipart/form-data` encoding and sent as this
            request body. If this parameter is specified `content-type` header will be set to `multipart/form-data` unless
            explicitly provided. File values can be passed as file-like object containing file name, mime-type and its content.
        timeout : Union[float, None]
            Request timeout in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout.
        fail_on_status_code : Union[bool, None]
            Whether to throw on response codes other than 2xx and 3xx. By default response object is returned for all status
            codes.
        ignore_https_errors : Union[bool, None]
            Whether to ignore HTTPS errors when sending network requests. Defaults to `false`.
        max_redirects : Union[int, None]
            Maximum number of request redirects that will be followed automatically. An error will be thrown if the number is
            exceeded. Defaults to `20`. Pass `0` to not follow redirects.
        max_retries : Union[int, None]
            Maximum number of times network errors should be retried. Currently only `ECONNRESET` error is retried. Does not
            retry based on HTTP response codes. An error will be thrown if the limit is exceeded. Defaults to `0` - no retries.

        Returns
        -------
        APIResponse
        """

        return mapping.from_impl(
            await self._impl_obj.fetch(
                urlOrRequest=url_or_request,
                params=mapping.to_impl(params),
                method=method,
                headers=mapping.to_impl(headers),
                data=mapping.to_impl(data),
                form=mapping.to_impl(form),
                multipart=mapping.to_impl(multipart),
                timeout=timeout,
                failOnStatusCode=fail_on_status_code,
                ignoreHTTPSErrors=ignore_https_errors,
                maxRedirects=max_redirects,
                maxRetries=max_retries,
            )
        )

    async def storage_state(
        self,
        *,
        path: typing.Optional[typing.Union[pathlib.Path, str]] = None,
        indexed_db: typing.Optional[bool] = None,
    ) -> StorageState:
        """APIRequestContext.storage_state

        Returns storage state for this request context, contains current cookies and local storage snapshot if it was
        passed to the constructor.

        Parameters
        ----------
        path : Union[pathlib.Path, str, None]
            The file path to save the storage state to. If `path` is a relative path, then it is resolved relative to current
            working directory. If no path is provided, storage state is still returned, but won't be saved to the disk.
        indexed_db : Union[bool, None]
            Set to `true` to include IndexedDB in the storage state snapshot.

        Returns
        -------
        {cookies: List[{name: str, value: str, domain: str, path: str, expires: float, httpOnly: bool, secure: bool, sameSite: Union["Lax", "None", "Strict"]}], origins: List[{origin: str, localStorage: List[{name: str, value: str}]}]}
        """

        return mapping.from_impl(
            await self._impl_obj.storage_state(path=path, indexedDB=indexed_db)
        )


mapping.register(APIRequestContextImpl, APIRequestContext)


class APIRequest(AsyncBase):

    async def new_context(
        self,
        *,
        base_url: typing.Optional[str] = None,
        extra_http_headers: typing.Optional[typing.Dict[str, str]] = None,
        http_credentials: typing.Optional[HttpCredentials] = None,
        ignore_https_errors: typing.Optional[bool] = None,
        proxy: typing.Optional[ProxySettings] = None,
        user_agent: typing.Optional[str] = None,
        timeout: typing.Optional[float] = None,
        storage_state: typing.Optional[
            typing.Union[StorageState, str, pathlib.Path]
        ] = None,
        client_certificates: typing.Optional[typing.List[ClientCertificate]] = None,
        fail_on_status_code: typing.Optional[bool] = None,
        max_redirects: typing.Optional[int] = None,
    ) -> "APIRequestContext":
        """APIRequest.new_context

        Creates new instances of `APIRequestContext`.

        Parameters
        ----------
        base_url : Union[str, None]
            Methods like `a_pi_request_context.get()` take the base URL into consideration by using the
            [`URL()`](https://developer.mozilla.org/en-US/docs/Web/API/URL/URL) constructor for building the corresponding URL.
            Examples:
            - baseURL: `http://localhost:3000` and sending request to `/bar.html` results in `http://localhost:3000/bar.html`
            - baseURL: `http://localhost:3000/foo/` and sending request to `./bar.html` results in
              `http://localhost:3000/foo/bar.html`
            - baseURL: `http://localhost:3000/foo` (without trailing slash) and navigating to `./bar.html` results in
              `http://localhost:3000/bar.html`
        extra_http_headers : Union[Dict[str, str], None]
            An object containing additional HTTP headers to be sent with every request. Defaults to none.
        http_credentials : Union[{username: str, password: str, origin: Union[str, None], send: Union["always", "unauthorized", None]}, None]
            Credentials for [HTTP authentication](https://developer.mozilla.org/en-US/docs/Web/HTTP/Authentication). If no
            origin is specified, the username and password are sent to any servers upon unauthorized responses.
        ignore_https_errors : Union[bool, None]
            Whether to ignore HTTPS errors when sending network requests. Defaults to `false`.
        proxy : Union[{server: str, bypass: Union[str, None], username: Union[str, None], password: Union[str, None]}, None]
            Network proxy settings.
        user_agent : Union[str, None]
            Specific user agent to use in this context.
        timeout : Union[float, None]
            Maximum time in milliseconds to wait for the response. Defaults to `30000` (30 seconds). Pass `0` to disable
            timeout.
        storage_state : Union[pathlib.Path, str, {cookies: Sequence[{name: str, value: str, domain: str, path: str, expires: float, httpOnly: bool, secure: bool, sameSite: Union["Lax", "None", "Strict"]}], origins: Sequence[{origin: str, localStorage: Sequence[{name: str, value: str}]}]}, None]
            Populates context with given storage state. This option can be used to initialize context with logged-in
            information obtained via `browser_context.storage_state()` or `a_pi_request_context.storage_state()`.
            Either a path to the file with saved storage, or the value returned by one of
            `browser_context.storage_state()` or `a_pi_request_context.storage_state()` methods.
        client_certificates : Union[Sequence[{origin: str, certPath: Union[pathlib.Path, str, None], cert: Union[bytes, None], keyPath: Union[pathlib.Path, str, None], key: Union[bytes, None], pfxPath: Union[pathlib.Path, str, None], pfx: Union[bytes, None], passphrase: Union[str, None]}], None]
            TLS Client Authentication allows the server to request a client certificate and verify it.

            **Details**

            An array of client certificates to be used. Each certificate object must have either both `certPath` and `keyPath`,
            a single `pfxPath`, or their corresponding direct value equivalents (`cert` and `key`, or `pfx`). Optionally,
            `passphrase` property should be provided if the certificate is encrypted. The `origin` property should be provided
            with an exact match to the request origin that the certificate is valid for.

            Client certificate authentication is only active when at least one client certificate is provided. If you want to
            reject all client certificates sent by the server, you need to provide a client certificate with an `origin` that
            does not match any of the domains you plan to visit.

            **NOTE** When using WebKit on macOS, accessing `localhost` will not pick up client certificates. You can make it
            work by replacing `localhost` with `local.playwright`.

        fail_on_status_code : Union[bool, None]
            Whether to throw on response codes other than 2xx and 3xx. By default response object is returned for all status
            codes.
        max_redirects : Union[int, None]
            Maximum number of request redirects that will be followed automatically. An error will be thrown if the number is
            exceeded. Defaults to `20`. Pass `0` to not follow redirects. This can be overwritten for each request
            individually.

        Returns
        -------
        APIRequestContext
        """

        return mapping.from_impl(
            await self._impl_obj.new_context(
                baseURL=base_url,
                extraHTTPHeaders=mapping.to_impl(extra_http_headers),
                httpCredentials=http_credentials,
                ignoreHTTPSErrors=ignore_https_errors,
                proxy=proxy,
                userAgent=user_agent,
                timeout=timeout,
                storageState=storage_state,
                clientCertificates=client_certificates,
                failOnStatusCode=fail_on_status_code,
                maxRedirects=max_redirects,
            )
        )


mapping.register(APIRequestImpl, APIRequest)


class PageAssertions(AsyncBase):

    async def to_have_title(
        self,
        title_or_reg_exp: typing.Union[typing.Pattern[str], str],
        *,
        timeout: typing.Optional[float] = None,
    ) -> None:
        """PageAssertions.to_have_title

        Ensures the page has the given title.

        **Usage**

        ```py
        import re
        from playwright.async_api import expect

        # ...
        await expect(page).to_have_title(re.compile(r\".*checkout\"))
        ```

        Parameters
        ----------
        title_or_reg_exp : Union[Pattern[str], str]
            Expected title or RegExp.
        timeout : Union[float, None]
            Time to retry the assertion for in milliseconds. Defaults to `5000`.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            await self._impl_obj.to_have_title(
                titleOrRegExp=title_or_reg_exp, timeout=timeout
            )
        )

    async def not_to_have_title(
        self,
        title_or_reg_exp: typing.Union[typing.Pattern[str], str],
        *,
        timeout: typing.Optional[float] = None,
    ) -> None:
        """PageAssertions.not_to_have_title

        The opposite of `page_assertions.to_have_title()`.

        Parameters
        ----------
        title_or_reg_exp : Union[Pattern[str], str]
            Expected title or RegExp.
        timeout : Union[float, None]
            Time to retry the assertion for in milliseconds. Defaults to `5000`.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            await self._impl_obj.not_to_have_title(
                titleOrRegExp=title_or_reg_exp, timeout=timeout
            )
        )

    async def to_have_url(
        self,
        url_or_reg_exp: typing.Union[str, typing.Pattern[str]],
        *,
        timeout: typing.Optional[float] = None,
        ignore_case: typing.Optional[bool] = None,
    ) -> None:
        """PageAssertions.to_have_url

        Ensures the page is navigated to the given URL.

        **Usage**

        ```py
        import re
        from playwright.async_api import expect

        # ...
        await expect(page).to_have_url(re.compile(\".*checkout\"))
        ```

        Parameters
        ----------
        url_or_reg_exp : Union[Pattern[str], str]
            Expected URL string or RegExp.
        timeout : Union[float, None]
            Time to retry the assertion for in milliseconds. Defaults to `5000`.
        ignore_case : Union[bool, None]
            Whether to perform case-insensitive match. `ignoreCase` option takes precedence over the corresponding regular
            expression parameter if specified. A provided predicate ignores this flag.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            await self._impl_obj.to_have_url(
                urlOrRegExp=url_or_reg_exp, timeout=timeout, ignoreCase=ignore_case
            )
        )

    async def not_to_have_url(
        self,
        url_or_reg_exp: typing.Union[typing.Pattern[str], str],
        *,
        timeout: typing.Optional[float] = None,
        ignore_case: typing.Optional[bool] = None,
    ) -> None:
        """PageAssertions.not_to_have_url

        The opposite of `page_assertions.to_have_url()`.

        Parameters
        ----------
        url_or_reg_exp : Union[Pattern[str], str]
            Expected URL string or RegExp.
        timeout : Union[float, None]
            Time to retry the assertion for in milliseconds. Defaults to `5000`.
        ignore_case : Union[bool, None]
            Whether to perform case-insensitive match. `ignoreCase` option takes precedence over the corresponding regular
            expression flag if specified.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            await self._impl_obj.not_to_have_url(
                urlOrRegExp=url_or_reg_exp, timeout=timeout, ignoreCase=ignore_case
            )
        )


mapping.register(PageAssertionsImpl, PageAssertions)


class LocatorAssertions(AsyncBase):

    async def to_contain_text(
        self,
        expected: typing.Union[
            typing.Sequence[str],
            typing.Sequence[typing.Pattern[str]],
            typing.Sequence[typing.Union[typing.Pattern[str], str]],
            typing.Pattern[str],
            str,
        ],
        *,
        use_inner_text: typing.Optional[bool] = None,
        timeout: typing.Optional[float] = None,
        ignore_case: typing.Optional[bool] = None,
    ) -> None:
        """LocatorAssertions.to_contain_text

        Ensures the `Locator` points to an element that contains the given text. All nested elements will be considered
        when computing the text content of the element. You can use regular expressions for the value as well.

        **Details**

        When `expected` parameter is a string, Playwright will normalize whitespaces and line breaks both in the actual
        text and in the expected string before matching. When regular expression is used, the actual text is matched as is.

        **Usage**

        ```py
        import re
        from playwright.async_api import expect

        locator = page.locator('.title')
        await expect(locator).to_contain_text(\"substring\")
        await expect(locator).to_contain_text(re.compile(r\"\\d messages\"))
        ```

        If you pass an array as an expected value, the expectations are:
        1. Locator resolves to a list of elements.
        1. Elements from a **subset** of this list contain text from the expected array, respectively.
        1. The matching subset of elements has the same order as the expected array.
        1. Each text value from the expected array is matched by some element from the list.

        For example, consider the following list:

        ```html
        <ul>
          <li>Item Text 1</li>
          <li>Item Text 2</li>
          <li>Item Text 3</li>
        </ul>
        ```

        Let's see how we can use the assertion:

        ```py
        from playwright.async_api import expect

        # ✓ Contains the right items in the right order
        await expect(page.locator(\"ul > li\")).to_contain_text([\"Text 1\", \"Text 3\"])

        # ✖ Wrong order
        await expect(page.locator(\"ul > li\")).to_contain_text([\"Text 3\", \"Text 2\"])

        # ✖ No item contains this text
        await expect(page.locator(\"ul > li\")).to_contain_text([\"Some 33\"])

        # ✖ Locator points to the outer list element, not to the list items
        await expect(page.locator(\"ul\")).to_contain_text([\"Text 3\"])
        ```

        Parameters
        ----------
        expected : Union[Pattern[str], Sequence[Pattern[str]], Sequence[Union[Pattern[str], str]], Sequence[str], str]
            Expected substring or RegExp or a list of those.
        use_inner_text : Union[bool, None]
            Whether to use `element.innerText` instead of `element.textContent` when retrieving DOM node text.
        timeout : Union[float, None]
            Time to retry the assertion for in milliseconds. Defaults to `5000`.
        ignore_case : Union[bool, None]
            Whether to perform case-insensitive match. `ignoreCase` option takes precedence over the corresponding regular
            expression flag if specified.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            await self._impl_obj.to_contain_text(
                expected=mapping.to_impl(expected),
                useInnerText=use_inner_text,
                timeout=timeout,
                ignoreCase=ignore_case,
            )
        )

    async def not_to_contain_text(
        self,
        expected: typing.Union[
            typing.Sequence[str],
            typing.Sequence[typing.Pattern[str]],
            typing.Sequence[typing.Union[typing.Pattern[str], str]],
            typing.Pattern[str],
            str,
        ],
        *,
        use_inner_text: typing.Optional[bool] = None,
        timeout: typing.Optional[float] = None,
        ignore_case: typing.Optional[bool] = None,
    ) -> None:
        """LocatorAssertions.not_to_contain_text

        The opposite of `locator_assertions.to_contain_text()`.

        Parameters
        ----------
        expected : Union[Pattern[str], Sequence[Pattern[str]], Sequence[Union[Pattern[str], str]], Sequence[str], str]
            Expected substring or RegExp or a list of those.
        use_inner_text : Union[bool, None]
            Whether to use `element.innerText` instead of `element.textContent` when retrieving DOM node text.
        timeout : Union[float, None]
            Time to retry the assertion for in milliseconds. Defaults to `5000`.
        ignore_case : Union[bool, None]
            Whether to perform case-insensitive match. `ignoreCase` option takes precedence over the corresponding regular
            expression flag if specified.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            await self._impl_obj.not_to_contain_text(
                expected=mapping.to_impl(expected),
                useInnerText=use_inner_text,
                timeout=timeout,
                ignoreCase=ignore_case,
            )
        )

    async def to_have_attribute(
        self,
        name: str,
        value: typing.Union[str, typing.Pattern[str]],
        *,
        ignore_case: typing.Optional[bool] = None,
        timeout: typing.Optional[float] = None,
    ) -> None:
        """LocatorAssertions.to_have_attribute

        Ensures the `Locator` points to an element with given attribute.

        **Usage**

        ```py
        from playwright.async_api import expect

        locator = page.locator(\"input\")
        await expect(locator).to_have_attribute(\"type\", \"text\")
        ```

        Parameters
        ----------
        name : str
            Attribute name.
        value : Union[Pattern[str], str]
            Expected attribute value.
        ignore_case : Union[bool, None]
            Whether to perform case-insensitive match. `ignoreCase` option takes precedence over the corresponding regular
            expression flag if specified.
        timeout : Union[float, None]
            Time to retry the assertion for in milliseconds. Defaults to `5000`.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            await self._impl_obj.to_have_attribute(
                name=name, value=value, ignoreCase=ignore_case, timeout=timeout
            )
        )

    async def not_to_have_attribute(
        self,
        name: str,
        value: typing.Union[str, typing.Pattern[str]],
        *,
        ignore_case: typing.Optional[bool] = None,
        timeout: typing.Optional[float] = None,
    ) -> None:
        """LocatorAssertions.not_to_have_attribute

        The opposite of `locator_assertions.to_have_attribute()`.

        Parameters
        ----------
        name : str
            Attribute name.
        value : Union[Pattern[str], str]
            Expected attribute value.
        ignore_case : Union[bool, None]
            Whether to perform case-insensitive match. `ignoreCase` option takes precedence over the corresponding regular
            expression flag if specified.
        timeout : Union[float, None]
            Time to retry the assertion for in milliseconds. Defaults to `5000`.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            await self._impl_obj.not_to_have_attribute(
                name=name, value=value, ignoreCase=ignore_case, timeout=timeout
            )
        )

    async def to_have_class(
        self,
        expected: typing.Union[
            typing.Sequence[str],
            typing.Sequence[typing.Pattern[str]],
            typing.Sequence[typing.Union[typing.Pattern[str], str]],
            typing.Pattern[str],
            str,
        ],
        *,
        timeout: typing.Optional[float] = None,
    ) -> None:
        """LocatorAssertions.to_have_class

        Ensures the `Locator` points to an element with given CSS classes. When a string is provided, it must fully match
        the element's `class` attribute. To match individual classes use `locator_assertions.to_contain_class()`.

        **Usage**

        ```html
        <div class='middle selected row' id='component'></div>
        ```

        ```py
        from playwright.async_api import expect

        locator = page.locator(\"#component\")
        await expect(locator).to_have_class(\"middle selected row\")
        await expect(locator).to_have_class(re.compile(r\"(^|\\\\s)selected(\\\\s|$)\"))
        ```

        When an array is passed, the method asserts that the list of elements located matches the corresponding list of
        expected class values. Each element's class attribute is matched against the corresponding string or regular
        expression in the array:

        ```py
        from playwright.async_api import expect

        locator = page.locator(\".list > .component\")
        await expect(locator).to_have_class([\"component\", \"component selected\", \"component\"])
        ```

        Parameters
        ----------
        expected : Union[Pattern[str], Sequence[Pattern[str]], Sequence[Union[Pattern[str], str]], Sequence[str], str]
            Expected class or RegExp or a list of those.
        timeout : Union[float, None]
            Time to retry the assertion for in milliseconds. Defaults to `5000`.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            await self._impl_obj.to_have_class(
                expected=mapping.to_impl(expected), timeout=timeout
            )
        )

    async def not_to_have_class(
        self,
        expected: typing.Union[
            typing.Sequence[str],
            typing.Sequence[typing.Pattern[str]],
            typing.Sequence[typing.Union[typing.Pattern[str], str]],
            typing.Pattern[str],
            str,
        ],
        *,
        timeout: typing.Optional[float] = None,
    ) -> None:
        """LocatorAssertions.not_to_have_class

        The opposite of `locator_assertions.to_have_class()`.

        Parameters
        ----------
        expected : Union[Pattern[str], Sequence[Pattern[str]], Sequence[Union[Pattern[str], str]], Sequence[str], str]
            Expected class or RegExp or a list of those.
        timeout : Union[float, None]
            Time to retry the assertion for in milliseconds. Defaults to `5000`.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            await self._impl_obj.not_to_have_class(
                expected=mapping.to_impl(expected), timeout=timeout
            )
        )

    async def to_contain_class(
        self,
        expected: typing.Union[typing.Sequence[str], str],
        *,
        timeout: typing.Optional[float] = None,
    ) -> None:
        """LocatorAssertions.to_contain_class

        Ensures the `Locator` points to an element with given CSS classes. All classes from the asserted value, separated
        by spaces, must be present in the
        [Element.classList](https://developer.mozilla.org/en-US/docs/Web/API/Element/classList) in any order.

        **Usage**

        ```html
        <div class='middle selected row' id='component'></div>
        ```

        ```py
        from playwright.async_api import expect

        locator = page.locator(\"#component\")
        await expect(locator).to_contain_class(\"middle selected row\")
        await expect(locator).to_contain_class(\"selected\")
        await expect(locator).to_contain_class(\"row middle\")
        ```

        When an array is passed, the method asserts that the list of elements located matches the corresponding list of
        expected class lists. Each element's class attribute is matched against the corresponding class in the array:

        ```html
        <div class='list'>
          <div class='component inactive'></div>
          <div class='component active'></div>
          <div class='component inactive'></div>
        </div>
        ```

        ```py
        from playwright.async_api import expect

        locator = page.locator(\".list > .component\")
        await expect(locator).to_contain_class([\"inactive\", \"active\", \"inactive\"])
        ```

        Parameters
        ----------
        expected : Union[Sequence[str], str]
            A string containing expected class names, separated by spaces, or a list of such strings to assert multiple
            elements.
        timeout : Union[float, None]
            Time to retry the assertion for in milliseconds. Defaults to `5000`.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            await self._impl_obj.to_contain_class(
                expected=mapping.to_impl(expected), timeout=timeout
            )
        )

    async def not_to_contain_class(
        self,
        expected: typing.Union[typing.Sequence[str], str],
        *,
        timeout: typing.Optional[float] = None,
    ) -> None:
        """LocatorAssertions.not_to_contain_class

        The opposite of `locator_assertions.to_contain_class()`.

        Parameters
        ----------
        expected : Union[Sequence[str], str]
            Expected class or RegExp or a list of those.
        timeout : Union[float, None]
            Time to retry the assertion for in milliseconds. Defaults to `5000`.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            await self._impl_obj.not_to_contain_class(
                expected=mapping.to_impl(expected), timeout=timeout
            )
        )

    async def to_have_count(
        self, count: int, *, timeout: typing.Optional[float] = None
    ) -> None:
        """LocatorAssertions.to_have_count

        Ensures the `Locator` resolves to an exact number of DOM nodes.

        **Usage**

        ```py
        from playwright.async_api import expect

        locator = page.locator(\"list > .component\")
        await expect(locator).to_have_count(3)
        ```

        Parameters
        ----------
        count : int
            Expected count.
        timeout : Union[float, None]
            Time to retry the assertion for in milliseconds. Defaults to `5000`.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            await self._impl_obj.to_have_count(count=count, timeout=timeout)
        )

    async def not_to_have_count(
        self, count: int, *, timeout: typing.Optional[float] = None
    ) -> None:
        """LocatorAssertions.not_to_have_count

        The opposite of `locator_assertions.to_have_count()`.

        Parameters
        ----------
        count : int
            Expected count.
        timeout : Union[float, None]
            Time to retry the assertion for in milliseconds. Defaults to `5000`.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            await self._impl_obj.not_to_have_count(count=count, timeout=timeout)
        )

    async def to_have_css(
        self,
        name: str,
        value: typing.Union[str, typing.Pattern[str]],
        *,
        timeout: typing.Optional[float] = None,
    ) -> None:
        """LocatorAssertions.to_have_css

        Ensures the `Locator` resolves to an element with the given computed CSS style.

        **Usage**

        ```py
        from playwright.async_api import expect

        locator = page.get_by_role(\"button\")
        await expect(locator).to_have_css(\"display\", \"flex\")
        ```

        Parameters
        ----------
        name : str
            CSS property name.
        value : Union[Pattern[str], str]
            CSS property value.
        timeout : Union[float, None]
            Time to retry the assertion for in milliseconds. Defaults to `5000`.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            await self._impl_obj.to_have_css(name=name, value=value, timeout=timeout)
        )

    async def not_to_have_css(
        self,
        name: str,
        value: typing.Union[str, typing.Pattern[str]],
        *,
        timeout: typing.Optional[float] = None,
    ) -> None:
        """LocatorAssertions.not_to_have_css

        The opposite of `locator_assertions.to_have_css()`.

        Parameters
        ----------
        name : str
            CSS property name.
        value : Union[Pattern[str], str]
            CSS property value.
        timeout : Union[float, None]
            Time to retry the assertion for in milliseconds. Defaults to `5000`.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            await self._impl_obj.not_to_have_css(
                name=name, value=value, timeout=timeout
            )
        )

    async def to_have_id(
        self,
        id: typing.Union[str, typing.Pattern[str]],
        *,
        timeout: typing.Optional[float] = None,
    ) -> None:
        """LocatorAssertions.to_have_id

        Ensures the `Locator` points to an element with the given DOM Node ID.

        **Usage**

        ```py
        from playwright.async_api import expect

        locator = page.get_by_role(\"textbox\")
        await expect(locator).to_have_id(\"lastname\")
        ```

        Parameters
        ----------
        id : Union[Pattern[str], str]
            Element id.
        timeout : Union[float, None]
            Time to retry the assertion for in milliseconds. Defaults to `5000`.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            await self._impl_obj.to_have_id(id=id, timeout=timeout)
        )

    async def not_to_have_id(
        self,
        id: typing.Union[str, typing.Pattern[str]],
        *,
        timeout: typing.Optional[float] = None,
    ) -> None:
        """LocatorAssertions.not_to_have_id

        The opposite of `locator_assertions.to_have_id()`.

        Parameters
        ----------
        id : Union[Pattern[str], str]
            Element id.
        timeout : Union[float, None]
            Time to retry the assertion for in milliseconds. Defaults to `5000`.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            await self._impl_obj.not_to_have_id(id=id, timeout=timeout)
        )

    async def to_have_js_property(
        self, name: str, value: typing.Any, *, timeout: typing.Optional[float] = None
    ) -> None:
        """LocatorAssertions.to_have_js_property

        Ensures the `Locator` points to an element with given JavaScript property. Note that this property can be of a
        primitive type as well as a plain serializable JavaScript object.

        **Usage**

        ```py
        from playwright.async_api import expect

        locator = page.locator(\".component\")
        await expect(locator).to_have_js_property(\"loaded\", True)
        ```

        Parameters
        ----------
        name : str
            Property name.
        value : Any
            Property value.
        timeout : Union[float, None]
            Time to retry the assertion for in milliseconds. Defaults to `5000`.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            await self._impl_obj.to_have_js_property(
                name=name, value=mapping.to_impl(value), timeout=timeout
            )
        )

    async def not_to_have_js_property(
        self, name: str, value: typing.Any, *, timeout: typing.Optional[float] = None
    ) -> None:
        """LocatorAssertions.not_to_have_js_property

        The opposite of `locator_assertions.to_have_js_property()`.

        Parameters
        ----------
        name : str
            Property name.
        value : Any
            Property value.
        timeout : Union[float, None]
            Time to retry the assertion for in milliseconds. Defaults to `5000`.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            await self._impl_obj.not_to_have_js_property(
                name=name, value=mapping.to_impl(value), timeout=timeout
            )
        )

    async def to_have_value(
        self,
        value: typing.Union[str, typing.Pattern[str]],
        *,
        timeout: typing.Optional[float] = None,
    ) -> None:
        """LocatorAssertions.to_have_value

        Ensures the `Locator` points to an element with the given input value. You can use regular expressions for the
        value as well.

        **Usage**

        ```py
        import re
        from playwright.async_api import expect

        locator = page.locator(\"input[type=number]\")
        await expect(locator).to_have_value(re.compile(r\"[0-9]\"))
        ```

        Parameters
        ----------
        value : Union[Pattern[str], str]
            Expected value.
        timeout : Union[float, None]
            Time to retry the assertion for in milliseconds. Defaults to `5000`.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            await self._impl_obj.to_have_value(value=value, timeout=timeout)
        )

    async def not_to_have_value(
        self,
        value: typing.Union[str, typing.Pattern[str]],
        *,
        timeout: typing.Optional[float] = None,
    ) -> None:
        """LocatorAssertions.not_to_have_value

        The opposite of `locator_assertions.to_have_value()`.

        Parameters
        ----------
        value : Union[Pattern[str], str]
            Expected value.
        timeout : Union[float, None]
            Time to retry the assertion for in milliseconds. Defaults to `5000`.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            await self._impl_obj.not_to_have_value(value=value, timeout=timeout)
        )

    async def to_have_values(
        self,
        values: typing.Union[
            typing.Sequence[str],
            typing.Sequence[typing.Pattern[str]],
            typing.Sequence[typing.Union[typing.Pattern[str], str]],
        ],
        *,
        timeout: typing.Optional[float] = None,
    ) -> None:
        """LocatorAssertions.to_have_values

        Ensures the `Locator` points to multi-select/combobox (i.e. a `select` with the `multiple` attribute) and the
        specified values are selected.

        **Usage**

        For example, given the following element:

        ```html
        <select id=\"favorite-colors\" multiple>
          <option value=\"R\">Red</option>
          <option value=\"G\">Green</option>
          <option value=\"B\">Blue</option>
        </select>
        ```

        ```py
        import re
        from playwright.async_api import expect

        locator = page.locator(\"id=favorite-colors\")
        await locator.select_option([\"R\", \"G\"])
        await expect(locator).to_have_values([re.compile(r\"R\"), re.compile(r\"G\")])
        ```

        Parameters
        ----------
        values : Union[Sequence[Pattern[str]], Sequence[Union[Pattern[str], str]], Sequence[str]]
            Expected options currently selected.
        timeout : Union[float, None]
            Time to retry the assertion for in milliseconds. Defaults to `5000`.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            await self._impl_obj.to_have_values(
                values=mapping.to_impl(values), timeout=timeout
            )
        )

    async def not_to_have_values(
        self,
        values: typing.Union[
            typing.Sequence[str],
            typing.Sequence[typing.Pattern[str]],
            typing.Sequence[typing.Union[typing.Pattern[str], str]],
        ],
        *,
        timeout: typing.Optional[float] = None,
    ) -> None:
        """LocatorAssertions.not_to_have_values

        The opposite of `locator_assertions.to_have_values()`.

        Parameters
        ----------
        values : Union[Sequence[Pattern[str]], Sequence[Union[Pattern[str], str]], Sequence[str]]
            Expected options currently selected.
        timeout : Union[float, None]
            Time to retry the assertion for in milliseconds. Defaults to `5000`.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            await self._impl_obj.not_to_have_values(
                values=mapping.to_impl(values), timeout=timeout
            )
        )

    async def to_have_text(
        self,
        expected: typing.Union[
            typing.Sequence[str],
            typing.Sequence[typing.Pattern[str]],
            typing.Sequence[typing.Union[typing.Pattern[str], str]],
            typing.Pattern[str],
            str,
        ],
        *,
        use_inner_text: typing.Optional[bool] = None,
        timeout: typing.Optional[float] = None,
        ignore_case: typing.Optional[bool] = None,
    ) -> None:
        """LocatorAssertions.to_have_text

        Ensures the `Locator` points to an element with the given text. All nested elements will be considered when
        computing the text content of the element. You can use regular expressions for the value as well.

        **Details**

        When `expected` parameter is a string, Playwright will normalize whitespaces and line breaks both in the actual
        text and in the expected string before matching. When regular expression is used, the actual text is matched as is.

        **Usage**

        ```py
        import re
        from playwright.async_api import expect

        locator = page.locator(\".title\")
        await expect(locator).to_have_text(re.compile(r\"Welcome, Test User\"))
        await expect(locator).to_have_text(re.compile(r\"Welcome, .*\"))
        ```

        If you pass an array as an expected value, the expectations are:
        1. Locator resolves to a list of elements.
        1. The number of elements equals the number of expected values in the array.
        1. Elements from the list have text matching expected array values, one by one, in order.

        For example, consider the following list:

        ```html
        <ul>
          <li>Text 1</li>
          <li>Text 2</li>
          <li>Text 3</li>
        </ul>
        ```

        Let's see how we can use the assertion:

        ```py
        from playwright.async_api import expect

        # ✓ Has the right items in the right order
        await expect(page.locator(\"ul > li\")).to_have_text([\"Text 1\", \"Text 2\", \"Text 3\"])

        # ✖ Wrong order
        await expect(page.locator(\"ul > li\")).to_have_text([\"Text 3\", \"Text 2\", \"Text 1\"])

        # ✖ Last item does not match
        await expect(page.locator(\"ul > li\")).to_have_text([\"Text 1\", \"Text 2\", \"Text\"])

        # ✖ Locator points to the outer list element, not to the list items
        await expect(page.locator(\"ul\")).to_have_text([\"Text 1\", \"Text 2\", \"Text 3\"])
        ```

        Parameters
        ----------
        expected : Union[Pattern[str], Sequence[Pattern[str]], Sequence[Union[Pattern[str], str]], Sequence[str], str]
            Expected string or RegExp or a list of those.
        use_inner_text : Union[bool, None]
            Whether to use `element.innerText` instead of `element.textContent` when retrieving DOM node text.
        timeout : Union[float, None]
            Time to retry the assertion for in milliseconds. Defaults to `5000`.
        ignore_case : Union[bool, None]
            Whether to perform case-insensitive match. `ignoreCase` option takes precedence over the corresponding regular
            expression flag if specified.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            await self._impl_obj.to_have_text(
                expected=mapping.to_impl(expected),
                useInnerText=use_inner_text,
                timeout=timeout,
                ignoreCase=ignore_case,
            )
        )

    async def not_to_have_text(
        self,
        expected: typing.Union[
            typing.Sequence[str],
            typing.Sequence[typing.Pattern[str]],
            typing.Sequence[typing.Union[typing.Pattern[str], str]],
            typing.Pattern[str],
            str,
        ],
        *,
        use_inner_text: typing.Optional[bool] = None,
        timeout: typing.Optional[float] = None,
        ignore_case: typing.Optional[bool] = None,
    ) -> None:
        """LocatorAssertions.not_to_have_text

        The opposite of `locator_assertions.to_have_text()`.

        Parameters
        ----------
        expected : Union[Pattern[str], Sequence[Pattern[str]], Sequence[Union[Pattern[str], str]], Sequence[str], str]
            Expected string or RegExp or a list of those.
        use_inner_text : Union[bool, None]
            Whether to use `element.innerText` instead of `element.textContent` when retrieving DOM node text.
        timeout : Union[float, None]
            Time to retry the assertion for in milliseconds. Defaults to `5000`.
        ignore_case : Union[bool, None]
            Whether to perform case-insensitive match. `ignoreCase` option takes precedence over the corresponding regular
            expression flag if specified.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            await self._impl_obj.not_to_have_text(
                expected=mapping.to_impl(expected),
                useInnerText=use_inner_text,
                timeout=timeout,
                ignoreCase=ignore_case,
            )
        )

    async def to_be_attached(
        self,
        *,
        attached: typing.Optional[bool] = None,
        timeout: typing.Optional[float] = None,
    ) -> None:
        """LocatorAssertions.to_be_attached

        Ensures that `Locator` points to an element that is
        [connected](https://developer.mozilla.org/en-US/docs/Web/API/Node/isConnected) to a Document or a ShadowRoot.

        **Usage**

        ```py
        await expect(page.get_by_text(\"Hidden text\")).to_be_attached()
        ```

        Parameters
        ----------
        attached : Union[bool, None]
        timeout : Union[float, None]
            Time to retry the assertion for in milliseconds. Defaults to `5000`.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            await self._impl_obj.to_be_attached(attached=attached, timeout=timeout)
        )

    async def to_be_checked(
        self,
        *,
        timeout: typing.Optional[float] = None,
        checked: typing.Optional[bool] = None,
        indeterminate: typing.Optional[bool] = None,
    ) -> None:
        """LocatorAssertions.to_be_checked

        Ensures the `Locator` points to a checked input.

        **Usage**

        ```py
        from playwright.async_api import expect

        locator = page.get_by_label(\"Subscribe to newsletter\")
        await expect(locator).to_be_checked()
        ```

        Parameters
        ----------
        timeout : Union[float, None]
            Time to retry the assertion for in milliseconds. Defaults to `5000`.
        checked : Union[bool, None]
            Provides state to assert for. Asserts for input to be checked by default. This option can't be used when
            `indeterminate` is set to true.
        indeterminate : Union[bool, None]
            Asserts that the element is in the indeterminate (mixed) state. Only supported for checkboxes and radio buttons.
            This option can't be true when `checked` is provided.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            await self._impl_obj.to_be_checked(
                timeout=timeout, checked=checked, indeterminate=indeterminate
            )
        )

    async def not_to_be_attached(
        self,
        *,
        attached: typing.Optional[bool] = None,
        timeout: typing.Optional[float] = None,
    ) -> None:
        """LocatorAssertions.not_to_be_attached

        The opposite of `locator_assertions.to_be_attached()`.

        Parameters
        ----------
        attached : Union[bool, None]
        timeout : Union[float, None]
            Time to retry the assertion for in milliseconds. Defaults to `5000`.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            await self._impl_obj.not_to_be_attached(attached=attached, timeout=timeout)
        )

    async def not_to_be_checked(
        self, *, timeout: typing.Optional[float] = None
    ) -> None:
        """LocatorAssertions.not_to_be_checked

        The opposite of `locator_assertions.to_be_checked()`.

        Parameters
        ----------
        timeout : Union[float, None]
            Time to retry the assertion for in milliseconds. Defaults to `5000`.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            await self._impl_obj.not_to_be_checked(timeout=timeout)
        )

    async def to_be_disabled(self, *, timeout: typing.Optional[float] = None) -> None:
        """LocatorAssertions.to_be_disabled

        Ensures the `Locator` points to a disabled element. Element is disabled if it has \"disabled\" attribute or is
        disabled via
        ['aria-disabled'](https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/Attributes/aria-disabled). Note
        that only native control elements such as HTML `button`, `input`, `select`, `textarea`, `option`, `optgroup` can be
        disabled by setting \"disabled\" attribute. \"disabled\" attribute on other elements is ignored by the browser.

        **Usage**

        ```py
        from playwright.async_api import expect

        locator = page.locator(\"button.submit\")
        await expect(locator).to_be_disabled()
        ```

        Parameters
        ----------
        timeout : Union[float, None]
            Time to retry the assertion for in milliseconds. Defaults to `5000`.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            await self._impl_obj.to_be_disabled(timeout=timeout)
        )

    async def not_to_be_disabled(
        self, *, timeout: typing.Optional[float] = None
    ) -> None:
        """LocatorAssertions.not_to_be_disabled

        The opposite of `locator_assertions.to_be_disabled()`.

        Parameters
        ----------
        timeout : Union[float, None]
            Time to retry the assertion for in milliseconds. Defaults to `5000`.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            await self._impl_obj.not_to_be_disabled(timeout=timeout)
        )

    async def to_be_editable(
        self,
        *,
        editable: typing.Optional[bool] = None,
        timeout: typing.Optional[float] = None,
    ) -> None:
        """LocatorAssertions.to_be_editable

        Ensures the `Locator` points to an editable element.

        **Usage**

        ```py
        from playwright.async_api import expect

        locator = page.get_by_role(\"textbox\")
        await expect(locator).to_be_editable()
        ```

        Parameters
        ----------
        editable : Union[bool, None]
        timeout : Union[float, None]
            Time to retry the assertion for in milliseconds. Defaults to `5000`.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            await self._impl_obj.to_be_editable(editable=editable, timeout=timeout)
        )

    async def not_to_be_editable(
        self,
        *,
        editable: typing.Optional[bool] = None,
        timeout: typing.Optional[float] = None,
    ) -> None:
        """LocatorAssertions.not_to_be_editable

        The opposite of `locator_assertions.to_be_editable()`.

        Parameters
        ----------
        editable : Union[bool, None]
        timeout : Union[float, None]
            Time to retry the assertion for in milliseconds. Defaults to `5000`.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            await self._impl_obj.not_to_be_editable(editable=editable, timeout=timeout)
        )

    async def to_be_empty(self, *, timeout: typing.Optional[float] = None) -> None:
        """LocatorAssertions.to_be_empty

        Ensures the `Locator` points to an empty editable element or to a DOM node that has no text.

        **Usage**

        ```py
        from playwright.async_api import expect

        locator = page.locator(\"div.warning\")
        await expect(locator).to_be_empty()
        ```

        Parameters
        ----------
        timeout : Union[float, None]
            Time to retry the assertion for in milliseconds. Defaults to `5000`.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            await self._impl_obj.to_be_empty(timeout=timeout)
        )

    async def not_to_be_empty(self, *, timeout: typing.Optional[float] = None) -> None:
        """LocatorAssertions.not_to_be_empty

        The opposite of `locator_assertions.to_be_empty()`.

        Parameters
        ----------
        timeout : Union[float, None]
            Time to retry the assertion for in milliseconds. Defaults to `5000`.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            await self._impl_obj.not_to_be_empty(timeout=timeout)
        )

    async def to_be_enabled(
        self,
        *,
        enabled: typing.Optional[bool] = None,
        timeout: typing.Optional[float] = None,
    ) -> None:
        """LocatorAssertions.to_be_enabled

        Ensures the `Locator` points to an enabled element.

        **Usage**

        ```py
        from playwright.async_api import expect

        locator = page.locator(\"button.submit\")
        await expect(locator).to_be_enabled()
        ```

        Parameters
        ----------
        enabled : Union[bool, None]
        timeout : Union[float, None]
            Time to retry the assertion for in milliseconds. Defaults to `5000`.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            await self._impl_obj.to_be_enabled(enabled=enabled, timeout=timeout)
        )

    async def not_to_be_enabled(
        self,
        *,
        enabled: typing.Optional[bool] = None,
        timeout: typing.Optional[float] = None,
    ) -> None:
        """LocatorAssertions.not_to_be_enabled

        The opposite of `locator_assertions.to_be_enabled()`.

        Parameters
        ----------
        enabled : Union[bool, None]
        timeout : Union[float, None]
            Time to retry the assertion for in milliseconds. Defaults to `5000`.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            await self._impl_obj.not_to_be_enabled(enabled=enabled, timeout=timeout)
        )

    async def to_be_hidden(self, *, timeout: typing.Optional[float] = None) -> None:
        """LocatorAssertions.to_be_hidden

        Ensures that `Locator` either does not resolve to any DOM node, or resolves to a
        [non-visible](https://playwright.dev/python/docs/actionability#visible) one.

        **Usage**

        ```py
        from playwright.async_api import expect

        locator = page.locator('.my-element')
        await expect(locator).to_be_hidden()
        ```

        Parameters
        ----------
        timeout : Union[float, None]
            Time to retry the assertion for in milliseconds. Defaults to `5000`.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            await self._impl_obj.to_be_hidden(timeout=timeout)
        )

    async def not_to_be_hidden(self, *, timeout: typing.Optional[float] = None) -> None:
        """LocatorAssertions.not_to_be_hidden

        The opposite of `locator_assertions.to_be_hidden()`.

        Parameters
        ----------
        timeout : Union[float, None]
            Time to retry the assertion for in milliseconds. Defaults to `5000`.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            await self._impl_obj.not_to_be_hidden(timeout=timeout)
        )

    async def to_be_visible(
        self,
        *,
        visible: typing.Optional[bool] = None,
        timeout: typing.Optional[float] = None,
    ) -> None:
        """LocatorAssertions.to_be_visible

        Ensures that `Locator` points to an attached and [visible](https://playwright.dev/python/docs/actionability#visible) DOM node.

        To check that at least one element from the list is visible, use `locator.first()`.

        **Usage**

        ```py
        # A specific element is visible.
        await expect(page.get_by_text(\"Welcome\")).to_be_visible()

        # At least one item in the list is visible.
        await expect(page.get_by_test_id(\"todo-item\").first).to_be_visible()

        # At least one of the two elements is visible, possibly both.
        await expect(
            page.get_by_role(\"button\", name=\"Sign in\")
            .or_(page.get_by_role(\"button\", name=\"Sign up\"))
            .first
        ).to_be_visible()
        ```

        Parameters
        ----------
        visible : Union[bool, None]
        timeout : Union[float, None]
            Time to retry the assertion for in milliseconds. Defaults to `5000`.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            await self._impl_obj.to_be_visible(visible=visible, timeout=timeout)
        )

    async def not_to_be_visible(
        self,
        *,
        visible: typing.Optional[bool] = None,
        timeout: typing.Optional[float] = None,
    ) -> None:
        """LocatorAssertions.not_to_be_visible

        The opposite of `locator_assertions.to_be_visible()`.

        Parameters
        ----------
        visible : Union[bool, None]
        timeout : Union[float, None]
            Time to retry the assertion for in milliseconds. Defaults to `5000`.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            await self._impl_obj.not_to_be_visible(visible=visible, timeout=timeout)
        )

    async def to_be_focused(self, *, timeout: typing.Optional[float] = None) -> None:
        """LocatorAssertions.to_be_focused

        Ensures the `Locator` points to a focused DOM node.

        **Usage**

        ```py
        from playwright.async_api import expect

        locator = page.get_by_role(\"textbox\")
        await expect(locator).to_be_focused()
        ```

        Parameters
        ----------
        timeout : Union[float, None]
            Time to retry the assertion for in milliseconds. Defaults to `5000`.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            await self._impl_obj.to_be_focused(timeout=timeout)
        )

    async def not_to_be_focused(
        self, *, timeout: typing.Optional[float] = None
    ) -> None:
        """LocatorAssertions.not_to_be_focused

        The opposite of `locator_assertions.to_be_focused()`.

        Parameters
        ----------
        timeout : Union[float, None]
            Time to retry the assertion for in milliseconds. Defaults to `5000`.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            await self._impl_obj.not_to_be_focused(timeout=timeout)
        )

    async def to_be_in_viewport(
        self,
        *,
        ratio: typing.Optional[float] = None,
        timeout: typing.Optional[float] = None,
    ) -> None:
        """LocatorAssertions.to_be_in_viewport

        Ensures the `Locator` points to an element that intersects viewport, according to the
        [intersection observer API](https://developer.mozilla.org/en-US/docs/Web/API/Intersection_Observer_API).

        **Usage**

        ```py
        from playwright.async_api import expect

        locator = page.get_by_role(\"button\")
        # Make sure at least some part of element intersects viewport.
        await expect(locator).to_be_in_viewport()
        # Make sure element is fully outside of viewport.
        await expect(locator).not_to_be_in_viewport()
        # Make sure that at least half of the element intersects viewport.
        await expect(locator).to_be_in_viewport(ratio=0.5)
        ```

        Parameters
        ----------
        ratio : Union[float, None]
            The minimal ratio of the element to intersect viewport. If equals to `0`, then element should intersect viewport at
            any positive ratio. Defaults to `0`.
        timeout : Union[float, None]
            Time to retry the assertion for in milliseconds. Defaults to `5000`.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            await self._impl_obj.to_be_in_viewport(ratio=ratio, timeout=timeout)
        )

    async def not_to_be_in_viewport(
        self,
        *,
        ratio: typing.Optional[float] = None,
        timeout: typing.Optional[float] = None,
    ) -> None:
        """LocatorAssertions.not_to_be_in_viewport

        The opposite of `locator_assertions.to_be_in_viewport()`.

        Parameters
        ----------
        ratio : Union[float, None]
        timeout : Union[float, None]
            Time to retry the assertion for in milliseconds. Defaults to `5000`.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            await self._impl_obj.not_to_be_in_viewport(ratio=ratio, timeout=timeout)
        )

    async def to_have_accessible_description(
        self,
        description: typing.Union[str, typing.Pattern[str]],
        *,
        ignore_case: typing.Optional[bool] = None,
        timeout: typing.Optional[float] = None,
    ) -> None:
        """LocatorAssertions.to_have_accessible_description

        Ensures the `Locator` points to an element with a given
        [accessible description](https://w3c.github.io/accname/#dfn-accessible-description).

        **Usage**

        ```py
        locator = page.get_by_test_id(\"save-button\")
        await expect(locator).to_have_accessible_description(\"Save results to disk\")
        ```

        Parameters
        ----------
        description : Union[Pattern[str], str]
            Expected accessible description.
        ignore_case : Union[bool, None]
            Whether to perform case-insensitive match. `ignoreCase` option takes precedence over the corresponding regular
            expression flag if specified.
        timeout : Union[float, None]
            Time to retry the assertion for in milliseconds. Defaults to `5000`.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            await self._impl_obj.to_have_accessible_description(
                description=description, ignoreCase=ignore_case, timeout=timeout
            )
        )

    async def not_to_have_accessible_description(
        self,
        name: typing.Union[str, typing.Pattern[str]],
        *,
        ignore_case: typing.Optional[bool] = None,
        timeout: typing.Optional[float] = None,
    ) -> None:
        """LocatorAssertions.not_to_have_accessible_description

        The opposite of `locator_assertions.to_have_accessible_description()`.

        Parameters
        ----------
        name : Union[Pattern[str], str]
            Expected accessible description.
        ignore_case : Union[bool, None]
            Whether to perform case-insensitive match. `ignoreCase` option takes precedence over the corresponding regular
            expression flag if specified.
        timeout : Union[float, None]
            Time to retry the assertion for in milliseconds. Defaults to `5000`.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            await self._impl_obj.not_to_have_accessible_description(
                name=name, ignoreCase=ignore_case, timeout=timeout
            )
        )

    async def to_have_accessible_name(
        self,
        name: typing.Union[str, typing.Pattern[str]],
        *,
        ignore_case: typing.Optional[bool] = None,
        timeout: typing.Optional[float] = None,
    ) -> None:
        """LocatorAssertions.to_have_accessible_name

        Ensures the `Locator` points to an element with a given
        [accessible name](https://w3c.github.io/accname/#dfn-accessible-name).

        **Usage**

        ```py
        locator = page.get_by_test_id(\"save-button\")
        await expect(locator).to_have_accessible_name(\"Save to disk\")
        ```

        Parameters
        ----------
        name : Union[Pattern[str], str]
            Expected accessible name.
        ignore_case : Union[bool, None]
            Whether to perform case-insensitive match. `ignoreCase` option takes precedence over the corresponding regular
            expression flag if specified.
        timeout : Union[float, None]
            Time to retry the assertion for in milliseconds. Defaults to `5000`.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            await self._impl_obj.to_have_accessible_name(
                name=name, ignoreCase=ignore_case, timeout=timeout
            )
        )

    async def not_to_have_accessible_name(
        self,
        name: typing.Union[str, typing.Pattern[str]],
        *,
        ignore_case: typing.Optional[bool] = None,
        timeout: typing.Optional[float] = None,
    ) -> None:
        """LocatorAssertions.not_to_have_accessible_name

        The opposite of `locator_assertions.to_have_accessible_name()`.

        Parameters
        ----------
        name : Union[Pattern[str], str]
            Expected accessible name.
        ignore_case : Union[bool, None]
            Whether to perform case-insensitive match. `ignoreCase` option takes precedence over the corresponding regular
            expression flag if specified.
        timeout : Union[float, None]
            Time to retry the assertion for in milliseconds. Defaults to `5000`.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            await self._impl_obj.not_to_have_accessible_name(
                name=name, ignoreCase=ignore_case, timeout=timeout
            )
        )

    async def to_have_role(
        self,
        role: Literal[
            "alert",
            "alertdialog",
            "application",
            "article",
            "banner",
            "blockquote",
            "button",
            "caption",
            "cell",
            "checkbox",
            "code",
            "columnheader",
            "combobox",
            "complementary",
            "contentinfo",
            "definition",
            "deletion",
            "dialog",
            "directory",
            "document",
            "emphasis",
            "feed",
            "figure",
            "form",
            "generic",
            "grid",
            "gridcell",
            "group",
            "heading",
            "img",
            "insertion",
            "link",
            "list",
            "listbox",
            "listitem",
            "log",
            "main",
            "marquee",
            "math",
            "menu",
            "menubar",
            "menuitem",
            "menuitemcheckbox",
            "menuitemradio",
            "meter",
            "navigation",
            "none",
            "note",
            "option",
            "paragraph",
            "presentation",
            "progressbar",
            "radio",
            "radiogroup",
            "region",
            "row",
            "rowgroup",
            "rowheader",
            "scrollbar",
            "search",
            "searchbox",
            "separator",
            "slider",
            "spinbutton",
            "status",
            "strong",
            "subscript",
            "superscript",
            "switch",
            "tab",
            "table",
            "tablist",
            "tabpanel",
            "term",
            "textbox",
            "time",
            "timer",
            "toolbar",
            "tooltip",
            "tree",
            "treegrid",
            "treeitem",
        ],
        *,
        timeout: typing.Optional[float] = None,
    ) -> None:
        """LocatorAssertions.to_have_role

        Ensures the `Locator` points to an element with a given [ARIA role](https://www.w3.org/TR/wai-aria-1.2/#roles).

        Note that role is matched as a string, disregarding the ARIA role hierarchy. For example, asserting  a superclass
        role `\"checkbox\"` on an element with a subclass role `\"switch\"` will fail.

        **Usage**

        ```py
        locator = page.get_by_test_id(\"save-button\")
        await expect(locator).to_have_role(\"button\")
        ```

        Parameters
        ----------
        role : Union["alert", "alertdialog", "application", "article", "banner", "blockquote", "button", "caption", "cell", "checkbox", "code", "columnheader", "combobox", "complementary", "contentinfo", "definition", "deletion", "dialog", "directory", "document", "emphasis", "feed", "figure", "form", "generic", "grid", "gridcell", "group", "heading", "img", "insertion", "link", "list", "listbox", "listitem", "log", "main", "marquee", "math", "menu", "menubar", "menuitem", "menuitemcheckbox", "menuitemradio", "meter", "navigation", "none", "note", "option", "paragraph", "presentation", "progressbar", "radio", "radiogroup", "region", "row", "rowgroup", "rowheader", "scrollbar", "search", "searchbox", "separator", "slider", "spinbutton", "status", "strong", "subscript", "superscript", "switch", "tab", "table", "tablist", "tabpanel", "term", "textbox", "time", "timer", "toolbar", "tooltip", "tree", "treegrid", "treeitem"]
            Required aria role.
        timeout : Union[float, None]
            Time to retry the assertion for in milliseconds. Defaults to `5000`.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            await self._impl_obj.to_have_role(role=role, timeout=timeout)
        )

    async def to_have_accessible_error_message(
        self,
        error_message: typing.Union[str, typing.Pattern[str]],
        *,
        ignore_case: typing.Optional[bool] = None,
        timeout: typing.Optional[float] = None,
    ) -> None:
        """LocatorAssertions.to_have_accessible_error_message

        Ensures the `Locator` points to an element with a given
        [aria errormessage](https://w3c.github.io/aria/#aria-errormessage).

        **Usage**

        ```py
        locator = page.get_by_test_id(\"username-input\")
        await expect(locator).to_have_accessible_error_message(\"Username is required.\")
        ```

        Parameters
        ----------
        error_message : Union[Pattern[str], str]
            Expected accessible error message.
        ignore_case : Union[bool, None]
            Whether to perform case-insensitive match. `ignoreCase` option takes precedence over the corresponding regular
            expression flag if specified.
        timeout : Union[float, None]
            Time to retry the assertion for in milliseconds. Defaults to `5000`.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            await self._impl_obj.to_have_accessible_error_message(
                errorMessage=error_message, ignoreCase=ignore_case, timeout=timeout
            )
        )

    async def not_to_have_accessible_error_message(
        self,
        error_message: typing.Union[str, typing.Pattern[str]],
        *,
        ignore_case: typing.Optional[bool] = None,
        timeout: typing.Optional[float] = None,
    ) -> None:
        """LocatorAssertions.not_to_have_accessible_error_message

        The opposite of `locator_assertions.to_have_accessible_error_message()`.

        Parameters
        ----------
        error_message : Union[Pattern[str], str]
            Expected accessible error message.
        ignore_case : Union[bool, None]
            Whether to perform case-insensitive match. `ignoreCase` option takes precedence over the corresponding regular
            expression flag if specified.
        timeout : Union[float, None]
            Time to retry the assertion for in milliseconds. Defaults to `5000`.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            await self._impl_obj.not_to_have_accessible_error_message(
                errorMessage=error_message, ignoreCase=ignore_case, timeout=timeout
            )
        )

    async def not_to_have_role(
        self,
        role: Literal[
            "alert",
            "alertdialog",
            "application",
            "article",
            "banner",
            "blockquote",
            "button",
            "caption",
            "cell",
            "checkbox",
            "code",
            "columnheader",
            "combobox",
            "complementary",
            "contentinfo",
            "definition",
            "deletion",
            "dialog",
            "directory",
            "document",
            "emphasis",
            "feed",
            "figure",
            "form",
            "generic",
            "grid",
            "gridcell",
            "group",
            "heading",
            "img",
            "insertion",
            "link",
            "list",
            "listbox",
            "listitem",
            "log",
            "main",
            "marquee",
            "math",
            "menu",
            "menubar",
            "menuitem",
            "menuitemcheckbox",
            "menuitemradio",
            "meter",
            "navigation",
            "none",
            "note",
            "option",
            "paragraph",
            "presentation",
            "progressbar",
            "radio",
            "radiogroup",
            "region",
            "row",
            "rowgroup",
            "rowheader",
            "scrollbar",
            "search",
            "searchbox",
            "separator",
            "slider",
            "spinbutton",
            "status",
            "strong",
            "subscript",
            "superscript",
            "switch",
            "tab",
            "table",
            "tablist",
            "tabpanel",
            "term",
            "textbox",
            "time",
            "timer",
            "toolbar",
            "tooltip",
            "tree",
            "treegrid",
            "treeitem",
        ],
        *,
        timeout: typing.Optional[float] = None,
    ) -> None:
        """LocatorAssertions.not_to_have_role

        The opposite of `locator_assertions.to_have_role()`.

        Parameters
        ----------
        role : Union["alert", "alertdialog", "application", "article", "banner", "blockquote", "button", "caption", "cell", "checkbox", "code", "columnheader", "combobox", "complementary", "contentinfo", "definition", "deletion", "dialog", "directory", "document", "emphasis", "feed", "figure", "form", "generic", "grid", "gridcell", "group", "heading", "img", "insertion", "link", "list", "listbox", "listitem", "log", "main", "marquee", "math", "menu", "menubar", "menuitem", "menuitemcheckbox", "menuitemradio", "meter", "navigation", "none", "note", "option", "paragraph", "presentation", "progressbar", "radio", "radiogroup", "region", "row", "rowgroup", "rowheader", "scrollbar", "search", "searchbox", "separator", "slider", "spinbutton", "status", "strong", "subscript", "superscript", "switch", "tab", "table", "tablist", "tabpanel", "term", "textbox", "time", "timer", "toolbar", "tooltip", "tree", "treegrid", "treeitem"]
            Required aria role.
        timeout : Union[float, None]
            Time to retry the assertion for in milliseconds. Defaults to `5000`.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            await self._impl_obj.not_to_have_role(role=role, timeout=timeout)
        )

    async def to_match_aria_snapshot(
        self, expected: str, *, timeout: typing.Optional[float] = None
    ) -> None:
        """LocatorAssertions.to_match_aria_snapshot

        Asserts that the target element matches the given [accessibility snapshot](https://playwright.dev/python/docs/aria-snapshots).

        **Usage**

        ```py
        await page.goto(\"https://demo.playwright.dev/todomvc/\")
        await expect(page.locator('body')).to_match_aria_snapshot('''
          - heading \"todos\"
          - textbox \"What needs to be done?\"
        ''')
        ```

        Parameters
        ----------
        expected : str
        timeout : Union[float, None]
            Time to retry the assertion for in milliseconds. Defaults to `5000`.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            await self._impl_obj.to_match_aria_snapshot(
                expected=expected, timeout=timeout
            )
        )

    async def not_to_match_aria_snapshot(
        self, expected: str, *, timeout: typing.Optional[float] = None
    ) -> None:
        """LocatorAssertions.not_to_match_aria_snapshot

        The opposite of `locator_assertions.to_match_aria_snapshot()`.

        Parameters
        ----------
        expected : str
        timeout : Union[float, None]
            Time to retry the assertion for in milliseconds. Defaults to `5000`.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            await self._impl_obj.not_to_match_aria_snapshot(
                expected=expected, timeout=timeout
            )
        )


mapping.register(LocatorAssertionsImpl, LocatorAssertions)


class APIResponseAssertions(AsyncBase):

    async def to_be_ok(self) -> None:
        """APIResponseAssertions.to_be_ok

        Ensures the response status code is within `200..299` range.

        **Usage**

        ```py
        from playwright.async_api import expect

        # ...
        await expect(response).to_be_ok()
        ```
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(await self._impl_obj.to_be_ok())

    async def not_to_be_ok(self) -> None:
        """APIResponseAssertions.not_to_be_ok

        The opposite of `a_pi_response_assertions.to_be_ok()`.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(await self._impl_obj.not_to_be_ok())


mapping.register(APIResponseAssertionsImpl, APIResponseAssertions)
