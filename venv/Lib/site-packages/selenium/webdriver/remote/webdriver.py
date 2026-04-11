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

"""The WebDriver implementation."""

import base64
import contextlib
import copy
import os
import pkgutil
import tempfile
import types
import warnings
import zipfile
from abc import ABCMeta
from base64 import b64decode, urlsafe_b64encode
from contextlib import asynccontextmanager, contextmanager
from importlib import import_module
from typing import Any, cast

from selenium.common.exceptions import (
    InvalidArgumentException,
    JavascriptException,
    NoSuchCookieException,
    NoSuchElementException,
    WebDriverException,
)
from selenium.webdriver.common.bidi.browser import Browser
from selenium.webdriver.common.bidi.browsing_context import BrowsingContext
from selenium.webdriver.common.bidi.emulation import Emulation
from selenium.webdriver.common.bidi.input import Input
from selenium.webdriver.common.bidi.network import Network
from selenium.webdriver.common.bidi.permissions import Permissions
from selenium.webdriver.common.bidi.script import Script
from selenium.webdriver.common.bidi.session import Session
from selenium.webdriver.common.bidi.storage import Storage
from selenium.webdriver.common.bidi.webextension import WebExtension
from selenium.webdriver.common.by import By
from selenium.webdriver.common.fedcm.dialog import Dialog
from selenium.webdriver.common.options import ArgOptions, BaseOptions
from selenium.webdriver.common.print_page_options import PrintOptions
from selenium.webdriver.common.timeouts import Timeouts
from selenium.webdriver.common.virtual_authenticator import (
    Credential,
    VirtualAuthenticatorOptions,
    required_virtual_authenticator,
)
from selenium.webdriver.remote.bidi_connection import BidiConnection
from selenium.webdriver.remote.client_config import ClientConfig
from selenium.webdriver.remote.command import Command
from selenium.webdriver.remote.errorhandler import ErrorHandler
from selenium.webdriver.remote.fedcm import FedCM
from selenium.webdriver.remote.file_detector import FileDetector, LocalFileDetector
from selenium.webdriver.remote.locator_converter import LocatorConverter
from selenium.webdriver.remote.mobile import Mobile
from selenium.webdriver.remote.remote_connection import RemoteConnection
from selenium.webdriver.remote.script_key import ScriptKey
from selenium.webdriver.remote.shadowroot import ShadowRoot
from selenium.webdriver.remote.switch_to import SwitchTo
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.remote.websocket_connection import WebSocketConnection
from selenium.webdriver.support.relative_locator import RelativeBy

cdp = None


def import_cdp() -> None:
    global cdp
    if not cdp:
        cdp = import_module("selenium.webdriver.common.bidi.cdp")


def _create_caps(caps) -> dict:
    """Makes a W3C alwaysMatch capabilities object.

    Filters out capability names that are not in the W3C spec. Spec-compliant
    drivers will reject requests containing unknown capability names.

    Moves the Firefox profile, if present, from the old location to the new Firefox
    options object.

    Args:
        caps: A dictionary of capabilities requested by the caller.
    """
    caps = copy.deepcopy(caps)
    always_match = {}
    for k, v in caps.items():
        always_match[k] = v
    return {"capabilities": {"firstMatch": [{}], "alwaysMatch": always_match}}


def get_remote_connection(
    capabilities: dict,
    command_executor: str | RemoteConnection,
    keep_alive: bool,
    ignore_local_proxy: bool,
    client_config: ClientConfig | None = None,
) -> RemoteConnection:
    if isinstance(command_executor, str):
        client_config = client_config or ClientConfig(remote_server_addr=command_executor)
        client_config.remote_server_addr = command_executor
        command_executor = RemoteConnection(client_config=client_config)

    browser_name = capabilities.get("browserName")
    handler: type[RemoteConnection]
    if browser_name == "chrome":
        from selenium.webdriver.chrome.remote_connection import ChromeRemoteConnection

        handler = ChromeRemoteConnection
    elif browser_name == "MicrosoftEdge":
        from selenium.webdriver.edge.remote_connection import EdgeRemoteConnection

        handler = EdgeRemoteConnection
    elif browser_name == "firefox":
        from selenium.webdriver.firefox.remote_connection import FirefoxRemoteConnection

        handler = FirefoxRemoteConnection
    elif browser_name == "Safari":
        from selenium.webdriver.safari.remote_connection import SafariRemoteConnection

        handler = SafariRemoteConnection
    else:
        handler = RemoteConnection

    if hasattr(command_executor, "client_config") and command_executor.client_config:
        remote_server_addr = command_executor.client_config.remote_server_addr
    else:
        remote_server_addr = command_executor

    return handler(
        remote_server_addr=remote_server_addr,
        keep_alive=keep_alive,
        ignore_proxy=ignore_local_proxy,
        client_config=client_config,
    )


def create_matches(options: list[BaseOptions]) -> dict:
    capabilities: dict[str, Any] = {"capabilities": {}}
    opts = []
    for opt in options:
        opts.append(opt.to_capabilities())
    opts_size = len(opts)
    samesies = {}

    # Can not use bitwise operations on the dicts or lists due to
    # https://bugs.python.org/issue38210
    for i in range(opts_size):
        min_index = i
        if i + 1 < opts_size:
            first_keys = opts[min_index].keys()

            for kys in first_keys:
                if kys in opts[i + 1].keys():
                    if opts[min_index][kys] == opts[i + 1][kys]:
                        samesies.update({kys: opts[min_index][kys]})

    always = {}
    for k, v in samesies.items():
        always[k] = v

    for opt_dict in opts:
        for k in always:
            del opt_dict[k]

    capabilities["capabilities"]["alwaysMatch"] = always
    capabilities["capabilities"]["firstMatch"] = opts

    return capabilities


class BaseWebDriver(metaclass=ABCMeta):
    """Abstract Base Class for all Webdriver subtypes.

    ABC's allow custom implementations of Webdriver to be registered so
    that isinstance type checks will succeed.
    """


