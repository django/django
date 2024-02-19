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
import json
import logging
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import List

from selenium.common import WebDriverException
from selenium.webdriver.common.options import BaseOptions

logger = logging.getLogger(__name__)


class SeleniumManager:
    """Wrapper for getting information from the Selenium Manager binaries.

    This implementation is still in beta, and may change.
    """

    @staticmethod
    def get_binary() -> Path:
        """Determines the path of the correct Selenium Manager binary.

        :Returns: The Selenium Manager executable location

        :Raises: WebDriverException if the platform is unsupported
        """

        if (path := os.getenv("SE_MANAGER_PATH")) is not None:
            return Path(path)

        dirs = {
            ("darwin", "any"): "macos",
            ("win32", "any"): "windows",
            ("cygwin", "any"): "windows",
            ("linux", "x86_64"): "linux",
            ("freebsd", "x86_64"): "linux",
            ("openbsd", "x86_64"): "linux",
        }

        arch = platform.machine() if sys.platform in ("linux", "freebsd", "openbsd") else "any"

        directory = dirs.get((sys.platform, arch))
        if directory is None:
            raise WebDriverException(f"Unsupported platform/architecture combination: {sys.platform}/{arch}")

        if sys.platform in ["freebsd", "openbsd"]:
            logger.warning("Selenium Manager binary may not be compatible with %s; verify settings", sys.platform)

        file = "selenium-manager.exe" if directory == "windows" else "selenium-manager"

        path = Path(__file__).parent.joinpath(directory, file)

        if not path.is_file():
            raise WebDriverException(f"Unable to obtain working Selenium Manager binary; {path}")

        logger.debug("Selenium Manager binary found at: %s", path)

        return path

    def driver_location(self, options: BaseOptions) -> str:
        """Determines the path of the correct driver.

        :Args:
         - browser: which browser to get the driver path for.
        :Returns: The driver path to use
        """

        browser = options.capabilities["browserName"]

        args = [str(self.get_binary()), "--browser", browser]

        if options.browser_version:
            args.append("--browser-version")
            args.append(str(options.browser_version))

        binary_location = getattr(options, "binary_location", None)
        if binary_location:
            args.append("--browser-path")
            args.append(str(binary_location))

        proxy = options.proxy
        if proxy and (proxy.http_proxy or proxy.ssl_proxy):
            args.append("--proxy")
            value = proxy.ssl_proxy if proxy.ssl_proxy else proxy.http_proxy
            args.append(value)

        output = self.run(args)

        browser_path = output["browser_path"]
        driver_path = output["driver_path"]
        logger.debug("Using driver at: %s", driver_path)

        if hasattr(options.__class__, "binary_location") and browser_path:
            options.binary_location = browser_path
            options.browser_version = None  # if we have the binary location we no longer need the version

        return driver_path

    @staticmethod
    def run(args: List[str]) -> dict:
        """Executes the Selenium Manager Binary.

        :Args:
         - args: the components of the command being executed.
        :Returns: The log string containing the driver location.
        """
        if logger.getEffectiveLevel() == logging.DEBUG:
            args.append("--debug")
        args.append("--language-binding")
        args.append("python")
        args.append("--output")
        args.append("json")

        command = " ".join(args)
        logger.debug("Executing process: %s", command)
        try:
            if sys.platform == "win32":
                completed_proc = subprocess.run(args, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                completed_proc = subprocess.run(args, capture_output=True)
            stdout = completed_proc.stdout.decode("utf-8").rstrip("\n")
            stderr = completed_proc.stderr.decode("utf-8").rstrip("\n")
            output = json.loads(stdout)
            result = output["result"]
        except Exception as err:
            raise WebDriverException(f"Unsuccessful command executed: {command}") from err

        for item in output["logs"]:
            if item["level"] == "WARN":
                logger.warning(item["message"])
            if item["level"] == "DEBUG" or item["level"] == "INFO":
                logger.debug(item["message"])

        if completed_proc.returncode:
            raise WebDriverException(f"Unsuccessful command executed: {command}.\n{result}{stderr}")
        return result
