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
from base64 import b64decode, encodebytes
from hashlib import md5 as md5_hash
from io import BytesIO

from selenium.common.exceptions import JavascriptException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.utils import keys_to_typing
from selenium.webdriver.remote.command import Command
from selenium.webdriver.remote.shadowroot import ShadowRoot

# TODO: Use built in importlib_resources.files.
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
    `StaleElementReferenceException` is thrown, and all future calls to this
    instance will fail.
    """

    def __init__(self, parent, id_) -> None:
        self._parent = parent
        self._id = id_

    def __repr__(self):
        return f'<{type(self).__module__}.{type(self).__name__} (session="{self.session_id}", element="{self._id}")>'

    @property
    def session_id(self) -> str:
        return self._parent.session_id

    @property
    def tag_name(self) -> str:
        """This element's `tagName` property.

        Returns:
            The tag name of the element.

        Example:
            element = driver.find_element(By.ID, "foo")
        """
        return self._execute(Command.GET_ELEMENT_TAG_NAME)["value"]

    @property
    def text(self) -> str:
        """The text of the element.

        Returns:
            The text of the element.

        Example:
            element = driver.find_element(By.ID, "foo")
            print(element.text)
        """
        return self._execute(Command.GET_ELEMENT_TEXT)["value"]

    def click(self) -> None:
        """Clicks the element.

        Example:
            element = driver.find_element(By.ID, "foo")
            element.click()
        """
        self._execute(Command.CLICK_ELEMENT)

    def submit(self) -> None:
        """Submits a form.

        Example:
            form = driver.find_element(By.NAME, "login")
            form.submit()
        """
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
        """Clears the text if it's a text entry element.

        Example:
            text_field = driver.find_element(By.NAME, "username")
            text_field.clear()
        """
        self._execute(Command.CLEAR_ELEMENT)

    def get_property(self, name) -> str | bool | WebElement | dict:
        """Gets the given property of the element.

        Args:
            name: Name of the property to retrieve.

        Returns:
            The value of the property.

        Example:
            text_length = target_element.get_property("text_length")
        """
        try:
            return self._execute(Command.GET_ELEMENT_PROPERTY, {"name": name})["value"]
        except WebDriverException:
            # if we hit an end point that doesn't understand getElementProperty lets fake it
            return self.parent.execute_script("return arguments[0][arguments[1]]", self, name)

    def get_dom_attribute(self, name) -> str:
        """Get the HTML attribute value (not reflected properties) of the element.

        Returns only attributes declared in the element's HTML markup, unlike
        `selenium.webdriver.remote.BaseWebElement.get_attribute`.

        Args:
            name: Name of the attribute to retrieve.

        Returns:
            The value of the attribute.

        Example:
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

        Args:
            name: Name of the attribute/property to retrieve.

        Returns:
            The value of the attribute/property.

        Example:
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

        This method is generally used on checkboxes, options in a select
        and radio buttons.

        Example:
            is_selected = element.is_selected()
        """
        return self._execute(Command.IS_ELEMENT_SELECTED)["value"]

    def is_enabled(self) -> bool:
        """Returns whether the element is enabled.

        Example:
            is_enabled = element.is_enabled()
        """
        return self._execute(Command.IS_ELEMENT_ENABLED)["value"]

    def send_keys(self, *value: str) -> None:
        """Simulates typing into the element.

        Use this to send simple key events or to fill out form fields.
        This can also be used to set file inputs.

        Args:
            value: A string for typing, or setting form fields. For setting
                file inputs, this could be a local file path.

        Examples:
            To send a simple key event::

            form_textfield = driver.find_element(By.NAME, "username")
            form_textfield.send_keys("admin")

            or to set a file input field::

            file_input = driver.find_element(By.NAME, "profilePic")
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
                value = tuple("\n".join(remote_files))

        self._execute(
            Command.SEND_KEYS_TO_ELEMENT, {"text": "".join(keys_to_typing(value)), "value": keys_to_typing(value)}
        )

    @property
    def shadow_root(self) -> ShadowRoot:
        """Get the shadow root attached to this element if present (Chromium, Firefox, Safari).

        Returns:
            The ShadowRoot object.

        Raises:
            NoSuchShadowRoot: If no shadow root was attached to element.

        Example:
            try:
                shadow_root = element.shadow_root
            except NoSuchShadowRoot:
                print("No shadow root attached to element")
        """
        return self._execute(Command.GET_SHADOW_ROOT)["value"]

    # RenderedWebElement Items
    def is_displayed(self) -> bool:
        """Whether the element is visible to a user.

        Example:
            is_displayed = element.is_displayed()
        """
        # Only go into this conditional for browsers that don't use the atom themselves
        if isDisplayed_js is None:
            _load_js()
        return self.parent.execute_script(f"/* isDisplayed */return ({isDisplayed_js}).apply(null, arguments);", self)

    @property
    def location_once_scrolled_into_view(self) -> dict:
        """Get the element's location on screen after scrolling it into view.

        This may change without warning and scrolls the element into view
        before calculating coordinates for clicking purposes.

        Returns:
            The top lefthand corner location on the screen, or zero
            coordinates if the element is not visible.

        Example:
            loc = element.location_once_scrolled_into_view
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
        """Get the size of the element.

        Returns:
            The width and height of the element.

        Example:
            size = element.size
        """
        size = self._execute(Command.GET_ELEMENT_RECT)["value"]
        new_size = {"height": size["height"], "width": size["width"]}
        return new_size

    def value_of_css_property(self, property_name) -> str:
        """Get the value of a CSS property.

        Args:
            property_name: The name of the CSS property to get the value of.

        Returns:
            The value of the CSS property.

        Example:
            value = element.value_of_css_property("color")
        """
        return self._execute(Command.GET_ELEMENT_VALUE_OF_CSS_PROPERTY, {"propertyName": property_name})["value"]

    @property
    def location(self) -> dict:
        """Get the location of the element in the renderable canvas.

        Returns:
            The x and y coordinates of the element.

        Example:
            loc = element.location
        """
        old_loc = self._execute(Command.GET_ELEMENT_RECT)["value"]
        new_loc = {"x": round(old_loc["x"]), "y": round(old_loc["y"])}
        return new_loc

    @property
    def rect(self) -> dict:
        """Get the size and location of the element.

        Returns:
            A dictionary with size and location of the element.

        Example:
            rect = element.rect
        """
        return self._execute(Command.GET_ELEMENT_RECT)["value"]

    @property
    def aria_role(self) -> str:
        """Get the ARIA role of the current web element.

        Returns:
            The ARIA role of the element.

        Example:
            role = element.aria_role
        """
        return self._execute(Command.GET_ELEMENT_ARIA_ROLE)["value"]

    @property
    def accessible_name(self) -> str:
        """Get the ARIA Level of the current webelement.

        Returns:
            The ARIA Level of the element.

        Example:
            name = element.accessible_name
        """
        return self._execute(Command.GET_ELEMENT_ARIA_LABEL)["value"]

    @property
    def screenshot_as_base64(self) -> str:
        """Get a base64-encoded screenshot of the current element.

        Returns:
            The screenshot of the element as a base64 encoded string.

        Example:
            img_b64 = element.screenshot_as_base64
        """
        return self._execute(Command.ELEMENT_SCREENSHOT)["value"]

    @property
    def screenshot_as_png(self) -> bytes:
        """Get the screenshot of the current element as a binary data.

        Returns:
            The screenshot of the element as binary data.

        Example:
            element_png = element.screenshot_as_png
        """
        return b64decode(self.screenshot_as_base64.encode("ascii"))

    def screenshot(self, filename) -> bool:
        """Save a PNG screenshot of the current element to a file.

        Use full paths in your filename.

        Args:
            filename: The full path you wish to save your screenshot to. This
                should end with a `.png` extension.

        Returns:
            True if the screenshot was saved successfully, False otherwise.

        Example:
            element.screenshot("/Screenshots/foo.png")
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
        """Get the WebDriver instance this element was found from.

        Example:
            element = driver.find_element(By.ID, "foo")
            parent_element = element.parent
        """
        return self._parent

    @property
    def id(self) -> str:
        """Get the ID used by selenium.

        This is mainly for internal use. Simple use cases such as checking if 2
        webelements refer to the same element, can be done using ``==``::

        Example:
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
            params: A dictionary of named Parameters to send with the command.

        Returns:
            The command's JSON response loaded into a dictionary object.
        """
        if not params:
            params = {}
        params["id"] = self._id
        return self._parent.execute(command, params)

    def find_element(self, by: str = By.ID, value: str | None = None) -> WebElement:
        """Find an element given a By strategy and locator.

        Args:
            by: The locating strategy to use. Default is `By.ID`. Supported values include:
                - By.ID: Locate by element ID.
                - By.NAME: Locate by the `name` attribute.
                - By.XPATH: Locate by an XPath expression.
                - By.CSS_SELECTOR: Locate by a CSS selector.
                - By.CLASS_NAME: Locate by the `class` attribute.
                - By.TAG_NAME: Locate by the tag name (e.g., "input", "button").
                - By.LINK_TEXT: Locate a link element by its exact text.
                - By.PARTIAL_LINK_TEXT: Locate a link element by partial text match.
            value: The locator value to use with the specified `by` strategy.

        Returns:
            The first matching `WebElement` found on the page.

        Example:
            element = driver.find_element(By.ID, "foo")
        """
        by, value = self._parent.locator_converter.convert(by, value)
        return self._execute(Command.FIND_CHILD_ELEMENT, {"using": by, "value": value})["value"]

    def find_elements(self, by: str = By.ID, value: str | None = None) -> list[WebElement]:
        """Find elements given a By strategy and locator.

        Args:
            by: The locating strategy to use. Default is `By.ID`. Supported values include:
                - By.ID: Locate by element ID.
                - By.NAME: Locate by the `name` attribute.
                - By.XPATH: Locate by an XPath expression.
                - By.CSS_SELECTOR: Locate by a CSS selector.
                - By.CLASS_NAME: Locate by the `class` attribute.
                - By.TAG_NAME: Locate by the tag name (e.g., "input", "button").
                - By.LINK_TEXT: Locate a link element by its exact text.
                - By.PARTIAL_LINK_TEXT: Locate a link element by partial text match.
            value: The locator value to use with the specified `by` strategy.

        Returns:
            List of `WebElements` matching locator strategy found on the page.

        Example:
            element = driver.find_elements(By.ID, "foo")
        """
        by, value = self._parent.locator_converter.convert(by, value)
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
