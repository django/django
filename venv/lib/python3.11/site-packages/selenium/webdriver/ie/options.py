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
from enum import Enum

from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.common.options import ArgOptions


class ElementScrollBehavior(Enum):
    TOP = 0
    BOTTOM = 1


class _IeOptionsDescriptor:
    """_IeOptionsDescriptor is an implementation of Descriptor Protocol:

    : Any look-up or assignment to the below attributes in `Options` class will be intercepted
    by `__get__` and `__set__` method respectively.

    - `browser_attach_timeout`
    - `element_scroll_behavior`
    - `ensure_clean_session`
    - `file_upload_dialog_timeout`
    - `force_create_process_api`
    - `force_shell_windows_api`
    - `full_page_screenshot`
    - `ignore_protected_mode_settings`
    - `ignore_zoom_level`
    - `initial_browser_url`
    - `native_events`
    - `persistent_hover`
    - `require_window_focus`
    - `use_per_process_proxy`
    - `use_legacy_file_upload_dialog_handling`
    - `attach_to_edge_chrome`
    - `edge_executable_path`


    : When an attribute lookup happens,
    Example:
        `self. browser_attach_timeout`
        `__get__` method does a dictionary look up in the dictionary `_options` in `Options` class
        and returns the value of key `browserAttachTimeout`
    : When an attribute assignment happens,
    Example:
        `self.browser_attach_timeout` = 30
        `__set__` method sets/updates the value of the key `browserAttachTimeout` in `_options`
        dictionary in `Options` class.
    """

    def __init__(self, name, expected_type):
        self.name = name
        self.expected_type = expected_type

    def __get__(self, obj, cls):
        return obj._options.get(self.name)

    def __set__(self, obj, value) -> None:
        if not isinstance(value, self.expected_type):
            raise ValueError(f"{self.name} should be of type {self.expected_type.__name__}")

        if self.name == "elementScrollBehavior" and value not in [
            ElementScrollBehavior.TOP,
            ElementScrollBehavior.BOTTOM,
        ]:
            raise ValueError("Element Scroll Behavior out of range.")
        obj._options[self.name] = value


