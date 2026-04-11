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
import warnings
from typing import NoReturn, overload

from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By, ByType
from selenium.webdriver.remote.webelement import WebElement


def with_tag_name(tag_name: str) -> "RelativeBy":
    """Start searching for relative objects using a tag name.

    Args:
        tag_name: The DOM tag of element to start searching.

    Returns:
        RelativeBy: Use this object to create filters within a `find_elements` call.

    Raises:
        WebDriverException: If `tag_name` is None.

    Note:
        This method is deprecated and may be removed in future versions.
        Please use `locate_with` instead.
    """
    warnings.warn("This method is deprecated and may be removed in future versions. Please use `locate_with` instead.")
    if not tag_name:
        raise WebDriverException("tag_name can not be null")
    return RelativeBy({By.CSS_SELECTOR: tag_name})


def locate_with(by: ByType, using: str) -> "RelativeBy":
    """Start searching for relative objects your search criteria with By.

    Args:
        by: The method to find the element.
        using: The value from `By` passed in.

    Returns:
        RelativeBy: Use this object to create filters within a `find_elements` call.

    Example:
        >>> lowest = driver.find_element(By.ID, "below")
        >>> elements = driver.find_elements(locate_with(By.CSS_SELECTOR, "p").above(lowest))
    """
    assert by is not None, "Please pass in a by argument"
    assert using is not None, "Please pass in a using argument"
    return RelativeBy({by: using})


