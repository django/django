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

from typing import Dict

from playwright._impl._browser_type import BrowserType
from playwright._impl._connection import ChannelOwner, from_channel
from playwright._impl._fetch import APIRequest
from playwright._impl._selectors import Selectors


class Playwright(ChannelOwner):
    devices: Dict
    selectors: Selectors
    chromium: BrowserType
    firefox: BrowserType
    webkit: BrowserType
    request: APIRequest

    def __init__(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        self.request = APIRequest(self)
        self.chromium = from_channel(initializer["chromium"])
        self.chromium._playwright = self
        self.firefox = from_channel(initializer["firefox"])
        self.firefox._playwright = self
        self.webkit = from_channel(initializer["webkit"])
        self.webkit._playwright = self

        self.selectors = Selectors(self._loop, self._dispatcher_fiber)

        self.devices = self._connection.local_utils.devices

    def __getitem__(self, value: str) -> "BrowserType":
        if value == "chromium":
            return self.chromium
        elif value == "firefox":
            return self.firefox
        elif value == "webkit":
            return self.webkit
        raise ValueError("Invalid browser " + value)

    def _set_selectors(self, selectors: Selectors) -> None:
        self.selectors = selectors

    async def stop(self) -> None:
        pass