class Options(ArgOptions):
    KEY = "se:ieOptions"
    SWITCHES = "ie.browserCommandLineSwitches"

    BROWSER_ATTACH_TIMEOUT = "browserAttachTimeout"
    ELEMENT_SCROLL_BEHAVIOR = "elementScrollBehavior"
    ENSURE_CLEAN_SESSION = "ie.ensureCleanSession"
    FILE_UPLOAD_DIALOG_TIMEOUT = "ie.fileUploadDialogTimeout"
    FORCE_CREATE_PROCESS_API = "ie.forceCreateProcessApi"
    FORCE_SHELL_WINDOWS_API = "ie.forceShellWindowsApi"
    FULL_PAGE_SCREENSHOT = "ie.enableFullPageScreenshot"
    IGNORE_PROTECTED_MODE_SETTINGS = "ignoreProtectedModeSettings"
    IGNORE_ZOOM_LEVEL = "ignoreZoomSetting"
    INITIAL_BROWSER_URL = "initialBrowserUrl"
    NATIVE_EVENTS = "nativeEvents"
    PERSISTENT_HOVER = "enablePersistentHover"
    REQUIRE_WINDOW_FOCUS = "requireWindowFocus"
    USE_PER_PROCESS_PROXY = "ie.usePerProcessProxy"
    USE_LEGACY_FILE_UPLOAD_DIALOG_HANDLING = "ie.useLegacyFileUploadDialogHandling"
    ATTACH_TO_EDGE_CHROME = "ie.edgechromium"
    EDGE_EXECUTABLE_PATH = "ie.edgepath"
    IGNORE_PROCESS_MATCH = "ie.ignoreprocessmatch"

    # Creating descriptor objects for each of the above IE options
    browser_attach_timeout = _IeOptionsDescriptor(BROWSER_ATTACH_TIMEOUT, int)
    """Gets and Sets `browser_attach_timeout`

    Usage
    -----
    - Get
        - `self.browser_attach_timeout`
    - Set
        - `self.browser_attach_timeout` = `value`

    Parameters
    ----------
    `value`: `int` (Timeout) in milliseconds
    """

    element_scroll_behavior = _IeOptionsDescriptor(ELEMENT_SCROLL_BEHAVIOR, Enum)
    """Gets and Sets `element_scroll_behavior`

    Usage
    -----
    - Get
        - `self.element_scroll_behavior`
    - Set
        - `self.element_scroll_behavior` = `value`

    Parameters
    ----------
    `value`: `int` either 0 - Top, 1 - Bottom
    """

    ensure_clean_session = _IeOptionsDescriptor(ENSURE_CLEAN_SESSION, bool)
    """Gets and Sets `ensure_clean_session`

    Usage
    -----
    - Get
        - `self.ensure_clean_session`
    - Set
        - `self.ensure_clean_session` = `value`

    Parameters
    ----------
    `value`: `bool`
    """

    file_upload_dialog_timeout = _IeOptionsDescriptor(FILE_UPLOAD_DIALOG_TIMEOUT, int)
    """Gets and Sets `file_upload_dialog_timeout`

    Usage
    -----
    - Get
        - `self.file_upload_dialog_timeout`
    - Set
        - `self.file_upload_dialog_timeout` = `value`

    Parameters
    ----------
    `value`: `int` (Timeout) in milliseconds
    """

    force_create_process_api = _IeOptionsDescriptor(FORCE_CREATE_PROCESS_API, bool)
    """Gets and Sets `force_create_process_api`

    Usage
    -----
    - Get
        - `self.force_create_process_api`
    - Set
        - `self.force_create_process_api` = `value`

    Parameters
    ----------
    `value`: `bool`
    """

    force_shell_windows_api = _IeOptionsDescriptor(FORCE_SHELL_WINDOWS_API, bool)
    """Gets and Sets `force_shell_windows_api`

    Usage
    -----
    - Get
        - `self.force_shell_windows_api`
    - Set
        - `self.force_shell_windows_api` = `value`

    Parameters
    ----------
    `value`: `bool`
    """

    full_page_screenshot = _IeOptionsDescriptor(FULL_PAGE_SCREENSHOT, bool)
    """Gets and Sets `full_page_screenshot`

    Usage
    -----
    - Get
        - `self.full_page_screenshot`
    - Set
        - `self.full_page_screenshot` = `value`

    Parameters
    ----------
    `value`: `bool`
    """

    ignore_protected_mode_settings = _IeOptionsDescriptor(IGNORE_PROTECTED_MODE_SETTINGS, bool)
    """Gets and Sets `ignore_protected_mode_settings`

    Usage
    -----
    - Get
        - `self.ignore_protected_mode_settings`
    - Set
        - `self.ignore_protected_mode_settings` = `value`

    Parameters
    ----------
    `value`: `bool`
    """

    ignore_zoom_level = _IeOptionsDescriptor(IGNORE_ZOOM_LEVEL, bool)
    """Gets and Sets `ignore_zoom_level`

    Usage
    -----
    - Get
        - `self.ignore_zoom_level`
    - Set
        - `self.ignore_zoom_level` = `value`

    Parameters
    ----------
    `value`: `bool`
    """

    initial_browser_url = _IeOptionsDescriptor(INITIAL_BROWSER_URL, str)
    """Gets and Sets `initial_browser_url`

    Usage
    -----
    - Get
        - `self.initial_browser_url`
    - Set
        - `self.initial_browser_url` = `value`

    Parameters
    ----------
    `value`: `str`
    """

    native_events = _IeOptionsDescriptor(NATIVE_EVENTS, bool)
    """Gets and Sets `native_events`

    Usage
    -----
    - Get
        - `self.native_events`
    - Set
        - `self.native_events` = `value`

    Parameters
    ----------
    `value`: `bool`
    """

    persistent_hover = _IeOptionsDescriptor(PERSISTENT_HOVER, bool)
    """Gets and Sets `persistent_hover`

    Usage
    -----
    - Get
        - `self.persistent_hover`
    - Set
        - `self.persistent_hover` = `value`

    Parameters
    ----------
    `value`: `bool`
    """

    require_window_focus = _IeOptionsDescriptor(REQUIRE_WINDOW_FOCUS, bool)
    """Gets and Sets `require_window_focus`

    Usage
    -----
    - Get
        - `self.require_window_focus`
    - Set
        - `self.require_window_focus` = `value`

    Parameters
    ----------
    `value`: `bool`
    """

    use_per_process_proxy = _IeOptionsDescriptor(USE_PER_PROCESS_PROXY, bool)
    """Gets and Sets `use_per_process_proxy`

    Usage
    -----
    - Get
        - `self.use_per_process_proxy`
    - Set
        - `self.use_per_process_proxy` = `value`

    Parameters
    ----------
    `value`: `bool`
    """

    use_legacy_file_upload_dialog_handling = _IeOptionsDescriptor(USE_LEGACY_FILE_UPLOAD_DIALOG_HANDLING, bool)
    """Gets and Sets `use_legacy_file_upload_dialog_handling`

    Usage
    -----
    - Get
        - `self.use_legacy_file_upload_dialog_handling`
    - Set
        - `self.use_legacy_file_upload_dialog_handling` = `value`

    Parameters
    ----------
    `value`: `bool`
    """

    attach_to_edge_chrome = _IeOptionsDescriptor(ATTACH_TO_EDGE_CHROME, bool)
    """Gets and Sets `attach_to_edge_chrome`

    Usage
    -----
    - Get
        - `self.attach_to_edge_chrome`
    - Set
        - `self.attach_to_edge_chrome` = `value`

    Parameters
    ----------
    `value`: `bool`
    """

    edge_executable_path = _IeOptionsDescriptor(EDGE_EXECUTABLE_PATH, str)
    """Gets and Sets `edge_executable_path`

    Usage
    -----
    - Get
        - `self.edge_executable_path`
    - Set
        - `self.edge_executable_path` = `value`

    Parameters
    ----------
    `value`: `str`
    """

    def __init__(self) -> None:
        super().__init__()
        self._options = {}
        self._additional = {}

    @property
    def options(self) -> dict:
        """:Returns: A dictionary of browser options."""
        return self._options

    @property
    def additional_options(self) -> dict:
        """:Returns: The additional options."""
        return self._additional

    def add_additional_option(self, name: str, value):
        """Adds an additional option not yet added as a safe option for IE.

        :Args:
         - name: name of the option to add
         - value: value of the option to add
        """
        self._additional[name] = value

    def to_capabilities(self) -> dict:
        """Marshals the IE options to the correct object."""
        caps = self._caps

        opts = self._options.copy()
        if self._arguments:
            opts[self.SWITCHES] = " ".join(self._arguments)

        if self._additional:
            opts.update(self._additional)

        if opts:
            caps[Options.KEY] = opts
        return caps

    @property
    def default_capabilities(self) -> dict:
        return DesiredCapabilities.INTERNETEXPLORER.copy()
