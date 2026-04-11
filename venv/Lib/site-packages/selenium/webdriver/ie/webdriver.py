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

from selenium.webdriver.common.driver_finder import DriverFinder
from selenium.webdriver.common.webdriver import LocalWebDriver
from selenium.webdriver.ie.options import Options
from selenium.webdriver.ie.service import Service
from selenium.webdriver.remote.client_config import ClientConfig
from selenium.webdriver.remote.remote_connection import RemoteConnection


class WebDriver(LocalWebDriver):
    """Control the IEServerDriver and drive Internet Explorer."""

    def __init__(
        self,
        options: Options | None = None,
        service: Service | None = None,
        keep_alive: bool = True,
    ) -> None:
        """Creates a new instance of the Ie driver.

        Starts the service and then creates new instance of Ie driver.

        Args:
            options: Instance of Options.
            service: Service object for handling the browser driver if you need to pass extra details.
            keep_alive: Whether to configure RemoteConnection to use HTTP keep-alive.
        """
        self.service = service if service else Service()
        self.options = options if options else Options()

        self.service.path = self.service.env_path() or DriverFinder(self.service, self.options).get_driver_path()
        self.service.start()

        client_config = ClientConfig(remote_server_addr=self.service.service_url, keep_alive=keep_alive, timeout=120)
        executor = RemoteConnection(
            ignore_proxy=self.options._ignore_local_proxy,
            client_config=client_config,
        )

        try:
            super().__init__(command_executor=executor, options=self.options)
        except Exception:
            self.quit()
            raise
