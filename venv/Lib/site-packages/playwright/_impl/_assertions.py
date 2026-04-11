# Copyright (c) Microsoft Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import collections.abc
from typing import Any, List, Optional, Pattern, Sequence, Union
from urllib.parse import urljoin

from playwright._impl._api_structures import (
    AriaRole,
    ExpectedTextValue,
    FrameExpectOptions,
    FrameExpectResult,
)
from playwright._impl._connection import format_call_log
from playwright._impl._errors import Error
from playwright._impl._fetch import APIResponse
from playwright._impl._helper import is_textual_mime_type
from playwright._impl._locator import Locator
from playwright._impl._page import Page
from playwright._impl._str_utils import escape_regex_flags


class AssertionsBase:
    def __init__(
        self,
        locator: Locator,
        timeout: float = None,
        is_not: bool = False,
        message: Optional[str] = None,
    ) -> None:
        self._actual_locator = locator
        self._loop = locator._loop
        self._dispatcher_fiber = locator._dispatcher_fiber
        self._timeout = timeout
        self._is_not = is_not
        self._custom_message = message

    async def _call_expect(
        self, expression: str, expect_options: FrameExpectOptions, title: Optional[str]
    ) -> FrameExpectResult:
        raise NotImplementedError(
            "_call_expect must be implemented in a derived class."
        )

    async def _expect_impl(
        self,
        expression: str,
        expect_options: FrameExpectOptions,
        expected: Any,
        message: str,
        title: str = None,
    ) -> None:
        __tracebackhide__ = True
        expect_options["isNot"] = self._is_not
        if expect_options.get("timeout") is None:
            expect_options["timeout"] = self._timeout or 5_000
        if expect_options["isNot"]:
            message = message.replace("expected to", "expected not to")
        if "useInnerText" in expect_options and expect_options["useInnerText"] is None:
            del expect_options["useInnerText"]
        result = await self._call_expect(expression, expect_options, title)
        if result["matches"] == self._is_not:
            actual = result.get("received")
            if self._custom_message:
                out_message = self._custom_message
                if expected is not None:
                    out_message += f"\nExpected value: '{expected or '<None>'}'"
            else:
                out_message = (
                    f"{message} '{expected}'" if expected is not None else f"{message}"
                )
            error_message = result.get("errorMessage")
            error_message = f"\n{error_message}" if error_message else ""
            raise AssertionError(
                f"{out_message}\nActual value: {actual}{error_message} {format_call_log(result.get('log'))}"
            )


class PageAssertions(AssertionsBase):
    def __init__(
        self,
        page: Page,
        timeout: float = None,
        is_not: bool = False,
        message: Optional[str] = None,
    ) -> None:
        super().__init__(page.locator(":root"), timeout, is_not, message)
        self._actual_page = page

    async def _call_expect(
        self, expression: str, expect_options: FrameExpectOptions, title: Optional[str]
    ) -> FrameExpectResult:
        __tracebackhide__ = True
        return await self._actual_page.main_frame._expect(
            None, expression, expect_options, title
        )

    @property
    def _not(self) -> "PageAssertions":
        return PageAssertions(
            self._actual_page, self._timeout, not self._is_not, self._custom_message
        )

    async def to_have_title(
        self, titleOrRegExp: Union[Pattern[str], str], timeout: float = None
    ) -> None:
        __tracebackhide__ = True
        expected_values = to_expected_text_values(
            [titleOrRegExp], normalize_white_space=True
        )
        await self._expect_impl(
            "to.have.title",
            FrameExpectOptions(expectedText=expected_values, timeout=timeout),
            titleOrRegExp,
            "Page title expected to be",
            'Expect "to_have_title"',
        )

    async def not_to_have_title(
        self, titleOrRegExp: Union[Pattern[str], str], timeout: float = None
    ) -> None:
        __tracebackhide__ = True
        await self._not.to_have_title(titleOrRegExp, timeout)

    async def to_have_url(
        self,
        urlOrRegExp: Union[str, Pattern[str]],
        timeout: float = None,
        ignoreCase: bool = None,
    ) -> None:
        __tracebackhide__ = True
        base_url = self._actual_page.context._base_url
        if isinstance(urlOrRegExp, str) and base_url:
            urlOrRegExp = urljoin(base_url, urlOrRegExp)
        expected_text = to_expected_text_values([urlOrRegExp], ignoreCase=ignoreCase)
        await self._expect_impl(
            "to.have.url",
            FrameExpectOptions(expectedText=expected_text, timeout=timeout),
            urlOrRegExp,
            "Page URL expected to be",
            'Expect "to_have_url"',
        )

    async def not_to_have_url(
        self,
        urlOrRegExp: Union[Pattern[str], str],
        timeout: float = None,
        ignoreCase: bool = None,
    ) -> None:
        __tracebackhide__ = True
        await self._not.to_have_url(urlOrRegExp, timeout, ignoreCase)


