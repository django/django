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

from selenium.webdriver.common import service


class Service(service.Service):
    """A Service class that is responsible for the starting and stopping of
    `safaridriver`  This is only supported on MAC OSX.

    :param executable_path: install path of the safaridriver executable, defaults to `/usr/bin/safaridriver`.
    :param port: Port for the service to run on, defaults to 0 where the operating system will decide.
    :param service_args: (Optional) List of args to be passed to the subprocess when launching the executable.
    :param env: (Optional) Mapping of environment variables for the new process, defaults to `os.environ`.
    """

    def __init__(
        self,
        executable_path: str = None,
        port: int = 0,
        service_args: typing.Optional[typing.List[str]] = None,
        env: typing.Optional[typing.Mapping[str, str]] = None,
        reuse_service=False,
        **kwargs,
    ) -> None:
        self.service_args = service_args or []

        self.reuse_service = reuse_service
        super().__init__(
            executable_path=executable_path,
            port=port,
            env=env,
            **kwargs,
        )

    def command_line_args(self) -> typing.List[str]:
        return ["-p", f"{self.port}"] + self.service_args

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
