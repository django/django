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


class Options(object):

    def __init__(self):
        self._page_load_strategy = "normal"
        self._caps = DesiredCapabilities.EDGE.copy()

    @property
    def page_load_strategy(self):
        return self._page_load_strategy

    @page_load_strategy.setter
    def page_load_strategy(self, value):
        if value not in ['normal', 'eager', 'none']:
            raise ValueError("Page Load Strategy should be 'normal', 'eager' or 'none'.")
        self._page_load_strategy = value

    @property
    def capabilities(self):
        return self._caps

    def set_capability(self, name, value):
        """Sets a capability."""
        self._caps[name] = value

    def to_capabilities(self):
        """
            Creates a capabilities with all the options that have been set and

            returns a dictionary with everything
        """
        caps = self._caps
        caps['pageLoadStrategy'] = self._page_load_strategy

        return caps
