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

import shutil
from collections.abc import Mapping, Sequence
from typing import IO, Any

from selenium.webdriver.common import service

DEFAULT_EXECUTABLE_PATH: str | None = shutil.which("WebKitWebDriver")


class Service(service.Service):
    """Service class that is responsible for the starting and stopping of `WebKitWebDriver`.

    Args:
        executable_path: Install path of the WebKitWebDriver executable, defaults to the first `WebKitWebDriver`
            in `$PATH`.
        port: (Optional) Port for the service to run on, defaults to 0 where the operating system will decide.
        log_output: (Optional) int representation of STDOUT/DEVNULL, any IO instance or String path to file.
        service_args: (Optional) Sequence of args to be passed to the subprocess when launching the executable.
        env: (Optional) Mapping of environment variables for the new process, defaults to `os.environ`.
    """

    def __init__(
        self,
        executable_path: str | None = DEFAULT_EXECUTABLE_PATH,
        port: int = 0,
        log_output: int | str | IO[Any] | None = None,
        service_args: Sequence[str] | None = None,
        env: Mapping[str, str] | None = None,
        **kwargs,
    ) -> None:
        self._service_args = list(service_args or [])

        super().__init__(
            executable_path=executable_path,
            port=port,
            log_output=log_output,
            env=env,
            **kwargs,
        )

    def command_line_args(self) -> list[str]:
        return ["-p", f"{self.port}"] + self._service_args

    @property
    def service_args(self) -> Sequence[str]:
        """Returns the sequence of service arguments."""
        return self._service_args

    @service_args.setter
    def service_args(self, value: Sequence[str]):
        if isinstance(value, str) or not isinstance(value, Sequence):
            raise TypeError("service_args must be a sequence")
        self._service_args = list(value)
