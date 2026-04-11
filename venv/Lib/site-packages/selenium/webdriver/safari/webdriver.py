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

from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.driver_finder import DriverFinder
from selenium.webdriver.common.webdriver import LocalWebDriver
from selenium.webdriver.safari.options import Options
from selenium.webdriver.safari.remote_connection import SafariRemoteConnection
from selenium.webdriver.safari.service import Service


class WebDriver(LocalWebDriver):
    """Controls the SafariDriver and allows you to drive the browser."""

    def __init__(
        self,
        options: Options | None = None,
        service: Service | None = None,
        keep_alive: bool = True,
    ) -> None:
        """Create a new Safari driver instance and launch or find a running safaridriver service.

        Args:
            options: Instance of Options.
            service: Service object for handling the browser driver if you need to pass extra details.
            keep_alive: Whether to configure SafariRemoteConnection to use HTTP keep-alive.
        """
        self.service = service if service else Service()
        self.options = options if options else Options()

        self.service.path = self.service.env_path() or DriverFinder(self.service, self.options).get_driver_path()

        if not self.service.reuse_service:
            self.service.start()

        executor = SafariRemoteConnection(
            remote_server_addr=self.service.service_url,
            keep_alive=keep_alive,
            ignore_proxy=self.options._ignore_local_proxy,
        )

        try:
            super().__init__(command_executor=executor, options=self.options)
        except Exception:
            self.quit()
            raise

    def quit(self):
        """Closes the browser and shuts down the SafariDriver executable."""
        try:
            super().quit()
        except Exception:
            # We don't care about the message because something probably has gone wrong
            pass
        finally:
            if not self.service.reuse_service:
                self.service.stop()

    # safaridriver extension commands. The canonical command support matrix is here:
    # https://developer.apple.com/library/content/documentation/NetworkingInternetWeb/Conceptual/WebDriverEndpointDoc/Commands/Commands.html

    # First available in Safari 11.1 and Safari Technology Preview 41.
    def set_permission(self, permission, value):
        if not isinstance(value, bool):
            raise WebDriverException("Value of a session permission must be set to True or False.")

        payload = {permission: value}
        self.execute("SET_PERMISSIONS", {"permissions": payload})

    # First available in Safari 11.1 and Safari Technology Preview 41.
    def get_permission(self, permission):
        payload = self.execute("GET_PERMISSIONS")["value"]
        permissions = payload["permissions"]
        if not permissions:
            return None

        if permission not in permissions:
            return None

        value = permissions[permission]
        if not isinstance(value, bool):
            return None

        return value

    # First available in Safari 11.1 and Safari Technology Preview 42.
    def debug(self):
        self.execute("ATTACH_DEBUGGER")
        self.execute_script("debugger;")
