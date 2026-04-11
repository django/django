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

import json
import logging
import os
import platform
import subprocess
import sys
import sysconfig
from pathlib import Path

from selenium.common import WebDriverException

logger = logging.getLogger(__name__)


class SeleniumManager:
    """Wrapper for getting information from the Selenium Manager binaries.

    This implementation is still in beta, and may change.
    """

    def binary_paths(self, args: list) -> dict:
        """Determines the locations of the requested assets.

        Args:
            args: the commands to send to the selenium manager binary.

        Returns:
            Dictionary of assets and their path.
        """
        args = [str(self._get_binary())] + args
        if logger.getEffectiveLevel() == logging.DEBUG:
            args.append("--debug")
        args.append("--language-binding")
        args.append("python")
        args.append("--output")
        args.append("json")

        return self._run(args)

    @staticmethod
    def _get_binary() -> Path:
        """Determines the path of the Selenium Manager binary.

        Location of the binary is checked in this order:

        1. location set in an environment variable
        2. location where setuptools-rust places the compiled binary (built from the sdist package)
        3. location where we ship binaries in the wheel package for the platform this is running on
        4. give up

        Returns:
            The Selenium Manager executable location.

        Raises:
            WebDriverException: If the platform is unsupported or Selenium Manager executable can't be found.
        """
        compiled_path = Path(__file__).parent.joinpath("selenium-manager")
        exe = sysconfig.get_config_var("EXE")
        if exe is not None:
            compiled_path = compiled_path.with_suffix(exe)

        path: Path | None = None

        if (env_path := os.getenv("SE_MANAGER_PATH")) is not None:
            logger.debug(f"Selenium Manager set by env SE_MANAGER_PATH to: {env_path}")
            path_candidate = Path(env_path)
            if not path_candidate.is_file():
                raise WebDriverException(f"SE_MANAGER_PATH does not point to a file: {env_path}")
            path = path_candidate
        elif compiled_path.is_file():
            path = compiled_path
        else:
            allowed = {
                ("darwin", "any"): "macos/selenium-manager",
                ("win32", "any"): "windows/selenium-manager.exe",
                ("cygwin", "any"): "windows/selenium-manager.exe",
                ("linux", "x86_64"): "linux/selenium-manager",
                ("freebsd", "x86_64"): "linux/selenium-manager",
                ("openbsd", "x86_64"): "linux/selenium-manager",
            }

            arch = platform.machine() if sys.platform in ("linux", "freebsd", "openbsd") else "any"
            if sys.platform in ["freebsd", "openbsd"]:
                logger.warning(f"Selenium Manager binary may not be compatible with {sys.platform}; verify settings")

            location = allowed.get((sys.platform, arch))
            if location is None:
                raise WebDriverException(f"Unsupported platform/architecture combination: {sys.platform}/{arch}")

            path = Path(__file__).parent.joinpath(location)

        if path is None or not path.is_file():
            raise WebDriverException(f"Unable to obtain working Selenium Manager binary; {path}")

        logger.debug(f"Selenium Manager binary found at: {path}")

        return path

    @staticmethod
    def _run(args: list[str]) -> dict:
        """Executes the Selenium Manager Binary.

        Args:
            args: the components of the command being executed.

        Returns:
            The log string containing the driver location.
        """
        command = " ".join(args)
        logger.debug("Executing process: %s", command)
        try:
            if sys.platform == "win32":
                completed_proc = subprocess.run(args, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                completed_proc = subprocess.run(args, capture_output=True)
            stdout = completed_proc.stdout.decode("utf-8").rstrip("\n")
            stderr = completed_proc.stderr.decode("utf-8").rstrip("\n")
            output = json.loads(stdout) if stdout != "" else {"logs": [], "result": {}}
        except Exception as err:
            raise WebDriverException(f"Unsuccessful command executed: {command}") from err

        SeleniumManager._process_logs(output["logs"])
        result = output["result"]
        if completed_proc.returncode:
            raise WebDriverException(
                f"Unsuccessful command executed: {command}; code: {completed_proc.returncode}\n{result}\n{stderr}"
            )
        return result

    @staticmethod
    def _process_logs(log_items: list[dict]):
        for item in log_items:
            if item["level"] == "WARN":
                logger.warning(item["message"])
            elif item["level"] in ["DEBUG", "INFO"]:
                logger.debug(item["message"])
