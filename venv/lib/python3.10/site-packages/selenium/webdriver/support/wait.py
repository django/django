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
import typing

from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import TimeoutException
from selenium.types import WaitExcTypes

POLL_FREQUENCY: float = 0.5  # How long to sleep in between calls to the method
IGNORED_EXCEPTIONS: typing.Tuple[typing.Type[Exception]] = (NoSuchElementException,)  # default to be ignored.


class WebDriverWait:
    def __init__(
        self,
        driver,
        timeout: float,
        poll_frequency: float = POLL_FREQUENCY,
        ignored_exceptions: typing.Optional[WaitExcTypes] = None,
    ):
        """Constructor, takes a WebDriver instance and timeout in seconds.

        :Args:
         - driver - Instance of WebDriver (Ie, Firefox, Chrome or Remote) or a WebElement
         - timeout - Number of seconds before timing out
         - poll_frequency - sleep interval between calls
           By default, it is 0.5 second.
         - ignored_exceptions - iterable structure of exception classes ignored during calls.
           By default, it contains NoSuchElementException only.

        Example::

         from selenium.webdriver.support.wait import WebDriverWait \n
         element = WebDriverWait(driver, 10).until(lambda x: x.find_element(By.ID, "someId")) \n
         is_disappeared = WebDriverWait(driver, 30, 1, (ElementNotVisibleException)).\\ \n
                     until_not(lambda x: x.find_element(By.ID, "someId").is_displayed())
        """
        self._driver = driver
        self._timeout = float(timeout)
        self._poll = poll_frequency
        # avoid the divide by zero
        if self._poll == 0:
            self._poll = POLL_FREQUENCY
        exceptions = list(IGNORED_EXCEPTIONS)
        if ignored_exceptions:
            try:
                exceptions.extend(iter(ignored_exceptions))
            except TypeError:  # ignored_exceptions is not iterable
                exceptions.append(ignored_exceptions)
        self._ignored_exceptions = tuple(exceptions)

    def __repr__(self):
        return f'<{type(self).__module__}.{type(self).__name__} (session="{self._driver.session_id}")>'

    def until(self, method, message: str = ""):
        """Calls the method provided with the driver as an argument until the \
        return value does not evaluate to ``False``.

        :param method: callable(WebDriver)
        :param message: optional message for :exc:`TimeoutException`
        :returns: the result of the last call to `method`
        :raises: :exc:`selenium.common.exceptions.TimeoutException` if timeout occurs
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
            time.sleep(self._poll)
            if time.monotonic() > end_time:
                break
        raise TimeoutException(message, screen, stacktrace)

    def until_not(self, method, message: str = ""):
        """Calls the method provided with the driver as an argument until the \
        return value evaluates to ``False``.

        :param method: callable(WebDriver)
        :param message: optional message for :exc:`TimeoutException`
        :returns: the result of the last call to `method`, or
                  ``True`` if `method` has raised one of the ignored exceptions
        :raises: :exc:`selenium.common.exceptions.TimeoutException` if timeout occurs
        """
        end_time = time.monotonic() + self._timeout
        while True:
            try:
                value = method(self._driver)
                if not value:
                    return value
            except self._ignored_exceptions:
                return True
            time.sleep(self._poll)
            if time.monotonic() > end_time:
                break
        raise TimeoutException(message)
