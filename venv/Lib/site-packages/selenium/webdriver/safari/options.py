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

from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.common.options import ArgOptions


class _SafariOptionsDescriptor:
    """_SafariOptionsDescriptor is an implementation of Descriptor protocol.

    Any look-up or assignment to the below attributes in `Options` class will be intercepted
    by `__get__` and `__set__` method respectively when an attribute lookup happens:

      - `automatic_inspection`
      - `automatic_profiling`
      - `use_technology_preview`

    Example:
        `self.automatic_inspection`
        (`__get__` method does a dictionary look up in the dictionary `_caps` of `Options` class
            and returns the value of key `safari:automaticInspection`)

    Example:
        `self.automatic_inspection` = True
        (`__set__` method sets/updates the value of the key `safari:automaticInspection` in `_caps`
            dictionary in `Options` class)
    """

    def __init__(self, name, expected_type):
        self.name = name
        self.expected_type = expected_type

    def __get__(self, obj, cls):
        if self.name == "Safari Technology Preview":
            return obj._caps.get("browserName") == self.name
        return obj._caps.get(self.name)

    def __set__(self, obj, value):
        if not isinstance(value, self.expected_type):
            raise TypeError(f"{self.name} must be of type {self.expected_type}")
        if self.name == "Safari Technology Preview":
            obj._caps["browserName"] = self.name if value else "safari"
        else:
            obj._caps[self.name] = value


class Options(ArgOptions):
    # @see https://developer.apple.com/documentation/webkit/about_webdriver_for_safari
    AUTOMATIC_INSPECTION = "safari:automaticInspection"
    AUTOMATIC_PROFILING = "safari:automaticProfiling"
    SAFARI_TECH_PREVIEW = "Safari Technology Preview"

    # creating descriptor objects
    automatic_inspection = _SafariOptionsDescriptor(AUTOMATIC_INSPECTION, bool)
    """Whether to enable automatic inspection."""

    automatic_profiling = _SafariOptionsDescriptor(AUTOMATIC_PROFILING, bool)
    """Whether to enable automatic profiling."""

    use_technology_preview = _SafariOptionsDescriptor(SAFARI_TECH_PREVIEW, bool)
    """Whether to use Safari Technology Preview."""

    @property
    def default_capabilities(self) -> dict[str, str]:
        return DesiredCapabilities.SAFARI.copy()
