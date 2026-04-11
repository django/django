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


from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.bidi.common import command_builder


class WebExtension:
    """BiDi implementation of the webExtension module."""

    def __init__(self, conn):
        self.conn = conn

    def install(self, path=None, archive_path=None, base64_value=None) -> dict:
        """Installs a web extension in the remote end.

        You must provide exactly one of the parameters.

        Args:
            path: Path to an extension directory.
            archive_path: Path to an extension archive file.
            base64_value: Base64 encoded string of the extension archive.

        Returns:
            A dictionary containing the extension ID.
        """
        if sum(x is not None for x in (path, archive_path, base64_value)) != 1:
            raise ValueError("Exactly one of path, archive_path, or base64_value must be provided")

        if path is not None:
            extension_data = {"type": "path", "path": path}
        elif archive_path is not None:
            extension_data = {"type": "archivePath", "path": archive_path}
        elif base64_value is not None:
            extension_data = {"type": "base64", "value": base64_value}

        params = {"extensionData": extension_data}

        try:
            result = self.conn.execute(command_builder("webExtension.install", params))
            return result
        except WebDriverException as e:
            if "Method not available" in str(e):
                raise WebDriverException(
                    f"{e!s}. If you are using Chrome or Edge, add '--enable-unsafe-extension-debugging' "
                    "and '--remote-debugging-pipe' arguments or set options.enable_webextensions = True"
                ) from e
            raise

    def uninstall(self, extension_id_or_result: str | dict) -> None:
        """Uninstalls a web extension from the remote end.

        Args:
            extension_id_or_result: Either the extension ID as a string or the result dictionary
              from a previous install() call containing the extension ID.
        """
        if isinstance(extension_id_or_result, dict):
            extension_id = extension_id_or_result.get("extension")
        else:
            extension_id = extension_id_or_result

        params = {"extension": extension_id}
        self.conn.execute(command_builder("webExtension.uninstall", params))