class LocatorAssertions(AssertionsBase):
    def __init__(
        self,
        locator: Locator,
        timeout: float = None,
        is_not: bool = False,
        message: Optional[str] = None,
    ) -> None:
        super().__init__(locator, timeout, is_not, message)
        self._actual_locator = locator

    async def _call_expect(
        self, expression: str, expect_options: FrameExpectOptions, title: Optional[str]
    ) -> FrameExpectResult:
        __tracebackhide__ = True
        return await self._actual_locator._expect(expression, expect_options, title)

    @property
    def _not(self) -> "LocatorAssertions":
        return LocatorAssertions(
            self._actual_locator, self._timeout, not self._is_not, self._custom_message
        )

    async def to_contain_text(
        self,
        expected: Union[
            Sequence[str],
            Sequence[Pattern[str]],
            Sequence[Union[Pattern[str], str]],
            Pattern[str],
            str,
        ],
        useInnerText: bool = None,
        timeout: float = None,
        ignoreCase: bool = None,
    ) -> None:
        __tracebackhide__ = True
        if isinstance(expected, collections.abc.Sequence) and not isinstance(
            expected, str
        ):
            expected_text = to_expected_text_values(
                expected,
                match_substring=True,
                normalize_white_space=True,
                ignoreCase=ignoreCase,
            )
            await self._expect_impl(
                "to.contain.text.array",
                FrameExpectOptions(
                    expectedText=expected_text,
                    useInnerText=useInnerText,
                    timeout=timeout,
                ),
                expected,
                "Locator expected to contain text",
                'Expect "to_contain_text"',
            )
        else:
            expected_text = to_expected_text_values(
                [expected],
                match_substring=True,
                normalize_white_space=True,
                ignoreCase=ignoreCase,
            )
            await self._expect_impl(
                "to.have.text",
                FrameExpectOptions(
                    expectedText=expected_text,
                    useInnerText=useInnerText,
                    timeout=timeout,
                ),
                expected,
                "Locator expected to contain text",
                'Expect "to_contain_text"',
            )

    async def not_to_contain_text(
        self,
        expected: Union[
            Sequence[str],
            Sequence[Pattern[str]],
            Sequence[Union[Pattern[str], str]],
            Pattern[str],
            str,
        ],
        useInnerText: bool = None,
        timeout: float = None,
        ignoreCase: bool = None,
    ) -> None:
        __tracebackhide__ = True
        await self._not.to_contain_text(expected, useInnerText, timeout, ignoreCase)

    async def to_have_attribute(
        self,
        name: str,
        value: Union[str, Pattern[str]],
        ignoreCase: bool = None,
        timeout: float = None,
    ) -> None:
        __tracebackhide__ = True
        expected_text = to_expected_text_values([value], ignoreCase=ignoreCase)
        await self._expect_impl(
            "to.have.attribute.value",
            FrameExpectOptions(
                expressionArg=name, expectedText=expected_text, timeout=timeout
            ),
            value,
            "Locator expected to have attribute",
            'Expect "to_have_attribute"',
        )

    async def not_to_have_attribute(
        self,
        name: str,
        value: Union[str, Pattern[str]],
        ignoreCase: bool = None,
        timeout: float = None,
    ) -> None:
        __tracebackhide__ = True
        await self._not.to_have_attribute(
            name, value, ignoreCase=ignoreCase, timeout=timeout
        )

    async def to_have_class(
        self,
        expected: Union[
            Sequence[str],
            Sequence[Pattern[str]],
            Sequence[Union[Pattern[str], str]],
            Pattern[str],
            str,
        ],
        timeout: float = None,
    ) -> None:
        __tracebackhide__ = True
        if isinstance(expected, collections.abc.Sequence) and not isinstance(
            expected, str
        ):
            expected_text = to_expected_text_values(expected)
            await self._expect_impl(
                "to.have.class.array",
                FrameExpectOptions(expectedText=expected_text, timeout=timeout),
                expected,
                "Locator expected to have class",
                'Expect "to_have_class"',
            )
        else:
            expected_text = to_expected_text_values([expected])
            await self._expect_impl(
                "to.have.class",
                FrameExpectOptions(expectedText=expected_text, timeout=timeout),
                expected,
                "Locator expected to have class",
                'Expect "to_have_class"',
            )

    async def not_to_have_class(
        self,
        expected: Union[
            Sequence[str],
            Sequence[Pattern[str]],
            Sequence[Union[Pattern[str], str]],
            Pattern[str],
            str,
        ],
        timeout: float = None,
    ) -> None:
        __tracebackhide__ = True
        await self._not.to_have_class(expected, timeout)

    async def to_contain_class(
        self,
        expected: Union[
            Sequence[str],
            str,
        ],
        timeout: float = None,
    ) -> None:
        __tracebackhide__ = True
        if isinstance(expected, collections.abc.Sequence) and not isinstance(
            expected, str
        ):
            expected_text = to_expected_text_values(expected)
            await self._expect_impl(
                "to.contain.class.array",
                FrameExpectOptions(expectedText=expected_text, timeout=timeout),
                expected,
                "Locator expected to contain class names",
                'Expect "to_contain_class"',
            )
        else:
            expected_text = to_expected_text_values([expected])
            await self._expect_impl(
                "to.contain.class",
                FrameExpectOptions(expectedText=expected_text, timeout=timeout),
                expected,
                "Locator expected to contain class",
                'Expect "to_contain_class"',
            )

    async def not_to_contain_class(
        self,
        expected: Union[
            Sequence[str],
            str,
        ],
        timeout: float = None,
    ) -> None:
        __tracebackhide__ = True
        await self._not.to_contain_class(expected, timeout)

    async def to_have_count(
        self,
        count: int,
        timeout: float = None,
    ) -> None:
        __tracebackhide__ = True
        await self._expect_impl(
            "to.have.count",
            FrameExpectOptions(expectedNumber=count, timeout=timeout),
            count,
            "Locator expected to have count",
            'Expect "to_have_count"',
        )

    async def not_to_have_count(
        self,
        count: int,
        timeout: float = None,
    ) -> None:
        __tracebackhide__ = True
        await self._not.to_have_count(count, timeout)

    async def to_have_css(
        self,
        name: str,
        value: Union[str, Pattern[str]],
        timeout: float = None,
    ) -> None:
        __tracebackhide__ = True
        expected_text = to_expected_text_values([value])
        await self._expect_impl(
            "to.have.css",
            FrameExpectOptions(
                expressionArg=name, expectedText=expected_text, timeout=timeout
            ),
            value,
            "Locator expected to have CSS",
            'Expect "to_have_css"',
        )

    async def not_to_have_css(
        self,
        name: str,
        value: Union[str, Pattern[str]],
        timeout: float = None,
    ) -> None:
        __tracebackhide__ = True
        await self._not.to_have_css(name, value, timeout)

    async def to_have_id(
        self,
        id: Union[str, Pattern[str]],
        timeout: float = None,
    ) -> None:
        __tracebackhide__ = True
        expected_text = to_expected_text_values([id])
        await self._expect_impl(
            "to.have.id",
            FrameExpectOptions(expectedText=expected_text, timeout=timeout),
            id,
            "Locator expected to have ID",
            'Expect "to_have_id"',
        )

    async def not_to_have_id(
        self,
        id: Union[str, Pattern[str]],
        timeout: float = None,
    ) -> None:
        __tracebackhide__ = True
        await self._not.to_have_id(id, timeout)

    async def to_have_js_property(
        self,
        name: str,
        value: Any,
        timeout: float = None,
    ) -> None:
        __tracebackhide__ = True
        await self._expect_impl(
            "to.have.property",
            FrameExpectOptions(
                expressionArg=name, expectedValue=value, timeout=timeout
            ),
            value,
            "Locator expected to have JS Property",
            'Expect "to_have_property"',
        )

    async def not_to_have_js_property(
        self,
        name: str,
        value: Any,
        timeout: float = None,
    ) -> None:
        __tracebackhide__ = True
        await self._not.to_have_js_property(name, value, timeout)

    async def to_have_value(
        self,
        value: Union[str, Pattern[str]],
        timeout: float = None,
    ) -> None:
        __tracebackhide__ = True
        expected_text = to_expected_text_values([value])
        await self._expect_impl(
            "to.have.value",
            FrameExpectOptions(expectedText=expected_text, timeout=timeout),
            value,
            "Locator expected to have Value",
            'Expect "to_have_value"',
        )

    async def not_to_have_value(
        self,
        value: Union[str, Pattern[str]],
        timeout: float = None,
    ) -> None:
        __tracebackhide__ = True
        await self._not.to_have_value(value, timeout)

    async def to_have_values(
        self,
        values: Union[
            Sequence[str], Sequence[Pattern[str]], Sequence[Union[Pattern[str], str]]
        ],
        timeout: float = None,
    ) -> None:
        __tracebackhide__ = True
        expected_text = to_expected_text_values(values)
        await self._expect_impl(
            "to.have.values",
            FrameExpectOptions(expectedText=expected_text, timeout=timeout),
            values,
            "Locator expected to have Values",
            'Expect "to_have_values"',
        )

    async def not_to_have_values(
        self,
        values: Union[
            Sequence[str], Sequence[Pattern[str]], Sequence[Union[Pattern[str], str]]
        ],
        timeout: float = None,
    ) -> None:
        __tracebackhide__ = True
        await self._not.to_have_values(values, timeout)

    async def to_have_text(
        self,
        expected: Union[
            Sequence[str],
            Sequence[Pattern[str]],
            Sequence[Union[Pattern[str], str]],
            Pattern[str],
            str,
        ],
        useInnerText: bool = None,
        timeout: float = None,
        ignoreCase: bool = None,
    ) -> None:
        __tracebackhide__ = True
        if isinstance(expected, collections.abc.Sequence) and not isinstance(
            expected, str
        ):
            expected_text = to_expected_text_values(
                expected,
                normalize_white_space=True,
                ignoreCase=ignoreCase,
            )
            await self._expect_impl(
                "to.have.text.array",
                FrameExpectOptions(
                    expectedText=expected_text,
                    useInnerText=useInnerText,
                    timeout=timeout,
                ),
                expected,
                "Locator expected to have text",
                'Expect "to_have_text"',
            )
        else:
            expected_text = to_expected_text_values(
                [expected], normalize_white_space=True, ignoreCase=ignoreCase
            )
            await self._expect_impl(
                "to.have.text",
                FrameExpectOptions(
                    expectedText=expected_text,
                    useInnerText=useInnerText,
                    timeout=timeout,
                ),
                expected,
                "Locator expected to have text",
                'Expect "to_have_text"',
            )

    async def not_to_have_text(
        self,
        expected: Union[
            Sequence[str],
            Sequence[Pattern[str]],
            Sequence[Union[Pattern[str], str]],
            Pattern[str],
            str,
        ],
        useInnerText: bool = None,
        timeout: float = None,
        ignoreCase: bool = None,
    ) -> None:
        __tracebackhide__ = True
        await self._not.to_have_text(expected, useInnerText, timeout, ignoreCase)

    async def to_be_attached(
        self,
        attached: bool = None,
        timeout: float = None,
    ) -> None:
        __tracebackhide__ = True
        if attached is None:
            attached = True
        attached_string = "attached" if attached else "detached"
        await self._expect_impl(
            ("to.be.attached" if attached else "to.be.detached"),
            FrameExpectOptions(timeout=timeout),
            None,
            f"Locator expected to be {attached_string}",
            'Expect "to_be_attached"',
        )

    async def to_be_checked(
        self,
        timeout: float = None,
        checked: bool = None,
        indeterminate: bool = None,
    ) -> None:
        __tracebackhide__ = True
        expected_value = {}
        if indeterminate is not None:
            expected_value["indeterminate"] = indeterminate
        if checked is not None:
            expected_value["checked"] = checked
        checked_string: str
        if indeterminate:
            checked_string = "indeterminate"
        else:
            checked_string = "unchecked" if checked is False else "checked"
        await self._expect_impl(
            "to.be.checked",
            FrameExpectOptions(timeout=timeout, expectedValue=expected_value),
            None,
            f"Locator expected to be {checked_string}",
            'Expect "to_be_checked"',
        )

    async def not_to_be_attached(
        self,
        attached: bool = None,
        timeout: float = None,
    ) -> None:
        __tracebackhide__ = True
        await self._not.to_be_attached(attached=attached, timeout=timeout)

    async def not_to_be_checked(
        self,
        timeout: float = None,
    ) -> None:
        __tracebackhide__ = True
        await self._not.to_be_checked(timeout)

    async def to_be_disabled(
        self,
        timeout: float = None,
    ) -> None:
        __tracebackhide__ = True
        await self._expect_impl(
            "to.be.disabled",
            FrameExpectOptions(timeout=timeout),
            None,
            "Locator expected to be disabled",
            'Expect "to_be_disabled"',
        )

    async def not_to_be_disabled(
        self,
        timeout: float = None,
    ) -> None:
        __tracebackhide__ = True
        await self._not.to_be_disabled(timeout)

    async def to_be_editable(
        self,
        editable: bool = None,
        timeout: float = None,
    ) -> None:
        __tracebackhide__ = True
        if editable is None:
            editable = True
        editable_string = "editable" if editable else "readonly"
        await self._expect_impl(
            "to.be.editable" if editable else "to.be.readonly",
            FrameExpectOptions(timeout=timeout),
            None,
            f"Locator expected to be {editable_string}",
            'Expect "to_be_editable"',
        )

    async def not_to_be_editable(
        self,
        editable: bool = None,
        timeout: float = None,
    ) -> None:
        __tracebackhide__ = True
        await self._not.to_be_editable(editable, timeout)

    async def to_be_empty(
        self,
        timeout: float = None,
    ) -> None:
        __tracebackhide__ = True
        await self._expect_impl(
            "to.be.empty",
            FrameExpectOptions(timeout=timeout),
            None,
            "Locator expected to be empty",
            'Expect "to_be_empty"',
        )

    async def not_to_be_empty(
        self,
        timeout: float = None,
    ) -> None:
        __tracebackhide__ = True
        await self._not.to_be_empty(timeout)

    async def to_be_enabled(
        self,
        enabled: bool = None,
        timeout: float = None,
    ) -> None:
        __tracebackhide__ = True
        if enabled is None:
            enabled = True
        enabled_string = "enabled" if enabled else "disabled"
        await self._expect_impl(
            "to.be.enabled" if enabled else "to.be.disabled",
            FrameExpectOptions(timeout=timeout),
            None,
            f"Locator expected to be {enabled_string}",
            'Expect "to_be_enabled"',
        )

    async def not_to_be_enabled(
        self,
        enabled: bool = None,
        timeout: float = None,
    ) -> None:
        __tracebackhide__ = True
        await self._not.to_be_enabled(enabled, timeout)

    async def to_be_hidden(
        self,
        timeout: float = None,
    ) -> None:
        __tracebackhide__ = True
        await self._expect_impl(
            "to.be.hidden",
            FrameExpectOptions(timeout=timeout),
            None,
            "Locator expected to be hidden",
            'Expect "to_be_hidden"',
        )

    async def not_to_be_hidden(
        self,
        timeout: float = None,
    ) -> None:
        __tracebackhide__ = True
        await self._not.to_be_hidden(timeout)

    async def to_be_visible(
        self,
        visible: bool = None,
        timeout: float = None,
    ) -> None:
        __tracebackhide__ = True
        if visible is None:
            visible = True
        visible_string = "visible" if visible else "hidden"
        await self._expect_impl(
            "to.be.visible" if visible else "to.be.hidden",
            FrameExpectOptions(timeout=timeout),
            None,
            f"Locator expected to be {visible_string}",
            'Expect "to_be_visible"',
        )

    async def not_to_be_visible(
        self,
        visible: bool = None,
        timeout: float = None,
    ) -> None:
        __tracebackhide__ = True
        await self._not.to_be_visible(visible, timeout)

    async def to_be_focused(
        self,
        timeout: float = None,
    ) -> None:
        __tracebackhide__ = True
        await self._expect_impl(
            "to.be.focused",
            FrameExpectOptions(timeout=timeout),
            None,
            "Locator expected to be focused",
            'Expect "to_be_focused"',
        )

    async def not_to_be_focused(
        self,
        timeout: float = None,
    ) -> None:
        __tracebackhide__ = True
        await self._not.to_be_focused(timeout)

    async def to_be_in_viewport(
        self,
        ratio: float = None,
        timeout: float = None,
    ) -> None:
        __tracebackhide__ = True
        await self._expect_impl(
            "to.be.in.viewport",
            FrameExpectOptions(timeout=timeout, expectedNumber=ratio),
            None,
            "Locator expected to be in viewport",
            'Expect "to_be_in_viewport"',
        )

    async def not_to_be_in_viewport(
        self, ratio: float = None, timeout: float = None
    ) -> None:
        __tracebackhide__ = True
        await self._not.to_be_in_viewport(ratio=ratio, timeout=timeout)

    async def to_have_accessible_description(
        self,
        description: Union[str, Pattern[str]],
        ignoreCase: bool = None,
        timeout: float = None,
    ) -> None:
        __tracebackhide__ = True
        expected_values = to_expected_text_values(
            [description], ignoreCase=ignoreCase, normalize_white_space=True
        )
        await self._expect_impl(
            "to.have.accessible.description",
            FrameExpectOptions(expectedText=expected_values, timeout=timeout),
            None,
            "Locator expected to have accessible description",
            'Expect "to_have_accessible_description"',
        )

    async def not_to_have_accessible_description(
        self,
        name: Union[str, Pattern[str]],
        ignoreCase: bool = None,
        timeout: float = None,
    ) -> None:
        __tracebackhide__ = True
        await self._not.to_have_accessible_description(name, ignoreCase, timeout)

    async def to_have_accessible_name(
        self,
        name: Union[str, Pattern[str]],
        ignoreCase: bool = None,
        timeout: float = None,
    ) -> None:
        __tracebackhide__ = True
        expected_values = to_expected_text_values(
            [name], ignoreCase=ignoreCase, normalize_white_space=True
        )
        await self._expect_impl(
            "to.have.accessible.name",
            FrameExpectOptions(expectedText=expected_values, timeout=timeout),
            None,
            "Locator expected to have accessible name",
            'Expect "to_have_accessible_name"',
        )

    async def not_to_have_accessible_name(
        self,
        name: Union[str, Pattern[str]],
        ignoreCase: bool = None,
        timeout: float = None,
    ) -> None:
        __tracebackhide__ = True
        await self._not.to_have_accessible_name(name, ignoreCase, timeout)

    async def to_have_role(self, role: AriaRole, timeout: float = None) -> None:
        __tracebackhide__ = True
        if isinstance(role, Pattern):
            raise Error('"role" argument in to_have_role must be a string')
        expected_values = to_expected_text_values([role])
        await self._expect_impl(
            "to.have.role",
            FrameExpectOptions(expectedText=expected_values, timeout=timeout),
            None,
            "Locator expected to have accessible role",
            'Expect "to_have_role"',
        )

    async def to_have_accessible_error_message(
        self,
        errorMessage: Union[str, Pattern[str]],
        ignoreCase: bool = None,
        timeout: float = None,
    ) -> None:
        __tracebackhide__ = True
        expected_values = to_expected_text_values(
            [errorMessage], ignoreCase=ignoreCase, normalize_white_space=True
        )
        await self._expect_impl(
            "to.have.accessible.error.message",
            FrameExpectOptions(expectedText=expected_values, timeout=timeout),
            None,
            "Locator expected to have accessible error message",
            'Expect "to_have_accessible_error_message"',
        )

    async def not_to_have_accessible_error_message(
        self,
        errorMessage: Union[str, Pattern[str]],
        ignoreCase: bool = None,
        timeout: float = None,
    ) -> None:
        __tracebackhide__ = True
        await self._not.to_have_accessible_error_message(
            errorMessage=errorMessage, ignoreCase=ignoreCase, timeout=timeout
        )

    async def not_to_have_role(self, role: AriaRole, timeout: float = None) -> None:
        __tracebackhide__ = True
        await self._not.to_have_role(role, timeout)

    async def to_match_aria_snapshot(
        self, expected: str, timeout: float = None
    ) -> None:
        __tracebackhide__ = True
        await self._expect_impl(
            "to.match.aria",
            FrameExpectOptions(expectedValue=expected, timeout=timeout),
            expected,
            "Locator expected to match Aria snapshot",
            'Expect "to_match_aria_snapshot"',
        )

    async def not_to_match_aria_snapshot(
        self, expected: str, timeout: float = None
    ) -> None:
        __tracebackhide__ = True
        await self._not.to_match_aria_snapshot(expected, timeout)


