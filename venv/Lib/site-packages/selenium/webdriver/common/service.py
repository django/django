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

import errno
import logging
import os
import subprocess
import sys
from abc import ABC, abstractmethod
from collections.abc import Mapping
from io import IOBase
from subprocess import PIPE
from time import sleep
from typing import IO, Any
from urllib import request
from urllib.error import URLError

from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common import utils

logger = logging.getLogger(__name__)


class Service(ABC):
    """Abstract base class for all service objects that manage driver processes.

    Services typically launch a child program in a new process as an interim process to
    communicate with a browser.

    Args:
        executable_path: (Optional) Install path of the executable.
        port: (Optional) Port for the service to run on, defaults to 0 where the operating system will decide.
        log_output: (Optional) int representation of STDOUT/DEVNULL, any IO instance or String path to file.
        env: (Optional) Mapping of environment variables for the new process, defaults to `os.environ`.
        driver_path_env_key: (Optional) Environment variable to use to get the path to the driver executable.
    """

    def __init__(
        self,
        executable_path: str | None = None,
        port: int = 0,
        log_output: int | str | IO[Any] | None = None,
        env: Mapping[Any, Any] | None = None,
        driver_path_env_key: str | None = None,
        **kwargs,
    ) -> None:
        self.log_output: int | IO[Any] | None
        if isinstance(log_output, str):
            self.log_output = open(log_output, "a+", encoding="utf-8")
        elif log_output == subprocess.STDOUT:
            self.log_output = None
        elif log_output is None or log_output == subprocess.DEVNULL:
            self.log_output = subprocess.DEVNULL
        else:
            self.log_output = log_output

        self.port = port or utils.free_port()
        # Default value for every python subprocess: subprocess.Popen(..., creationflags=0)
        self.popen_kw = kwargs.pop("popen_kw", {})
        self.creation_flags = self.popen_kw.pop("creation_flags", 0)
        self.env = env or os.environ
        self.DRIVER_PATH_ENV_KEY = driver_path_env_key
        self._path = self.env_path() or executable_path

    @property
    def service_url(self) -> str:
        """Gets the url of the Service."""
        return f"http://{utils.join_host_port('localhost', self.port)}"

    @abstractmethod
    def command_line_args(self) -> list[str]:
        """A List of program arguments (excluding the executable)."""
        raise NotImplementedError("This method needs to be implemented in a sub class")

    @property
    def path(self) -> str:
        return self._path or ""

    @path.setter
    def path(self, value: str) -> None:
        self._path = str(value)

    def start(self) -> None:
        """Starts the Service.

        Raises:
            WebDriverException: Raised either when it can't start the service
                or when it can't connect to the service
        """
        if self._path is None:
            raise WebDriverException("Service path cannot be None.")
        self._start_process(self._path)

        count = 0
        while True:
            self.assert_process_still_running()
            if self.is_connectable():
                break
            # sleep increasing: 0.01, 0.06, 0.11, 0.16, 0.21, 0.26, 0.31, 0.36, 0.41, 0.46, 0.5
            sleep(min(0.01 + 0.05 * count, 0.5))
            count += 1
            if count == 70:
                raise WebDriverException(f"Can not connect to the Service {self._path}")

    def assert_process_still_running(self) -> None:
        """Check if the underlying process is still running."""
        return_code = self.process.poll()
        if return_code:
            raise WebDriverException(f"Service {self._path} unexpectedly exited. Status code was: {return_code}")

    def is_connectable(self) -> bool:
        """Check if the service is ready via the W3C WebDriver /status endpoint.

        This makes an HTTP request to the /status endpoint and verifies if it is ready to accept new sessions.

        Returns:
            True if the service is ready to accept new sessions, False otherwise.
        """
        return utils.is_url_connectable(self.port)

    def send_remote_shutdown_command(self) -> None:
        """Dispatch an HTTP request to the shutdown endpoint to stop the service."""
        try:
            request.urlopen(f"{self.service_url}/shutdown")
        except URLError:
            return

        for _ in range(30):
            if not self.is_connectable():
                break
            sleep(1)

    def stop(self) -> None:
        """Stops the service."""
        if self.log_output not in {PIPE, subprocess.DEVNULL}:
            if isinstance(self.log_output, IOBase):
                self.log_output.close()
            elif isinstance(self.log_output, int):
                os.close(self.log_output)

        if self.process is not None and self.process.poll() is None:
            try:
                self.send_remote_shutdown_command()
            except TypeError:
                pass
            finally:
                self._terminate_process()

    def _terminate_process(self) -> None:
        """Terminate the child process.

        On POSIX this attempts a graceful SIGTERM followed by a SIGKILL,
        on a Windows OS kill is an alias to terminate.  Terminating does
        not raise itself if something has gone wrong but (currently)
        silently ignores errors here.
        """
        try:
            stdin, stdout, stderr = (
                self.process.stdin,
                self.process.stdout,
                self.process.stderr,
            )
            for stream in stdin, stdout, stderr:
                try:
                    stream.close()  # type: ignore
                except AttributeError:
                    pass
            self.process.terminate()
            try:
                self.process.wait(60)
            except subprocess.TimeoutExpired:
                logger.error(
                    "Service process refused to terminate gracefully with SIGTERM, escalating to SIGKILL.",
                    exc_info=True,
                )
                self.process.kill()
        except OSError:
            logger.error("Error terminating service process.", exc_info=True)

    def __del__(self) -> None:
        # `subprocess.Popen` doesn't send signal on `__del__`;
        # so we attempt to close the launched process when `__del__`
        # is triggered.
        # do not use globals here; interpreter shutdown may have already cleaned them up
        # and they would be `None`. This goes for anything this method is referencing internally.
        try:
            self.stop()
        except Exception:
            pass

    def _start_process(self, path: str) -> None:
        """Creates a subprocess by executing the command provided.

        Args:
            path: full command to execute
        """
        cmd = [path]
        cmd.extend(self.command_line_args())
        close_file_descriptors = self.popen_kw.pop("close_fds", sys.platform != "win32")
        try:
            start_info = None
            if sys.platform == "win32":
                start_info = subprocess.STARTUPINFO()
                start_info.dwFlags = subprocess.CREATE_NEW_CONSOLE | subprocess.STARTF_USESHOWWINDOW
                start_info.wShowWindow = subprocess.SW_HIDE

            self.process = subprocess.Popen(
                cmd,
                env=self.env,
                close_fds=close_file_descriptors,
                stdout=self.log_output,
                stderr=self.log_output,
                stdin=PIPE,
                creationflags=self.creation_flags,
                startupinfo=start_info,
                **self.popen_kw,
            )
            logger.debug(
                "Started executable: `%s` in a child process with pid: %s using %s to output %s",
                self._path,
                self.process.pid,
                self.creation_flags,
                self.log_output,
            )
        except TypeError:
            raise
        except OSError as err:
            if err.errno == errno.EACCES:
                if self._path is None:
                    raise WebDriverException("Service path cannot be None.")
                raise WebDriverException(
                    f"'{os.path.basename(self._path)}' executable may have wrong permissions."
                ) from err
            raise

    def env_path(self) -> str | None:
        if self.DRIVER_PATH_ENV_KEY:
            return os.getenv(self.DRIVER_PATH_ENV_KEY, None)
        return None
