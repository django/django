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

from selenium.webdriver.chromium.options import ChromiumOptions
from selenium.webdriver.chromium.remote_connection import ChromiumRemoteConnection
from selenium.webdriver.chromium.service import ChromiumService
from selenium.webdriver.common.driver_finder import DriverFinder
from selenium.webdriver.common.webdriver import LocalWebDriver
from selenium.webdriver.remote.command import Command


class ChromiumDriver(LocalWebDriver):
    """Control the WebDriver instance of ChromiumDriver and drive the browser."""

    def __init__(
        self,
        browser_name: str,
        vendor_prefix: str,
        options: ChromiumOptions | None = None,
        service: ChromiumService | None = None,
        keep_alive: bool = True,
    ) -> None:
        """Create a new WebDriver instance, start the service, and create new ChromiumDriver instance.

        Args:
            browser_name: Browser name used when matching capabilities.
            vendor_prefix: Company prefix to apply to vendor-specific WebDriver extension commands.
            options: Instance of ChromiumOptions.
            service: Service object for handling the browser driver if you need to pass extra details.
            keep_alive: Whether to configure ChromiumRemoteConnection to use HTTP keep-alive.
        """
        self.service = service if service else ChromiumService()
        self.options = options if options else ChromiumOptions()

        finder = DriverFinder(self.service, self.options)
        if finder.get_browser_path():
            self.options.binary_location = finder.get_browser_path()
            self.options.browser_version = None

        self.service.path = self.service.env_path() or finder.get_driver_path()
        self.service.start()

        executor = ChromiumRemoteConnection(
            remote_server_addr=self.service.service_url,
            browser_name=browser_name,
            vendor_prefix=vendor_prefix,
            keep_alive=keep_alive,
            ignore_proxy=self.options._ignore_local_proxy,
        )

        try:
            super().__init__(command_executor=executor, options=self.options)
        except Exception:
            self.quit()
            raise

    def launch_app(self, id):
        """Launches Chromium app specified by id.

        Args:
            id: The id of the Chromium app to launch.
        """
        return self.execute("launchApp", {"id": id})

    def get_network_conditions(self):
        """Gets Chromium network emulation settings.

        Returns:
            A dict. For example: {'latency': 4, 'download_throughput': 2, 'upload_throughput': 2}
        """
        return self.execute("getNetworkConditions")["value"]

    def set_network_conditions(self, **network_conditions) -> None:
        """Sets Chromium network emulation settings.

        Args:
            **network_conditions: A dict with conditions specification.

        Example:
            driver.set_network_conditions(
                offline=False,
                latency=5,  # additional latency (ms)
                download_throughput=500 * 1024,  # maximal throughput
                upload_throughput=500 * 1024,
            )  # maximal throughput

            Note: `throughput` can be used to set both (for download and upload).
        """
        self.execute("setNetworkConditions", {"network_conditions": network_conditions})

    def delete_network_conditions(self) -> None:
        """Resets Chromium network emulation settings."""
        self.execute("deleteNetworkConditions")

    def set_permissions(self, name: str, value: str) -> None:
        """Sets Applicable Permission.

        Args:
            name: The item to set the permission on.
            value: The value to set on the item

        Example:
            driver.set_permissions("clipboard-read", "denied")
        """
        self.execute("setPermissions", {"descriptor": {"name": name}, "state": value})

    def execute_cdp_cmd(self, cmd: str, cmd_args: dict):
        """Execute Chrome Devtools Protocol command and get returned result.

        The command and command args should follow chrome devtools protocol domains/commands

        See:
          - https://chromedevtools.github.io/devtools-protocol/

        Args:
            cmd: A str, command name
            cmd_args: A dict, command args. empty dict {} if there is no command args

        Example:
            `driver.execute_cdp_cmd('Network.getResponseBody', {'requestId': requestId})`

        Returns:
            A dict, empty dict {} if there is no result to return.
            For example to getResponseBody:
            {'base64Encoded': False, 'body': 'response body string'}
        """
        return super().execute_cdp_cmd(cmd, cmd_args)

    def get_sinks(self) -> list:
        """Get a list of sinks available for Cast."""
        return self.execute("getSinks")["value"]

    def get_issue_message(self):
        """Returns an error message when there is any issue in a Cast session."""
        return self.execute("getIssueMessage")["value"]

    @property
    def log_types(self):
        """Gets a list of the available log types.

        Example:
        --------
        >>> driver.log_types
        """
        return self.execute(Command.GET_AVAILABLE_LOG_TYPES)["value"]

    def get_log(self, log_type):
        """Gets the log for a given log type.

        Args:
            log_type: Type of log that which will be returned

        Example:
            >>> driver.get_log("browser")
            >>> driver.get_log("driver")
            >>> driver.get_log("client")
            >>> driver.get_log("server")
        """
        return self.execute(Command.GET_LOG, {"type": log_type})["value"]

    def set_sink_to_use(self, sink_name: str) -> dict:
        """Set a specific sink as a Cast session receiver target.

        Args:
            sink_name: Name of the sink to use as the target.
        """
        return self.execute("setSinkToUse", {"sinkName": sink_name})

    def start_desktop_mirroring(self, sink_name: str) -> dict:
        """Starts a desktop mirroring session on a specific receiver target.

        Args:
            sink_name: Name of the sink to use as the target.
        """
        return self.execute("startDesktopMirroring", {"sinkName": sink_name})

    def start_tab_mirroring(self, sink_name: str) -> dict:
        """Starts a tab mirroring session on a specific receiver target.

        Args:
            sink_name: Name of the sink to use as the target.
        """
        return self.execute("startTabMirroring", {"sinkName": sink_name})

    def stop_casting(self, sink_name: str) -> dict:
        """Stops the existing Cast session on a specific receiver target.

        Args:
            sink_name: Name of the sink to stop the Cast session.
        """
        return self.execute("stopCasting", {"sinkName": sink_name})