class APIResponseAssertions:
    def __init__(
        self,
        response: APIResponse,
        timeout: float = None,
        is_not: bool = False,
        message: Optional[str] = None,
    ) -> None:
        self._loop = response._loop
        self._dispatcher_fiber = response._dispatcher_fiber
        self._timeout = timeout
        self._is_not = is_not
        self._actual = response
        self._custom_message = message

    @property
    def _not(self) -> "APIResponseAssertions":
        return APIResponseAssertions(
            self._actual, self._timeout, not self._is_not, self._custom_message
        )

    async def to_be_ok(
        self,
    ) -> None:
        __tracebackhide__ = True
        if self._is_not is not self._actual.ok:
            return
        message = f"Response status expected to be within [200..299] range, was '{self._actual.status}'"
        if self._is_not:
            message = message.replace("expected to", "expected not to")
        out_message = self._custom_message or message
        out_message += format_call_log(await self._actual._fetch_log())

        content_type = self._actual.headers.get("content-type")
        is_text_encoding = content_type and is_textual_mime_type(content_type)
        text = await self._actual.text() if is_text_encoding else None
        if text is not None:
            out_message += f"\n Response Text:\n{text[:1000]}"

        raise AssertionError(out_message)

    async def not_to_be_ok(self) -> None:
        __tracebackhide__ = True
        await self._not.to_be_ok()


