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

import warnings
from abc import ABCMeta, abstractmethod
from enum import Enum

from selenium.common.exceptions import InvalidArgumentException
from selenium.webdriver.common.proxy import Proxy


class PageLoadStrategy(str, Enum):
    """Enum of possible page load strategies.

    Selenium support following strategies:
        * normal (default) - waits for all resources to download
        * eager - DOM access is ready, but other resources like images may still be loading
        * none - does not block `WebDriver` at all

    Docs: https://www.selenium.dev/documentation/webdriver/drivers/options/#pageloadstrategy.
    """

    normal = "normal"
    eager = "eager"
    none = "none"


class _BaseOptionsDescriptor:
    def __init__(self, name):
        self.name = name

    def __get__(self, obj, cls):
        if self.name == "enableBidi":
            # whether BiDi is or will be enabled
            value = obj._caps.get("webSocketUrl")
            return value is True or isinstance(value, str)
        if self.name == "webSocketUrl":
            # Return socket url or None if not created yet
            value = obj._caps.get(self.name)
            return None if not isinstance(value, str) else value
        if self.name in ("acceptInsecureCerts", "strictFileInteractability", "setWindowRect", "se:downloadsEnabled"):
            return obj._caps.get(self.name, False)
        return obj._caps.get(self.name)

    def __set__(self, obj, value):
        if self.name == "enableBidi":
            obj.set_capability("webSocketUrl", value)
        else:
            obj.set_capability(self.name, value)


class _PageLoadStrategyDescriptor:
    """Determines the point at which a navigation command is returned.

    See:
      - https://w3c.github.io/webdriver/#dfn-table-of-page-load-strategies.

    Args:
        strategy: the strategy corresponding to a document readiness state
    """

    def __init__(self, name):
        self.name = name

    def __get__(self, obj, cls):
        return obj._caps.get(self.name)

    def __set__(self, obj, value):
        if value in ("normal", "eager", "none"):
            obj.set_capability(self.name, value)
        else:
            raise ValueError("Strategy can only be one of the following: normal, eager, none")


class _UnHandledPromptBehaviorDescriptor:
    """How the driver should respond when an alert is present and the command sent is not handling the alert.

    See:
      - https://w3c.github.io/webdriver/#dfn-table-of-page-load-strategies:

    Args:
        behavior: behavior to use when an alert is encountered

    Returns:
        Values for implicit timeout, pageLoad timeout and script timeout if set (in milliseconds)
    """

    def __init__(self, name):
        self.name = name

    def __get__(self, obj, cls):
        return obj._caps.get(self.name)

    def __set__(self, obj, value):
        if value in ("dismiss", "accept", "dismiss and notify", "accept and notify", "ignore"):
            obj.set_capability(self.name, value)
        else:
            raise ValueError(
                "Behavior can only be one of the following: dismiss, accept, dismiss and notify, "
                "accept and notify, ignore"
            )


class _TimeoutsDescriptor:
    """How long the driver should wait for actions to complete before returning an error.

    See:
      - https://w3c.github.io/webdriver/#timeouts

    Args:
        timeouts: values in milliseconds for implicit wait, page load and script timeout

    Returns:
        Values for implicit timeout, pageLoad timeout and script timeout if set (in milliseconds)
    """

    def __init__(self, name):
        self.name = name

    def __get__(self, obj, cls):
        return obj._caps.get(self.name)

    def __set__(self, obj, value):
        if all(x in ("implicit", "pageLoad", "script") for x in value.keys()):
            obj.set_capability(self.name, value)
        else:
            raise ValueError("Timeout keys can only be one of the following: implicit, pageLoad, script")


class _ProxyDescriptor:
    """Descriptor for proxy property access.

    Returns:
        Proxy if set, otherwise None.
    """

    def __init__(self, name):
        self.name = name

    def __get__(self, obj, cls):
        return obj._proxy

    def __set__(self, obj, value):
        if not isinstance(value, Proxy):
            raise InvalidArgumentException("Only Proxy objects can be passed in.")
        obj._proxy = value
        obj._caps[self.name] = value.to_capabilities()


