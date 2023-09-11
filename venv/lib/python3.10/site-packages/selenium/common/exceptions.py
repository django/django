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
"""Exceptions that may happen in all the webdriver code."""

from typing import Optional
from typing import Sequence

SUPPORT_MSG = "For documentation on this error, please visit:"
ERROR_URL = "https://www.selenium.dev/documentation/webdriver/troubleshooting/errors"


class WebDriverException(Exception):
    """Base webdriver exception."""

    def __init__(
        self, msg: Optional[str] = None, screen: Optional[str] = None, stacktrace: Optional[Sequence[str]] = None
    ) -> None:
        super().__init__()
        self.msg = msg
        self.screen = screen
        self.stacktrace = stacktrace

    def __str__(self) -> str:
        exception_msg = f"Message: {self.msg}\n"
        if self.screen:
            exception_msg += "Screenshot: available via screen\n"
        if self.stacktrace:
            stacktrace = "\n".join(self.stacktrace)
            exception_msg += f"Stacktrace:\n{stacktrace}"
        return exception_msg


class InvalidSwitchToTargetException(WebDriverException):
    """Thrown when frame or window target to be switched doesn't exist."""


class NoSuchFrameException(InvalidSwitchToTargetException):
    """Thrown when frame target to be switched doesn't exist."""


class NoSuchWindowException(InvalidSwitchToTargetException):
    """Thrown when window target to be switched doesn't exist.

    To find the current set of active window handles, you can get a list
    of the active window handles in the following way::

        print driver.window_handles
    """


class NoSuchElementException(WebDriverException):
    """Thrown when element could not be found.

    If you encounter this exception, you may want to check the following:
        * Check your selector used in your find_by...
        * Element may not yet be on the screen at the time of the find operation,
          (webpage is still loading) see selenium.webdriver.support.wait.WebDriverWait()
          for how to write a wait wrapper to wait for an element to appear.
    """

    def __init__(
        self, msg: Optional[str] = None, screen: Optional[str] = None, stacktrace: Optional[Sequence[str]] = None
    ) -> None:
        with_support = f"{msg}; {SUPPORT_MSG} {ERROR_URL}#no-such-element-exception"

        super().__init__(with_support, screen, stacktrace)


class NoSuchAttributeException(WebDriverException):
    """Thrown when the attribute of element could not be found.

    You may want to check if the attribute exists in the particular
    browser you are testing against.  Some browsers may have different
    property names for the same property.  (IE8's .innerText vs. Firefox
    .textContent)
    """


class NoSuchShadowRootException(WebDriverException):
    """Thrown when trying to access the shadow root of an element when it does
    not have a shadow root attached."""


class StaleElementReferenceException(WebDriverException):
    """Thrown when a reference to an element is now "stale".

    Stale means the element no longer appears on the DOM of the page.


    Possible causes of StaleElementReferenceException include, but not limited to:
        * You are no longer on the same page, or the page may have refreshed since the element
          was located.
        * The element may have been removed and re-added to the screen, since it was located.
          Such as an element being relocated.
          This can happen typically with a javascript framework when values are updated and the
          node is rebuilt.
        * Element may have been inside an iframe or another context which was refreshed.
    """

    def __init__(
        self, msg: Optional[str] = None, screen: Optional[str] = None, stacktrace: Optional[Sequence[str]] = None
    ) -> None:
        with_support = f"{msg}; {SUPPORT_MSG} {ERROR_URL}#stale-element-reference-exception"

        super().__init__(with_support, screen, stacktrace)


class InvalidElementStateException(WebDriverException):
    """Thrown when a command could not be completed because the element is in
    an invalid state.

    This can be caused by attempting to clear an element that isn't both
    editable and resettable.
    """


class UnexpectedAlertPresentException(WebDriverException):
    """Thrown when an unexpected alert has appeared.

    Usually raised when  an unexpected modal is blocking the webdriver
    from executing commands.
    """

    def __init__(
        self,
        msg: Optional[str] = None,
        screen: Optional[str] = None,
        stacktrace: Optional[Sequence[str]] = None,
        alert_text: Optional[str] = None,
    ) -> None:
        super().__init__(msg, screen, stacktrace)
        self.alert_text = alert_text

    def __str__(self) -> str:
        return f"Alert Text: {self.alert_text}\n{super().__str__()}"


