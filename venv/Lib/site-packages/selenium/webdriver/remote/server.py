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

import collections
import os
import re
import shutil
import socket
import subprocess
import time
import urllib

from selenium.webdriver.common.selenium_manager import SeleniumManager


class Server:
    """Manage a Selenium Grid (Remote) Server in standalone mode.

    This class contains functionality for downloading the server and starting/stopping it.

    For more information on Selenium Grid, see:
        - https://www.selenium.dev/documentation/grid/getting_started/

    Args:
        host: Hostname or IP address to bind to (determined automatically if not specified).
        port: Port to listen on (4444 if not specified).
        path: Path/filename of existing server .jar file (Selenium Manager is used if not specified).
        version: Version of server to download (latest version if not specified).
        log_level: Logging level to control logging output ("INFO" if not specified).
            Available levels: "SEVERE", "WARNING", "INFO", "CONFIG", "FINE", "FINER", "FINEST".
        env: Mapping that defines the environment variables for the server process.
        java_path: Path to the java executable to run the server.
    """

    def __init__(
        self,
        host=None,
        port=4444,
        path=None,
        version=None,
        log_level="INFO",
        env=None,
        java_path=None,
        startup_timeout=10,
    ):
        if path and version:
            raise TypeError("Not allowed to specify a version when using an existing server path")

        self.host = host
        self.port = port
        self.path = path
        self.version = version
        self.log_level = log_level
        self.env = env
        self.java_path = java_path
        self.startup_timeout = startup_timeout
        self.process = None

    @property
    def startup_timeout(self):
        return self._startup_timeout

    @startup_timeout.setter
    def startup_timeout(self, timeout):
        self._startup_timeout = int(timeout)

    @property
    def status_url(self):
        host = self.host if self.host is not None else "localhost"
        return f"http://{host}:{self.port}/status"

    @property
    def path(self):
        return self._path

    @path.setter
    def path(self, path):
        if path and not os.path.exists(path):
            raise OSError(f"Can't find server .jar located at {path}")
        self._path = path

    @property
    def port(self):
        return self._port

    @port.setter
    def port(self, port):
        try:
            port = int(port)
        except ValueError:
            raise TypeError(f"{__class__.__name__}.__init__() got an invalid port: '{port}'")
        if not (0 <= port <= 65535):
            raise ValueError("port must be 0-65535")
        self._port = port

    @property
    def version(self):
        return self._version

    @version.setter
    def version(self, version):
        if version:
            if not re.match(r"^\d+\.\d+\.\d+$", str(version)):
                raise TypeError(f"{__class__.__name__}.__init__() got an invalid version: '{version}'")
        self._version = version

    @property
    def log_level(self):
        return self._log_level

    @log_level.setter
    def log_level(self, log_level):
        levels = ("SEVERE", "WARNING", "INFO", "CONFIG", "FINE", "FINER", "FINEST")
        if log_level not in levels:
            raise TypeError(f"log_level must be one of: {', '.join(levels)}")
        self._log_level = log_level

    @property
    def env(self):
        return self._env

    @env.setter
    def env(self, env):
        if env is not None and not isinstance(env, collections.abc.Mapping):
            raise TypeError("env must be a mapping of environment variables")
        self._env = env

    @property
    def java_path(self):
        return self._java_path

    @java_path.setter
    def java_path(self, java_path):
        if java_path and not os.path.exists(java_path):
            raise OSError(f"Can't find java executable located at {java_path}")
        self._java_path = java_path

    def _wait_for_server(self, timeout=10):
        start = time.time()
        while time.time() - start < timeout:
            try:
                urllib.request.urlopen(self.status_url)
                return True
            except urllib.error.URLError:
                time.sleep(0.2)
        return False

    def download_if_needed(self, version=None):
        """Download the server if it doesn't already exist.

        Latest version is downloaded unless specified.
        """
        args = ["--grid"]
        if version is not None:
            args.append(version)
        return SeleniumManager().binary_paths(args)["driver_path"]

    def start(self):
        """Start the server.

        Selenium Manager will detect the server location and download it if necessary,
        unless an existing server path was specified.
        """
        path = self.download_if_needed(self.version) if self.path is None else self.path

        java_path = self.java_path or shutil.which("java")
        if java_path is None:
            raise OSError("Can't find java on system PATH. JRE is required to run the Selenium server")

        command = [
            java_path,
            "-jar",
            path,
            "standalone",
            "--port",
            str(self.port),
            "--log-level",
            self.log_level,
            "--selenium-manager",
            "true",
            "--enable-managed-downloads",
            "true",
        ]
        if self.host is not None:
            command.extend(["--host", self.host])

        host = self.host if self.host is not None else "localhost"

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect((host, self.port))
            raise ConnectionError(f"Selenium server is already running, or something else is using port {self.port}")
        except ConnectionRefusedError:
            print("Starting Selenium server...")
            self.process = subprocess.Popen(command, env=self.env)
            print(f"Selenium server running as process: {self.process.pid}")
            if not self._wait_for_server(timeout=self.startup_timeout):
                raise TimeoutError(f"Timed out waiting for Selenium server at {self.status_url}")
            print("Selenium server is ready")
        return self.process

    def stop(self):
        """Stop the server."""
        if self.process is None:
            raise RuntimeError("Selenium server isn't running")
        else:
            if self.process.poll() is None:
                self.process.terminate()
                self.process.wait()
            self.process = None
            print("Selenium server has been terminated")
