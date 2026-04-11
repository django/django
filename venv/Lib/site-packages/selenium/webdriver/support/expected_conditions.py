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

import re
from collections.abc import Callable, Iterable
from typing import Any, Literal, TypeVar

from selenium.common.exceptions import (
    NoAlertPresentException,
    NoSuchElementException,
    NoSuchFrameException,
    StaleElementReferenceException,
    WebDriverException,
)
from selenium.webdriver.common.alert import Alert
from selenium.webdriver.remote.webdriver import WebDriver, WebElement

"""
 * Canned "Expected Conditions" which are generally useful within webdriver
 * tests.
"""

D = TypeVar("D")
T = TypeVar("T")

WebDriverOrWebElement = WebDriver | WebElement


def title_is(title: str) -> Callable[[WebDriver], bool]:
    """An expectation for checking the title of a page.

    Args:
        title: The expected title, which must be an exact match.

    Returns:
        True if the title matches, False otherwise.
    """

    def _predicate(driver: WebDriver):
        return driver.title == title

    return _predicate


def title_contains(title: str) -> Callable[[WebDriver], bool]:
    """Check that the title contains a case-sensitive substring.

    Args:
        title: The fragment of title expected.

    Returns:
        True when the title matches, False otherwise.
    """

    def _predicate(driver: WebDriver):
        return title in driver.title

    return _predicate


def presence_of_element_located(locator: tuple[str, str]) -> Callable[[WebDriverOrWebElement], WebElement]:
    """Check that an element is present on the DOM (not necessarily visible).

    Args:
        locator: Used to find the element.

    Returns:
        The WebElement once it is located.

    Example:
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        element = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "q")))
    """

    def _predicate(driver: WebDriverOrWebElement):
        return driver.find_element(*locator)

    return _predicate


def url_contains(url: str) -> Callable[[WebDriver], bool]:
    """Check that the current url contains a case-sensitive substring.

    Args:
        url: The fragment of url expected.

    Returns:
        True when the url matches, False otherwise.
    """

    def _predicate(driver: WebDriver):
        return url in driver.current_url

    return _predicate


def url_matches(pattern: str) -> Callable[[WebDriver], bool]:
    """An expectation for checking the current url.

    Args:
        pattern: The pattern to match with the current url.

    Returns:
        True when the pattern matches, False otherwise.

    Note:
        More powerful than url_contains, as it allows for regular expressions.
    """

    def _predicate(driver: WebDriver):
        return re.search(pattern, driver.current_url) is not None

    return _predicate


def url_to_be(url: str) -> Callable[[WebDriver], bool]:
    """An expectation for checking the current url.

    Args:
        url: The expected url, which must be an exact match.

    Returns:
        True when the url matches, False otherwise.
    """

    def _predicate(driver: WebDriver):
        return url == driver.current_url

    return _predicate


def url_changes(url: str) -> Callable[[WebDriver], bool]:
    """Check that the current url differs from a given string.

    Args:
        url: The expected url, which must not be an exact match.

    Returns:
        True when the url does not match, False otherwise.
    """

    def _predicate(driver: WebDriver):
        return url != driver.current_url

    return _predicate


def visibility_of_element_located(
    locator: tuple[str, str],
) -> Callable[[WebDriverOrWebElement], Literal[False] | WebElement]:
    """Check that an element is visible (present in DOM and width/height greater than zero).

    Args:
        locator: Used to find the element.

    Returns:
        The WebElement once it is located and visible.

    Example:
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        element = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.NAME, "q")))
    """

    def _predicate(driver: WebDriverOrWebElement):
        try:
            return _element_if_visible(driver.find_element(*locator))
        except StaleElementReferenceException:
            return False

    return _predicate


def visibility_of(element: WebElement) -> Callable[[Any], Literal[False] | WebElement]:
    """Check that an element is visible (present in DOM and width/height greater than zero).

    Args:
        element: The WebElement to check.

    Returns:
        The WebElement once it is visible.

    Example:
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        element = WebDriverWait(driver, 10).until(EC.visibility_of(driver.find_element(By.NAME, "q")))
    """

    def _predicate(_):
        return _element_if_visible(element)

    return _predicate


