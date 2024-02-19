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

import http.client as http_client

from selenium.webdriver.common.driver_finder import DriverFinder
from selenium.webdriver.remote.webdriver import WebDriver as RemoteWebDriver

from .options import Options
from .service import Service


class WebDriver(RemoteWebDriver):
    """Controls the WPEWebKitDriver and allows you to drive the browser."""

    def __init__(
        self,
        options=None,
        service: Service = None,
    ):
        """Creates a new instance of the WPEWebKit driver.

        Starts the service and then creates new instance of WPEWebKit Driver.

        :Args:
         - options : an instance of ``WPEWebKitOptions``
         - service : Service object for handling the browser driver if you need to pass extra details
        """
        if not options:
            options = Options()

        self.service = service if service else Service()
        self.service.path = DriverFinder.get_path(self.service, options)
        self.service.start()

        super().__init__(command_executor=self.service.service_url, options=options)
        self._is_remote = False

    def quit(self):
        """Closes the browser and shuts down the WPEWebKitDriver executable
        that is started when starting the WPEWebKitDriver."""
        try:
            super().quit()
        except http_client.BadStatusLine:
            pass
        finally:
            self.service.stop()
