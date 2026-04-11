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

"""
Python package `playwright` is a Python library to automate Chromium,
Firefox and WebKit with a single API. Playwright is built to enable cross-browser
web automation that is ever-green, capable, reliable and fast.
"""

from typing import Any, Optional, Union, overload

import playwright._impl._api_structures
import playwright._impl._errors
import playwright.async_api._generated
from playwright._impl._assertions import (
    APIResponseAssertions as APIResponseAssertionsImpl,
)
from playwright._impl._assertions import LocatorAssertions as LocatorAssertionsImpl
from playwright._impl._assertions import PageAssertions as PageAssertionsImpl
from playwright.async_api._context_manager import PlaywrightContextManager
from playwright.async_api._generated import (
    APIRequest,
    APIRequestContext,
    APIResponse,
    APIResponseAssertions,
    Browser,
    BrowserContext,
    BrowserType,
    CDPSession,
    ConsoleMessage,
    Dialog,
    Download,
    ElementHandle,
    FileChooser,
    Frame,
    FrameLocator,
    JSHandle,
    Keyboard,
    Locator,
    LocatorAssertions,
    Mouse,
    Page,
    PageAssertions,
    Playwright,
    Request,
    Response,
    Route,
    Selectors,
    Touchscreen,
    Video,
    WebError,
    WebSocket,
    WebSocketRoute,
    Worker,
)

ChromiumBrowserContext = BrowserContext

Cookie = playwright._impl._api_structures.Cookie
FilePayload = playwright._impl._api_structures.FilePayload
FloatRect = playwright._impl._api_structures.FloatRect
Geolocation = playwright._impl._api_structures.Geolocation
HttpCredentials = playwright._impl._api_structures.HttpCredentials
PdfMargins = playwright._impl._api_structures.PdfMargins
Position = playwright._impl._api_structures.Position
ProxySettings = playwright._impl._api_structures.ProxySettings
ResourceTiming = playwright._impl._api_structures.ResourceTiming
SourceLocation = playwright._impl._api_structures.SourceLocation
StorageState = playwright._impl._api_structures.StorageState
StorageStateCookie = playwright._impl._api_structures.StorageStateCookie
ViewportSize = playwright._impl._api_structures.ViewportSize

Error = playwright._impl._errors.Error
TimeoutError = playwright._impl._errors.TimeoutError


def async_playwright() -> PlaywrightContextManager:
    return PlaywrightContextManager()


class Expect:
    _unset: Any = object()

    def __init__(self) -> None:
        self._timeout: Optional[float] = None

    def set_options(self, timeout: Optional[float] = _unset) -> None:
        """
        This method sets global `expect()` options.

        Args:
            timeout (float): Timeout value in milliseconds. Default to 5000 milliseconds.

        Returns:
            None
        """
        if timeout is not self._unset:
            self._timeout = timeout

    @overload
    def __call__(
        self, actual: Page, message: Optional[str] = None
    ) -> PageAssertions: ...

    @overload
    def __call__(
        self, actual: Locator, message: Optional[str] = None
    ) -> LocatorAssertions: ...

    @overload
    def __call__(
        self, actual: APIResponse, message: Optional[str] = None
    ) -> APIResponseAssertions: ...

    def __call__(
        self, actual: Union[Page, Locator, APIResponse], message: Optional[str] = None
    ) -> Union[PageAssertions, LocatorAssertions, APIResponseAssertions]:
        if isinstance(actual, Page):
            return PageAssertions(
                PageAssertionsImpl(actual._impl_obj, self._timeout, message=message)
            )
        elif isinstance(actual, Locator):
            return LocatorAssertions(
                LocatorAssertionsImpl(actual._impl_obj, self._timeout, message=message)
            )
        elif isinstance(actual, APIResponse):
            return APIResponseAssertions(
                APIResponseAssertionsImpl(
                    actual._impl_obj, self._timeout, message=message
                )
            )
        raise ValueError(f"Unsupported type: {type(actual)}")


expect = Expect()


__all__ = [
    "expect",
    "async_playwright",
    "APIRequest",
    "APIRequestContext",
    "APIResponse",
    "Browser",
    "BrowserContext",
    "BrowserType",
    "CDPSession",
    "ChromiumBrowserContext",
    "ConsoleMessage",
    "Cookie",
    "Dialog",
    "Download",
    "ElementHandle",
    "Error",
    "FileChooser",
    "FilePayload",
    "FloatRect",
    "Frame",
    "FrameLocator",
    "Geolocation",
    "HttpCredentials",
    "JSHandle",
    "Keyboard",
    "Locator",
    "Mouse",
    "Page",
    "PdfMargins",
    "Position",
    "Playwright",
    "ProxySettings",
    "Request",
    "ResourceTiming",
    "Response",
    "Route",
    "Selectors",
    "SourceLocation",
    "StorageState",
    "StorageStateCookie",
    "TimeoutError",
    "Touchscreen",
    "Video",
    "ViewportSize",
    "WebError",
    "WebSocket",
    "WebSocketRoute",
    "Worker",
]