def _element_if_visible(element: WebElement, visibility: bool = True) -> Literal[False] | WebElement:
    """Check if an element has the expected visibility state.

    Args:
        element: The WebElement to check.
        visibility: The expected visibility of the element.

    Returns:
        The WebElement once it is visible or not visible.
    """
    return element if element.is_displayed() == visibility else False


def presence_of_all_elements_located(locator: tuple[str, str]) -> Callable[[WebDriverOrWebElement], list[WebElement]]:
    """Check that all elements matching the locator are present on the DOM.

    Args:
        locator: Used to find the element.

    Returns:
        The list of WebElements once they are located.

    Example:
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        elements = WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.CLASS_NAME, "foo")))
    """

    def _predicate(driver: WebDriverOrWebElement):
        return driver.find_elements(*locator)

    return _predicate


def visibility_of_any_elements_located(locator: tuple[str, str]) -> Callable[[WebDriverOrWebElement], list[WebElement]]:
    """Check that at least one element is visible on the web page (present in DOM and width/height greater than zero).

    Args:
        locator: Used to find the element.

    Returns:
        The list of WebElements once they are located and visible.

    Example:
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        elements = WebDriverWait(driver, 10).until(EC.visibility_of_any_elements_located((By.CLASS_NAME, "foo")))
    """

    def _predicate(driver: WebDriverOrWebElement):
        return [element for element in driver.find_elements(*locator) if _element_if_visible(element)]

    return _predicate


def visibility_of_all_elements_located(
    locator: tuple[str, str],
) -> Callable[[WebDriverOrWebElement], list[WebElement] | Literal[False]]:
    """Check that all elements are visible (present in DOM and width/height greater than zero).

    Args:
        locator: Used to find the elements.

    Returns:
        The list of WebElements once they are located and visible.

    Example:
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        elements = WebDriverWait(driver, 10).until(EC.visibility_of_all_elements_located((By.CLASS_NAME, "foo")))
    """

    def _predicate(driver: WebDriverOrWebElement):
        try:
            elements = driver.find_elements(*locator)
            for element in elements:
                if _element_if_visible(element, visibility=False):
                    return False
            return elements
        except StaleElementReferenceException:
            return False

    return _predicate


def text_to_be_present_in_element(locator: tuple[str, str], text_: str) -> Callable[[WebDriverOrWebElement], bool]:
    """Check that the given text is present in the specified element.

    Args:
        locator: Used to find the element.
        text_: The text to be present in the element.

    Returns:
        True when the text is present, False otherwise.

    Example:
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        is_text_in_element = WebDriverWait(driver, 10).until(
            EC.text_to_be_present_in_element((By.CLASS_NAME, "foo"), "bar")
        )
    """

    def _predicate(driver: WebDriverOrWebElement):
        try:
            element_text = driver.find_element(*locator).text
            return text_ in element_text
        except StaleElementReferenceException:
            return False

    return _predicate


def text_to_be_present_in_element_value(
    locator: tuple[str, str], text_: str
) -> Callable[[WebDriverOrWebElement], bool]:
    """Check that the given text is present in the element's value.

    Args:
        locator: Used to find the element.
        text_: The text to be present in the element's value.

    Returns:
        True when the text is present, False otherwise.

    Example:
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        is_text_in_element_value = WebDriverWait(driver, 10).until(
            EC.text_to_be_present_in_element_value((By.CLASS_NAME, "foo"), "bar")
        )
    """

    def _predicate(driver: WebDriverOrWebElement):
        try:
            element_text = driver.find_element(*locator).get_attribute("value")
            if element_text is None:
                return False
            return text_ in element_text
        except StaleElementReferenceException:
            return False

    return _predicate


