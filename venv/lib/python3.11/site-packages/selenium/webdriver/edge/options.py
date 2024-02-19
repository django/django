# Licensed to the Software Freedom Conservancy (SFC) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The SFC licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

from selenium.webdriver.chromium.options import ChromiumOptions
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities


class Options(ChromiumOptions):
    KEY = "ms:edgeOptions"

    def __init__(self) -> None:
        super().__init__()
        self._use_webview = False

    @property
    def use_webview(self) -> bool:
        return self._use_webview

    @use_webview.setter
    def use_webview(self, value: bool) -> None:
        self._use_webview = bool(value)

    def to_capabilities(self) -> dict:
        """Creates a capabilities with all the options that have been set and
        :Returns: A dictionary with everything."""
        caps = super().to_capabilities()
        if self._use_webview:
            caps["browserName"] = "webview2"

        return caps

    @property
    def default_capabilities(self) -> dict:
        return DesiredCapabilities.EDGE.copy()
