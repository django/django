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

from selenium.webdriver.remote.webdriver import WebDriver as RemoteWebDriver


class LocalWebDriver(RemoteWebDriver):
    """Base class for local WebDrivers."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._is_remote = False

    def __new__(cls, *args, **kwargs):
        if cls is LocalWebDriver:
            raise TypeError(f"Only children of '{cls.__name__}' may be instantiated")
        return object.__new__(cls)

    def quit(self) -> None:
        """Closes the browser and shuts down the driver executable."""
        try:
            super().quit()
        except Exception:
            # We don't care about the message because something probably has gone wrong
            pass
        finally:
            if hasattr(self, "service") and self.service is not None:
                self.service.stop()

    def download_file(self, *args, **kwargs):
        """Only implemented in RemoteWebDriver."""
        raise NotImplementedError

    def get_downloadable_files(self, *args, **kwargs):
        """Only implemented in RemoteWebDriver."""
        raise NotImplementedError

    def delete_downloadable_files(self, *args, **kwargs):
        """Only implemented in RemoteWebDriver."""
        raise NotImplementedError
