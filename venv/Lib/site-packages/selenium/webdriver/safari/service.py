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

from collections.abc import Mapping, Sequence

from selenium.webdriver.common import service


class Service(service.Service):
    """Service class responsible for starting and stopping of `safaridriver`.

    This service is only supported on macOS.

    Args:
        executable_path: (Optional) Install path of the safaridriver executable, defaults to `/usr/bin/safaridriver`.
        port: (Optional) Port for the service to run on, defaults to 0 where the operating system will decide.
        service_args: (Optional) Sequence of args to be passed to the subprocess when launching the executable.
        env: (Optional) Mapping of environment variables for the new process, defaults to `os.environ`.
        enable_logging: (Optional) Enable logging of the service. Logs can be located at
            `~/Library/Logs/com.apple.WebDriver/`
        driver_path_env_key: (Optional) Environment variable to use to get the path to the driver executable.
    """

    def __init__(
        self,
        executable_path: str | None = None,
        port: int = 0,
        service_args: Sequence[str] | None = None,
        env: Mapping[str, str] | None = None,
        reuse_service=False,
        enable_logging: bool = False,
        driver_path_env_key: str | None = None,
        **kwargs,
    ) -> None:
        self._service_args = list(service_args or [])
        driver_path_env_key = driver_path_env_key or "SE_SAFARIDRIVER"

        if enable_logging:
            self._service_args.append("--diagnose")

        self.reuse_service = reuse_service
        super().__init__(
            executable_path=executable_path,
            port=port,
            env=env,
            driver_path_env_key=driver_path_env_key,
            **kwargs,
        )

    def command_line_args(self) -> list[str]:
        return ["-p", f"{self.port}"] + self._service_args

    @property
    def service_url(self) -> str:
        """Gets the url of the SafariDriver Service."""
        return f"http://localhost:{self.port}"

    @property
    def reuse_service(self) -> bool:
        return self._reuse_service

    @reuse_service.setter
    def reuse_service(self, reuse: bool) -> None:
        if not isinstance(reuse, bool):
            raise TypeError("reuse must be a boolean")
        self._reuse_service = reuse

    @property
    def service_args(self) -> Sequence[str]:
        """Returns the sequence of service arguments."""
        return self._service_args

    @service_args.setter
    def service_args(self, value: Sequence[str]):
        if isinstance(value, str) or not isinstance(value, Sequence):
            raise TypeError("service_args must be a sequence")
        self._service_args = list(value)