class NoAlertPresentException(WebDriverException):
    """Thrown when switching to no presented alert.

    This can be caused by calling an operation on the Alert() class when
    an alert is not yet on the screen.
    """


class ElementNotVisibleException(InvalidElementStateException):
    """Thrown when an element is present on the DOM, but it is not visible, and
    so is not able to be interacted with.

    Most commonly encountered when trying to click or read text of an
    element that is hidden from view.
    """


class ElementNotInteractableException(InvalidElementStateException):
    """Thrown when an element is present in the DOM but interactions with that
    element will hit another element due to paint order."""


class ElementNotSelectableException(InvalidElementStateException):
    """Thrown when trying to select an unselectable element.

    For example, selecting a 'script' element.
    """


class InvalidCookieDomainException(WebDriverException):
    """Thrown when attempting to add a cookie under a different domain than the
    current URL."""


class UnableToSetCookieException(WebDriverException):
    """Thrown when a driver fails to set a cookie."""


class TimeoutException(WebDriverException):
    """Thrown when a command does not complete in enough time."""


class MoveTargetOutOfBoundsException(WebDriverException):
    """Thrown when the target provided to the `ActionsChains` move() method is
    invalid, i.e. out of document."""


class UnexpectedTagNameException(WebDriverException):
    """Thrown when a support class did not get an expected web element."""


class InvalidSelectorException(WebDriverException):
    """Thrown when the selector which is used to find an element does not
    return a WebElement.

    Currently this only happens when the selector is an xpath expression
    and it is either syntactically invalid (i.e. it is not a xpath
    expression) or the expression does not select WebElements (e.g.
    "count(//input)").
    """

    def __init__(
        self, msg: Optional[str] = None, screen: Optional[str] = None, stacktrace: Optional[Sequence[str]] = None
    ) -> None:
        with_support = f"{msg}; {SUPPORT_MSG} {ERROR_URL}#invalid-selector-exception"

        super().__init__(with_support, screen, stacktrace)


class ImeNotAvailableException(WebDriverException):
    """Thrown when IME support is not available.

    This exception is thrown for every IME-related method call if IME
    support is not available on the machine.
    """


class ImeActivationFailedException(WebDriverException):
    """Thrown when activating an IME engine has failed."""


class InvalidArgumentException(WebDriverException):
    """The arguments passed to a command are either invalid or malformed."""


class JavascriptException(WebDriverException):
    """An error occurred while executing JavaScript supplied by the user."""


class NoSuchCookieException(WebDriverException):
    """No cookie matching the given path name was found amongst the associated
    cookies of the current browsing context's active document."""


class ScreenshotException(WebDriverException):
    """A screen capture was made impossible."""


class ElementClickInterceptedException(WebDriverException):
    """The Element Click command could not be completed because the element
    receiving the events is obscuring the element that was requested to be
    clicked."""


class InsecureCertificateException(WebDriverException):
    """Navigation caused the user agent to hit a certificate warning, which is
    usually the result of an expired or invalid TLS certificate."""


class InvalidCoordinatesException(WebDriverException):
    """The coordinates provided to an interaction's operation are invalid."""


class InvalidSessionIdException(WebDriverException):
    """Occurs if the given session id is not in the list of active sessions,
    meaning the session either does not exist or that it's not active."""


class SessionNotCreatedException(WebDriverException):
    """A new session could not be created."""


class UnknownMethodException(WebDriverException):
    """The requested command matched a known URL but did not match any methods
    for that URL."""


class NoSuchDriverException(WebDriverException):
    """Raised when driver is not specified and cannot be located."""

    def __init__(
        self, msg: Optional[str] = None, screen: Optional[str] = None, stacktrace: Optional[Sequence[str]] = None
    ) -> None:
        with_support = f"{msg}; {SUPPORT_MSG} {ERROR_URL}/driver_location"

        super().__init__(with_support, screen, stacktrace)
