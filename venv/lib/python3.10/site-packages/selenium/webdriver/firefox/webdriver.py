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
import logging
import os
import warnings
import zipfile
from contextlib import contextmanager
from io import BytesIO

from selenium.webdriver.common.driver_finder import DriverFinder
from selenium.webdriver.remote.webdriver import WebDriver as RemoteWebDriver

from .options import Options
from .remote_connection import FirefoxRemoteConnection
from .service import Service

logger = logging.getLogger(__name__)


class WebDriver(RemoteWebDriver):
    """Controls the GeckoDriver and allows you to drive the browser."""

    CONTEXT_CHROME = "chrome"
    CONTEXT_CONTENT = "content"

    def __init__(
        self,
        options: Options = None,
        service: Service = None,
        keep_alive=True,
    ) -> None:
        """Creates a new instance of the Firefox driver. Starts the service and
        then creates new instance of Firefox driver.

        :Args:
         - options - Instance of ``options.Options``.
         - service - (Optional) service instance for managing the starting and stopping of the driver.
         - keep_alive - Whether to configure remote_connection.RemoteConnection to use HTTP keep-alive.
        """

        self.service = service if service else Service()
        options = options if options else Options()

        self.service.path = DriverFinder.get_path(self.service, options)
        self.service.start()

        executor = FirefoxRemoteConnection(
            remote_server_addr=self.service.service_url,
            ignore_proxy=options._ignore_local_proxy,
            keep_alive=keep_alive,
        )
        super().__init__(command_executor=executor, options=options)

        self._is_remote = False

    def quit(self) -> None:
        """Quits the driver and close every associated window."""
        try:
            super().quit()
        except Exception:
            # We don't care about the message because something probably has gone wrong
            pass

        self.service.stop()

    def set_context(self, context) -> None:
        self.execute("SET_CONTEXT", {"context": context})

    @contextmanager
    def context(self, context):
        """Sets the context that Selenium commands are running in using a
        `with` statement. The state of the context on the server is saved
        before entering the block, and restored upon exiting it.

        :param context: Context, may be one of the class properties
            `CONTEXT_CHROME` or `CONTEXT_CONTENT`.

        Usage example::

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

        :param temporary: allows you to load browser extensions temporarily during a session
        :param path: Absolute path to the addon that will be installed.

        :Usage:
            ::

                driver.install_addon('/path/to/firebug.xpi')
        """

        if os.path.isdir(path):
            fp = BytesIO()
            path_root = len(path) + 1  # account for trailing slash
            with zipfile.ZipFile(fp, "w", zipfile.ZIP_DEFLATED) as zipped:
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

        :Usage:
            ::

                driver.uninstall_addon('addon@foo.com')
        """
        self.execute("UNINSTALL_ADDON", {"id": identifier})

    def get_full_page_screenshot_as_file(self, filename) -> bool:
        """Saves a full document screenshot of the current window to a PNG
        image file. Returns False if there is any IOError, else returns True.
        Use full paths in your filename.

        :Args:
         - filename: The full path you wish to save your screenshot to. This
           should end with a `.png` extension.

        :Usage:
            ::

                driver.get_full_page_screenshot_as_file('/Screenshots/foo.png')
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
        """Saves a full document screenshot of the current window to a PNG
        image file. Returns False if there is any IOError, else returns True.
        Use full paths in your filename.

        :Args:
         - filename: The full path you wish to save your screenshot to. This
           should end with a `.png` extension.

        :Usage:
            ::

                driver.save_full_page_screenshot('/Screenshots/foo.png')
        """
        return self.get_full_page_screenshot_as_file(filename)

    def get_full_page_screenshot_as_png(self) -> bytes:
        """Gets the full document screenshot of the current window as a binary
        data.

        :Usage:
            ::

                driver.get_full_page_screenshot_as_png()
        """
        return base64.b64decode(self.get_full_page_screenshot_as_base64().encode("ascii"))

    def get_full_page_screenshot_as_base64(self) -> str:
        """Gets the full document screenshot of the current window as a base64
        encoded string which is useful in embedded images in HTML.

        :Usage:
            ::

                driver.get_full_page_screenshot_as_base64()
        """
        return self.execute("FULL_PAGE_SCREENSHOT")["value"]
