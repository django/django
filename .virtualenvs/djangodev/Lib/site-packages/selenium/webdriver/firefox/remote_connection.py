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

from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.remote.remote_connection import RemoteConnection


class FirefoxRemoteConnection(RemoteConnection):
    browser_name = DesiredCapabilities.FIREFOX["browserName"]

    def __init__(self, remote_server_addr, keep_alive=True, ignore_proxy=False) -> None:
        super().__init__(remote_server_addr, keep_alive, ignore_proxy)

        self._commands["GET_CONTEXT"] = ("GET", "/session/$sessionId/moz/context")
        self._commands["SET_CONTEXT"] = ("POST", "/session/$sessionId/moz/context")
        self._commands["INSTALL_ADDON"] = ("POST", "/session/$sessionId/moz/addon/install")
        self._commands["UNINSTALL_ADDON"] = ("POST", "/session/$sessionId/moz/addon/uninstall")
        self._commands["FULL_PAGE_SCREENSHOT"] = ("GET", "/session/$sessionId/moz/screenshot/full")
