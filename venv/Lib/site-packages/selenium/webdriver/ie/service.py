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
from collections.abc import Sequence
from typing import IO, Any

from selenium.webdriver.common import service


class Service(service.Service):
    """Service class responsible for starting and stopping of `IEDriver`.

    Args:
        executable_path: (Optional) Install path of the executable.
        port: (Optional) Port for the service to run on, defaults to 0 where the operating system will decide.
        host: (Optional) IP address the service port is bound
        service_args: (Optional) Sequence of args to be passed to the subprocess when launching the executable.
        log_level: (Optional) Level of logging of service, may be "FATAL", "ERROR", "WARN", "INFO", "DEBUG",
            "TRACE". Default is "FATAL".
        log_output: (Optional) int representation of STDOUT/DEVNULL, any IO instance or String path to file.
        driver_path_env_key: (Optional) Environment variable to use to get the path to the driver executable.
        **kwargs: Additional keyword arguments to pass to the parent Service class.
    """

    def __init__(
        self,
        executable_path: str | None = None,
        port: int = 0,
        host: str | None = None,
        service_args: Sequence[str] | None = None,
        log_level: str | None = None,
        log_output: int | str | IO[Any] | None = None,
        driver_path_env_key: str | None = None,
        **kwargs,
    ) -> None:
        self._service_args = list(service_args or [])
        driver_path_env_key = driver_path_env_key or "SE_IEDRIVER"

        if host:
            self._service_args.append(f"--host={host}")
        if log_level:
            self._service_args.append(f"--log-level={log_level}")

        if os.environ.get("SE_DEBUG"):
            has_arg_conflicts = any(x in arg for arg in self._service_args for x in ("log-level", "log-file"))
            has_output_conflict = log_output is not None
            if has_arg_conflicts or has_output_conflict:
                logging.getLogger(__name__).warning(
                    "Environment Variable `SE_DEBUG` is set; "
                    "forcing IEDriver log level to DEBUG and overriding configured log level/output."
                )
            if has_arg_conflicts:
                self._service_args = [
                    arg for arg in self._service_args if not any(x in arg for x in ("log-level", "log-file"))
                ]
            self._service_args.append("--log-level=DEBUG")
            log_output = sys.stderr

        super().__init__(
            executable_path=executable_path,
            port=port,
            log_output=log_output,
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