def text_to_be_present_in_element_attribute(
    locator: tuple[str, str], attribute_: str, text_: str
) -> Callable[[WebDriverOrWebElement], bool]:
    """Check that the given text is present in the element's attribute.

    Args:
        locator: Used to find the element.
        attribute_: The attribute to check the text in.
        text_: The text to be present in the element's attribute.

    Returns:
        True when the text is present, False otherwise.

    Example:
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        is_text_in_element_attribute = WebDriverWait(driver, 10).until(
            EC.text_to_be_present_in_element_attribute((By.CLASS_NAME, "foo"), "bar", "baz")
        )
    """

    def _predicate(driver: WebDriverOrWebElement):
        try:
            element_text = driver.find_element(*locator).get_attribute(attribute_)
            if element_text is None:
                return False
            return text_ in element_text
        except StaleElementReferenceException:
            return False

    return _predicate


def frame_to_be_available_and_switch_to_it(
    locator: tuple[str, str] | str | WebElement,
) -> Callable[[WebDriver], bool]:
    """Check that the given frame is available and switch to it.

    Args:
        locator: Used to find the frame.

    Returns:
        True when the frame is available, False otherwise.

    Example:
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        WebDriverWait(driver, 10).until(EC.frame_to_be_available_and_switch_to_it("frame_name"))
    """

    def _predicate(driver: WebDriver):
        try:
            if isinstance(locator, Iterable) and not isinstance(locator, str):
                driver.switch_to.frame(driver.find_element(*locator))
            else:
                driver.switch_to.frame(locator)
            return True
        except NoSuchFrameException:
            return False

    return _predicate


def invisibility_of_element_located(
    locator: WebElement | tuple[str, str],
) -> Callable[[WebDriverOrWebElement], WebElement | bool]:
    """Check that an element is either invisible or not present on the DOM.

    Args:
        locator: Used to find the element.

    Returns:
        True when the element is invisible or not present, False otherwise.

    Example:
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        is_invisible = WebDriverWait(driver, 10).until(EC.invisibility_of_element_located((By.CLASS_NAME, "foo")))

    Note:
        In the case of NoSuchElement, returns true because the element is not
        present in DOM. The try block checks if the element is present but is
        invisible.
        In the case of StaleElementReference, returns true because stale element
        reference implies that element is no longer visible.
    """

    def _predicate(driver: WebDriverOrWebElement):
        try:
            target = locator
            if not isinstance(target, WebElement):
                target = driver.find_element(*target)
            return _element_if_visible(target, visibility=False)
        except (NoSuchElementException, StaleElementReferenceException):
            # In the case of NoSuchElement, returns true because the element is
            # not present in DOM. The try block checks if the element is present
            # but is invisible.
            # In the case of StaleElementReference, returns true because stale
            # element reference implies that element is no longer visible.
            return True

    return _predicate


def invisibility_of_element(
    element: WebElement | tuple[str, str],
) -> Callable[[WebDriverOrWebElement], WebElement | bool]:
    """Check that an element is either invisible or not present on the DOM.

    Args:
        element: Used to find the element.

    Returns:
        True when the element is invisible or not present, False otherwise.

    Example:
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        is_invisible_or_not_present = WebDriverWait(driver, 10).until(
            EC.invisibility_of_element(driver.find_element(By.CLASS_NAME, "foo"))
        )
    """
    return invisibility_of_element_located(element)


def element_to_be_clickable(
    mark: WebElement | tuple[str, str],
) -> Callable[[WebDriverOrWebElement], Literal[False] | WebElement]:
    """Check that an element is visible and enabled so it can be clicked.

    Args:
        mark: Used to find the element.

    Returns:
        The WebElement once it is located and clickable.

    Example:
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        element = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CLASS_NAME, "foo")))
    """

    # renamed argument to 'mark', to indicate that both locator
    # and WebElement args are valid
    def _predicate(driver: WebDriverOrWebElement):
        target = mark
        if not isinstance(target, WebElement):  # if given locator instead of WebElement
            target = driver.find_element(*target)  # grab element at locator
        element = visibility_of(target)(driver)
        if element and element.is_enabled():
            return element
        return False

    return _predicate


