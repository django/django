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
from selenium.webdriver.wpewebkit.options import Options
from selenium.webdriver.wpewebkit.service import Service


class WebDriver(LocalWebDriver):
    """Controls the WPEWebKitDriver and allows you to drive the browser."""

    def __init__(
        self,
        options: Options | None = None,
        service: Service | None = None,
    ):
        """Creates a new instance of the WPEWebKit driver.

        Starts the service and then creates new instance of WPEWebKit Driver.

        Args:
            options: Instance of Options.
            service: Service object for handling the browser driver if you need to pass extra details.
        """
        self.options = options if options else Options()
        self.service = service if service else Service()
        self.service.path = DriverFinder(self.service, self.options).get_driver_path()
        self.service.start()

        try:
            super().__init__(command_executor=self.service.service_url, options=self.options)
        except Exception:
            self.quit()
            raise
