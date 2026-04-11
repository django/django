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
import warnings
import zipfile
from contextlib import contextmanager
from io import BytesIO

from selenium.webdriver.common.driver_finder import DriverFinder
from selenium.webdriver.common.webdriver import LocalWebDriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.remote_connection import FirefoxRemoteConnection
from selenium.webdriver.firefox.service import Service


class WebDriver(LocalWebDriver):
    """Controls the GeckoDriver and allows you to drive the browser."""

    CONTEXT_CHROME = "chrome"
    CONTEXT_CONTENT = "content"

    def __init__(
        self,
        options: Options | None = None,
        service: Service | None = None,
        keep_alive: bool = True,
    ) -> None:
        """Create a new instance of the Firefox driver, start the service, and create new instance.

        Args:
            options: Instance of Options.
            service: Service object for handling the browser driver if you need to pass extra details.
            keep_alive: Whether to configure FirefoxRemoteConnection to use HTTP keep-alive.
        """
        self.service = service if service else Service()
        self.options = options if options else Options()

        finder = DriverFinder(self.service, self.options)
        if finder.get_browser_path():
            self.options.binary_location = finder.get_browser_path()
            self.options.browser_version = None

        self.service.path = self.service.env_path() or finder.get_driver_path()
        self.service.start()

        executor = FirefoxRemoteConnection(
            remote_server_addr=self.service.service_url,
            keep_alive=keep_alive,
            ignore_proxy=self.options._ignore_local_proxy,
        )

        try:
            super().__init__(command_executor=executor, options=self.options)
        except Exception:
            self.quit()
            raise

    def set_context(self, context) -> None:
        """Sets the context that Selenium commands are running in.

        Args:
            context: Context to set, should be one of CONTEXT_CHROME or CONTEXT_CONTENT.
        """
        self.execute("SET_CONTEXT", {"context": context})

    @contextmanager
    def context(self, context):
        """Set the context that Selenium commands are running in using a `with` statement.

        The state of the context on the server is saved before entering the block,
        and restored upon exiting it.

        Args:
            context: Context, may be one of the class properties
                `CONTEXT_CHROME` or `CONTEXT_CONTENT`.

        Example:
            with selenium.context(selenium.CONTEXT_CHROME):
                # chrome scope
                ... do stuff ...
        """
        initial_context = self.execute("GET_CONTEXT").pop("value")
        self.set_context(context)
        try:
            yield
        finally:
            self.set_context(initial_context)

    def install_addon(self, path, temporary=False) -> str:
        """Installs Firefox addon.

        Returns identifier of installed addon. This identifier can later
        be used to uninstall addon.

        Args:
            path: Absolute path to the addon that will be installed.
            temporary: Allows you to load browser extensions temporarily during a session.

        Returns:
            Identifier of installed addon.

        Example:
            driver.install_addon("/path/to/firebug.xpi")
        """
        if os.path.isdir(path):
            fp = BytesIO()
            # filter all trailing slash found in path
            path = os.path.normpath(path)
            # account for trailing slash that will be added by os.walk()
            path_root = len(path) + 1
            with zipfile.ZipFile(fp, "w", zipfile.ZIP_DEFLATED, strict_timestamps=False) as zipped:
                for base, _, files in os.walk(path):
                    for fyle in files:
                        filename = os.path.join(base, fyle)
                        zipped.write(filename, filename[path_root:])
            addon = base64.b64encode(fp.getvalue()).decode("UTF-8")
        else:
            with open(path, "rb") as file:
                addon = base64.b64encode(file.read()).decode("UTF-8")

        payload = {"addon": addon, "temporary": temporary}
        return self.execute("INSTALL_ADDON", payload)["value"]

    def uninstall_addon(self, identifier) -> None:
        """Uninstalls Firefox addon using its identifier.

        Args:
            identifier: The addon identifier to uninstall.

        Example:
            driver.uninstall_addon("addon@foo.com")
        """
        self.execute("UNINSTALL_ADDON", {"id": identifier})

    def get_full_page_screenshot_as_file(self, filename) -> bool:
        """Save a full document screenshot of the current window to a PNG image file.

        Args:
            filename: The full path you wish to save your screenshot to. This
                should end with a `.png` extension.

        Returns:
            False if there is any IOError, else returns True. Use full paths in your filename.

        Example:
            driver.get_full_page_screenshot_as_file("/Screenshots/foo.png")
        """
        if not filename.lower().endswith(".png"):
            warnings.warn(
                "name used for saved screenshot does not match file type. It should end with a `.png` extension",
                UserWarning,
            )
        png = self.get_full_page_screenshot_as_png()
        try:
            with open(filename, "wb") as f:
                f.write(png)
        except OSError:
            return False
        finally:
            del png
        return True

    def save_full_page_screenshot(self, filename) -> bool:
        """Save a full document screenshot of the current window to a PNG image file.

        Args:
            filename: The full path you wish to save your screenshot to. This
                should end with a `.png` extension.

        Returns:
            False if there is any IOError, else returns True. Use full paths in your filename.

        Example:
            driver.save_full_page_screenshot("/Screenshots/foo.png")
        """
        return self.get_full_page_screenshot_as_file(filename)

    def get_full_page_screenshot_as_png(self) -> bytes:
        """Get the full document screenshot of the current window as binary data.

        Returns:
            Binary data of the screenshot.

        Example:
            driver.get_full_page_screenshot_as_png()
        """
        return base64.b64decode(self.get_full_page_screenshot_as_base64().encode("ascii"))

    def get_full_page_screenshot_as_base64(self) -> str:
        """Get the full document screenshot of the current window as a base64-encoded string.

        Returns:
            Base64 encoded string of the screenshot.

        Example:
            driver.get_full_page_screenshot_as_base64()
        """
        return self.execute("FULL_PAGE_SCREENSHOT")["value"]
