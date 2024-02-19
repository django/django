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

from selenium.webdriver.chromium.remote_connection import ChromiumRemoteConnection
from selenium.webdriver.common.driver_finder import DriverFinder
from selenium.webdriver.common.options import ArgOptions
from selenium.webdriver.common.service import Service
from selenium.webdriver.remote.webdriver import WebDriver as RemoteWebDriver


class ChromiumDriver(RemoteWebDriver):
    """Controls the WebDriver instance of ChromiumDriver and allows you to
    drive the browser."""

    def __init__(
        self,
        browser_name: str = None,
        vendor_prefix: str = None,
        options: ArgOptions = ArgOptions(),
        service: Service = None,
        keep_alive: bool = True,
    ) -> None:
        """Creates a new WebDriver instance of the ChromiumDriver. Starts the
        service and then creates new WebDriver instance of ChromiumDriver.

        :Args:
         - browser_name - Browser name used when matching capabilities.
         - vendor_prefix - Company prefix to apply to vendor-specific WebDriver extension commands.
         - options - this takes an instance of ChromiumOptions
         - service - Service object for handling the browser driver if you need to pass extra details
         - keep_alive - Whether to configure ChromiumRemoteConnection to use HTTP keep-alive.
        """
        self.service = service

        self.service.path = DriverFinder.get_path(self.service, options)
        self.service.start()

        executor = ChromiumRemoteConnection(
            remote_server_addr=self.service.service_url,
            browser_name=browser_name,
            vendor_prefix=vendor_prefix,
            keep_alive=keep_alive,
            ignore_proxy=options._ignore_local_proxy,
        )

        try:
            super().__init__(command_executor=executor, options=options)
        except Exception:
            self.quit()
            raise

        self._is_remote = False

    def launch_app(self, id):
        """Launches Chromium app specified by id."""
        return self.execute("launchApp", {"id": id})

    def get_network_conditions(self):
        """Gets Chromium network emulation settings.

        :Returns:     A dict. For example:     {'latency': 4,
        'download_throughput': 2, 'upload_throughput': 2,     'offline':
        False}
        """
        return self.execute("getNetworkConditions")["value"]

    def set_network_conditions(self, **network_conditions) -> None:
        """Sets Chromium network emulation settings.

        :Args:
         - network_conditions: A dict with conditions specification.

        :Usage:
            ::

                driver.set_network_conditions(
                    offline=False,
                    latency=5,  # additional latency (ms)
                    download_throughput=500 * 1024,  # maximal throughput
                    upload_throughput=500 * 1024)  # maximal throughput

            Note: 'throughput' can be used to set both (for download and upload).
        """
        self.execute("setNetworkConditions", {"network_conditions": network_conditions})

    def delete_network_conditions(self) -> None:
        """Resets Chromium network emulation settings."""
        self.execute("deleteNetworkConditions")

    def set_permissions(self, name: str, value: str) -> None:
        """Sets Applicable Permission.

        :Args:
         - name: The item to set the permission on.
         - value: The value to set on the item

        :Usage:
            ::

                driver.set_permissions('clipboard-read', 'denied')
        """
        self.execute("setPermissions", {"descriptor": {"name": name}, "state": value})

    def execute_cdp_cmd(self, cmd: str, cmd_args: dict):
        """Execute Chrome Devtools Protocol command and get returned result The
        command and command args should follow chrome devtools protocol
        domains/commands, refer to link
        https://chromedevtools.github.io/devtools-protocol/

        :Args:
         - cmd: A str, command name
         - cmd_args: A dict, command args. empty dict {} if there is no command args
        :Usage:
            ::

                driver.execute_cdp_cmd('Network.getResponseBody', {'requestId': requestId})
        :Returns:
            A dict, empty dict {} if there is no result to return.
            For example to getResponseBody:
            {'base64Encoded': False, 'body': 'response body string'}
        """
        return self.execute("executeCdpCommand", {"cmd": cmd, "params": cmd_args})["value"]

    def get_sinks(self) -> list:
        """:Returns: A list of sinks available for Cast."""
        return self.execute("getSinks")["value"]

    def get_issue_message(self):
        """:Returns: An error message when there is any issue in a Cast
        session."""
        return self.execute("getIssueMessage")["value"]

    def set_sink_to_use(self, sink_name: str) -> dict:
        """Sets a specific sink, using its name, as a Cast session receiver
        target.

        :Args:
         - sink_name: Name of the sink to use as the target.
        """
        return self.execute("setSinkToUse", {"sinkName": sink_name})

    def start_desktop_mirroring(self, sink_name: str) -> dict:
        """Starts a desktop mirroring session on a specific receiver target.

        :Args:
         - sink_name: Name of the sink to use as the target.
        """
        return self.execute("startDesktopMirroring", {"sinkName": sink_name})

    def start_tab_mirroring(self, sink_name: str) -> dict:
        """Starts a tab mirroring session on a specific receiver target.

        :Args:
         - sink_name: Name of the sink to use as the target.
        """
        return self.execute("startTabMirroring", {"sinkName": sink_name})

    def stop_casting(self, sink_name: str) -> dict:
        """Stops the existing Cast session on a specific receiver target.

        :Args:
         - sink_name: Name of the sink to stop the Cast session.
        """
        return self.execute("stopCasting", {"sinkName": sink_name})

    def quit(self) -> None:
        """Closes the browser and shuts down the ChromiumDriver executable."""
        try:
            super().quit()
        except Exception:
            # We don't care about the message because something probably has gone wrong
            pass
        finally:
            self.service.stop()