def staleness_of(element: WebElement) -> Callable[[Any], bool]:
    """Wait until an element is no longer attached to the DOM.

    Args:
        element: The element to wait for.

    Returns:
        False if the element is still attached to the DOM, true otherwise.

    Example:
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        is_stale = WebDriverWait(driver, 10).until(EC.staleness_of(driver.find_element(By.CLASS_NAME, "foo")))
    """

    def _predicate(_):
        try:
            # Calling any method forces a staleness check
            element.is_enabled()
            return False
        except StaleElementReferenceException:
            return True

    return _predicate


def element_to_be_selected(element: WebElement) -> Callable[[Any], bool]:
    """An expectation for checking the selection is selected.

    Args:
        element: The WebElement to check.

    Returns:
        True if the element is selected, False otherwise.

    Example:
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        is_selected = WebDriverWait(driver, 10).until(EC.element_to_be_selected(driver.find_element(
            By.CLASS_NAME, "foo"))
        )
    """

    def _predicate(_):
        return element.is_selected()

    return _predicate


def element_located_to_be_selected(locator: tuple[str, str]) -> Callable[[WebDriverOrWebElement], bool]:
    """An expectation for the element to be located is selected.

    Args:
        locator: Used to find the element.

    Returns:
        True if the element is selected, False otherwise.

    Example:
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        is_selected = WebDriverWait(driver, 10).until(EC.element_located_to_be_selected((By.CLASS_NAME, "foo")))
    """

    def _predicate(driver: WebDriverOrWebElement):
        return driver.find_element(*locator).is_selected()

    return _predicate


def element_selection_state_to_be(element: WebElement, is_selected: bool) -> Callable[[Any], bool]:
    """An expectation for checking if the given element is selected.

    Args:
        element: The WebElement to check.
        is_selected: The expected selection state.

    Returns:
        True if the element's selection state is the same as is_selected.

    Example:
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        is_selected = WebDriverWait(driver, 10).until(
            EC.element_selection_state_to_be(driver.find_element(By.CLASS_NAME, "foo"), True)
        )
    """

    def _predicate(_):
        return element.is_selected() == is_selected

    return _predicate


def element_located_selection_state_to_be(
    locator: tuple[str, str], is_selected: bool
) -> Callable[[WebDriverOrWebElement], bool]:
    """Check that an element's selection state matches the expected state.

    Args:
        locator: Used to find the element.
        is_selected: The expected selection state.

    Returns:
        True if the element's selection state is the same as is_selected.

    Example:
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        is_selected = WebDriverWait(driver, 10).until(EC.element_located_selection_state_to_be(
            (By.CLASS_NAME, "foo"), True)
        )
    """

    def _predicate(driver: WebDriverOrWebElement):
        try:
            element = driver.find_element(*locator)
            return element.is_selected() == is_selected
        except StaleElementReferenceException:
            return False

    return _predicate


def number_of_windows_to_be(num_windows: int) -> Callable[[WebDriver], bool]:
    """An expectation for the number of windows to be a certain value.

    Args:
        num_windows: The expected number of windows.

    Returns:
        True when the number of windows matches, False otherwise.

    Example:
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        is_number_of_windows = WebDriverWait(driver, 10).until(EC.number_of_windows_to_be(2))
    """

    def _predicate(driver: WebDriver):
        return len(driver.window_handles) == num_windows

    return _predicate


def new_window_is_opened(current_handles: set[str]) -> Callable[[WebDriver], bool]:
    """Check that a new window has been opened (window handles count increased).

    Args:
        current_handles: The current window handles.

    Returns:
        True when a new window is opened, False otherwise.

    Example:
        from selenium.webdriver.support.ui import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        is_new_window_opened = WebDriverWait(driver, 10).until(EC.new_window_is_opened(driver.window_handles))
    """

    def _predicate(driver: WebDriver):
        return len(driver.window_handles) > len(current_handles)

    return _predicate


