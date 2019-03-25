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
import warnings

from selenium.webdriver.common import utils
from selenium.webdriver.remote.webdriver import WebDriver as RemoteWebDriver
from selenium.webdriver.remote.remote_connection import RemoteConnection
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from .service import Service


class WebDriver(RemoteWebDriver):

    def __init__(self, executable_path='MicrosoftWebDriver.exe',
                 capabilities=None, port=0, verbose=False, service_log_path=None,
                 log_path=None, keep_alive=False):
        """
        Creates a new instance of the chrome driver.

        Starts the service and then creates new instance of chrome driver.

        :Args:
         - executable_path - path to the executable. If the default is used it assumes the executable is in the $PATH
         - capabilities - Dictionary object with non-browser specific
           capabilities only, such as "proxy" or "loggingPref".
         - port - port you would like the service to run, if left as 0, a free port will be found.
         - verbose - whether to set verbose logging in the service
         - service_log_path - Where to log information from the driver.
         - log_path: Deprecated argument for service_log_path
         - keep_alive - Whether to configure ChromeRemoteConnection to use HTTP keep-alive.
         """
        if log_path:
            warnings.warn('use service_log_path instead of log_path',
                          DeprecationWarning, stacklevel=2)
            service_log_path = log_path

        self.port = port
        if self.port == 0:
            self.port = utils.free_port()

        self.edge_service = Service(executable_path, port=self.port, verbose=verbose, log_path=service_log_path)
        self.edge_service.start()

        if capabilities is None:
            capabilities = DesiredCapabilities.EDGE

        RemoteWebDriver.__init__(
            self,
            command_executor=RemoteConnection('http://localhost:%d' % self.port,
                                              resolve_ip=False,
                                              keep_alive=keep_alive),
            desired_capabilities=capabilities)
        self._is_remote = False

    def quit(self):
        RemoteWebDriver.quit(self)
        self.edge_service.stop()
