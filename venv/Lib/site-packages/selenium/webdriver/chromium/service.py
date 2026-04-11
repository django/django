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

import logging
import os
import sys
from collections.abc import Mapping, Sequence
from typing import IO, Any

from selenium.webdriver.common import service


class ChromiumService(service.Service):
    """Service class responsible for starting and stopping the ChromiumDriver WebDriver instance.

    Args:
        executable_path: (Optional) Install path of the executable.
        port: (Optional) Port for the service to run on, defaults to 0 where the operating system will decide.
        service_args: (Optional) Sequence of args to be passed to the subprocess when launching the executable.
        log_output: (Optional) int representation of STDOUT/DEVNULL, any IO instance or String path to file.
        env: (Optional) Mapping of environment variables for the new process, defaults to `os.environ`.
        driver_path_env_key: (Optional) Environment variable to use to get the path to the driver executable.
    """

    def __init__(
        self,
        executable_path: str | None = None,
        port: int = 0,
        service_args: Sequence[str] | None = None,
        log_output: int | str | IO[Any] | None = None,
        env: Mapping[str, str] | None = None,
        driver_path_env_key: str | None = None,
        **kwargs,
    ) -> None:
        self._service_args = list(service_args or [])
        driver_path_env_key = driver_path_env_key or "SE_CHROMEDRIVER"

        if isinstance(log_output, str):
            self._service_args.append(f"--log-path={log_output}")
            self.log_output = None
        else:
            self.log_output = log_output

        if os.environ.get("SE_DEBUG"):
            has_arg_conflicts = any(x in arg for arg in self._service_args for x in ("log-level", "log-path", "silent"))
            has_output_conflict = self.log_output is not None
            if has_arg_conflicts or has_output_conflict:
                logging.getLogger(__name__).warning(
                    "Environment Variable `SE_DEBUG` is set; "
                    "forcing ChromiumDriver --verbose and overriding log-level/log-output/silent settings."
                )
            if has_arg_conflicts:
                self._service_args = [
                    arg for arg in self._service_args if not any(x in arg for x in ("log-level", "log-path", "silent"))
                ]
            self._service_args.append("--verbose")
            self.log_output = sys.stderr

        super().__init__(
            executable_path=executable_path,
            port=port,
            env=env,
            log_output=self.log_output,
            driver_path_env_key=driver_path_env_key,
            **kwargs,
        )

    def command_line_args(self) -> list[str]:
        return [f"--port={self.port}"] + self._service_args

    @property
    def service_args(self) -> Sequence[str]:
        """Returns the sequence of service arguments."""
        return self._service_args

    @service_args.setter
    def service_args(self, value: Sequence[str]):
        if isinstance(value, str) or not isinstance(value, Sequence):
            raise TypeError("service_args must be a sequence")
        self._service_args = list(value)