def expected_regex(
    pattern: Pattern[str],
    match_substring: bool,
    normalize_white_space: bool,
    ignoreCase: Optional[bool] = None,
) -> ExpectedTextValue:
    expected = ExpectedTextValue(
        regexSource=pattern.pattern,
        regexFlags=escape_regex_flags(pattern),
        matchSubstring=match_substring,
        normalizeWhiteSpace=normalize_white_space,
        ignoreCase=ignoreCase,
    )
    if expected["ignoreCase"] is None:
        del expected["ignoreCase"]
    return expected


def to_expected_text_values(
    items: Union[
        Sequence[Pattern[str]], Sequence[str], Sequence[Union[str, Pattern[str]]]
    ],
    match_substring: bool = False,
    normalize_white_space: bool = False,
    ignoreCase: Optional[bool] = None,
) -> Sequence[ExpectedTextValue]:
    out: List[ExpectedTextValue] = []
    assert isinstance(items, (list, tuple))
    for item in items:
        if isinstance(item, str):
            o = ExpectedTextValue(
                string=item,
                matchSubstring=match_substring,
                normalizeWhiteSpace=normalize_white_space,
                ignoreCase=ignoreCase,
            )
            if o["ignoreCase"] is None:
                del o["ignoreCase"]
            out.append(o)
        elif isinstance(item, Pattern):
            out.append(
                expected_regex(item, match_substring, normalize_white_space, ignoreCase)
            )
        else:
            raise Error("value must be a string or regular expression")
    return out
