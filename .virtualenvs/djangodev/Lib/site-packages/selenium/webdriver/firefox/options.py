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
from typing import Union

from typing_extensions import deprecated

from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.common.options import ArgOptions
from selenium.webdriver.firefox.firefox_binary import FirefoxBinary
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile


class Log:
    def __init__(self) -> None:
        self.level = None

    def to_capabilities(self) -> dict:
        if self.level:
            return {"log": {"level": self.level}}
        return {}


class Options(ArgOptions):
    KEY = "moz:firefoxOptions"

    def __init__(self) -> None:
        super().__init__()
        self._binary_location = ""
        self._preferences: dict = {}
        self._profile = None
        self.log = Log()

    @property
    @deprecated("use binary_location instead")
    def binary(self) -> FirefoxBinary:
        """Returns the FirefoxBinary instance."""
        return FirefoxBinary(self._binary_location)

    @binary.setter
    @deprecated("use binary_location instead")
    def binary(self, new_binary: Union[str, FirefoxBinary]) -> None:
        """Sets location of the browser binary, either by string or
        ``FirefoxBinary`` instance."""
        if isinstance(new_binary, FirefoxBinary):
            new_binary = new_binary._start_cmd
        self.binary_location = new_binary

    @property
    def binary_location(self) -> str:
        """:Returns: The location of the binary."""
        return self._binary_location

    @binary_location.setter  # noqa
    def binary_location(self, value: str) -> None:
        """Sets the location of the browser binary by string."""
        if not isinstance(value, str):
            raise TypeError(self.BINARY_LOCATION_ERROR)
        self._binary_location = value

    @property
    def preferences(self) -> dict:
        """:Returns: A dict of preferences."""
        return self._preferences

    def set_preference(self, name: str, value: Union[str, int, bool]):
        """Sets a preference."""
        self._preferences[name] = value

    @property
    def profile(self) -> FirefoxProfile:
        """:Returns: The Firefox profile to use."""
        return self._profile

    @profile.setter
    def profile(self, new_profile: Union[str, FirefoxProfile]) -> None:
        """Sets location of the browser profile to use, either by string or
        ``FirefoxProfile``."""
        if not isinstance(new_profile, FirefoxProfile):
            new_profile = FirefoxProfile(new_profile)
        self._profile = new_profile

    def enable_mobile(self, android_package: str = "org.mozilla.firefox", android_activity=None, device_serial=None):
        super().enable_mobile(android_package, android_activity, device_serial)

    def to_capabilities(self) -> dict:
        """Marshals the Firefox options to a `moz:firefoxOptions` object."""
        # This intentionally looks at the internal properties
        # so if a binary or profile has _not_ been set,
        # it will defer to geckodriver to find the system Firefox
        # and generate a fresh profile.
        caps = self._caps
        opts = {}

        if self._binary_location:
            opts["binary"] = self._binary_location
        if self._preferences:
            opts["prefs"] = self._preferences
        if self._profile:
            opts["profile"] = self._profile.encoded
        if self._arguments:
            opts["args"] = self._arguments
        if self.mobile_options:
            opts.update(self.mobile_options)

        opts.update(self.log.to_capabilities())

        if opts:
            caps[Options.KEY] = opts

        return caps

    @property
    def default_capabilities(self) -> dict:
        return DesiredCapabilities.FIREFOX.copy()
