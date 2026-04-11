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


from selenium.webdriver import DesiredCapabilities
from selenium.webdriver.chromium.remote_connection import ChromiumRemoteConnection
from selenium.webdriver.remote.client_config import ClientConfig


class EdgeRemoteConnection(ChromiumRemoteConnection):
    browser_name = DesiredCapabilities.EDGE["browserName"]

    def __init__(
        self,
        remote_server_addr: str,
        keep_alive: bool = True,
        ignore_proxy: bool = False,
        client_config: ClientConfig | None = None,
    ) -> None:
        super().__init__(
            remote_server_addr=remote_server_addr,
            vendor_prefix="ms",
            browser_name=EdgeRemoteConnection.browser_name,
            keep_alive=keep_alive,
            ignore_proxy=ignore_proxy,
            client_config=client_config,
        )
