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

import importlib
import logging
import os

# Enable debug logging if SE_DEBUG environment variable is set
if os.environ.get("SE_DEBUG"):
    logger = logging.getLogger("selenium")
    logger.setLevel(logging.DEBUG)
    if not logger.handlers:
        logger.addHandler(logging.StreamHandler())
    logger.warning(
        "Environment Variable `SE_DEBUG` is set; "
        "Selenium is forcing verbose logging which may override user-specified settings."
    )

__version__ = "4.41.0"

# Lazy import mapping: name -> (module_path, attribute_name)
_LAZY_IMPORTS = {
    # Chrome
    "Chrome": ("selenium.webdriver.chrome.webdriver", "WebDriver"),
    "ChromeOptions": ("selenium.webdriver.chrome.options", "Options"),
    "ChromeService": ("selenium.webdriver.chrome.service", "Service"),
    # Edge
    "Edge": ("selenium.webdriver.edge.webdriver", "WebDriver"),
    "ChromiumEdge": ("selenium.webdriver.edge.webdriver", "WebDriver"),
    "EdgeOptions": ("selenium.webdriver.edge.options", "Options"),
    "EdgeService": ("selenium.webdriver.edge.service", "Service"),
    # Firefox
    "Firefox": ("selenium.webdriver.firefox.webdriver", "WebDriver"),
    "FirefoxOptions": ("selenium.webdriver.firefox.options", "Options"),
    "FirefoxProfile": ("selenium.webdriver.firefox.firefox_profile", "FirefoxProfile"),
    "FirefoxService": ("selenium.webdriver.firefox.service", "Service"),
    # IE
    "Ie": ("selenium.webdriver.ie.webdriver", "WebDriver"),
    "IeOptions": ("selenium.webdriver.ie.options", "Options"),
    "IeService": ("selenium.webdriver.ie.service", "Service"),
    # Safari
    "Safari": ("selenium.webdriver.safari.webdriver", "WebDriver"),
    "SafariOptions": ("selenium.webdriver.safari.options", "Options"),
    "SafariService": ("selenium.webdriver.safari.service", "Service"),
    # Remote
    "Remote": ("selenium.webdriver.remote.webdriver", "WebDriver"),
    # WebKitGTK
    "WebKitGTK": ("selenium.webdriver.webkitgtk.webdriver", "WebDriver"),
    "WebKitGTKOptions": ("selenium.webdriver.webkitgtk.options", "Options"),
    "WebKitGTKService": ("selenium.webdriver.webkitgtk.service", "Service"),
    # WPEWebKit
    "WPEWebKit": ("selenium.webdriver.wpewebkit.webdriver", "WebDriver"),
    "WPEWebKitOptions": ("selenium.webdriver.wpewebkit.options", "Options"),
    "WPEWebKitService": ("selenium.webdriver.wpewebkit.service", "Service"),
    # Common utilities
    "ActionChains": ("selenium.webdriver.common.action_chains", "ActionChains"),
    "DesiredCapabilities": ("selenium.webdriver.common.desired_capabilities", "DesiredCapabilities"),
    "Keys": ("selenium.webdriver.common.keys", "Keys"),
    "Proxy": ("selenium.webdriver.common.proxy", "Proxy"),
}

# Submodules that can be lazily imported as modules
_LAZY_SUBMODULES = {
    "chrome": "selenium.webdriver.chrome",
    "chromium": "selenium.webdriver.chromium",
    "common": "selenium.webdriver.common",
    "edge": "selenium.webdriver.edge",
    "firefox": "selenium.webdriver.firefox",
    "ie": "selenium.webdriver.ie",
    "remote": "selenium.webdriver.remote",
    "safari": "selenium.webdriver.safari",
    "support": "selenium.webdriver.support",
    "webkitgtk": "selenium.webdriver.webkitgtk",
    "wpewebkit": "selenium.webdriver.wpewebkit",
}


def __getattr__(name):
    if name in _LAZY_IMPORTS:
        module_path, attr_name = _LAZY_IMPORTS[name]
        module = importlib.import_module(module_path)
        value = getattr(module, attr_name)
        globals()[name] = value
        return value
    if name in _LAZY_SUBMODULES:
        module = importlib.import_module(_LAZY_SUBMODULES[name])
        globals()[name] = module
        return module
    raise AttributeError(f"module 'selenium.webdriver' has no attribute {name!r}")


def __dir__():
    return sorted(set(__all__) | set(_LAZY_SUBMODULES.keys()))


__all__ = sorted(_LAZY_IMPORTS.keys())
