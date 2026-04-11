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
"""The By implementation."""

from typing import Literal

ByType = Literal["id", "xpath", "link text", "partial link text", "name", "tag name", "class name", "css selector"]


class By:
    """Set of supported locator strategies.

    ID:
    --
    Select the element by its ID.

    >>> element = driver.find_element(By.ID, "myElement")

    XPATH:
    ------
    Select the element via XPATH.
        - absolute path
        - relative path

    >>> element = driver.find_element(By.XPATH, "//html/body/div")

    LINK_TEXT:
    ----------
    Select the link element having the exact text.

    >>> element = driver.find_element(By.LINK_TEXT, "myLink")

    PARTIAL_LINK_TEXT:
    ------------------
    Select the link element having the partial text.

    >>> element = driver.find_element(By.PARTIAL_LINK_TEXT, "my")

    NAME:
    ----
    Select the element by its name attribute.

    >>> element = driver.find_element(By.NAME, "myElement")

    TAG_NAME:
    --------
    Select the element by its tag name.

    >>> element = driver.find_element(By.TAG_NAME, "div")

    CLASS_NAME:
    -----------
    Select the element by its class name.

    >>> element = driver.find_element(By.CLASS_NAME, "myElement")

    CSS_SELECTOR:
    -------------
    Select the element by its CSS selector.

    >>> element = driver.find_element(By.CSS_SELECTOR, "div.myElement")
    """

    ID: ByType = "id"
    XPATH: ByType = "xpath"
    LINK_TEXT: ByType = "link text"
    PARTIAL_LINK_TEXT: ByType = "partial link text"
    NAME: ByType = "name"
    TAG_NAME: ByType = "tag name"
    CLASS_NAME: ByType = "class name"
    CSS_SELECTOR: ByType = "css selector"

    _custom_finders: dict[str, str] = {}

    @classmethod
    def register_custom_finder(cls, name: str, strategy: str) -> None:
        cls._custom_finders[name] = strategy

    @classmethod
    def get_finder(cls, name: str) -> str | None:
        return cls._custom_finders.get(name) or getattr(cls, name.upper(), None)

    @classmethod
    def clear_custom_finders(cls) -> None:
        cls._custom_finders.clear()
