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
import pathlib
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional, Pattern, Sequence, Union, cast

from playwright._impl._api_structures import (
    ClientCertificate,
    Geolocation,
    HttpCredentials,
    ProxySettings,
    ViewportSize,
)
from playwright._impl._browser import Browser
from playwright._impl._browser_context import BrowserContext
from playwright._impl._connection import ChannelOwner, Connection, from_channel
from playwright._impl._errors import Error
from playwright._impl._helper import (
    PLAYWRIGHT_MAX_DEADLINE,
    ColorScheme,
    Contrast,
    Env,
    ForcedColors,
    HarContentPolicy,
    HarMode,
    ReducedMotion,
    ServiceWorkersPolicy,
    TimeoutSettings,
    async_readfile,
    locals_to_params,
)
from playwright._impl._json_pipe import JsonPipeTransport
from playwright._impl._network import serialize_headers, to_client_certificates_protocol
from playwright._impl._waiter import throw_on_timeout

if TYPE_CHECKING:
    from playwright._impl._playwright import Playwright


class BrowserType(ChannelOwner):
    def __init__(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        self._playwright: "Playwright"

    def __repr__(self) -> str:
        return f"<BrowserType name={self.name} executable_path={self.executable_path}>"

    @property
    def name(self) -> str:
        return self._initializer["name"]

    @property
    def executable_path(self) -> str:
        return self._initializer["executablePath"]

    async def launch(
        self,
        executablePath: Union[str, Path] = None,
        channel: str = None,
        args: Sequence[str] = None,
        ignoreDefaultArgs: Union[bool, Sequence[str]] = None,
        handleSIGINT: bool = None,
        handleSIGTERM: bool = None,
        handleSIGHUP: bool = None,
        timeout: float = None,
        env: Env = None,
        headless: bool = None,
        proxy: ProxySettings = None,
        downloadsPath: Union[str, Path] = None,
        slowMo: float = None,
        tracesDir: Union[pathlib.Path, str] = None,
        chromiumSandbox: bool = None,
        firefoxUserPrefs: Dict[str, Union[str, float, bool]] = None,
    ) -> Browser:
        params = locals_to_params(locals())
        normalize_launch_params(params)
        browser = cast(
            Browser,
            from_channel(
                await self._channel.send(
                    "launch", TimeoutSettings.launch_timeout, params
                )
            ),
        )
        browser._connect_to_browser_type(
            self, str(tracesDir) if tracesDir is not None else None
        )
        return browser

    async def launch_persistent_context(
        self,
        userDataDir: Union[str, Path],
        channel: str = None,
        executablePath: Union[str, Path] = None,
        args: Sequence[str] = None,
        ignoreDefaultArgs: Union[bool, Sequence[str]] = None,
        handleSIGINT: bool = None,
        handleSIGTERM: bool = None,
        handleSIGHUP: bool = None,
        timeout: float = None,
        env: Env = None,
        headless: bool = None,
        proxy: ProxySettings = None,
        downloadsPath: Union[str, Path] = None,
        slowMo: float = None,
        viewport: ViewportSize = None,
        screen: ViewportSize = None,
        noViewport: bool = None,
        ignoreHTTPSErrors: bool = None,
        javaScriptEnabled: bool = None,
        bypassCSP: bool = None,
        userAgent: str = None,
        locale: str = None,
        timezoneId: str = None,
        geolocation: Geolocation = None,
        permissions: Sequence[str] = None,
        extraHTTPHeaders: Dict[str, str] = None,
        offline: bool = None,
        httpCredentials: HttpCredentials = None,
        deviceScaleFactor: float = None,
        isMobile: bool = None,
        hasTouch: bool = None,
        colorScheme: ColorScheme = None,
        reducedMotion: ReducedMotion = None,
        forcedColors: ForcedColors = None,
        contrast: Contrast = None,
        acceptDownloads: bool = None,
        tracesDir: Union[pathlib.Path, str] = None,
        chromiumSandbox: bool = None,
        firefoxUserPrefs: Dict[str, Union[str, float, bool]] = None,
        recordHarPath: Union[Path, str] = None,
        recordHarOmitContent: bool = None,
        recordVideoDir: Union[Path, str] = None,
        recordVideoSize: ViewportSize = None,
        baseURL: str = None,
        strictSelectors: bool = None,
        serviceWorkers: ServiceWorkersPolicy = None,
        recordHarUrlFilter: Union[Pattern[str], str] = None,
        recordHarMode: HarMode = None,
        recordHarContent: HarContentPolicy = None,
        clientCertificates: List[ClientCertificate] = None,
    ) -> BrowserContext:
        userDataDir = self._user_data_dir(userDataDir)
        params = locals_to_params(locals())
        await self._prepare_browser_context_params(params)
        normalize_launch_params(params)
        result = await self._channel.send_return_as_dict(
            "launchPersistentContext", TimeoutSettings.launch_timeout, params
        )
        browser = cast(
            Browser,
            from_channel(result["browser"]),
        )
        browser._connect_to_browser_type(
            self, str(tracesDir) if tracesDir is not None else None
        )
        context = cast(BrowserContext, from_channel(result["context"]))
        await context._initialize_har_from_options(
            record_har_content=recordHarContent,
            record_har_mode=recordHarMode,
            record_har_omit_content=recordHarOmitContent,
            record_har_path=recordHarPath,
            record_har_url_filter=recordHarUrlFilter,
        )
        return context

    def _user_data_dir(self, userDataDir: Optional[Union[str, Path]]) -> str:
        if not userDataDir:
            return ""
        if not Path(userDataDir).is_absolute():
            # Can be dropped once we drop Python 3.9 support (10/2025):
            # https://github.com/python/cpython/issues/82852
            if sys.platform == "win32" and sys.version_info[:2] < (3, 10):
                return str(pathlib.Path.cwd() / userDataDir)
            return str(Path(userDataDir).resolve())
        return str(Path(userDataDir))

    async def connect_over_cdp(
        self,
        endpointURL: str,
        timeout: float = None,
        slowMo: float = None,
        headers: Dict[str, str] = None,
        isLocal: bool = None,
    ) -> Browser:
        params = locals_to_params(locals())
        if params.get("headers"):
            params["headers"] = serialize_headers(params["headers"])
        response = await self._channel.send_return_as_dict(
            "connectOverCDP", TimeoutSettings.launch_timeout, params
        )
        browser = cast(Browser, from_channel(response["browser"]))
        browser._connect_to_browser_type(self, None)

        return browser

    async def connect(
        self,
        wsEndpoint: str,
        timeout: float = None,
        slowMo: float = None,
        headers: Dict[str, str] = None,
        exposeNetwork: str = None,
    ) -> Browser:
        if slowMo is None:
            slowMo = 0

        headers = {**(headers if headers else {}), "x-playwright-browser": self.name}
        local_utils = self._connection.local_utils
        pipe_channel = (
            await local_utils._channel.send_return_as_dict(
                "connect",
                None,
                {
                    "wsEndpoint": wsEndpoint,
                    "headers": headers,
                    "slowMo": slowMo,
                    "timeout": timeout if timeout is not None else 0,
                    "exposeNetwork": exposeNetwork,
                },
            )
        )["pipe"]
        transport = JsonPipeTransport(self._connection._loop, pipe_channel)

        connection = Connection(
            self._connection._dispatcher_fiber,
            self._connection._object_factory,
            transport,
            self._connection._loop,
            local_utils=self._connection.local_utils,
        )
        connection.mark_as_remote()

        browser = None

        def handle_transport_close(reason: Optional[str]) -> None:
            if browser:
                for context in browser.contexts:
                    for page in context.pages:
                        page._on_close()
                    context._on_close()
                browser._on_close()
            connection.cleanup(reason)
            # TODO: Backport https://github.com/microsoft/playwright/commit/d8d5289e8692c9b1265d23ee66988d1ac5122f33
            # Give a chance to any API call promises to reject upon page/context closure.
            # This happens naturally when we receive page.onClose and browser.onClose from the server
            # in separate tasks. However, upon pipe closure we used to dispatch them all synchronously
            # here and promises did not have a chance to reject.
            # The order of rejects vs closure is a part of the API contract and our test runner
            # relies on it to attribute rejections to the right test.

        transport.once("close", handle_transport_close)

        connection._is_sync = self._connection._is_sync
        connection._loop.create_task(connection.run())
        playwright_future = connection.playwright_future

        timeout_future = throw_on_timeout(
            timeout if timeout is not None else PLAYWRIGHT_MAX_DEADLINE,
            Error("Connection timed out"),
        )
        done, pending = await asyncio.wait(
            {transport.on_error_future, playwright_future, timeout_future},
            return_when=asyncio.FIRST_COMPLETED,
        )
        if not playwright_future.done():
            playwright_future.cancel()
        if not timeout_future.done():
            timeout_future.cancel()
        playwright: "Playwright" = next(iter(done)).result()
        playwright._set_selectors(self._playwright.selectors)
        self._connection._child_ws_connections.append(connection)
        pre_launched_browser = playwright._initializer.get("preLaunchedBrowser")
        assert pre_launched_browser
        browser = cast(Browser, from_channel(pre_launched_browser))
        browser._should_close_connection_on_close = True
        browser._connect_to_browser_type(self, None)

        return browser

    async def _prepare_browser_context_params(self, params: Dict) -> None:
        if params.get("noViewport"):
            del params["noViewport"]
            params["noDefaultViewport"] = True
        if "defaultBrowserType" in params:
            del params["defaultBrowserType"]
        if "extraHTTPHeaders" in params:
            params["extraHTTPHeaders"] = serialize_headers(params["extraHTTPHeaders"])
        if "recordVideoDir" in params:
            params["recordVideo"] = {"dir": Path(params["recordVideoDir"]).absolute()}
            if "recordVideoSize" in params:
                params["recordVideo"]["size"] = params["recordVideoSize"]
                del params["recordVideoSize"]
            del params["recordVideoDir"]
        if "storageState" in params:
            storageState = params["storageState"]
            if not isinstance(storageState, dict):
                params["storageState"] = json.loads(
                    (await async_readfile(storageState)).decode()
                )
        if params.get("colorScheme", None) == "null":
            params["colorScheme"] = "no-override"
        if params.get("reducedMotion", None) == "null":
            params["reducedMotion"] = "no-override"
        if params.get("forcedColors", None) == "null":
            params["forcedColors"] = "no-override"
        if params.get("contrast", None) == "null":
            params["contrast"] = "no-override"
        if "acceptDownloads" in params:
            params["acceptDownloads"] = (
                "accept" if params["acceptDownloads"] else "deny"
            )

        if "clientCertificates" in params:
            params["clientCertificates"] = await to_client_certificates_protocol(
                params["clientCertificates"]
            )
        params["selectorEngines"] = self._playwright.selectors._selector_engines
        params["testIdAttributeName"] = (
            self._playwright.selectors._test_id_attribute_name
        )

        # Remove HAR options
        params.pop("recordHarPath", None)
        params.pop("recordHarOmitContent", None)
        params.pop("recordHarUrlFilter", None)
        params.pop("recordHarMode", None)
        params.pop("recordHarContent", None)


def normalize_launch_params(params: Dict) -> None:
    if "env" in params:
        params["env"] = [
            {"name": name, "value": str(value)}
            for [name, value] in params["env"].items()
        ]
    if "ignoreDefaultArgs" in params:
        if params["ignoreDefaultArgs"] is True:
            params["ignoreAllDefaultArgs"] = True
            del params["ignoreDefaultArgs"]
    if "executablePath" in params:
        params["executablePath"] = str(Path(params["executablePath"]))
    if "downloadsPath" in params:
        params["downloadsPath"] = str(Path(params["downloadsPath"]))
    if "tracesDir" in params:
        params["tracesDir"] = str(Path(params["tracesDir"]))