class RelativeBy:
    """Find elements based on their relative location from a root element.

    It is recommended that you use the helper function to create instances.

    Example:
    --------
    >>> lowest = driver.find_element(By.ID, "below")
    >>> elements = driver.find_elements(locate_with(By.CSS_SELECTOR, "p").above(lowest))
    >>> ids = [el.get_attribute("id") for el in elements]
    >>> assert "above" in ids
    >>> assert "mid" in ids
    """

    LocatorType = dict[ByType, str]

    def __init__(self, root: dict[ByType, str] | None = None, filters: list | None = None):
        """Create a RelativeBy object (prefer using `locate_with` instead).

        Args:
            root: A dict with `By` enum as the key and the search query as the value
            filters: A list of the filters that will be searched. If none are passed
                in please use the fluent API on the object to create the filters
        """
        self.root = root
        self.filters = filters or []

    @overload
    def above(self, element_or_locator: WebElement | LocatorType) -> "RelativeBy": ...

    @overload
    def above(self, element_or_locator: None = None) -> "NoReturn": ...

    def above(self, element_or_locator: WebElement | LocatorType | None = None) -> "RelativeBy":
        """Add a filter to look for elements above.

        Args:
            element_or_locator: Element to look above

        Returns:
            RelativeBy

        Raises:
            WebDriverException: If `element_or_locator` is None.

        Example:
        --------
        >>> lowest = driver.find_element(By.ID, "below")
        >>> elements = driver.find_elements(locate_with(By.CSS_SELECTOR, "p").above(lowest))
        """
        if not element_or_locator:
            raise WebDriverException("Element or locator must be given when calling above method")

        self.filters.append({"kind": "above", "args": [element_or_locator]})
        return self

    @overload
    def below(self, element_or_locator: WebElement | LocatorType) -> "RelativeBy": ...

    @overload
    def below(self, element_or_locator: None = None) -> "NoReturn": ...

    def below(self, element_or_locator: WebElement | dict | None = None) -> "RelativeBy":
        """Add a filter to look for elements below.

        Args:
            element_or_locator: Element to look below

        Returns:
            RelativeBy

        Raises:
            WebDriverException: If `element_or_locator` is None.

        Example:
            >>> highest = driver.find_element(By.ID, "high")
            >>> elements = driver.find_elements(locate_with(By.CSS_SELECTOR, "p").below(highest))
        """
        if not element_or_locator:
            raise WebDriverException("Element or locator must be given when calling below method")

        self.filters.append({"kind": "below", "args": [element_or_locator]})
        return self

    @overload
    def to_left_of(self, element_or_locator: WebElement | LocatorType) -> "RelativeBy": ...

    @overload
    def to_left_of(self, element_or_locator: None = None) -> "NoReturn": ...

    def to_left_of(self, element_or_locator: WebElement | dict | None = None) -> "RelativeBy":
        """Add a filter to look for elements to the left of.

        Args:
            element_or_locator: Element to look to the left of

        Returns:
            RelativeBy

        Raises:
            WebDriverException: If `element_or_locator` is None.

        Example:
            >>> right = driver.find_element(By.ID, "right")
            >>> elements = driver.find_elements(locate_with(By.CSS_SELECTOR, "p").to_left_of(right))
        """
        if not element_or_locator:
            raise WebDriverException("Element or locator must be given when calling to_left_of method")

        self.filters.append({"kind": "left", "args": [element_or_locator]})
        return self

    @overload
    def to_right_of(self, element_or_locator: WebElement | LocatorType) -> "RelativeBy": ...

    @overload
    def to_right_of(self, element_or_locator: None = None) -> "NoReturn": ...

    def to_right_of(self, element_or_locator: WebElement | dict | None = None) -> "RelativeBy":
        """Add a filter to look for elements right of.

        Args:
            element_or_locator: Element to look right of

        Returns:
            RelativeBy

        Raises:
            WebDriverException: If `element_or_locator` is None.

        Example:
            >>> left = driver.find_element(By.ID, "left")
            >>> elements = driver.find_elements(locate_with(By.CSS_SELECTOR, "p").to_right_of(left))
        """
        if not element_or_locator:
            raise WebDriverException("Element or locator must be given when calling to_right_of method")

        self.filters.append({"kind": "right", "args": [element_or_locator]})
        return self

    @overload
    def straight_above(self, element_or_locator: WebElement | LocatorType) -> "RelativeBy": ...

    @overload
    def straight_above(self, element_or_locator: None = None) -> "NoReturn": ...

    def straight_above(self, element_or_locator: WebElement | LocatorType | None = None) -> "RelativeBy":
        """Add a filter to look for elements above.

        Args:
            element_or_locator: Element to look above
        """
        if not element_or_locator:
            raise WebDriverException("Element or locator must be given when calling above method")

        self.filters.append({"kind": "straightAbove", "args": [element_or_locator]})
        return self

    @overload
    def straight_below(self, element_or_locator: WebElement | LocatorType) -> "RelativeBy": ...

    @overload
    def straight_below(self, element_or_locator: None = None) -> "NoReturn": ...

    def straight_below(self, element_or_locator: WebElement | dict | None = None) -> "RelativeBy":
        """Add a filter to look for elements below.

        Args:
            element_or_locator: Element to look below
        """
        if not element_or_locator:
            raise WebDriverException("Element or locator must be given when calling below method")

        self.filters.append({"kind": "straightBelow", "args": [element_or_locator]})
        return self

    @overload
    def straight_left_of(self, element_or_locator: WebElement | LocatorType) -> "RelativeBy": ...

    @overload
    def straight_left_of(self, element_or_locator: None = None) -> "NoReturn": ...

    def straight_left_of(self, element_or_locator: WebElement | dict | None = None) -> "RelativeBy":
        """Add a filter to look for elements to the left of.

        Args:
            element_or_locator: Element to look to the left of
        """
        if not element_or_locator:
            raise WebDriverException("Element or locator must be given when calling to_left_of method")

        self.filters.append({"kind": "straightLeft", "args": [element_or_locator]})
        return self

    @overload
    def straight_right_of(self, element_or_locator: WebElement | LocatorType) -> "RelativeBy": ...

    @overload
    def straight_right_of(self, element_or_locator: None = None) -> "NoReturn": ...

    def straight_right_of(self, element_or_locator: WebElement | dict | None = None) -> "RelativeBy":
        """Add a filter to look for elements right of.

        Args:
            element_or_locator: Element to look right of
        """
        if not element_or_locator:
            raise WebDriverException("Element or locator must be given when calling to_right_of method")

        self.filters.append({"kind": "straightRight", "args": [element_or_locator]})
        return self

    @overload
    def near(self, element_or_locator: WebElement | LocatorType, distance: int = 50) -> "RelativeBy": ...

    @overload
    def near(self, element_or_locator: None = None, distance: int = 50) -> "NoReturn": ...

    def near(self, element_or_locator: WebElement | LocatorType | None = None, distance: int = 50) -> "RelativeBy":
        """Add a filter to look for elements near.

        Args:
            element_or_locator: Element to look near by the element or within a distance
            distance: Distance in pixel

        Returns:
            RelativeBy

        Raises:
            WebDriverException: If `element_or_locator` is None
            WebDriverException: If `distance` is less than or equal to 0.

        Example:
            >>> near = driver.find_element(By.ID, "near")
            >>> elements = driver.find_elements(locate_with(By.CSS_SELECTOR, "p").near(near, 50))
        """
        if not element_or_locator:
            raise WebDriverException("Element or locator must be given when calling near method")
        if distance <= 0:
            raise WebDriverException("Distance must be positive")

        self.filters.append({"kind": "near", "args": [element_or_locator, distance]})
        return self

    def to_dict(self) -> dict:
        """Create a dict to be passed to the driver for element searching."""
        return {
            "relative": {
                "root": self.root,
                "filters": self.filters,
            }
        }
