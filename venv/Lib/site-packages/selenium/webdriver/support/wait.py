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

import time
from collections.abc import Callable, Iterable
from typing import Generic, Literal, TypeVar

from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement

POLL_FREQUENCY: float = 0.5  # How long to sleep in between calls to the method
IGNORED_EXCEPTIONS: tuple[type[Exception]] = (NoSuchElementException,)  # default to be ignored.

D = TypeVar("D", bound=WebDriver | WebElement)
T = TypeVar("T")


class WebDriverWait(Generic[D]):
    def __init__(
        self,
        driver: D,
        timeout: float,
        poll_frequency: float = POLL_FREQUENCY,
        ignored_exceptions: Iterable[type[Exception]] | None = None,
    ):
        """Constructor, takes a WebDriver instance and timeout in seconds.

        Args:
            driver: Instance of WebDriver (Ie, Firefox, Chrome or Remote) or
                a WebElement.
            timeout: Number of seconds before timing out.
            poll_frequency: Sleep interval between calls. By default, it is
                0.5 second.
            ignored_exceptions: Iterable structure of exception classes ignored
                during calls. By default, it contains NoSuchElementException only.

        Example:
            >>> from selenium.webdriver.common.by import By
            >>> from selenium.webdriver.support.wait import WebDriverWait
            >>> from selenium.common.exceptions import ElementNotVisibleException
            >>>
            >>> # Wait until the element is no longer visible
            >>> is_disappeared = WebDriverWait(driver, 30, 1, (ElementNotVisibleException))
            ...     .until_not(lambda x: x.find_element(By.ID, "someId").is_displayed())
        """
        self._driver = driver
        self._timeout = float(timeout)
        self._poll = poll_frequency
        # avoid the divide by zero
        if self._poll == 0:
            self._poll = POLL_FREQUENCY
        exceptions: list = list(IGNORED_EXCEPTIONS)
        if ignored_exceptions:
            try:
                exceptions.extend(iter(ignored_exceptions))
            except TypeError:  # ignored_exceptions is not iterable
                exceptions.append(ignored_exceptions)
        self._ignored_exceptions = tuple(exceptions)

    def __repr__(self) -> str:
        return f'<{type(self).__module__}.{type(self).__name__} (session="{self._driver.session_id}")>'

    def until(self, method: Callable[[D], Literal[False] | T], message: str = "") -> T:
        """Wait until the method returns a value that is not False.

        Calls the method provided with the driver as an argument until the
        return value does not evaluate to ``False``.

        Args:
            method: A callable object that takes a WebDriver instance as an
                argument.
            message: Optional message for TimeoutException.

        Returns:
            The result of the last call to `method`.

        Raises:
            TimeoutException: If 'method' does not return a truthy value within
                the WebDriverWait object's timeout.

        Example:
            >>> from selenium.webdriver.common.by import By
            >>> from selenium.webdriver.support.ui import WebDriverWait
            >>> from selenium.webdriver.support import expected_conditions as EC
            >>>
            >>> # Wait until an element is visible on the page
            >>> wait = WebDriverWait(driver, 10)
            >>> element = wait.until(EC.visibility_of_element_located((By.ID, "exampleId")))
            >>> print(element.text)
        """
        screen = None
        stacktrace = None

        end_time = time.monotonic() + self._timeout
        while True:
            try:
                value = method(self._driver)
                if value:
                    return value
            except self._ignored_exceptions as exc:
                screen = getattr(exc, "screen", None)
                stacktrace = getattr(exc, "stacktrace", None)
            if time.monotonic() > end_time:
                break
            time.sleep(self._poll)
        raise TimeoutException(message, screen, stacktrace)

    def until_not(self, method: Callable[[D], T], message: str = "") -> T | Literal[True]:
        """Wait until the method returns a value that is False.

        Calls the method provided with the driver as an argument until the
        return value evaluates to ``False``.

        Args:
            method: A callable object that takes a WebDriver instance as an
                argument.
            message: Optional message for TimeoutException.

        Returns:
            The result of the last call to `method`.

        Raises:
            TimeoutException: If 'method' does not return False within the
                WebDriverWait object's timeout.

        Example:
            >>> from selenium.webdriver.common.by import By
            >>> from selenium.webdriver.support.ui import WebDriverWait
            >>> from selenium.webdriver.support import expected_conditions as EC
            >>>
            >>> # Wait until an element is no longer visible on the page
            >>> wait = WebDriverWait(driver, 10)
            >>> is_disappeared = wait.until_not(EC.visibility_of_element_located((By.ID, "exampleId")))
        """
        end_time = time.monotonic() + self._timeout
        while True:
            try:
                value = method(self._driver)
                if not value:
                    return value
            except self._ignored_exceptions:
                return True
            if time.monotonic() > end_time:
                break
            time.sleep(self._poll)
        raise TimeoutException(message)
