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

from selenium.webdriver.chromium.webdriver import ChromiumDriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.service import Service


class WebDriver(ChromiumDriver):
    """Controls the MSEdgeDriver and allows you to drive the browser."""

    def __init__(
        self,
        options: Options | None = None,
        service: Service | None = None,
        keep_alive: bool = True,
    ) -> None:
        """Creates a new instance of the edge driver.

        Starts the service and then creates new instance of edge driver.

        Args:
            options: Instance of Options.
            service: Service object for handling the browser driver if you need to pass extra details.
            keep_alive: Whether to configure EdgeRemoteConnection to use HTTP keep-alive.
        """
        self.service = service if service else Service()
        self.options = options if options else Options()

        super().__init__(
            browser_name=DesiredCapabilities.EDGE["browserName"],
            vendor_prefix="ms",
            options=self.options,
            service=self.service,
            keep_alive=keep_alive,
        )
