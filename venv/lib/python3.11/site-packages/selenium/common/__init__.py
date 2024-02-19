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

from .exceptions import ElementClickInterceptedException
from .exceptions import ElementNotInteractableException
from .exceptions import ElementNotSelectableException
from .exceptions import ElementNotVisibleException
from .exceptions import ImeActivationFailedException
from .exceptions import ImeNotAvailableException
from .exceptions import InsecureCertificateException
from .exceptions import InvalidArgumentException
from .exceptions import InvalidCookieDomainException
from .exceptions import InvalidCoordinatesException
from .exceptions import InvalidElementStateException
from .exceptions import InvalidSelectorException
from .exceptions import InvalidSessionIdException
from .exceptions import InvalidSwitchToTargetException
from .exceptions import JavascriptException
from .exceptions import MoveTargetOutOfBoundsException
from .exceptions import NoAlertPresentException
from .exceptions import NoSuchAttributeException
from .exceptions import NoSuchCookieException
from .exceptions import NoSuchDriverException
from .exceptions import NoSuchElementException
from .exceptions import NoSuchFrameException
from .exceptions import NoSuchShadowRootException
from .exceptions import NoSuchWindowException
from .exceptions import ScreenshotException
from .exceptions import SessionNotCreatedException
from .exceptions import StaleElementReferenceException
from .exceptions import TimeoutException
from .exceptions import UnableToSetCookieException
from .exceptions import UnexpectedAlertPresentException
from .exceptions import UnexpectedTagNameException
from .exceptions import UnknownMethodException
from .exceptions import WebDriverException

__all__ = [
    "WebDriverException",
    "InvalidSwitchToTargetException",
    "NoSuchFrameException",
    "NoSuchWindowException",
    "NoSuchElementException",
    "NoSuchAttributeException",
    "NoSuchDriverException",
    "NoSuchShadowRootException",
    "StaleElementReferenceException",
    "InvalidElementStateException",
    "UnexpectedAlertPresentException",
    "NoAlertPresentException",
    "ElementNotVisibleException",
    "ElementNotInteractableException",
    "ElementNotSelectableException",
    "InvalidCookieDomainException",
    "UnableToSetCookieException",
    "TimeoutException",
    "MoveTargetOutOfBoundsException",
    "UnexpectedTagNameException",
    "InvalidSelectorException",
    "ImeNotAvailableException",
    "ImeActivationFailedException",
    "InvalidArgumentException",
    "JavascriptException",
    "NoSuchCookieException",
    "ScreenshotException",
    "ElementClickInterceptedException",
    "InsecureCertificateException",
    "InvalidCoordinatesException",
    "InvalidSessionIdException",
    "SessionNotCreatedException",
    "UnknownMethodException",
]
