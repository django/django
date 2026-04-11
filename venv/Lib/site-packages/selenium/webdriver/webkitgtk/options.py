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

from typing import Any

from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.common.options import ArgOptions


class Options(ArgOptions):
    KEY = "webkitgtk:browserOptions"

    def __init__(self) -> None:
        super().__init__()
        self._binary_location = ""
        self._overlay_scrollbars_enabled = True

    @property
    def binary_location(self) -> str:
        """Return the location of the browser binary or an empty string."""
        return self._binary_location

    @binary_location.setter
    def binary_location(self, value: str) -> None:
        """Allows you to set the browser binary to launch.

        Args:
            value: path to the browser binary
        """
        self._binary_location = value

    @property
    def overlay_scrollbars_enabled(self) -> bool:
        """Return whether overlay scrollbars should be enabled."""
        return self._overlay_scrollbars_enabled

    @overlay_scrollbars_enabled.setter
    def overlay_scrollbars_enabled(self, value) -> None:
        """Allows you to enable or disable overlay scrollbars.

        Args:
            value: True or False
        """
        self._overlay_scrollbars_enabled = value

    def to_capabilities(self) -> dict:
        """Create a capabilities dictionary with all set options."""
        caps = self._caps

        browser_options: dict[str, Any] = {}
        if self.binary_location:
            browser_options["binary"] = self.binary_location
        if self.arguments:
            browser_options["args"] = self.arguments
        browser_options["useOverlayScrollbars"] = self.overlay_scrollbars_enabled

        caps[Options.KEY] = browser_options

        return caps

    @property
    def default_capabilities(self):
        return DesiredCapabilities.WEBKITGTK.copy()
