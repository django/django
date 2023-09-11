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
from selenium.webdriver.common import utils


class Service(service.Service):
    """A Service class that is responsible for the starting and stopping of
    `geckodriver`.

    :param executable_path: install path of the geckodriver executable, defaults to `geckodriver`.
    :param port: Port for the service to run on, defaults to 0 where the operating system will decide.
    :param service_args: (Optional) List of args to be passed to the subprocess when launching the executable.
    :param log_path: (Optional) File path for the file to be opened and passed as the subprocess stdout/stderr handler,
        defaults to `geckodriver.log`.
    :param env: (Optional) Mapping of environment variables for the new process, defaults to `os.environ`.
    """

    def __init__(
        self,
        executable_path: str = None,
        port: int = 0,
        service_args: typing.Optional[typing.List[str]] = None,
        log_path: typing.Optional[str] = None,
        log_output: SubprocessStdAlias = None,
        env: typing.Optional[typing.Mapping[str, str]] = None,
        **kwargs,
    ) -> None:
        self.service_args = service_args or []
        if log_path is not None:
            warnings.warn("log_path has been deprecated, please use log_output", DeprecationWarning, stacklevel=2)
            log_output = open(log_path, "a+", encoding="utf-8")

        if log_path is None and log_output is None:
            warnings.warn(
                "Firefox will soon stop logging to geckodriver.log by default; Specify desired logs with log_output",
                DeprecationWarning,
                stacklevel=2,
            )
            log_output = open("geckodriver.log", "a+", encoding="utf-8")

        super().__init__(
            executable=executable_path,
            port=port,
            log_output=log_output,
            env=env,
            **kwargs,
        )

        # Set a port for CDP
        if "--connect-existing" not in self.service_args:
            self.service_args.append("--websocket-port")
            self.service_args.append(f"{utils.free_port()}")

    def command_line_args(self) -> List[str]:
        return ["--port", f"{self.port}"] + self.service_args