class WebDriver(BaseWebDriver):
    """Control a browser by sending commands to a remote WebDriver server.

    This class expects the remote server to be running the WebDriver wire protocol
    as defined at https://www.selenium.dev/documentation/legacy/json_wire_protocol/.

    Attributes:
    -----------
    session_id - String ID of the browser session started and controlled by this WebDriver.
    capabilities - Dictionary of effective capabilities of this browser session as returned
        by the remote server. See https://www.selenium.dev/documentation/legacy/desired_capabilities/
    command_executor : str or remote_connection.RemoteConnection object used to execute commands.
    error_handler - errorhandler.ErrorHandler object used to handle errors.
    """

    _web_element_cls = WebElement
    _shadowroot_cls = ShadowRoot

    def __init__(
        self,
        command_executor: str | RemoteConnection = "http://127.0.0.1:4444",
        keep_alive: bool = True,
        file_detector: FileDetector | None = None,
        options: BaseOptions | list[BaseOptions] | None = None,
        locator_converter: LocatorConverter | None = None,
        web_element_cls: type[WebElement] | None = None,
        client_config: ClientConfig | None = None,
    ) -> None:
        """Create a new driver instance that issues commands using the WebDriver protocol.

        Args:
            command_executor: Either a string representing the URL of the remote
                server or a custom remote_connection.RemoteConnection object.
                Defaults to 'http://127.0.0.1:4444/wd/hub'.
            keep_alive: (Deprecated) Whether to configure
                remote_connection.RemoteConnection to use HTTP keep-alive.
                Defaults to True.
            file_detector: Pass a custom file detector object during
                instantiation. If None, the default LocalFileDetector() will be
                used.
            options: Instance of a driver options.Options class.
            locator_converter: Custom locator converter to use. Defaults to None.
            web_element_cls: Custom class to use for web elements. Defaults to
                WebElement.
            client_config: Custom client configuration to use. Defaults to None.
        """
        if options is None:
            raise TypeError(
                "missing 1 required keyword-only argument: 'options' (instance of driver `options.Options` class)"
            )
        elif isinstance(options, list):
            capabilities = create_matches(options)
            _ignore_local_proxy = False
        else:
            capabilities = options.to_capabilities()
            _ignore_local_proxy = options._ignore_local_proxy
        self.command_executor = command_executor
        if isinstance(self.command_executor, (str, bytes)):
            self.command_executor = get_remote_connection(
                capabilities,
                command_executor=command_executor,
                keep_alive=keep_alive,
                ignore_local_proxy=_ignore_local_proxy,
                client_config=client_config,
            )
        self._is_remote = True
        self.session_id: str | None = None
        self.caps: dict[str, Any] = {}
        self.pinned_scripts: dict[str, Any] = {}
        self.error_handler = ErrorHandler()
        self._switch_to = SwitchTo(self)
        self._mobile = Mobile(self)
        self.file_detector = file_detector or LocalFileDetector()
        self.locator_converter = locator_converter or LocatorConverter()
        self._web_element_cls = web_element_cls or self._web_element_cls
        self._authenticator_id = None
        self.start_client()
        self.start_session(capabilities)
        self._fedcm = FedCM(self)

        self._websocket_connection: WebSocketConnection | None = None
        self._script: Script | None = None
        self._network: Network | None = None
        self._browser: Browser | None = None
        self._bidi_session: Session | None = None
        self._browsing_context: BrowsingContext | None = None
        self._storage: Storage | None = None
        self._webextension: WebExtension | None = None
        self._permissions: Permissions | None = None
        self._emulation: Emulation | None = None
        self._input: Input | None = None
        self._devtools: Any | None = None

    def __repr__(self) -> str:
        return f'<{type(self).__module__}.{type(self).__name__} (session="{self.session_id}")>'

    def __enter__(self) -> "WebDriver":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: types.TracebackType | None,
    ):
        self.quit()

    @contextmanager
    def file_detector_context(self, file_detector_class, *args, **kwargs):
        """Override the current file detector temporarily within a limited context.

        Ensures the original file detector is set after exiting the context.

        Args:
            file_detector_class: Class of the desired file detector. If the
                class is different from the current file_detector, then the
                class is instantiated with args and kwargs and used as a file
                detector during the duration of the context manager.
            *args: Optional arguments that get passed to the file detector class
                during instantiation.
            **kwargs: Keyword arguments, passed the same way as args.

        Example:
            ```
            with webdriver.file_detector_context(UselessFileDetector):
                someinput.send_keys("/etc/hosts")
            ````
        """
        last_detector = None
        if not isinstance(self.file_detector, file_detector_class):
            last_detector = self.file_detector
            self.file_detector = file_detector_class(*args, **kwargs)
        try:
            yield
        finally:
            if last_detector:
                self.file_detector = last_detector

    @property
    def mobile(self) -> Mobile:
        return self._mobile

    @property
    def name(self) -> str:
        """Returns the name of the underlying browser for this instance."""
        if "browserName" in self.caps:
            return self.caps["browserName"]
        raise KeyError("browserName not specified in session capabilities")

    def start_client(self) -> None:
        """Called before starting a new session.

        This method may be overridden to define custom startup behavior.
        """
        pass

    def stop_client(self) -> None:
        """Called after executing a quit command.

        This method may be overridden to define custom shutdown
        behavior.
        """
        pass

    def start_session(self, capabilities: dict) -> None:
        """Creates a new session with the desired capabilities.

        Args:
            capabilities: A capabilities dict to start the session with.
        """
        caps = _create_caps(capabilities)
        try:
            response = self.execute(Command.NEW_SESSION, caps)["value"]
            self.session_id = response.get("sessionId")
            self.caps = response.get("capabilities")
        except Exception:
            if hasattr(self, "service") and self.service is not None:
                self.service.stop()
            raise

    def _wrap_value(self, value):
        if isinstance(value, dict):
            converted = {}
            for key, val in value.items():
                converted[key] = self._wrap_value(val)
            return converted
        if isinstance(value, self._web_element_cls):
            return {"element-6066-11e4-a52e-4f735466cecf": value.id}
        if isinstance(value, self._shadowroot_cls):
            return {"shadow-6066-11e4-a52e-4f735466cecf": value.id}
        if isinstance(value, list):
            return list(self._wrap_value(item) for item in value)
        return value

    def create_web_element(self, element_id: str) -> WebElement:
        """Creates a web element with the specified `element_id`."""
        return self._web_element_cls(self, element_id)

    def _unwrap_value(self, value):
        if isinstance(value, dict):
            if "element-6066-11e4-a52e-4f735466cecf" in value:
                return self.create_web_element(value["element-6066-11e4-a52e-4f735466cecf"])
            if "shadow-6066-11e4-a52e-4f735466cecf" in value:
                return self._shadowroot_cls(self, value["shadow-6066-11e4-a52e-4f735466cecf"])
            for key, val in value.items():
                value[key] = self._unwrap_value(val)
            return value
        if isinstance(value, list):
            return list(self._unwrap_value(item) for item in value)
        return value

    def execute_cdp_cmd(self, cmd: str, cmd_args: dict):
        """Execute Chrome Devtools Protocol command and get returned result.

        The command and command args should follow chrome devtools protocol domains/commands:
          - https://chromedevtools.github.io/devtools-protocol/

        Args:
            cmd: Command name.
            cmd_args: Command args. Empty dict {} if there is no command args.

        Returns:
            A dict, empty dict {} if there is no result to return. To
            getResponseBody: {'base64Encoded': False, 'body': 'response body
            string'}

        Example:
            `driver.execute_cdp_cmd("Network.getResponseBody", {"requestId": requestId})`
        """
        return self.execute("executeCdpCommand", {"cmd": cmd, "params": cmd_args})["value"]

    def execute(self, driver_command: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Sends a command to be executed by a command.CommandExecutor.

        Args:
            driver_command: The name of the command to execute as a string.
            params: A dictionary of named parameters to send with the command.

        Returns:
            The command's JSON response loaded into a dictionary object.
        """
        params = self._wrap_value(params)

        if self.session_id:
            if not params:
                params = {"sessionId": self.session_id}
            elif "sessionId" not in params:
                params["sessionId"] = self.session_id

        response = cast(RemoteConnection, self.command_executor).execute(driver_command, params)

        if response:
            self.error_handler.check_response(response)
            response["value"] = self._unwrap_value(response.get("value", None))
            return response
        # If the server doesn't send a response, assume the command was
        # a success
        return {"success": 0, "value": None, "sessionId": self.session_id}

    def get(self, url: str) -> None:
        """Navigate the browser to the specified URL.

        The method does not return until the page is fully loaded (i.e. the
        onload event has fired) in the current window or tab.

        Args:
            url: The URL to be opened by the browser. Must include the protocol
                (e.g., http://, https://).

        Example:
            `driver.get("https://example.com")`
        """
        self.execute(Command.GET, {"url": url})

    @property
    def title(self) -> str:
        """Returns the title of the current page.

        Example:
            ```
            element = driver.find_element(By.ID, "foo")
            print(element.title())
            ```
        """
        return self.execute(Command.GET_TITLE).get("value", "")

    def pin_script(self, script: str, script_key=None) -> ScriptKey:
        """Store a JavaScript script by a unique hashable ID for later execution.

        Example:
            `script = "return document.getElementById('foo').value"`
        """
        script_key_instance = ScriptKey(script_key)
        self.pinned_scripts[script_key_instance.id] = script
        return script_key_instance

    def unpin(self, script_key: ScriptKey) -> None:
        """Remove a pinned script from storage.

        Example:
            `driver.unpin(script_key)`
        """
        try:
            self.pinned_scripts.pop(script_key.id)
        except KeyError:
            raise KeyError(f"No script with key: {script_key} existed in {self.pinned_scripts}") from None

    def get_pinned_scripts(self) -> list[str]:
        """Return a list of all pinned scripts.

        Example:
            `pinned_scripts = driver.get_pinned_scripts()`
        """
        return list(self.pinned_scripts)

    def execute_script(self, script: str, *args):
        """Synchronously Executes JavaScript in the current window/frame.

        Args:
            script: The javascript to execute.
            *args: Any applicable arguments for your JavaScript.

        Example:
            ```
            id = "username"
            value = "test_user"
            driver.execute_script("document.getElementById(arguments[0]).value = arguments[1];", id, value)
            ```
        """
        if isinstance(script, ScriptKey):
            try:
                script = self.pinned_scripts[script.id]
            except KeyError:
                raise JavascriptException("Pinned script could not be found")

        converted_args = list(args)
        command = Command.W3C_EXECUTE_SCRIPT

        return self.execute(command, {"script": script, "args": converted_args})["value"]

    def execute_async_script(self, script: str, *args) -> dict:
        """Asynchronously Executes JavaScript in the current window/frame.

        Args:
            script: The javascript to execute.
            *args: Any applicable arguments for your JavaScript.

        Example:
            ```
            script = "var callback = arguments[arguments.length - 1]; "
                "window.setTimeout(function(){ callback('timeout') }, 3000);"
            driver.execute_async_script(script)
            ```
        """
        converted_args = list(args)
        command = Command.W3C_EXECUTE_SCRIPT_ASYNC

        return self.execute(command, {"script": script, "args": converted_args})["value"]

    @property
    def current_url(self) -> str:
        """Gets the URL of the current page."""
        return self.execute(Command.GET_CURRENT_URL)["value"]

    @property
    def page_source(self) -> str:
        """Gets the source of the current page."""
        return self.execute(Command.GET_PAGE_SOURCE)["value"]

    def close(self) -> None:
        """Closes the current window."""
        self.execute(Command.CLOSE)

    def quit(self) -> None:
        """Quits the driver and closes every associated window."""
        try:
            self.execute(Command.QUIT)
        finally:
            self.stop_client()
            executor = cast(RemoteConnection, self.command_executor)
            executor.close()

    @property
    def current_window_handle(self) -> str:
        """Returns the handle of the current window."""
        return self.execute(Command.W3C_GET_CURRENT_WINDOW_HANDLE)["value"]

    @property
    def window_handles(self) -> list[str]:
        """Returns the handles of all windows within the current session."""
        return self.execute(Command.W3C_GET_WINDOW_HANDLES)["value"]

    def maximize_window(self) -> None:
        """Maximizes the current window that webdriver is using."""
        command = Command.W3C_MAXIMIZE_WINDOW
        self.execute(command, None)

    def fullscreen_window(self) -> None:
        """Invokes the window manager-specific 'full screen' operation."""
        self.execute(Command.FULLSCREEN_WINDOW)

    def minimize_window(self) -> None:
        """Invokes the window manager-specific 'minimize' operation."""
        self.execute(Command.MINIMIZE_WINDOW)

    def print_page(self, print_options: PrintOptions | None = None) -> str:
        """Takes PDF of the current page.

        The driver makes a best effort to return a PDF based on the
        provided parameters.
        """
        options: dict[str, Any] | Any = {}
        if print_options:
            options = print_options.to_dict()

        return self.execute(Command.PRINT_PAGE, options)["value"]

    @property
    def switch_to(self) -> SwitchTo:
        """Return an object containing all options to switch focus into.

        Returns:
            An object containing all options to switch focus into.

        Examples:
            `element = driver.switch_to.active_element`
            `alert = driver.switch_to.alert`
            `driver.switch_to.default_content()`
            `driver.switch_to.frame("frame_name")`
            `driver.switch_to.frame(1)`
            `driver.switch_to.frame(driver.find_elements(By.TAG_NAME, "iframe")[0])`
            `driver.switch_to.parent_frame()`
            `driver.switch_to.window("main")`
        """
        return self._switch_to

    # Navigation
    def back(self) -> None:
        """Goes one step backward in the browser history."""
        self.execute(Command.GO_BACK)

    def forward(self) -> None:
        """Goes one step forward in the browser history."""
        self.execute(Command.GO_FORWARD)

    def refresh(self) -> None:
        """Refreshes the current page."""
        self.execute(Command.REFRESH)

    def get_cookies(self) -> list[dict]:
        """Get all cookies visible to the current WebDriver instance.

        Returns:
            A list of dictionaries, corresponding to cookies visible in the
            current session.
        """
        return self.execute(Command.GET_ALL_COOKIES)["value"]

    def get_cookie(self, name) -> dict | None:
        """Get a single cookie by name (case-sensitive,).

        Returns:
             A cookie dictionary or None if not found.

        Raises:
            ValueError if the name is empty or whitespace.

        Example:
            `cookie = driver.get_cookie("my_cookie")`
        """
        if not name or name.isspace():
            raise ValueError("Cookie name cannot be empty")

        with contextlib.suppress(NoSuchCookieException):
            return self.execute(Command.GET_COOKIE, {"name": name})["value"]

        return None

    def delete_cookie(self, name) -> None:
        """Delete a single cookie with the given name (case-sensitive).

        Raises:
            ValueError if the name is empty or whitespace.

        Example:
            `driver.delete_cookie("my_cookie")`
        """
        # Firefox deletes all cookies when "" is passed as name
        if not name or name.isspace():
            raise ValueError("Cookie name cannot be empty")

        self.execute(Command.DELETE_COOKIE, {"name": name})

    def delete_all_cookies(self) -> None:
        """Delete all cookies in the scope of the session."""
        self.execute(Command.DELETE_ALL_COOKIES)

    def add_cookie(self, cookie_dict) -> None:
        """Adds a cookie to your current session.

        Args:
            cookie_dict: A dictionary object, with required keys - "name" and
                "value"; Optional keys - "path", "domain", "secure", "httpOnly",
                "expiry", "sameSite".

        Examples:
            `driver.add_cookie({"name": "foo", "value": "bar"})`
            `driver.add_cookie({"name": "foo", "value": "bar", "path": "/"})`
            `driver.add_cookie({"name": "foo", "value": "bar", "path": "/", "secure": True})`
            `driver.add_cookie({"name": "foo", "value": "bar", "sameSite": "Strict"})`
        """
        if "sameSite" in cookie_dict:
            assert cookie_dict["sameSite"] in ["Strict", "Lax", "None"]
            self.execute(Command.ADD_COOKIE, {"cookie": cookie_dict})
        else:
            self.execute(Command.ADD_COOKIE, {"cookie": cookie_dict})

    # Timeouts
    def implicitly_wait(self, time_to_wait: float) -> None:
        """Set a sticky implicit timeout for element location and command completion.

        This method sets a timeout that applies to all element location strategies
        for the duration of the session. It only needs to be called once per session.
        To set the timeout for asynchronous script execution, see set_script_timeout.

        Args:
            time_to_wait: Amount of time to wait (in seconds).

        Example:
            `driver.implicitly_wait(30)`
        """
        self.execute(Command.SET_TIMEOUTS, {"implicit": int(float(time_to_wait) * 1000)})

    def set_script_timeout(self, time_to_wait: float) -> None:
        """Set the timeout for asynchronous script execution.

        This timeout specifies how long a script can run during an
        execute_async_script call before throwing an error.

        Args:
            time_to_wait: The amount of time to wait (in seconds).

        Example:
            `driver.set_script_timeout(30)`
        """
        self.execute(Command.SET_TIMEOUTS, {"script": int(float(time_to_wait) * 1000)})

    def set_page_load_timeout(self, time_to_wait: float) -> None:
        """Set the timeout for page load completion.

        This specifies how long to wait for a page load to complete before
        throwing an error.

        Args:
            time_to_wait: The amount of time to wait (in seconds).

        Example:
            `driver.set_page_load_timeout(30)`
        """
        try:
            self.execute(Command.SET_TIMEOUTS, {"pageLoad": int(float(time_to_wait) * 1000)})
        except WebDriverException:
            self.execute(Command.SET_TIMEOUTS, {"ms": float(time_to_wait) * 1000, "type": "page load"})

    @property
    def timeouts(self) -> Timeouts:
        """Get all the timeouts that have been set on the current session.

        Returns:
            A named tuple with the following fields:
              - implicit_wait: The time to wait for elements to be found.
              - page_load: The time to wait for a page to load.
              - script: The time to wait for scripts to execute.

        Example:
            `driver.timeouts`
        """
        timeouts = self.execute(Command.GET_TIMEOUTS)["value"]
        timeouts["implicit_wait"] = timeouts.pop("implicit") / 1000
        timeouts["page_load"] = timeouts.pop("pageLoad") / 1000
        timeouts["script"] = timeouts.pop("script") / 1000
        return Timeouts(**timeouts)

    @timeouts.setter
    def timeouts(self, timeouts) -> None:
        """Set all timeouts for the session.

        This will override any previously set timeouts.

        Example:
            ```
            my_timeouts = Timeouts()
            my_timeouts.implicit_wait = 10
            driver.timeouts = my_timeouts
            ```
        """
        _ = self.execute(Command.SET_TIMEOUTS, timeouts._to_json())["value"]

    def find_element(self, by: str | RelativeBy = By.ID, value: str | None = None) -> WebElement:
        """Find an element given a By strategy and locator.

        Args:
            by: The locating strategy to use. Default is `By.ID`. Supported
                values include: By.ID, By.NAME, By.XPATH, By.CSS_SELECTOR,
                By.CLASS_NAME, By.TAG_NAME, By.LINK_TEXT, By.PARTIAL_LINK_TEXT,
                or RelativeBy.
            value: The locator value to use with the specified `by` strategy.

        Returns:
            The first matching WebElement found on the page.

        Example:
            `element = driver.find_element(By.ID, 'foo')`
        """
        by, value = self.locator_converter.convert(by, value)

        if isinstance(by, RelativeBy):
            elements = self.find_elements(by=by, value=value)
            if not elements:
                raise NoSuchElementException(f"Cannot locate relative element with: {by.root}")
            return elements[0]

        return self.execute(Command.FIND_ELEMENT, {"using": by, "value": value})["value"]

    def find_elements(self, by: str | RelativeBy = By.ID, value: str | None = None) -> list[WebElement]:
        """Find elements given a By strategy and locator.

        Args:
            by: The locating strategy to use. Default is `By.ID`. Supported
                values include: By.ID, By.NAME, By.XPATH, By.CSS_SELECTOR,
                By.CLASS_NAME, By.TAG_NAME, By.LINK_TEXT, By.PARTIAL_LINK_TEXT,
                or RelativeBy.
            value: The locator value to use with the specified `by` strategy.

        Returns:
            List of WebElements matching locator strategy found on the page.

        Example:
            `element = driver.find_elements(By.ID, 'foo')`
        """
        by, value = self.locator_converter.convert(by, value)

        if isinstance(by, RelativeBy):
            _pkg = ".".join(__name__.split(".")[:-1])
            raw_data = pkgutil.get_data(_pkg, "findElements.js")
            if raw_data is None:
                raise FileNotFoundError(f"Could not find findElements.js in package {_pkg}")
            raw_function = raw_data.decode("utf8")
            find_element_js = f"/* findElements */return ({raw_function}).apply(null, arguments);"
            return self.execute_script(find_element_js, by.to_dict())

        # Return empty list if driver returns null
        # See https://github.com/SeleniumHQ/selenium/issues/4555
        return self.execute(Command.FIND_ELEMENTS, {"using": by, "value": value})["value"] or []

    @property
    def capabilities(self) -> dict:
        """Returns the drivers current capabilities being used."""
        return self.caps

    def get_screenshot_as_file(self, filename) -> bool:
        """Save a screenshot of the current window to a PNG image file.

        Returns:
            False if there is any IOError, else returns True. Use full paths in your filename.

        Args:
            filename: The full path you wish to save your screenshot to. This
                should end with a `.png` extension.

        Example:
            `driver.get_screenshot_as_file("./screenshots/foo.png")`
        """
        if not str(filename).lower().endswith(".png"):
            warnings.warn(
                "name used for saved screenshot does not match file type. It should end with a `.png` extension",
                UserWarning,
                stacklevel=2,
            )
        png = self.get_screenshot_as_png()
        try:
            with open(filename, "wb") as f:
                f.write(png)
        except OSError:
            return False
        finally:
            del png
        return True

    def save_screenshot(self, filename) -> bool:
        """Save a screenshot of the current window to a PNG image file.

        Returns:
            False if there is any IOError, else returns True. Use full paths in your filename.

        Args:
            filename: The full path you wish to save your screenshot to. This
                should end with a `.png` extension.

        Example:
            `driver.save_screenshot("./screenshots/foo.png")`
        """
        return self.get_screenshot_as_file(filename)

    def get_screenshot_as_png(self) -> bytes:
        """Gets the screenshot of the current window as a binary data.

        Example:
            `driver.get_screenshot_as_png()`
        """
        return b64decode(self.get_screenshot_as_base64().encode("ascii"))

    def get_screenshot_as_base64(self) -> str:
        """Get a base64-encoded screenshot of the current window.

        This encoding is useful for embedding screenshots in HTML.

        Example:
            `driver.get_screenshot_as_base64()`
        """
        return self.execute(Command.SCREENSHOT)["value"]

    def set_window_size(self, width, height, windowHandle: str = "current") -> None:
        """Sets the width and height of the current window.

        Args:
            width: The width in pixels to set the window to.
            height: The height in pixels to set the window to.
            windowHandle: The handle of the window to resize. Default is "current".

        Example:
            `driver.set_window_size(800, 600)`
        """
        self._check_if_window_handle_is_current(windowHandle)
        self.set_window_rect(width=int(width), height=int(height))

    def get_window_size(self, windowHandle: str = "current") -> dict:
        """Gets the width and height of the current window.

        Example:
            `driver.get_window_size()`
        """
        self._check_if_window_handle_is_current(windowHandle)
        size = self.get_window_rect()

        if size.get("value", None):
            size = size["value"]

        return {k: size[k] for k in ("width", "height")}

    def set_window_position(self, x: float, y: float, windowHandle: str = "current") -> dict:
        """Sets the x,y position of the current window.

        Args:
            x: The x-coordinate in pixels to set the window position.
            y: The y-coordinate in pixels to set the window position.
            windowHandle: The handle of the window to reposition. Default is "current".

        Example:
            `driver.set_window_position(0, 0)`
        """
        self._check_if_window_handle_is_current(windowHandle)
        return self.set_window_rect(x=int(x), y=int(y))

    def get_window_position(self, windowHandle="current") -> dict:
        """Gets the x,y position of the current window.

        Example:
            `driver.get_window_position()`
        """
        self._check_if_window_handle_is_current(windowHandle)
        position = self.get_window_rect()

        return {k: position[k] for k in ("x", "y")}

    def _check_if_window_handle_is_current(self, windowHandle: str) -> None:
        """Warns if the window handle is not equal to `current`."""
        if windowHandle != "current":
            warnings.warn("Only 'current' window is supported for W3C compatible browsers.", stacklevel=2)

    def get_window_rect(self) -> dict:
        """Get the window's position and size.

        Returns:
            x, y coordinates and height and width of the current window.

        Example:
            `driver.get_window_rect()`
        """
        return self.execute(Command.GET_WINDOW_RECT)["value"]

    def set_window_rect(self, x=None, y=None, width=None, height=None) -> dict:
        """Set the window's position and size.

        Sets the x, y coordinates and height and width of the current window.
        This method is only supported for W3C compatible browsers; other browsers
        should use `set_window_position` and `set_window_size`.

        Example:
            `driver.set_window_rect(x=10, y=10)`
            `driver.set_window_rect(width=100, height=200)`
            `driver.set_window_rect(x=10, y=10, width=100, height=200)`
        """
        if (x is None and y is None) and (not height and not width):
            raise InvalidArgumentException("x and y or height and width need values")

        return self.execute(Command.SET_WINDOW_RECT, {"x": x, "y": y, "width": width, "height": height})["value"]

    @property
    def file_detector(self) -> FileDetector:
        return self._file_detector

    @file_detector.setter
    def file_detector(self, detector) -> None:
        """Set the file detector for keyboard input.

        By default, this is set to a file detector that does nothing.
        See FileDetector, LocalFileDetector, and UselessFileDetector.

        Args:
            detector: The detector to use. Must not be None.
        """
        if not detector:
            raise WebDriverException("You may not set a file detector that is null")
        if not isinstance(detector, FileDetector):
            raise WebDriverException("Detector has to be instance of FileDetector")
        self._file_detector = detector

    @property
    def orientation(self) -> dict:
        """Gets the current orientation of the device.

        Example:
            `orientation = driver.orientation`
        """
        return self.execute(Command.GET_SCREEN_ORIENTATION)["value"]

    @orientation.setter
    def orientation(self, value) -> None:
        """Sets the current orientation of the device.

        Args:
            value: Orientation to set it to.

        Example:
            `driver.orientation = "landscape"`
        """
        allowed_values = ["LANDSCAPE", "PORTRAIT"]
        if value.upper() in allowed_values:
            self.execute(Command.SET_SCREEN_ORIENTATION, {"orientation": value})
        else:
            raise WebDriverException("You can only set the orientation to 'LANDSCAPE' and 'PORTRAIT'")

    def start_devtools(self) -> tuple[Any, WebSocketConnection]:
        global cdp
        import_cdp()
        if self.caps.get("se:cdp"):
            ws_url = self.caps.get("se:cdp")
            cdp_version = self.caps.get("se:cdpVersion")
            if cdp_version is None:
                raise WebDriverException("CDP version not found in capabilities")
            version = cdp_version.split(".")[0]
        else:
            version, ws_url = self._get_cdp_details()

        if not ws_url:
            raise WebDriverException("Unable to find url to connect to from capabilities")

        if cdp is None:
            raise WebDriverException("CDP module not loaded")

        self._devtools = cdp.import_devtools(version)
        if self._websocket_connection:
            return self._devtools, self._websocket_connection
        if self.caps["browserName"].lower() == "firefox":
            raise RuntimeError("CDP support for Firefox has been removed. Please switch to WebDriver BiDi.")
        if not isinstance(self.command_executor, RemoteConnection):
            raise WebDriverException("command_executor must be a RemoteConnection instance for CDP support")
        self._websocket_connection = WebSocketConnection(
            ws_url,
            self.command_executor.client_config.websocket_timeout,
            self.command_executor.client_config.websocket_interval,
        )
        targets = self._websocket_connection.execute(self._devtools.target.get_targets())
        for target in targets:
            if target.target_id == self.current_window_handle:
                target_id = target.target_id
                break
        session = self._websocket_connection.execute(self._devtools.target.attach_to_target(target_id, True))
        self._websocket_connection.session_id = session
        return self._devtools, self._websocket_connection

    @asynccontextmanager
    async def bidi_connection(self):
        global cdp
        import_cdp()
        if self.caps.get("se:cdp"):
            ws_url = self.caps.get("se:cdp")
            version = self.caps.get("se:cdpVersion").split(".")[0]
        else:
            version, ws_url = self._get_cdp_details()

        if not ws_url:
            raise WebDriverException("Unable to find url to connect to from capabilities")

        devtools = cdp.import_devtools(version)
        async with cdp.open_cdp(ws_url) as conn:
            targets = await conn.execute(devtools.target.get_targets())
            for target in targets:
                if target.target_id == self.current_window_handle:
                    target_id = target.target_id
                    break
            async with conn.open_session(target_id) as session:
                yield BidiConnection(session, cdp, devtools)

    @property
    def script(self) -> Script:
        if not self._websocket_connection:
            self._start_bidi()

        if not self._script:
            self._script = Script(self._websocket_connection, self)

        return self._script

    def _start_bidi(self) -> None:
        if self.caps.get("webSocketUrl"):
            ws_url = self.caps.get("webSocketUrl")
        else:
            raise WebDriverException("Unable to find url to connect to from capabilities")

        if not isinstance(self.command_executor, RemoteConnection):
            raise WebDriverException("command_executor must be a RemoteConnection instance for BiDi support")

        self._websocket_connection = WebSocketConnection(
            ws_url,
            self.command_executor.client_config.websocket_timeout,
            self.command_executor.client_config.websocket_interval,
        )

    @property
    def network(self) -> Network:
        if not self._websocket_connection:
            self._start_bidi()

        assert self._websocket_connection is not None
        if not hasattr(self, "_network") or self._network is None:
            assert self._websocket_connection is not None
            self._network = Network(self._websocket_connection)

        return self._network

    @property
    def browser(self) -> Browser:
        """Returns a browser module object for BiDi browser commands.

        Returns:
            An object containing access to BiDi browser commands.

        Examples:
            `user_context = driver.browser.create_user_context()`
            `user_contexts = driver.browser.get_user_contexts()`
            `client_windows = driver.browser.get_client_windows()`
            `driver.browser.remove_user_context(user_context)`
        """
        if not self._websocket_connection:
            self._start_bidi()

        if self._browser is None:
            self._browser = Browser(self._websocket_connection)

        return self._browser

    @property
    def _session(self) -> Session:
        """Returns the BiDi session object for the current WebDriver session."""
        if not self._websocket_connection:
            self._start_bidi()

        if self._bidi_session is None:
            self._bidi_session = Session(self._websocket_connection)

        return self._bidi_session

    @property
    def browsing_context(self) -> BrowsingContext:
        """Returns a browsing context module object for BiDi browsing context commands.

        Returns:
            An object containing access to BiDi browsing context commands.

        Examples:
            `context_id = driver.browsing_context.create(type="tab")`
            `driver.browsing_context.navigate(context=context_id, url="https://www.selenium.dev")`
            `driver.browsing_context.capture_screenshot(context=context_id)`
            `driver.browsing_context.close(context_id)`
        """
        if not self._websocket_connection:
            self._start_bidi()

        if self._browsing_context is None:
            self._browsing_context = BrowsingContext(self._websocket_connection)

        return self._browsing_context

    @property
    def storage(self) -> Storage:
        """Returns a storage module object for BiDi storage commands.

        Returns:
            An object containing access to BiDi storage commands.

        Examples:
            ```
            cookie_filter = CookieFilter(name="example")
            result = driver.storage.get_cookies(filter=cookie_filter)
            cookie=PartialCookie("name", BytesValue(BytesValue.TYPE_STRING, "value")
            driver.storage.set_cookie(cookie=cookie, "domain"))
            cookie_filter=CookieFilter(name="example")
            driver.storage.delete_cookies(filter=cookie_filter)
            ```
        """
        if not self._websocket_connection:
            self._start_bidi()

        assert self._websocket_connection is not None
        if self._storage is None:
            self._storage = Storage(self._websocket_connection)

        return self._storage

    @property
    def permissions(self) -> Permissions:
        """Get a permissions module object for BiDi permissions commands.

        Returns:
            An object containing access to BiDi permissions commands.

        Examples:
            ```
            from selenium.webdriver.common.bidi.permissions import PermissionDescriptor, PermissionState

            descriptor = PermissionDescriptor("geolocation")
            driver.permissions.set_permission(descriptor, PermissionState.GRANTED, "https://example.com")
            ```
        """
        if not self._websocket_connection:
            self._start_bidi()

        if self._permissions is None:
            self._permissions = Permissions(self._websocket_connection)

        return self._permissions

    @property
    def webextension(self) -> WebExtension:
        """Get a webextension module object for BiDi webextension commands.

        Returns:
            An object containing access to BiDi webextension commands.

        Examples:
            `extension_path = "/path/to/extension"`
            `extension_result = driver.webextension.install(path=extension_path)`
            `driver.webextension.uninstall(extension_result)`
        """
        if not self._websocket_connection:
            self._start_bidi()

        if self._webextension is None:
            self._webextension = WebExtension(self._websocket_connection)

        return self._webextension

    @property
    def emulation(self) -> Emulation:
        """Get an emulation module object for BiDi emulation commands.

        Returns:
            An object containing access to BiDi emulation commands.

        Examples:
            ```
            from selenium.webdriver.common.bidi.emulation import GeolocationCoordinates

            coordinates = GeolocationCoordinates(37.7749, -122.4194)
            driver.emulation.set_geolocation_override(coordinates=coordinates, contexts=[context_id])
            ```
        """
        if not self._websocket_connection:
            self._start_bidi()

        assert self._websocket_connection is not None
        if self._emulation is None:
            self._emulation = Emulation(self._websocket_connection)

        return self._emulation

    @property
    def input(self) -> Input:
        """Get an input module object for BiDi input commands.

        Returns:
            An object containing access to BiDi input commands.

        Examples:
            ```
            from selenium.webdriver.common.bidi.input import KeySourceActions, KeyDownAction, KeyUpAction

            actions = KeySourceActions(id="keyboard", actions=[KeyDownAction(value="a"), KeyUpAction(value="a")])
            driver.input.perform_actions(driver.current_window_handle, [actions])
            driver.input.release_actions(driver.current_window_handle)
            ```
        """
        if not self._websocket_connection:
            self._start_bidi()

        if self._input is None:
            self._input = Input(self._websocket_connection)

        return self._input

    def _get_cdp_details(self):
        import json

        import urllib3

        http = urllib3.PoolManager()
        try:
            if self.caps.get("browserName") == "chrome":
                debugger_address = self.caps.get("goog:chromeOptions").get("debuggerAddress")
            elif self.caps.get("browserName") in ("MicrosoftEdge", "webview2"):
                debugger_address = self.caps.get("ms:edgeOptions").get("debuggerAddress")
        except AttributeError:
            raise WebDriverException("Can't get debugger address.")

        res = http.request("GET", f"http://{debugger_address}/json/version")
        data = json.loads(res.data)

        browser_version = data.get("Browser")
        websocket_url = data.get("webSocketDebuggerUrl")

        import re

        version = re.search(r".*/(\d+)\.", browser_version).group(1)

        return version, websocket_url

    # Virtual Authenticator Methods
    def add_virtual_authenticator(self, options: VirtualAuthenticatorOptions) -> None:
        """Adds a virtual authenticator with the given options.

        Example:
            ```
            from selenium.webdriver.common.virtual_authenticator import VirtualAuthenticatorOptions

            options = VirtualAuthenticatorOptions(protocol="u2f", transport="usb", device_id="myDevice123")
            driver.add_virtual_authenticator(options)
            ```
        """
        self._authenticator_id = self.execute(Command.ADD_VIRTUAL_AUTHENTICATOR, options.to_dict())["value"]

    @property
    def virtual_authenticator_id(self) -> str | None:
        """Returns the id of the virtual authenticator."""
        return self._authenticator_id

    @required_virtual_authenticator
    def remove_virtual_authenticator(self) -> None:
        """Removes a previously added virtual authenticator.

        The authenticator is no longer valid after removal, so no
        methods may be called.
        """
        self.execute(Command.REMOVE_VIRTUAL_AUTHENTICATOR, {"authenticatorId": self._authenticator_id})
        self._authenticator_id = None

    @required_virtual_authenticator
    def add_credential(self, credential: Credential) -> None:
        """Injects a credential into the authenticator.

        Example:
            ```
            from selenium.webdriver.common.credential import Credential

            credential = Credential(id="user@example.com", password="aPassword")
            driver.add_credential(credential)
            ```
        """
        self.execute(Command.ADD_CREDENTIAL, {**credential.to_dict(), "authenticatorId": self._authenticator_id})

    @required_virtual_authenticator
    def get_credentials(self) -> list[Credential]:
        """Returns the list of credentials owned by the authenticator."""
        credential_data = self.execute(Command.GET_CREDENTIALS, {"authenticatorId": self._authenticator_id})
        return [Credential.from_dict(credential) for credential in credential_data["value"]]

    @required_virtual_authenticator
    def remove_credential(self, credential_id: str | bytearray) -> None:
        """Removes a credential from the authenticator.

        Example:
            `credential_id = "user@example.com"`
            `driver.remove_credential(credential_id)`
        """
        # Check if the credential is bytearray converted to b64 string
        if isinstance(credential_id, bytearray):
            credential_id = urlsafe_b64encode(credential_id).decode()

        self.execute(
            Command.REMOVE_CREDENTIAL, {"credentialId": credential_id, "authenticatorId": self._authenticator_id}
        )

    @required_virtual_authenticator
    def remove_all_credentials(self) -> None:
        """Removes all credentials from the authenticator."""
        self.execute(Command.REMOVE_ALL_CREDENTIALS, {"authenticatorId": self._authenticator_id})

    @required_virtual_authenticator
    def set_user_verified(self, verified: bool) -> None:
        """Set whether the authenticator will simulate success or failure on user verification.

        Args:
            verified: True if the authenticator will pass user verification,
                False otherwise.

        Example:
            `driver.set_user_verified(True)`
        """
        self.execute(Command.SET_USER_VERIFIED, {"authenticatorId": self._authenticator_id, "isUserVerified": verified})

    def get_downloadable_files(self) -> list:
        """Retrieves the downloadable files as a list of file names."""
        if "se:downloadsEnabled" not in self.capabilities:
            raise WebDriverException("You must enable downloads in order to work with downloadable files.")

        return self.execute(Command.GET_DOWNLOADABLE_FILES)["value"]["names"]

    def download_file(self, file_name: str, target_directory: str) -> None:
        """Download a file with the specified file name to the target directory.

        Args:
            file_name: The name of the file to download.
            target_directory: The path to the directory to save the downloaded file.

        Example:
            `driver.download_file("example.zip", "/path/to/directory")`
        """
        if "se:downloadsEnabled" not in self.capabilities:
            raise WebDriverException("You must enable downloads in order to work with downloadable files.")

        if not os.path.exists(target_directory):
            os.makedirs(target_directory)

        contents = self.execute(Command.DOWNLOAD_FILE, {"name": file_name})["value"]["contents"]

        with tempfile.TemporaryDirectory() as tmp_dir:
            zip_file = os.path.join(tmp_dir, file_name + ".zip")
            with open(zip_file, "wb") as file:
                file.write(base64.b64decode(contents))

            with zipfile.ZipFile(zip_file, "r") as zip_ref:
                zip_ref.extractall(target_directory)

    def delete_downloadable_files(self) -> None:
        """Deletes all downloadable files."""
        if "se:downloadsEnabled" not in self.capabilities:
            raise WebDriverException("You must enable downloads in order to work with downloadable files.")

        self.execute(Command.DELETE_DOWNLOADABLE_FILES)

    def fire_session_event(self, event_type: str, payload: dict | None = None) -> dict:
        """Fire a custom session event to the remote server event bus.

        This allows test code to trigger server-side utilities that subscribe to
        the event bus.

        Args:
            event_type: The type of event (e.g., "test:failed", "log:collect", "marker:add").
            payload: Optional data to include with the event.

        Returns:
            A dictionary containing the response data including success status,
            event type, and timestamp.

        Raises:
            WebDriverException: If the event cannot be fired.

        Examples:
            Simple event::

                driver.fire_session_event("test:started")

            Event with payload::

                driver.fire_session_event("test:failed", {"testName": "LoginTest", "error": "Element not found"})
        """
        params: dict[str, str | dict] = {"eventType": event_type}
        if payload:
            params["payload"] = payload
        return self.execute(Command.FIRE_SESSION_EVENT, params)["value"]

    @property
    def fedcm(self) -> FedCM:
        """Get the Federated Credential Management (FedCM) dialog commands.

        Returns:
            An object providing access to all Federated Credential Management
            (FedCM) dialog commands.

        Examples:
            `driver.fedcm.title`
            `driver.fedcm.subtitle`
            `driver.fedcm.dialog_type`
            `driver.fedcm.account_list`
            `driver.fedcm.select_account(0)`
            `driver.fedcm.accept()`
            `driver.fedcm.dismiss()`
            `driver.fedcm.enable_delay()`
            `driver.fedcm.disable_delay()`
            `driver.fedcm.reset_cooldown()`
        """
        return self._fedcm

    @property
    def supports_fedcm(self) -> bool:
        """Returns whether the browser supports FedCM capabilities."""
        return self.capabilities.get(ArgOptions.FEDCM_CAPABILITY, False)

    def _require_fedcm_support(self) -> None:
        """Raises an exception if FedCM is not supported."""
        if not self.supports_fedcm:
            raise WebDriverException(
                "This browser does not support Federated Credential Management. "
                "Please ensure you're using a supported browser."
            )

    @property
    def dialog(self) -> Dialog:
        """Returns the FedCM dialog object for interaction."""
        self._require_fedcm_support()
        return Dialog(self)

    def fedcm_dialog(self, timeout=5, poll_frequency=0.5, ignored_exceptions=None):
        """Waits for and returns the FedCM dialog.

        Args:
            timeout: How long to wait for the dialog.
            poll_frequency: How frequently to poll.
            ignored_exceptions: Exceptions to ignore while waiting.

        Returns:
            The FedCM dialog object if found.

        Raises:
            TimeoutException: If dialog doesn't appear.
            WebDriverException: If FedCM not supported.
        """
        from selenium.common.exceptions import NoAlertPresentException
        from selenium.webdriver.support.wait import WebDriverWait

        self._require_fedcm_support()

        if ignored_exceptions is None:
            ignored_exceptions = (NoAlertPresentException,)

        def _check_fedcm() -> Dialog | None:
            try:
                dialog = Dialog(self)
                return dialog if dialog.type else None
            except NoAlertPresentException:
                return None

        wait = WebDriverWait(self, timeout, poll_frequency=poll_frequency, ignored_exceptions=ignored_exceptions)
        return wait.until(lambda _: _check_fedcm())
