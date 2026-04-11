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


from selenium.common.exceptions import NoSuchElementException, UnexpectedTagNameException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement


class Select:
    def __init__(self, webelement: WebElement) -> None:
        """Constructor. A check is made that the given element is a SELECT tag.

        Args:
            webelement: SELECT element to wrap

        Example:
            from selenium.webdriver.support.ui import Select
            Select(driver.find_element(By.TAG_NAME, "select")).select_by_index(2)

        Raises:
            UnexpectedTagNameException: If the element is not a SELECT tag
        """
        if webelement.tag_name.lower() != "select":
            raise UnexpectedTagNameException(f"Select only works on <select> elements, not on {webelement.tag_name}")
        self._el = webelement
        multi = self._el.get_dom_attribute("multiple")
        self.is_multiple = multi and multi != "false"

    @property
    def options(self) -> list[WebElement]:
        """Returns a list of all options belonging to this select tag."""
        return self._el.find_elements(By.TAG_NAME, "option")

    @property
    def all_selected_options(self) -> list[WebElement]:
        """Return a list of all selected options belonging to this select tag."""
        return [opt for opt in self.options if opt.is_selected()]

    @property
    def first_selected_option(self) -> WebElement:
        """Return the first selected option or the currently selected option."""
        for opt in self.options:
            if opt.is_selected():
                return opt
        raise NoSuchElementException("No options are selected")

    def select_by_value(self, value: str) -> None:
        """Select all options that have a value matching the argument.

        Example:
            When given "foo" this would select an option like:

                `<option value="foo">Bar</option>`

        Args:
            value: The value to match against

        Raises:
            NoSuchElementException: If there is no option with specified value in SELECT
        """
        css = f"option[value ={self._escape_string(value)}]"
        opts = self._el.find_elements(By.CSS_SELECTOR, css)
        matched = False
        for opt in opts:
            self._set_selected(opt)
            if not self.is_multiple:
                return
            matched = True
        if not matched:
            raise NoSuchElementException(f"Cannot locate option with value: {value}")

    def select_by_index(self, index: int) -> None:
        """Select the option at the given index by examining the "index" attribute.

        Args:
            index: The option at this index will be selected

        Raises:
            NoSuchElementException: If there is no option with specified index in SELECT
        """
        match = str(index)
        for opt in self.options:
            if opt.get_attribute("index") == match:
                self._set_selected(opt)
                return
        raise NoSuchElementException(f"Could not locate element with index {index}")

    def select_by_visible_text(self, text: str) -> None:
        """Select all options that display text matching the argument.

        Example:
            When given "Bar" this would select an option like:

            `<option value="foo">Bar</option>`

        Args:
            text: The visible text to match against

        Raises:
            NoSuchElementException: If there is no option with specified text in SELECT
        """
        xpath = f".//option[normalize-space(.) = {self._escape_string(text)}]"
        opts = self._el.find_elements(By.XPATH, xpath)
        matched = False
        for opt in opts:
            if not self._has_css_property_and_visible(opt):
                raise NoSuchElementException(f"Invisible option with text: {text}")
            self._set_selected(opt)
            if not self.is_multiple:
                return
            matched = True

        if len(opts) == 0 and " " in text:
            sub_string_without_space = self._get_longest_token(text)
            if sub_string_without_space == "":
                candidates = self.options
            else:
                xpath = f".//option[contains(.,{self._escape_string(sub_string_without_space)})]"
                candidates = self._el.find_elements(By.XPATH, xpath)
            for candidate in candidates:
                if text == candidate.text:
                    if not self._has_css_property_and_visible(candidate):
                        raise NoSuchElementException(f"Invisible option with text: {text}")
                    self._set_selected(candidate)
                    if not self.is_multiple:
                        return
                    matched = True

        if not matched:
            raise NoSuchElementException(f"Could not locate element with visible text: {text}")

    def deselect_all(self) -> None:
        """Clear all selected entries.

        This is only valid when the SELECT supports multiple selections.
        throws NotImplementedError If the SELECT does not support
        multiple selections
        """
        if not self.is_multiple:
            raise NotImplementedError("You may only deselect all options of a multi-select")
        for opt in self.options:
            self._unset_selected(opt)

    def deselect_by_value(self, value: str) -> None:
        """Deselect all options that have a value matching the argument.

        Example:
            When given "foo" this would deselect an option like:

                `<option value="foo">Bar</option>`

        Args:
            value: The value to match against

        Raises:
            NoSuchElementException: If there is no option with specified value in SELECT
        """
        if not self.is_multiple:
            raise NotImplementedError("You may only deselect options of a multi-select")
        matched = False
        css = f"option[value = {self._escape_string(value)}]"
        opts = self._el.find_elements(By.CSS_SELECTOR, css)
        for opt in opts:
            self._unset_selected(opt)
            matched = True
        if not matched:
            raise NoSuchElementException(f"Could not locate element with value: {value}")

    def deselect_by_index(self, index: int) -> None:
        """Deselect the option at the given index by examining the "index" attribute.

        Args:
            index: The option at this index will be deselected

        Raises:
            NoSuchElementException: If there is no option with specified index in SELECT
        """
        if not self.is_multiple:
            raise NotImplementedError("You may only deselect options of a multi-select")
        for opt in self.options:
            if opt.get_attribute("index") == str(index):
                self._unset_selected(opt)
                return
        raise NoSuchElementException(f"Could not locate element with index {index}")

    def deselect_by_visible_text(self, text: str) -> None:
        """Deselect all options that display text matching the argument.

        Example:
            when given "Bar" this would deselect an option like:

                `<option value="foo">Bar</option>`

        Args:
            text: The visible text to match against
        """
        if not self.is_multiple:
            raise NotImplementedError("You may only deselect options of a multi-select")
        matched = False
        xpath = f".//option[normalize-space(.) = {self._escape_string(text)}]"
        opts = self._el.find_elements(By.XPATH, xpath)
        for opt in opts:
            if not self._has_css_property_and_visible(opt):
                raise NoSuchElementException(f"Invisible option with text: {text}")
            self._unset_selected(opt)
            matched = True
        if not matched:
            raise NoSuchElementException(f"Could not locate element with visible text: {text}")

    def _set_selected(self, option) -> None:
        if not option.is_selected():
            if not option.is_enabled():
                raise NotImplementedError("You may not select a disabled option")
            option.click()

    def _unset_selected(self, option) -> None:
        if option.is_selected():
            option.click()

    def _escape_string(self, value: str) -> str:
        if '"' in value and "'" in value:
            substrings = value.split('"')
            result = ["concat("]
            for substring in substrings:
                result.append(f'"{substring}"')
                result.append(", '\"', ")
            result = result[0:-1]
            if value.endswith('"'):
                result.append(", '\"'")
            return "".join(result) + ")"

        if '"' in value:
            return f"'{value}'"

        return f'"{value}"'

    def _get_longest_token(self, value: str) -> str:
        items = value.split(" ")
        longest = ""
        for item in items:
            if len(item) > len(longest):
                longest = item
        return longest

    def _has_css_property_and_visible(self, option) -> bool:
        css_value_candidates = ["hidden", "none", "0", "0.0"]
        css_property_candidates = ["visibility", "display", "opacity"]

        for css_property in css_property_candidates:
            css_value = option.value_of_css_property(css_property)
            if css_value in css_value_candidates:
                return False
        return True
