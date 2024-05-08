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
import logging
from pathlib import Path

from selenium.common.exceptions import NoSuchDriverException
from selenium.webdriver.common.options import BaseOptions
from selenium.webdriver.common.selenium_manager import SeleniumManager
from selenium.webdriver.common.service import Service

logger = logging.getLogger(__name__)


class DriverFinder:
    """A Driver finding class responsible for obtaining the correct driver and
    associated browser.

    :param service: instance of the driver service class.
    :param options: instance of the browser options class.
    """

    def __init__(self, service: Service, options: BaseOptions) -> None:
        self._service = service
        self._options = options
        self._paths = {"driver_path": "", "browser_path": ""}

    """Utility to find if a given file is present and executable.

    This implementation is still in beta, and may change.
    """

    def get_browser_path(self) -> str:
        return self._binary_paths()["browser_path"]

    def get_driver_path(self) -> str:
        return self._binary_paths()["driver_path"]

    def _binary_paths(self) -> dict:
        if self._paths["driver_path"]:
            return self._paths

        browser = self._options.capabilities["browserName"]
        try:
            path = self._service.path
            if path:
                logger.debug(
                    "Skipping Selenium Manager; path to %s driver specified in Service class: %s", browser, path
                )
                if not Path(path).is_file():
                    raise ValueError(f"The path is not a valid file: {path}")
                self._paths["driver_path"] = path
            else:
                output = SeleniumManager().binary_paths(self._to_args())
                if Path(output["driver_path"]).is_file():
                    self._paths["driver_path"] = output["driver_path"]
                else:
                    raise ValueError(f'The driver path is not a valid file: {output["driver_path"]}')
                if Path(output["browser_path"]).is_file():
                    self._paths["browser_path"] = output["browser_path"]
                else:
                    raise ValueError(f'The browser path is not a valid file: {output["browser_path"]}')
        except Exception as err:
            msg = f"Unable to obtain driver for {browser}"
            raise NoSuchDriverException(msg) from err
        return self._paths

    def _to_args(self) -> list:
        args = ["--browser", self._options.capabilities["browserName"]]

        if self._options.browser_version:
            args.append("--browser-version")
            args.append(str(self._options.browser_version))

        binary_location = getattr(self._options, "binary_location", None)
        if binary_location:
            args.append("--browser-path")
            args.append(str(binary_location))

        proxy = self._options.proxy
        if proxy and (proxy.http_proxy or proxy.ssl_proxy):
            args.append("--proxy")
            value = proxy.ssl_proxy if proxy.ssl_proxy else proxy.http_proxy
            args.append(value)

        return args
