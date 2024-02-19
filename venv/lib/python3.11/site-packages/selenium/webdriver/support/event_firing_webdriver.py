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
import typing

from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement

from .abstract_event_listener import AbstractEventListener


def _wrap_elements(result, ef_driver):
    # handle the case if another wrapper wraps EventFiringWebElement
    if isinstance(result, EventFiringWebElement):
        return result
    if isinstance(result, WebElement):
        return EventFiringWebElement(result, ef_driver)
    if isinstance(result, list):
        return [_wrap_elements(item, ef_driver) for item in result]
    return result


class EventFiringWebDriver:
    """A wrapper around an arbitrary WebDriver instance which supports firing
    events."""

    def __init__(self, driver: WebDriver, event_listener: AbstractEventListener) -> None:
        """Creates a new instance of the EventFiringWebDriver.

        :Args:
         - driver : A WebDriver instance
         - event_listener : Instance of a class that subclasses AbstractEventListener and implements it fully or partially

        Example:

        ::

            from selenium.webdriver import Firefox
            from selenium.webdriver.support.events import EventFiringWebDriver, AbstractEventListener

            class MyListener(AbstractEventListener):
                def before_navigate_to(self, url, driver):
                    print("Before navigate to %s" % url)
                def after_navigate_to(self, url, driver):
                    print("After navigate to %s" % url)

            driver = Firefox()
            ef_driver = EventFiringWebDriver(driver, MyListener())
            ef_driver.get("http://www.google.co.in/")
        """
        if not isinstance(driver, WebDriver):
            raise WebDriverException("A WebDriver instance must be supplied")
        if not isinstance(event_listener, AbstractEventListener):
            raise WebDriverException("Event listener must be a subclass of AbstractEventListener")
        self._driver = driver
        self._driver._wrap_value = self._wrap_value
        self._listener = event_listener

    @property
    def wrapped_driver(self) -> WebDriver:
        """Returns the WebDriver instance wrapped by this
        EventsFiringWebDriver."""
        return self._driver

    def get(self, url: str) -> None:
        self._dispatch("navigate_to", (url, self._driver), "get", (url,))

    def back(self) -> None:
        self._dispatch("navigate_back", (self._driver,), "back", ())

    def forward(self) -> None:
        self._dispatch("navigate_forward", (self._driver,), "forward", ())

    def execute_script(self, script, *args):
        unwrapped_args = (script,) + self._unwrap_element_args(args)
        return self._dispatch("execute_script", (script, self._driver), "execute_script", unwrapped_args)

    def execute_async_script(self, script, *args):
        unwrapped_args = (script,) + self._unwrap_element_args(args)
        return self._dispatch("execute_script", (script, self._driver), "execute_async_script", unwrapped_args)

    def close(self) -> None:
        self._dispatch("close", (self._driver,), "close", ())

    def quit(self) -> None:
        self._dispatch("quit", (self._driver,), "quit", ())

    def find_element(self, by=By.ID, value=None) -> WebElement:
        return self._dispatch("find", (by, value, self._driver), "find_element", (by, value))

    def find_elements(self, by=By.ID, value=None) -> typing.List[WebElement]:
        return self._dispatch("find", (by, value, self._driver), "find_elements", (by, value))

    def _dispatch(
        self, l_call: str, l_args: typing.Tuple[typing.Any, ...], d_call: str, d_args: typing.Tuple[typing.Any, ...]
    ):
        getattr(self._listener, f"before_{l_call}")(*l_args)
        try:
            result = getattr(self._driver, d_call)(*d_args)
        except Exception as exc:
            self._listener.on_exception(exc, self._driver)
            raise
        getattr(self._listener, f"after_{l_call}")(*l_args)
        return _wrap_elements(result, self)

    def _unwrap_element_args(self, args):
        if isinstance(args, EventFiringWebElement):
            return args.wrapped_element
        if isinstance(args, tuple):
            return tuple(self._unwrap_element_args(item) for item in args)
        if isinstance(args, list):
            return [self._unwrap_element_args(item) for item in args]
        return args

    def _wrap_value(self, value):
        if isinstance(value, EventFiringWebElement):
            return WebDriver._wrap_value(self._driver, value.wrapped_element)
        return WebDriver._wrap_value(self._driver, value)

    def __setattr__(self, item, value):
        if item.startswith("_") or not hasattr(self._driver, item):
            object.__setattr__(self, item, value)
        else:
            try:
                object.__setattr__(self._driver, item, value)
            except Exception as exc:
                self._listener.on_exception(exc, self._driver)
                raise

    def __getattr__(self, name):
        def _wrap(*args, **kwargs):
            try:
                result = attrib(*args, **kwargs)
                return _wrap_elements(result, self)
            except Exception as exc:
                self._listener.on_exception(exc, self._driver)
                raise

        try:
            attrib = getattr(self._driver, name)
            return _wrap if callable(attrib) else attrib
        except Exception as exc:
            self._listener.on_exception(exc, self._driver)
            raise


class EventFiringWebElement:
    """A wrapper around WebElement instance which supports firing events."""

    def __init__(self, webelement: WebElement, ef_driver: EventFiringWebDriver) -> None:
        """Creates a new instance of the EventFiringWebElement."""
        self._webelement = webelement
        self._ef_driver = ef_driver
        self._driver = ef_driver.wrapped_driver
        self._listener = ef_driver._listener

    @property
    def wrapped_element(self) -> WebElement:
        """Returns the WebElement wrapped by this EventFiringWebElement
        instance."""
        return self._webelement

    def click(self) -> None:
        self._dispatch("click", (self._webelement, self._driver), "click", ())

    def clear(self) -> None:
        self._dispatch("change_value_of", (self._webelement, self._driver), "clear", ())

    def send_keys(self, *value) -> None:
        self._dispatch("change_value_of", (self._webelement, self._driver), "send_keys", value)

    def find_element(self, by=By.ID, value=None) -> WebElement:
        return self._dispatch("find", (by, value, self._driver), "find_element", (by, value))

    def find_elements(self, by=By.ID, value=None) -> typing.List[WebElement]:
        return self._dispatch("find", (by, value, self._driver), "find_elements", (by, value))

    def _dispatch(self, l_call, l_args, d_call, d_args):
        getattr(self._listener, f"before_{l_call}")(*l_args)
        try:
            result = getattr(self._webelement, d_call)(*d_args)
        except Exception as exc:
            self._listener.on_exception(exc, self._driver)
            raise
        getattr(self._listener, f"after_{l_call}")(*l_args)
        return _wrap_elements(result, self._ef_driver)

    def __setattr__(self, item, value):
        if item.startswith("_") or not hasattr(self._webelement, item):
            object.__setattr__(self, item, value)
        else:
            try:
                object.__setattr__(self._webelement, item, value)
            except Exception as exc:
                self._listener.on_exception(exc, self._driver)
                raise

    def __getattr__(self, name):
        def _wrap(*args, **kwargs):
            try:
                result = attrib(*args, **kwargs)
                return _wrap_elements(result, self._ef_driver)
            except Exception as exc:
                self._listener.on_exception(exc, self._driver)
                raise

        try:
            attrib = getattr(self._webelement, name)
            return _wrap if callable(attrib) else attrib
        except Exception as exc:
            self._listener.on_exception(exc, self._driver)
            raise


# Register a virtual subclass.
WebElement.register(EventFiringWebElement)
