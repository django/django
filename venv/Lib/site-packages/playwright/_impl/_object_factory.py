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

from typing import Dict, cast

from playwright._impl._artifact import Artifact
from playwright._impl._browser import Browser
from playwright._impl._browser_context import BrowserContext
from playwright._impl._browser_type import BrowserType
from playwright._impl._cdp_session import CDPSession
from playwright._impl._connection import ChannelOwner
from playwright._impl._dialog import Dialog
from playwright._impl._element_handle import ElementHandle
from playwright._impl._fetch import APIRequestContext
from playwright._impl._frame import Frame
from playwright._impl._js_handle import JSHandle
from playwright._impl._local_utils import LocalUtils
from playwright._impl._network import (
    Request,
    Response,
    Route,
    WebSocket,
    WebSocketRoute,
)
from playwright._impl._page import BindingCall, Page, Worker
from playwright._impl._playwright import Playwright
from playwright._impl._stream import Stream
from playwright._impl._tracing import Tracing
from playwright._impl._writable_stream import WritableStream


class DummyObject(ChannelOwner):
    def __init__(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)


def create_remote_object(
    parent: ChannelOwner, type: str, guid: str, initializer: Dict
) -> ChannelOwner:
    if type == "Artifact":
        return Artifact(parent, type, guid, initializer)
    if type == "APIRequestContext":
        return APIRequestContext(parent, type, guid, initializer)
    if type == "BindingCall":
        return BindingCall(parent, type, guid, initializer)
    if type == "Browser":
        return Browser(cast(BrowserType, parent), type, guid, initializer)
    if type == "BrowserType":
        return BrowserType(parent, type, guid, initializer)
    if type == "BrowserContext":
        return BrowserContext(parent, type, guid, initializer)
    if type == "CDPSession":
        return CDPSession(parent, type, guid, initializer)
    if type == "Dialog":
        return Dialog(parent, type, guid, initializer)
    if type == "ElementHandle":
        return ElementHandle(parent, type, guid, initializer)
    if type == "Frame":
        return Frame(parent, type, guid, initializer)
    if type == "JSHandle":
        return JSHandle(parent, type, guid, initializer)
    if type == "LocalUtils":
        local_utils = LocalUtils(parent, type, guid, initializer)
        if not local_utils._connection._local_utils:
            local_utils._connection._local_utils = local_utils
        return local_utils
    if type == "Page":
        return Page(parent, type, guid, initializer)
    if type == "Playwright":
        return Playwright(parent, type, guid, initializer)
    if type == "Request":
        return Request(parent, type, guid, initializer)
    if type == "Response":
        return Response(parent, type, guid, initializer)
    if type == "Route":
        return Route(parent, type, guid, initializer)
    if type == "Stream":
        return Stream(parent, type, guid, initializer)
    if type == "Tracing":
        return Tracing(parent, type, guid, initializer)
    if type == "WebSocket":
        return WebSocket(parent, type, guid, initializer)
    if type == "WebSocketRoute":
        return WebSocketRoute(parent, type, guid, initializer)
    if type == "Worker":
        return Worker(parent, type, guid, initializer)
    if type == "WritableStream":
        return WritableStream(parent, type, guid, initializer)
    return DummyObject(parent, type, guid, initializer)
