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

import base64
import os
from typing import BinaryIO

from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.common.options import ArgOptions


class ChromiumOptions(ArgOptions):
    KEY = "goog:chromeOptions"

    def __init__(self) -> None:
        """Initialize ChromiumOptions with default settings."""
        super().__init__()
        self._binary_location: str = ""
        self._extension_files: list[str] = []
        self._extensions: list[str] = []
        self._experimental_options: dict[str, str | int | dict | list[str]] = {}
        self._debugger_address: str | None = None
        self._enable_webextensions: bool = False

    @property
    def binary_location(self) -> str:
        """Returns the location of the binary, otherwise an empty string."""
        return self._binary_location

    @binary_location.setter
    def binary_location(self, value: str) -> None:
        """Allows you to set where the chromium binary lives.

        Args:
            value: Path to the Chromium binary.
        """
        if not isinstance(value, str):
            raise TypeError(self.BINARY_LOCATION_ERROR)
        self._binary_location = value

    @property
    def debugger_address(self) -> str | None:
        """Returns the address of the remote devtools instance."""
        return self._debugger_address

    @debugger_address.setter
    def debugger_address(self, value: str) -> None:
        """Set the address of the remote devtools instance for active wait connection.

        Args:
            value: Address of remote devtools instance if any (hostname[:port]).
        """
        if not isinstance(value, str):
            raise TypeError("Debugger Address must be a string")
        self._debugger_address = value

    @property
    def extensions(self) -> list[str]:
        """Returns a list of encoded extensions that will be loaded."""

        def _decode(file_data: BinaryIO) -> str:
            # Should not use base64.encodestring() which inserts newlines every
            # 76 characters (per RFC 1521).  Chromedriver has to remove those
            # unnecessary newlines before decoding, causing performance hit.
            return base64.b64encode(file_data.read()).decode("utf-8")

        encoded_extensions = []
        for extension in self._extension_files:
            with open(extension, "rb") as f:
                encoded_extensions.append(_decode(f))

        return encoded_extensions + self._extensions

    def add_extension(self, extension: str) -> None:
        """Add the path to an extension to be extracted to ChromeDriver.

        Args:
            extension: Path to the *.crx file.
        """
        if extension:
            extension_to_add = os.path.abspath(os.path.expanduser(extension))
            if os.path.exists(extension_to_add):
                self._extension_files.append(extension_to_add)
            else:
                raise OSError("Path to the extension doesn't exist")
        else:
            raise ValueError("argument can not be null")

    def add_encoded_extension(self, extension: str) -> None:
        """Add Base64-encoded string with extension data to be extracted to ChromeDriver.

        Args:
            extension: Base64 encoded string with extension data.
        """
        if extension:
            self._extensions.append(extension)
        else:
            raise ValueError("argument can not be null")

    @property
    def experimental_options(self) -> dict:
        """Returns a dictionary of experimental options for chromium."""
        return self._experimental_options

    def add_experimental_option(self, name: str, value: str | int | dict | list[str]) -> None:
        """Adds an experimental option which is passed to chromium.

        Args:
            name: The experimental option name.
            value: The option value.
        """
        self._experimental_options[name] = value

    @property
    def enable_webextensions(self) -> bool:
        """Return whether webextension support is enabled for Chromium-based browsers."""
        return self._enable_webextensions

    @enable_webextensions.setter
    def enable_webextensions(self, value: bool) -> None:
        """Enables or disables webextension support for Chromium-based browsers.

        Args:
            value: True to enable webextension support, False to disable.

        Notes:
            - When enabled, this automatically adds the required Chromium flags:
                - --enable-unsafe-extension-debugging
                - --remote-debugging-pipe
            - When disabled, this removes BOTH flags listed above, even if they were manually added via add_argument()
              before enabling webextensions.
            - Enabling --remote-debugging-pipe makes the connection b/w chromedriver
              and the browser use a pipe instead of a port, disabling many CDP functionalities
              like devtools
        """
        self._enable_webextensions = value
        if value:
            # Add required flags for Chromium webextension support
            required_flags = ["--enable-unsafe-extension-debugging", "--remote-debugging-pipe"]
            for flag in required_flags:
                if flag not in self._arguments:
                    self.add_argument(flag)
        else:
            # Remove webextension flags if disabling
            flags_to_remove = ["--enable-unsafe-extension-debugging", "--remote-debugging-pipe"]
            for flag in flags_to_remove:
                if flag in self._arguments:
                    self._arguments.remove(flag)

    def to_capabilities(self) -> dict:
        """Creates a capabilities with all the options that have been set.

        Returns:
            A dictionary with all set options.
        """
        caps = self._caps
        chrome_options = self.experimental_options.copy()
        if self.mobile_options:
            chrome_options.update(self.mobile_options)
        chrome_options["extensions"] = self.extensions
        if self.binary_location:
            chrome_options["binary"] = self.binary_location
        chrome_options["args"] = self._arguments
        if self.debugger_address:
            chrome_options["debuggerAddress"] = self.debugger_address

        caps[self.KEY] = chrome_options

        return caps

    @property
    def default_capabilities(self) -> dict:
        return DesiredCapabilities.CHROME.copy()
