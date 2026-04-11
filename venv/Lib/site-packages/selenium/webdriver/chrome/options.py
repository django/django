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


from selenium.webdriver.chromium.options import ChromiumOptions
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities


class Options(ChromiumOptions):
    @property
    def default_capabilities(self) -> dict:
        return DesiredCapabilities.CHROME.copy()

    def enable_mobile(
        self,
        android_package: str | None = "com.android.chrome",
        android_activity: str | None = None,
        device_serial: str | None = None,
    ) -> None:
        super().enable_mobile(android_package, android_activity, device_serial)
