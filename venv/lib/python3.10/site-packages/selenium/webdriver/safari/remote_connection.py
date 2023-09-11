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


class SafariRemoteConnection(RemoteConnection):
    browser_name = DesiredCapabilities.SAFARI["browserName"]

    def __init__(self, remote_server_addr: str, keep_alive: bool = True, ignore_proxy: bool = False) -> None:
        super().__init__(remote_server_addr, keep_alive, ignore_proxy=ignore_proxy)
        self._commands["GET_PERMISSIONS"] = ("GET", "/session/$sessionId/apple/permissions")
        self._commands["SET_PERMISSIONS"] = ("POST", "/session/$sessionId/apple/permissions")
        self._commands["ATTACH_DEBUGGER"] = ("POST", "/session/$sessionId/apple/attach_debugger")
