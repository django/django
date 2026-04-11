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

from selenium.common.exceptions import InvalidSelectorException
from selenium.webdriver.common.by import By


class LocatorConverter:
    def convert(self, by, value):
        # Default conversion logic
        if by == By.ID:
            return By.CSS_SELECTOR, f'[id="{value}"]'
        elif by == By.CLASS_NAME:
            if value and any(char.isspace() for char in value.strip()):
                raise InvalidSelectorException("Compound class names are not allowed.")
            return By.CSS_SELECTOR, f".{value}"
        elif by == By.NAME:
            return By.CSS_SELECTOR, f'[name="{value}"]'
        return by, value