def alert_is_present() -> Callable[[WebDriver], Alert | Literal[False]]:
    """Check that an alert is present and switch to it.

    Returns:
        The Alert once it is located, or False if no alert is present.

    Example:
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        alert = WebDriverWait(driver, 10).until(EC.alert_is_present())
    """

    def _predicate(driver: WebDriver):
        try:
            return driver.switch_to.alert
        except NoAlertPresentException:
            return False

    return _predicate


def element_attribute_to_include(locator: tuple[str, str], attribute_: str) -> Callable[[WebDriverOrWebElement], bool]:
    """Check if the given attribute is included in the specified element.

    Args:
        locator: Used to find the element.
        attribute_: The attribute to check.

    Returns:
        True when the attribute is included, False otherwise.

    Example:
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        is_attribute_in_element = WebDriverWait(driver, 10).until(
            EC.element_attribute_to_include((By.CLASS_NAME, "foo"), "bar")
        )
    """

    def _predicate(driver: WebDriverOrWebElement):
        try:
            element_attribute = driver.find_element(*locator).get_attribute(attribute_)
            return element_attribute is not None
        except StaleElementReferenceException:
            return False

    return _predicate


def any_of(*expected_conditions: Callable[[D], T]) -> Callable[[D], Literal[False] | T]:
    """An expectation that any of multiple expected conditions is true.

    Equivalent to a logical 'OR'. Returns results of the first matching
    condition, or False if none do.

    Args:
        expected_conditions: The list of expected conditions to check.

    Returns:
        The result of the first matching condition, or False if none do.

    Example:
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        element = WebDriverWait(driver, 10).until(
            EC.any_of(EC.presence_of_element_located((By.NAME, "q"),
            EC.visibility_of_element_located((By.NAME, "q")))
        )
    """

    def any_of_condition(driver: D):
        for expected_condition in expected_conditions:
            try:
                result = expected_condition(driver)
                if result:
                    return result
            except WebDriverException:
                pass
        return False

    return any_of_condition


def all_of(
    *expected_conditions: Callable[[D], T | Literal[False]],
) -> Callable[[D], list[T] | Literal[False]]:
    """An expectation that all of multiple expected conditions is true.

    Equivalent to a logical 'AND'. When any ExpectedCondition is not met,
    returns False. When all ExpectedConditions are met, returns a List with
    each ExpectedCondition's return value.

    Args:
        expected_conditions: The list of expected conditions to check.

    Returns:
        The results of all the matching conditions, or False if any do not.

    Example:
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        elements = WebDriverWait(driver, 10).until(
            EC.all_of(EC.presence_of_element_located((By.NAME, "q"),
            EC.visibility_of_element_located((By.NAME, "q")))
        )
    """

    def all_of_condition(driver: D):
        results: list[T] = []
        for expected_condition in expected_conditions:
            try:
                result = expected_condition(driver)
                if not result:
                    return False
                results.append(result)
            except WebDriverException:
                return False
        return results

    return all_of_condition


def none_of(*expected_conditions: Callable[[D], Any]) -> Callable[[D], bool]:
    """An expectation that none of 1 or multiple expected conditions is true.

    Equivalent to a logical 'NOT-OR'.

    Args:
        expected_conditions: The list of expected conditions to check.

    Returns:
        True if none of the conditions are true, False otherwise.

    Example:
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        element = WebDriverWait(driver, 10).until(
            EC.none_of(EC.presence_of_element_located((By.NAME, "q"),
            EC.visibility_of_element_located((By.NAME, "q")))
        )
    """

    def none_of_condition(driver: D):
        for expected_condition in expected_conditions:
            try:
                result = expected_condition(driver)
                if result:
                    return False
            except WebDriverException:
                pass
        return True

    return none_of_condition