class BaseOptions(metaclass=ABCMeta):
    """Base class for individual browser options."""

    browser_version = _BaseOptionsDescriptor("browserVersion")
    """Gets and Sets the version of the browser.

    Usage:
        - Get: `self.browser_version`
        - Set: `self.browser_version = value`

    Args:
        value: str

    Returns:
        str when getting, None when setting.
    """

    platform_name = _BaseOptionsDescriptor("platformName")
    """Gets and Sets name of the platform.

    Usage:
        - Get: `self.platform_name`
        - Set: `self.platform_name = value`

    Args:
        value: str

    Returns:
        str when getting, None when setting.
    """

    accept_insecure_certs = _BaseOptionsDescriptor("acceptInsecureCerts")
    """Gets and Set whether the session accepts insecure certificates.

    Usage:
        - Get: `self.accept_insecure_certs`
        - Set: `self.accept_insecure_certs = value`

    Args:
        value: bool

    Returns:
        bool when getting, None when setting.
    """

    strict_file_interactability = _BaseOptionsDescriptor("strictFileInteractability")
    """Gets and Sets whether session is about file interactability.

    Usage:
        - Get: `self.strict_file_interactability`
        - Set: `self.strict_file_interactability = value`

    Args:
        value: bool

    Returns:
        bool when getting, None when setting.
    """

    set_window_rect = _BaseOptionsDescriptor("setWindowRect")
    """Gets and Sets window size and position.

    Usage:
        - Get: `self.set_window_rect`
        - Set: `self.set_window_rect = value`

    Args:
        value: bool

    Returns:
        bool when getting, None when setting.
    """

    enable_bidi = _BaseOptionsDescriptor("enableBidi")
    """Gets and Set whether the session has WebDriverBiDi enabled.

    Usage:
        - Get: `self.enable_bidi`
        - Set: `self.enable_bidi = value`

    Args:
        value: bool

    Returns:
        bool when getting, None when setting.
    """

    page_load_strategy = _PageLoadStrategyDescriptor("pageLoadStrategy")
    """Gets and Sets page load strategy, the default is "normal".

    Usage:
        - Get: `self.page_load_strategy`
        - Set: `self.page_load_strategy = value`

    Args:
        value: str

    Returns:
        str when getting, None when setting.
    """

    unhandled_prompt_behavior = _UnHandledPromptBehaviorDescriptor("unhandledPromptBehavior")
    """Gets and Sets unhandled prompt behavior, the default is "dismiss and notify".

    Usage:
        - Get: `self.unhandled_prompt_behavior`
        - Set: `self.unhandled_prompt_behavior = value`

    Args:
        value: str

    Returns:
        str when getting, None when setting.
    """

    timeouts = _TimeoutsDescriptor("timeouts")
    """Gets and Sets implicit timeout, pageLoad timeout and script timeout if set (in milliseconds).

    Usage:
        - Get: `self.timeouts`
        - Set: `self.timeouts = value`

    Args:
        value: dict

    Returns:
        dict when getting, None when setting.
    """

    proxy = _ProxyDescriptor("proxy")
    """Sets and Gets Proxy.

    Usage:
        - Get: `self.proxy`
        - Set: `self.proxy = value`

    Args:
        value: Proxy

    Returns:
        Proxy when getting, None when setting.
    """

    enable_downloads = _BaseOptionsDescriptor("se:downloadsEnabled")
    """Gets and Sets whether session can download files.

    Usage:
        - Get: `self.enable_downloads`
        - Set: `self.enable_downloads = value`

    Args:
        value: bool

    Returns:
        bool when getting, None when setting.
    """

    web_socket_url = _BaseOptionsDescriptor("webSocketUrl")
    """Gets and Sets WebSocket URL.

    Usage:
        - Get: `self.web_socket_url`
        - Set: `self.web_socket_url = value`

    Args:
        value: str

    Returns:
        str when getting, None when setting.
    """

    def __init__(self) -> None:
        super().__init__()
        self._caps = self.default_capabilities
        self._proxy = None
        self.set_capability("pageLoadStrategy", PageLoadStrategy.normal)
        self.mobile_options: dict[str, str] | None = None
        self._ignore_local_proxy = False

    @property
    def capabilities(self):
        return self._caps

    def set_capability(self, name, value) -> None:
        """Sets a capability."""
        self._caps[name] = value

    def enable_mobile(
        self,
        android_package: str | None = None,
        android_activity: str | None = None,
        device_serial: str | None = None,
    ) -> None:
        """Enables mobile browser use for browsers that support it.

        Args:
            android_package: The name of the android package to start
            android_activity: The name of the android activity
            device_serial: The device serial number
        """
        if not android_package:
            raise AttributeError("android_package must be passed in")
        self.mobile_options = {"androidPackage": android_package}
        if android_activity:
            self.mobile_options["androidActivity"] = android_activity
        if device_serial:
            self.mobile_options["androidDeviceSerial"] = device_serial

    @abstractmethod
    def to_capabilities(self):
        """Convert options into capabilities dictionary."""

    @property
    @abstractmethod
    def default_capabilities(self):
        """Return minimal capabilities necessary as a dictionary."""

    def ignore_local_proxy_environment_variables(self) -> None:
        """Ignore HTTP_PROXY and HTTPS_PROXY environment variables."""
        self._ignore_local_proxy = True


class ArgOptions(BaseOptions):
    BINARY_LOCATION_ERROR = "Binary Location Must be a String"
    # FedCM capability key
    FEDCM_CAPABILITY = "fedcm:accounts"

    def __init__(self) -> None:
        super().__init__()
        self._arguments: list[str] = []

    @property
    def arguments(self):
        """Returns a list of arguments needed for the browser."""
        return self._arguments

    def add_argument(self, argument: str) -> None:
        """Adds an argument to the list.

        Args:
            argument: Sets the arguments
        """
        if argument:
            self._arguments.append(argument)
        else:
            raise ValueError("argument can not be null")

    def ignore_local_proxy_environment_variables(self) -> None:
        """Ignore HTTP_PROXY and HTTPS_PROXY environment variables.

        This method is deprecated; use a Proxy instance with ProxyType.DIRECT instead.
        """
        warnings.warn(
            "using ignore_local_proxy_environment_variables in Options has been deprecated, "
            "instead, create a Proxy instance with ProxyType.DIRECT to ignore proxy settings, "
            "pass the proxy instance into a ClientConfig constructor, "
            "pass the client config instance into the Webdriver constructor",
            DeprecationWarning,
            stacklevel=2,
        )

        super().ignore_local_proxy_environment_variables()

    def to_capabilities(self):
        return self._caps

    @property
    def default_capabilities(self):
        return {}
