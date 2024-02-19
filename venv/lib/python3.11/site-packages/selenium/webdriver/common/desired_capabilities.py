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
"""The Desired Capabilities implementation."""


class DesiredCapabilities:
    """Set of default supported desired capabilities.

    Use this as a starting point for creating a desired capabilities object for
    requesting remote webdrivers for connecting to selenium server or selenium grid.

    Usage Example::

        from selenium import webdriver

        selenium_grid_url = "http://198.0.0.1:4444/wd/hub"

        # Create a desired capabilities object as a starting point.
        capabilities = DesiredCapabilities.FIREFOX.copy()
        capabilities['platform'] = "WINDOWS"
        capabilities['version'] = "10"

        # Instantiate an instance of Remote WebDriver with the desired capabilities.
        driver = webdriver.Remote(desired_capabilities=capabilities,
                                  command_executor=selenium_grid_url)

    Note: Always use '.copy()' on the DesiredCapabilities object to avoid the side
    effects of altering the Global class instance.
    """

    FIREFOX = {
        "browserName": "firefox",
        "acceptInsecureCerts": True,
        "moz:debuggerAddress": True,
    }

    INTERNETEXPLORER = {
        "browserName": "internet explorer",
        "platformName": "windows",
    }

    EDGE = {
        "browserName": "MicrosoftEdge",
    }

    CHROME = {
        "browserName": "chrome",
    }

    SAFARI = {
        "browserName": "safari",
        "platformName": "mac",
    }

    HTMLUNIT = {
        "browserName": "htmlunit",
        "version": "",
        "platform": "ANY",
    }

    HTMLUNITWITHJS = {
        "browserName": "htmlunit",
        "version": "firefox",
        "platform": "ANY",
        "javascriptEnabled": True,
    }

    IPHONE = {
        "browserName": "iPhone",
        "version": "",
        "platform": "mac",
    }

    IPAD = {
        "browserName": "iPad",
        "version": "",
        "platform": "mac",
    }

    WEBKITGTK = {
        "browserName": "MiniBrowser",
    }

    WPEWEBKIT = {
        "browserName": "MiniBrowser",
    }
