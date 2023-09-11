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
import typing
import warnings
from typing import List

from selenium.types import SubprocessStdAlias
from selenium.webdriver.common import service


class Service(service.Service):
    """Object that manages the starting and stopping of the IEDriver."""

    def __init__(
        self,
        executable_path: str = None,
        port: int = 0,
        host: typing.Optional[str] = None,
        service_args: typing.Optional[typing.List[str]] = None,
        log_level: typing.Optional[str] = None,
        log_output: SubprocessStdAlias = None,
        log_file: typing.Optional[str] = None,
        **kwargs,
    ) -> None:
        """Creates a new instance of the Service.

        :Args:
         - executable_path : Path to the IEDriver
         - port : Port the service is running on
         - host : IP address the service port is bound
         - log_level : Level of logging of service, may be "FATAL", "ERROR", "WARN", "INFO", "DEBUG", "TRACE".
           Default is "FATAL".
         - log_file : Target of logging of service, may be "stdout", "stderr" or file path.
           Default is "stdout".
        """
        self.service_args = service_args or []
        if host:
            self.service_args.append(f"--host={host}")
        if log_level:
            self.service_args.append(f"--log-level={log_level}")
        if log_file:
            warnings.warn("log_file has been deprecated, please use log_output", DeprecationWarning, stacklevel=2)
            self.service_args.append(f"--log-file={log_file}")

        super().__init__(
            executable_path,
            port=port,
            log_output=log_output,
            **kwargs,
        )

    def command_line_args(self) -> List[str]:
        return [f"--port={self.port}"] + self.service_args
