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

from pathlib import Path
from types import SimpleNamespace
from typing import (
    TYPE_CHECKING,
    Dict,
    List,
    Optional,
    Pattern,
    Sequence,
    Set,
    Union,
    cast,
)

from playwright._impl._api_structures import (
    ClientCertificate,
    Geolocation,
    HttpCredentials,
    ProxySettings,
    StorageState,
    ViewportSize,
)
from playwright._impl._artifact import Artifact
from playwright._impl._browser_context import BrowserContext
from playwright._impl._cdp_session import CDPSession
from playwright._impl._connection import ChannelOwner, from_channel
from playwright._impl._errors import is_target_closed_error
from playwright._impl._helper import (
    ColorScheme,
    Contrast,
    ForcedColors,
    HarContentPolicy,
    HarMode,
    ReducedMotion,
    ServiceWorkersPolicy,
    locals_to_params,
    make_dirs_for_file,
)
from playwright._impl._page import Page

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl._browser_type import BrowserType


class Browser(ChannelOwner):
    Events = SimpleNamespace(
        Disconnected="disconnected",
    )

    def __init__(
        self, parent: "BrowserType", type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        self._browser_type: Optional["BrowserType"] = None
        self._is_connected = True
        self._should_close_connection_on_close = False
        self._cr_tracing_path: Optional[str] = None

        self._contexts: Set[BrowserContext] = set()
        self._traces_dir: Optional[str] = None
        self._channel.on(
            "context",
            lambda params: self._did_create_context(
                cast(BrowserContext, from_channel(params["context"]))
            ),
        )
        self._channel.on("close", lambda _: self._on_close())
        self._close_reason: Optional[str] = None

    def __repr__(self) -> str:
        return f"<Browser type={self._browser_type} version={self.version}>"

    def _connect_to_browser_type(
        self,
        browser_type: "BrowserType",
        traces_dir: Optional[str] = None,
    ) -> None:
        # Note: when using connect(), `browserType` is different from `this.parent`.
        # This is why browser type is not wired up in the constructor, and instead this separate method is called later on.
        self._browser_type = browser_type
        self._traces_dir = traces_dir
        for context in self._contexts:
            self._setup_browser_context(context)

    def _did_create_context(self, context: BrowserContext) -> None:
        context._browser = self
        self._contexts.add(context)
        # Note: when connecting to a browser, initial contexts arrive before `_browserType` is set,
        # and will be configured later in `ConnectToBrowserType`.
        if self._browser_type:
            self._setup_browser_context(context)

    def _setup_browser_context(self, context: BrowserContext) -> None:
        context._tracing._traces_dir = self._traces_dir
        assert self._browser_type is not None
        self._browser_type._playwright.selectors._contexts_for_selectors.add(context)

    def _on_close(self) -> None:
        self._is_connected = False
        self.emit(Browser.Events.Disconnected, self)

    @property
    def contexts(self) -> List[BrowserContext]:
        return list(self._contexts)

    @property
    def browser_type(self) -> "BrowserType":
        assert self._browser_type is not None
        return self._browser_type

    def is_connected(self) -> bool:
        return self._is_connected

    async def new_context(
        self,
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
        defaultBrowserType: str = None,
        proxy: ProxySettings = None,
        recordHarPath: Union[Path, str] = None,
        recordHarOmitContent: bool = None,
        recordVideoDir: Union[Path, str] = None,
        recordVideoSize: ViewportSize = None,
        storageState: Union[StorageState, str, Path] = None,
        baseURL: str = None,
        strictSelectors: bool = None,
        serviceWorkers: ServiceWorkersPolicy = None,
        recordHarUrlFilter: Union[Pattern[str], str] = None,
        recordHarMode: HarMode = None,
        recordHarContent: HarContentPolicy = None,
        clientCertificates: List[ClientCertificate] = None,
    ) -> BrowserContext:
        params = locals_to_params(locals())
        assert self._browser_type is not None
        await self._browser_type._prepare_browser_context_params(params)

        channel = await self._channel.send("newContext", None, params)
        context = cast(BrowserContext, from_channel(channel))
        await context._initialize_har_from_options(
            record_har_content=recordHarContent,
            record_har_mode=recordHarMode,
            record_har_omit_content=recordHarOmitContent,
            record_har_path=recordHarPath,
            record_har_url_filter=recordHarUrlFilter,
        )
        return context

    async def new_page(
        self,
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
        forcedColors: ForcedColors = None,
        contrast: Contrast = None,
        reducedMotion: ReducedMotion = None,
        acceptDownloads: bool = None,
        defaultBrowserType: str = None,
        proxy: ProxySettings = None,
        recordHarPath: Union[Path, str] = None,
        recordHarOmitContent: bool = None,
        recordVideoDir: Union[Path, str] = None,
        recordVideoSize: ViewportSize = None,
        storageState: Union[StorageState, str, Path] = None,
        baseURL: str = None,
        strictSelectors: bool = None,
        serviceWorkers: ServiceWorkersPolicy = None,
        recordHarUrlFilter: Union[Pattern[str], str] = None,
        recordHarMode: HarMode = None,
        recordHarContent: HarContentPolicy = None,
        clientCertificates: List[ClientCertificate] = None,
    ) -> Page:
        params = locals_to_params(locals())

        async def inner() -> Page:
            context = await self.new_context(**params)
            page = await context.new_page()
            page._owned_context = context
            context._owner_page = page
            return page

        return await self._connection.wrap_api_call(inner, title="Create page")

    async def close(self, reason: str = None) -> None:
        self._close_reason = reason
        try:
            if self._should_close_connection_on_close:
                await self._connection.stop_async()
            else:
                await self._channel.send("close", None, {"reason": reason})
        except Exception as e:
            if not is_target_closed_error(e):
                raise e

    @property
    def version(self) -> str:
        return self._initializer["version"]

    async def new_browser_cdp_session(self) -> CDPSession:
        return from_channel(await self._channel.send("newBrowserCDPSession", None))

    async def start_tracing(
        self,
        page: Page = None,
        path: Union[str, Path] = None,
        screenshots: bool = None,
        categories: Sequence[str] = None,
    ) -> None:
        params = locals_to_params(locals())
        if page:
            params["page"] = page._channel
        if path:
            self._cr_tracing_path = str(path)
            params["path"] = str(path)
        await self._channel.send("startTracing", None, params)

    async def stop_tracing(self) -> bytes:
        artifact = cast(
            Artifact, from_channel(await self._channel.send("stopTracing", None))
        )
        buffer = await artifact.read_info_buffer()
        await artifact.delete()
        if self._cr_tracing_path:
            make_dirs_for_file(self._cr_tracing_path)
            with open(self._cr_tracing_path, "wb") as f:
                f.write(buffer)
            self._cr_tracing_path = None
        return buffer
