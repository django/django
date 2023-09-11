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
from __future__ import annotations

import os
import pkgutil
import warnings
import zipfile
from abc import ABCMeta
from base64 import b64decode
from base64 import encodebytes
from hashlib import md5 as md5_hash
from io import BytesIO

from selenium.common.exceptions import JavascriptException
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.utils import keys_to_typing

from .command import Command
from .shadowroot import ShadowRoot

# TODO: When moving to supporting python 3.9 as the minimum version we can
# use built in importlib_resources.files.
getAttribute_js = None
isDisplayed_js = None


def _load_js():
    global getAttribute_js
    global isDisplayed_js
    _pkg = ".".join(__name__.split(".")[:-1])
    getAttribute_js = pkgutil.get_data(_pkg, "getAttribute.js").decode("utf8")
    isDisplayed_js = pkgutil.get_data(_pkg, "isDisplayed.js").decode("utf8")


class BaseWebElement(metaclass=ABCMeta):
    """Abstract Base Class for WebElement.

    ABC's will allow custom types to be registered as a WebElement to
    pass type checks.
    """

    pass


class WebElement(BaseWebElement):
    """Represents a DOM element.

    Generally, all interesting operations that interact with a document will be
    performed through this interface.

    All method calls will do a freshness check to ensure that the element
    reference is still valid.  This essentially determines whether the
    element is still attached to the DOM.  If this test fails, then an
    ``StaleElementReferenceException`` is thrown, and all future calls to this
    instance will fail.
    """

    def __init__(self, parent, id_) -> None:
        self._parent = parent
        self._id = id_

    def __repr__(self):
        return f'<{type(self).__module__}.{type(self).__name__} (session="{self._parent.session_id}", element="{self._id}")>'

    @property
    def tag_name(self) -> str:
        """This element's ``tagName`` property."""
        return self._execute(Command.GET_ELEMENT_TAG_NAME)["value"]

    @property
    def text(self) -> str:
        """The text of the element."""
        return self._execute(Command.GET_ELEMENT_TEXT)["value"]

    def click(self) -> None:
        """Clicks the element."""
        self._execute(Command.CLICK_ELEMENT)

    def submit(self):
        """Submits a form."""
        script = (
            "/* submitForm */var form = arguments[0];\n"
            'while (form.nodeName != "FORM" && form.parentNode) {\n'
            "  form = form.parentNode;\n"
            "}\n"
            "if (!form) { throw Error('Unable to find containing form element'); }\n"
            "if (!form.ownerDocument) { throw Error('Unable to find owning document'); }\n"
            "var e = form.ownerDocument.createEvent('Event');\n"
            "e.initEvent('submit', true, true);\n"
            "if (form.dispatchEvent(e)) { HTMLFormElement.prototype.submit.call(form) }\n"
        )

        try:
            self._parent.execute_script(script, self)
        except JavascriptException as exc:
            raise WebDriverException("To submit an element, it must be nested inside a form element") from exc

    def clear(self) -> None:
        """Clears the text if it's a text entry element."""
        self._execute(Command.CLEAR_ELEMENT)

    def get_property(self, name) -> str | bool | WebElement | dict:
        """Gets the given property of the element.

        :Args:
            - name - Name of the property to retrieve.

        :Usage:
            ::

                text_length = target_element.get_property("text_length")
        """
        try:
            return self._execute(Command.GET_ELEMENT_PROPERTY, {"name": name})["value"]
        except WebDriverException:
            # if we hit an end point that doesn't understand getElementProperty lets fake it
            return self.parent.execute_script("return arguments[0][arguments[1]]", self, name)

    def get_dom_attribute(self, name) -> str:
        """Gets the given attribute of the element. Unlike
        :func:`~selenium.webdriver.remote.BaseWebElement.get_attribute`, this
        method only returns attributes declared in the element's HTML markup.

        :Args:
            - name - Name of the attribute to retrieve.

        :Usage:
            ::

                text_length = target_element.get_dom_attribute("class")
        """
        return self._execute(Command.GET_ELEMENT_ATTRIBUTE, {"name": name})["value"]

    def get_attribute(self, name) -> str | None:
        """Gets the given attribute or property of the element.

        This method will first try to return the value of a property with the
        given name. If a property with that name doesn't exist, it returns the
        value of the attribute with the same name. If there's no attribute with
        that name, ``None`` is returned.

        Values which are considered truthy, that is equals "true" or "false",
        are returned as booleans.  All other non-``None`` values are returned
        as strings.  For attributes or properties which do not exist, ``None``
        is returned.

        To obtain the exact value of the attribute or property,
        use :func:`~selenium.webdriver.remote.BaseWebElement.get_dom_attribute` or
        :func:`~selenium.webdriver.remote.BaseWebElement.get_property` methods respectively.

        :Args:
            - name - Name of the attribute/property to retrieve.

        Example::

            # Check if the "active" CSS class is applied to an element.
            is_active = "active" in target_element.get_attribute("class")
        """
        if getAttribute_js is None:
            _load_js()
        attribute_value = self.parent.execute_script(
            f"/* getAttribute */return ({getAttribute_js}).apply(null, arguments);", self, name
        )
        return attribute_value

    def is_selected(self) -> bool:
        """Returns whether the element is selected.

        Can be used to check if a checkbox or radio button is selected.
        """
        return self._execute(Command.IS_ELEMENT_SELECTED)["value"]

    def is_enabled(self) -> bool:
        """Returns whether the element is enabled."""
        return self._execute(Command.IS_ELEMENT_ENABLED)["value"]

    def send_keys(self, *value) -> None:
        """Simulates typing into the element.

        :Args:
            - value - A string for typing, or setting form fields.  For setting
              file inputs, this could be a local file path.

        Use this to send simple key events or to fill out form fields::

            form_textfield = driver.find_element(By.NAME, 'username')
            form_textfield.send_keys("admin")

        This can also be used to set file inputs.

        ::

            file_input = driver.find_element(By.NAME, 'profilePic')
            file_input.send_keys("path/to/profilepic.gif")
            # Generally it's better to wrap the file path in one of the methods
            # in os.path to return the actual path to support cross OS testing.
            # file_input.send_keys(os.path.abspath("path/to/profilepic.gif"))
        """
        # transfer file to another machine only if remote driver is used
        # the same behaviour as for java binding
        if self.parent._is_remote:
            local_files = list(
                map(
                    lambda keys_to_send: self.parent.file_detector.is_local_file(str(keys_to_send)),
                    "".join(map(str, value)).split("\n"),
                )
            )
            if None not in local_files:
                remote_files = []
                for file in local_files:
                    remote_files.append(self._upload(file))
                value = "\n".join(remote_files)

        self._execute(
            Command.SEND_KEYS_TO_ELEMENT, {"text": "".join(keys_to_typing(value)), "value": keys_to_typing(value)}
        )

    @property
    def shadow_root(self) -> ShadowRoot:
        """Returns a shadow root of the element if there is one or an error.
        Only works from Chromium 96, Firefox 96, and Safari 16.4 onwards.

        :Returns:
          - ShadowRoot object or
          - NoSuchShadowRoot - if no shadow root was attached to element
        """
        return self._execute(Command.GET_SHADOW_ROOT)["value"]

    # RenderedWebElement Items
    def is_displayed(self) -> bool:
        """Whether the element is visible to a user."""
        # Only go into this conditional for browsers that don't use the atom themselves
        if isDisplayed_js is None:
            _load_js()
        return self.parent.execute_script(f"/* isDisplayed */return ({isDisplayed_js}).apply(null, arguments);", self)

    @property
    def location_once_scrolled_into_view(self) -> dict:
        """THIS PROPERTY MAY CHANGE WITHOUT WARNING. Use this to discover where
        on the screen an element is so that we can click it. This method should
        cause the element to be scrolled into view.

        Returns the top lefthand corner location on the screen, or zero
        coordinates if the element is not visible.
        """
        old_loc = self._execute(
            Command.W3C_EXECUTE_SCRIPT,
            {
                "script": "arguments[0].scrollIntoView(true); return arguments[0].getBoundingClientRect()",
                "args": [self],
            },
        )["value"]
        return {"x": round(old_loc["x"]), "y": round(old_loc["y"])}

    @property
    def size(self) -> dict:
        """The size of the element."""
        size = self._execute(Command.GET_ELEMENT_RECT)["value"]
        new_size = {"height": size["height"], "width": size["width"]}
        return new_size

    def value_of_css_property(self, property_name) -> str:
        """The value of a CSS property."""
        return self._execute(Command.GET_ELEMENT_VALUE_OF_CSS_PROPERTY, {"propertyName": property_name})["value"]

    @property
    def location(self) -> dict:
        """The location of the element in the renderable canvas."""
        old_loc = self._execute(Command.GET_ELEMENT_RECT)["value"]
        new_loc = {"x": round(old_loc["x"]), "y": round(old_loc["y"])}
        return new_loc

    @property
    def rect(self) -> dict:
        """A dictionary with the size and location of the element."""
        return self._execute(Command.GET_ELEMENT_RECT)["value"]

    @property
    def aria_role(self) -> str:
        """Returns the ARIA role of the current web element."""
        return self._execute(Command.GET_ELEMENT_ARIA_ROLE)["value"]

    @property
    def accessible_name(self) -> str:
        """Returns the ARIA Level of the current webelement."""
        return self._execute(Command.GET_ELEMENT_ARIA_LABEL)["value"]

    @property
    def screenshot_as_base64(self) -> str:
        """Gets the screenshot of the current element as a base64 encoded
        string.

        :Usage:
            ::

                img_b64 = element.screenshot_as_base64
        """
        return self._execute(Command.ELEMENT_SCREENSHOT)["value"]

    @property
    def screenshot_as_png(self) -> bytes:
        """Gets the screenshot of the current element as a binary data.

        :Usage:
            ::

                element_png = element.screenshot_as_png
        """
        return b64decode(self.screenshot_as_base64.encode("ascii"))

    def screenshot(self, filename) -> bool:
        """Saves a screenshot of the current element to a PNG image file.
        Returns False if there is any IOError, else returns True. Use full
        paths in your filename.

        :Args:
         - filename: The full path you wish to save your screenshot to. This
           should end with a `.png` extension.

        :Usage:
            ::

                element.screenshot('/Screenshots/foo.png')
        """
        if not filename.lower().endswith(".png"):
            warnings.warn(
                "name used for saved screenshot does not match file type. It should end with a `.png` extension",
                UserWarning,
            )
        png = self.screenshot_as_png
        try:
            with open(filename, "wb") as f:
                f.write(png)
        except OSError:
            return False
        finally:
            del png
        return True

    @property
    def parent(self):
        """Internal reference to the WebDriver instance this element was found
        from."""
        return self._parent

    @property
    def id(self) -> str:
        """Internal ID used by selenium.

        This is mainly for internal use. Simple use cases such as checking if 2
        webelements refer to the same element, can be done using ``==``::

            if element1 == element2:
                print("These 2 are equal")
        """
        return self._id

    def __eq__(self, element):
        return hasattr(element, "id") and self._id == element.id

    def __ne__(self, element):
        return not self.__eq__(element)

    # Private Methods
    def _execute(self, command, params=None):
        """Executes a command against the underlying HTML element.

        Args:
          command: The name of the command to _execute as a string.
          params: A dictionary of named parameters to send with the command.

        Returns:
          The command's JSON response loaded into a dictionary object.
        """
        if not params:
            params = {}
        params["id"] = self._id
        return self._parent.execute(command, params)

    def find_element(self, by=By.ID, value=None) -> WebElement:
        """Find an element given a By strategy and locator.

        :Usage:
            ::

                element = element.find_element(By.ID, 'foo')

        :rtype: WebElement
        """
        if by == By.ID:
            by = By.CSS_SELECTOR
            value = f'[id="{value}"]'
        elif by == By.CLASS_NAME:
            by = By.CSS_SELECTOR
            value = f".{value}"
        elif by == By.NAME:
            by = By.CSS_SELECTOR
            value = f'[name="{value}"]'

        return self._execute(Command.FIND_CHILD_ELEMENT, {"using": by, "value": value})["value"]

    def find_elements(self, by=By.ID, value=None) -> list[WebElement]:
        """Find elements given a By strategy and locator.

        :Usage:
            ::

                element = element.find_elements(By.CLASS_NAME, 'foo')

        :rtype: list of WebElement
        """
        if by == By.ID:
            by = By.CSS_SELECTOR
            value = f'[id="{value}"]'
        elif by == By.CLASS_NAME:
            by = By.CSS_SELECTOR
            value = f".{value}"
        elif by == By.NAME:
            by = By.CSS_SELECTOR
            value = f'[name="{value}"]'

        return self._execute(Command.FIND_CHILD_ELEMENTS, {"using": by, "value": value})["value"]

    def __hash__(self) -> int:
        return int(md5_hash(self._id.encode("utf-8")).hexdigest(), 16)

    def _upload(self, filename):
        fp = BytesIO()
        zipped = zipfile.ZipFile(fp, "w", zipfile.ZIP_DEFLATED)
        zipped.write(filename, os.path.split(filename)[1])
        zipped.close()
        content = encodebytes(fp.getvalue())
        if not isinstance(content, str):
            content = content.decode("utf-8")
        try:
            return self._execute(Command.UPLOAD_FILE, {"file": content})["value"]
        except WebDriverException as e:
            if "Unrecognized command: POST" in str(e):
                return filename
            if "Command not found: POST " in str(e):
                return filename
            if '{"status":405,"value":["GET","HEAD","DELETE"]}' in str(e):
                return filename
            raise
