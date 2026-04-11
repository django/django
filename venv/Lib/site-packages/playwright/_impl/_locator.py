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

import json
import pathlib
import re
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    Dict,
    List,
    Literal,
    Optional,
    Pattern,
    Sequence,
    Tuple,
    TypeVar,
    Union,
)

from playwright._impl._api_structures import (
    AriaRole,
    FilePayload,
    FloatRect,
    FrameExpectOptions,
    FrameExpectResult,
    Position,
)
from playwright._impl._element_handle import ElementHandle
from playwright._impl._helper import (
    Error,
    KeyboardModifier,
    MouseButton,
    locals_to_params,
    monotonic_time,
    to_impl,
)
from playwright._impl._js_handle import Serializable
from playwright._impl._str_utils import (
    escape_for_attribute_selector,
    escape_for_text_selector,
)

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl._frame import Frame
    from playwright._impl._js_handle import JSHandle
    from playwright._impl._page import Page

T = TypeVar("T")


class Locator:
    def __init__(
        self,
        frame: "Frame",
        selector: str,
        has_text: Union[str, Pattern[str]] = None,
        has_not_text: Union[str, Pattern[str]] = None,
        has: "Locator" = None,
        has_not: "Locator" = None,
        visible: bool = None,
    ) -> None:
        self._frame = frame
        self._selector = selector
        self._loop = frame._loop
        self._dispatcher_fiber = frame._connection._dispatcher_fiber

        if has_text:
            self._selector += f" >> internal:has-text={escape_for_text_selector(has_text, exact=False)}"

        if has:
            if has._frame != frame:
                raise Error('Inner "has" locator must belong to the same frame.')
            self._selector += " >> internal:has=" + json.dumps(
                has._selector, ensure_ascii=False
            )

        if has_not_text:
            self._selector += f" >> internal:has-not-text={escape_for_text_selector(has_not_text, exact=False)}"

        if has_not:
            locator = has_not
            if locator._frame != frame:
                raise Error('Inner "has_not" locator must belong to the same frame.')
            self._selector += " >> internal:has-not=" + json.dumps(locator._selector)

        if visible is not None:
            self._selector += f" >> visible={bool_to_js_bool(visible)}"

    def __repr__(self) -> str:
        return f"<Locator frame={self._frame!r} selector={self._selector!r}>"

    async def _with_element(
        self,
        task: Callable[[ElementHandle, float], Awaitable[T]],
        timeout: float = None,
    ) -> T:
        timeout = self._frame._timeout(timeout)
        deadline = (monotonic_time() + timeout) if timeout else 0
        handle = await self.element_handle(timeout=timeout)
        if not handle:
            raise Error(f"Could not resolve {self._selector} to DOM Element")
        try:
            return await task(
                handle,
                (deadline - monotonic_time()) if deadline else 0,
            )
        finally:
            await handle.dispose()

    def _equals(self, locator: "Locator") -> bool:
        return self._frame == locator._frame and self._selector == locator._selector

    @property
    def page(self) -> "Page":
        return self._frame.page

    async def bounding_box(self, timeout: float = None) -> Optional[FloatRect]:
        return await self._with_element(
            lambda h, _: h.bounding_box(),
            timeout,
        )

    async def check(
        self,
        position: Position = None,
        timeout: float = None,
        force: bool = None,
        noWaitAfter: bool = None,
        trial: bool = None,
    ) -> None:
        params = locals_to_params(locals())
        return await self._frame.check(self._selector, strict=True, **params)

    async def click(
        self,
        modifiers: Sequence[KeyboardModifier] = None,
        position: Position = None,
        delay: float = None,
        button: MouseButton = None,
        clickCount: int = None,
        timeout: float = None,
        force: bool = None,
        noWaitAfter: bool = None,
        trial: bool = None,
        steps: int = None,
    ) -> None:
        params = locals_to_params(locals())
        return await self._frame._click(self._selector, strict=True, **params)

    async def dblclick(
        self,
        modifiers: Sequence[KeyboardModifier] = None,
        position: Position = None,
        delay: float = None,
        button: MouseButton = None,
        timeout: float = None,
        force: bool = None,
        noWaitAfter: bool = None,
        trial: bool = None,
        steps: int = None,
    ) -> None:
        params = locals_to_params(locals())
        return await self._frame.dblclick(self._selector, strict=True, **params)

    async def dispatch_event(
        self,
        type: str,
        eventInit: Dict = None,
        timeout: float = None,
    ) -> None:
        params = locals_to_params(locals())
        return await self._frame.dispatch_event(self._selector, strict=True, **params)

    async def evaluate(
        self, expression: str, arg: Serializable = None, timeout: float = None
    ) -> Any:
        return await self._with_element(
            lambda h, _: h.evaluate(expression, arg),
            timeout,
        )

    async def evaluate_all(self, expression: str, arg: Serializable = None) -> Any:
        params = locals_to_params(locals())
        return await self._frame.eval_on_selector_all(self._selector, **params)

    async def evaluate_handle(
        self, expression: str, arg: Serializable = None, timeout: float = None
    ) -> "JSHandle":
        return await self._with_element(
            lambda h, _: h.evaluate_handle(expression, arg), timeout
        )

    async def fill(
        self,
        value: str,
        timeout: float = None,
        noWaitAfter: bool = None,
        force: bool = None,
    ) -> None:
        params = locals_to_params(locals())
        return await self._frame.fill(self._selector, strict=True, **params)

    async def clear(
        self,
        timeout: float = None,
        noWaitAfter: bool = None,
        force: bool = None,
    ) -> None:
        params = locals_to_params(locals())
        await self._frame._fill(self._selector, value="", title="Clear", **params)

    def locator(
        self,
        selectorOrLocator: Union[str, "Locator"],
        hasText: Union[str, Pattern[str]] = None,
        hasNotText: Union[str, Pattern[str]] = None,
        has: "Locator" = None,
        hasNot: "Locator" = None,
    ) -> "Locator":
        if isinstance(selectorOrLocator, str):
            return Locator(
                self._frame,
                f"{self._selector} >> {selectorOrLocator}",
                has_text=hasText,
                has_not_text=hasNotText,
                has_not=hasNot,
                has=has,
            )
        selectorOrLocator = to_impl(selectorOrLocator)
        if selectorOrLocator._frame != self._frame:
            raise Error("Locators must belong to the same frame.")
        return Locator(
            self._frame,
            f"{self._selector} >> internal:chain={json.dumps(selectorOrLocator._selector)}",
            has_text=hasText,
            has_not_text=hasNotText,
            has_not=hasNot,
            has=has,
        )

    def get_by_alt_text(
        self, text: Union[str, Pattern[str]], exact: bool = None
    ) -> "Locator":
        return self.locator(get_by_alt_text_selector(text, exact=exact))

    def get_by_label(
        self, text: Union[str, Pattern[str]], exact: bool = None
    ) -> "Locator":
        return self.locator(get_by_label_selector(text, exact=exact))

    def get_by_placeholder(
        self, text: Union[str, Pattern[str]], exact: bool = None
    ) -> "Locator":
        return self.locator(get_by_placeholder_selector(text, exact=exact))

    def get_by_role(
        self,
        role: AriaRole,
        checked: bool = None,
        disabled: bool = None,
        expanded: bool = None,
        includeHidden: bool = None,
        level: int = None,
        name: Union[str, Pattern[str]] = None,
        pressed: bool = None,
        selected: bool = None,
        exact: bool = None,
    ) -> "Locator":
        return self.locator(
            get_by_role_selector(
                role,
                checked=checked,
                disabled=disabled,
                expanded=expanded,
                includeHidden=includeHidden,
                level=level,
                name=name,
                pressed=pressed,
                selected=selected,
                exact=exact,
            )
        )

    def get_by_test_id(self, testId: Union[str, Pattern[str]]) -> "Locator":
        return self.locator(get_by_test_id_selector(test_id_attribute_name(), testId))

    def get_by_text(
        self, text: Union[str, Pattern[str]], exact: bool = None
    ) -> "Locator":
        return self.locator(get_by_text_selector(text, exact=exact))

    def get_by_title(
        self, text: Union[str, Pattern[str]], exact: bool = None
    ) -> "Locator":
        return self.locator(get_by_title_selector(text, exact=exact))

    def frame_locator(self, selector: str) -> "FrameLocator":
        return FrameLocator(self._frame, self._selector + " >> " + selector)

    async def element_handle(
        self,
        timeout: float = None,
    ) -> ElementHandle:
        params = locals_to_params(locals())
        handle = await self._frame.wait_for_selector(
            self._selector, strict=True, state="attached", **params
        )
        assert handle
        return handle

    async def element_handles(self) -> List[ElementHandle]:
        return await self._frame.query_selector_all(self._selector)

    @property
    def first(self) -> "Locator":
        return Locator(self._frame, f"{self._selector} >> nth=0")

    @property
    def last(self) -> "Locator":
        return Locator(self._frame, f"{self._selector} >> nth=-1")

    def nth(self, index: int) -> "Locator":
        return Locator(self._frame, f"{self._selector} >> nth={index}")

    @property
    def content_frame(self) -> "FrameLocator":
        return FrameLocator(self._frame, self._selector)

    def describe(self, description: str) -> "Locator":
        return Locator(
            self._frame,
            f"{self._selector} >> internal:describe={json.dumps(description)}",
        )

    @property
    def description(self) -> Optional[str]:
        try:
            match = re.search(
                r' >> internal:describe=("(?:[^"\\]|\\.)*")$', self._selector
            )
            if match:
                description = json.loads(match.group(1))
                if isinstance(description, str):
                    return description
        except (json.JSONDecodeError, ValueError):
            pass
        return None

    def filter(
        self,
        hasText: Union[str, Pattern[str]] = None,
        hasNotText: Union[str, Pattern[str]] = None,
        has: "Locator" = None,
        hasNot: "Locator" = None,
        visible: bool = None,
    ) -> "Locator":
        return Locator(
            self._frame,
            self._selector,
            has_text=hasText,
            has_not_text=hasNotText,
            has=has,
            has_not=hasNot,
            visible=visible,
        )

    def or_(self, locator: "Locator") -> "Locator":
        if locator._frame != self._frame:
            raise Error("Locators must belong to the same frame.")
        return Locator(
            self._frame,
            self._selector + " >> internal:or=" + json.dumps(locator._selector),
        )

    def and_(self, locator: "Locator") -> "Locator":
        if locator._frame != self._frame:
            raise Error("Locators must belong to the same frame.")
        return Locator(
            self._frame,
            self._selector + " >> internal:and=" + json.dumps(locator._selector),
        )

    async def focus(self, timeout: float = None) -> None:
        params = locals_to_params(locals())
        return await self._frame.focus(self._selector, strict=True, **params)

    async def blur(self, timeout: float = None) -> None:
        await self._frame._channel.send(
            "blur",
            self._frame._timeout,
            {
                "selector": self._selector,
                "strict": True,
                **locals_to_params(locals()),
            },
        )

    async def all(
        self,
    ) -> List["Locator"]:
        result = []
        for index in range(await self.count()):
            result.append(self.nth(index))
        return result

    async def count(
        self,
    ) -> int:
        return await self._frame._query_count(self._selector)

    async def drag_to(
        self,
        target: "Locator",
        force: bool = None,
        noWaitAfter: bool = None,
        timeout: float = None,
        trial: bool = None,
        sourcePosition: Position = None,
        targetPosition: Position = None,
        steps: int = None,
    ) -> None:
        params = locals_to_params(locals())
        del params["target"]
        return await self._frame.drag_and_drop(
            self._selector, target._selector, strict=True, **params
        )

    async def get_attribute(self, name: str, timeout: float = None) -> Optional[str]:
        params = locals_to_params(locals())
        return await self._frame.get_attribute(
            self._selector,
            strict=True,
            **params,
        )

    async def hover(
        self,
        modifiers: Sequence[KeyboardModifier] = None,
        position: Position = None,
        timeout: float = None,
        noWaitAfter: bool = None,
        force: bool = None,
        trial: bool = None,
    ) -> None:
        params = locals_to_params(locals())
        return await self._frame.hover(
            self._selector,
            strict=True,
            **params,
        )

    async def inner_html(self, timeout: float = None) -> str:
        params = locals_to_params(locals())
        return await self._frame.inner_html(
            self._selector,
            strict=True,
            **params,
        )

    async def inner_text(self, timeout: float = None) -> str:
        params = locals_to_params(locals())
        return await self._frame.inner_text(
            self._selector,
            strict=True,
            **params,
        )

    async def input_value(self, timeout: float = None) -> str:
        params = locals_to_params(locals())
        return await self._frame.input_value(
            self._selector,
            strict=True,
            **params,
        )

    async def is_checked(self, timeout: float = None) -> bool:
        params = locals_to_params(locals())
        return await self._frame.is_checked(
            self._selector,
            strict=True,
            **params,
        )

    async def is_disabled(self, timeout: float = None) -> bool:
        params = locals_to_params(locals())
        return await self._frame.is_disabled(
            self._selector,
            strict=True,
            **params,
        )

    async def is_editable(self, timeout: float = None) -> bool:
        params = locals_to_params(locals())
        return await self._frame.is_editable(
            self._selector,
            strict=True,
            **params,
        )

    async def is_enabled(self, timeout: float = None) -> bool:
        params = locals_to_params(locals())
        return await self._frame.is_enabled(
            self._selector,
            strict=True,
            **params,
        )

    async def is_hidden(self, timeout: float = None) -> bool:
        # timeout is deprecated and does nothing
        return await self._frame.is_hidden(
            self._selector,
            strict=True,
        )

    async def is_visible(self, timeout: float = None) -> bool:
        # timeout is deprecated and does nothing
        return await self._frame.is_visible(
            self._selector,
            strict=True,
        )

    async def press(
        self,
        key: str,
        delay: float = None,
        timeout: float = None,
        noWaitAfter: bool = None,
    ) -> None:
        params = locals_to_params(locals())
        return await self._frame.press(self._selector, strict=True, **params)

    async def screenshot(
        self,
        timeout: float = None,
        type: Literal["jpeg", "png"] = None,
        path: Union[str, pathlib.Path] = None,
        quality: int = None,
        omitBackground: bool = None,
        animations: Literal["allow", "disabled"] = None,
        caret: Literal["hide", "initial"] = None,
        scale: Literal["css", "device"] = None,
        mask: Sequence["Locator"] = None,
        maskColor: str = None,
        style: str = None,
    ) -> bytes:
        params = locals_to_params(locals())
        return await self._with_element(
            lambda h, timeout: h.screenshot(
                **{**params, "timeout": timeout},
            ),
        )

    async def aria_snapshot(self, timeout: float = None) -> str:
        return await self._frame._channel.send(
            "ariaSnapshot",
            self._frame._timeout,
            {
                "selector": self._selector,
                **locals_to_params(locals()),
            },
        )

    async def scroll_into_view_if_needed(
        self,
        timeout: float = None,
    ) -> None:
        return await self._with_element(
            lambda h, timeout: h.scroll_into_view_if_needed(timeout=timeout),
            timeout,
        )

    async def select_option(
        self,
        value: Union[str, Sequence[str]] = None,
        index: Union[int, Sequence[int]] = None,
        label: Union[str, Sequence[str]] = None,
        element: Union["ElementHandle", Sequence["ElementHandle"]] = None,
        timeout: float = None,
        noWaitAfter: bool = None,
        force: bool = None,
    ) -> List[str]:
        params = locals_to_params(locals())
        return await self._frame.select_option(
            self._selector,
            strict=True,
            **params,
        )

    async def select_text(self, force: bool = None, timeout: float = None) -> None:
        params = locals_to_params(locals())
        return await self._with_element(
            lambda h, timeout: h.select_text(**{**params, "timeout": timeout}),
            timeout,
        )

    async def set_input_files(
        self,
        files: Union[
            str,
            pathlib.Path,
            FilePayload,
            Sequence[Union[str, pathlib.Path]],
            Sequence[FilePayload],
        ],
        timeout: float = None,
        noWaitAfter: bool = None,
    ) -> None:
        params = locals_to_params(locals())
        return await self._frame.set_input_files(
            self._selector,
            strict=True,
            **params,
        )

    async def tap(
        self,
        modifiers: Sequence[KeyboardModifier] = None,
        position: Position = None,
        timeout: float = None,
        force: bool = None,
        noWaitAfter: bool = None,
        trial: bool = None,
    ) -> None:
        params = locals_to_params(locals())
        return await self._frame.tap(
            self._selector,
            strict=True,
            **params,
        )

    async def text_content(self, timeout: float = None) -> Optional[str]:
        params = locals_to_params(locals())
        return await self._frame.text_content(
            self._selector,
            strict=True,
            **params,
        )

    async def type(
        self,
        text: str,
        delay: float = None,
        timeout: float = None,
        noWaitAfter: bool = None,
    ) -> None:
        params = locals_to_params(locals())
        return await self._frame.type(
            self._selector,
            strict=True,
            **params,
        )

    async def press_sequentially(
        self,
        text: str,
        delay: float = None,
        timeout: float = None,
        noWaitAfter: bool = None,
    ) -> None:
        await self.type(text, delay=delay, timeout=timeout)

    async def uncheck(
        self,
        position: Position = None,
        timeout: float = None,
        force: bool = None,
        noWaitAfter: bool = None,
        trial: bool = None,
    ) -> None:
        params = locals_to_params(locals())
        return await self._frame.uncheck(
            self._selector,
            strict=True,
            **params,
        )

    async def all_inner_texts(
        self,
    ) -> List[str]:
        return await self._frame.eval_on_selector_all(
            self._selector, "ee => ee.map(e => e.innerText)"
        )

    async def all_text_contents(
        self,
    ) -> List[str]:
        return await self._frame.eval_on_selector_all(
            self._selector, "ee => ee.map(e => e.textContent || '')"
        )

    async def wait_for(
        self,
        timeout: float = None,
        state: Literal["attached", "detached", "hidden", "visible"] = None,
    ) -> None:
        await self._frame.wait_for_selector(
            self._selector, strict=True, timeout=timeout, state=state
        )

    async def set_checked(
        self,
        checked: bool,
        position: Position = None,
        timeout: float = None,
        force: bool = None,
        noWaitAfter: bool = None,
        trial: bool = None,
    ) -> None:
        if checked:
            await self.check(
                position=position,
                timeout=timeout,
                force=force,
                trial=trial,
            )
        else:
            await self.uncheck(
                position=position,
                timeout=timeout,
                force=force,
                trial=trial,
            )

    async def _expect(
        self,
        expression: str,
        options: FrameExpectOptions,
        title: str = None,
    ) -> FrameExpectResult:
        return await self._frame._expect(self._selector, expression, options, title)

    async def highlight(self) -> None:
        await self._frame._highlight(self._selector)


class FrameLocator:
    def __init__(self, frame: "Frame", frame_selector: str) -> None:
        self._frame = frame
        self._loop = frame._loop
        self._dispatcher_fiber = frame._connection._dispatcher_fiber
        self._frame_selector = frame_selector

    def locator(
        self,
        selectorOrLocator: Union["Locator", str],
        hasText: Union[str, Pattern[str]] = None,
        hasNotText: Union[str, Pattern[str]] = None,
        has: Locator = None,
        hasNot: Locator = None,
    ) -> Locator:
        if isinstance(selectorOrLocator, str):
            return Locator(
                self._frame,
                f"{self._frame_selector} >> internal:control=enter-frame >> {selectorOrLocator}",
                has_text=hasText,
                has_not_text=hasNotText,
                has=has,
                has_not=hasNot,
            )
        selectorOrLocator = to_impl(selectorOrLocator)
        if selectorOrLocator._frame != self._frame:
            raise ValueError("Locators must belong to the same frame.")
        return Locator(
            self._frame,
            f"{self._frame_selector} >> internal:control=enter-frame >> {selectorOrLocator._selector}",
            has_text=hasText,
            has_not_text=hasNotText,
            has=has,
            has_not=hasNot,
        )

    def get_by_alt_text(
        self, text: Union[str, Pattern[str]], exact: bool = None
    ) -> "Locator":
        return self.locator(get_by_alt_text_selector(text, exact=exact))

    def get_by_label(
        self, text: Union[str, Pattern[str]], exact: bool = None
    ) -> "Locator":
        return self.locator(get_by_label_selector(text, exact=exact))

    def get_by_placeholder(
        self, text: Union[str, Pattern[str]], exact: bool = None
    ) -> "Locator":
        return self.locator(get_by_placeholder_selector(text, exact=exact))

    def get_by_role(
        self,
        role: AriaRole,
        checked: bool = None,
        disabled: bool = None,
        expanded: bool = None,
        includeHidden: bool = None,
        level: int = None,
        name: Union[str, Pattern[str]] = None,
        pressed: bool = None,
        selected: bool = None,
        exact: bool = None,
    ) -> "Locator":
        return self.locator(
            get_by_role_selector(
                role,
                checked=checked,
                disabled=disabled,
                expanded=expanded,
                includeHidden=includeHidden,
                level=level,
                name=name,
                pressed=pressed,
                selected=selected,
                exact=exact,
            )
        )

    def get_by_test_id(self, testId: Union[str, Pattern[str]]) -> "Locator":
        return self.locator(get_by_test_id_selector(test_id_attribute_name(), testId))

    def get_by_text(
        self, text: Union[str, Pattern[str]], exact: bool = None
    ) -> "Locator":
        return self.locator(get_by_text_selector(text, exact=exact))

    def get_by_title(
        self, text: Union[str, Pattern[str]], exact: bool = None
    ) -> "Locator":
        return self.locator(get_by_title_selector(text, exact=exact))

    def frame_locator(self, selector: str) -> "FrameLocator":
        return FrameLocator(
            self._frame,
            f"{self._frame_selector} >> internal:control=enter-frame >> {selector}",
        )

    @property
    def first(self) -> "FrameLocator":
        return FrameLocator(self._frame, f"{self._frame_selector} >> nth=0")

    @property
    def last(self) -> "FrameLocator":
        return FrameLocator(self._frame, f"{self._frame_selector} >> nth=-1")

    @property
    def owner(self) -> "Locator":
        return Locator(self._frame, self._frame_selector)

    def nth(self, index: int) -> "FrameLocator":
        return FrameLocator(self._frame, f"{self._frame_selector} >> nth={index}")

    def __repr__(self) -> str:
        return f"<FrameLocator frame={self._frame!r} selector={self._frame_selector!r}>"


_test_id_attribute_name: str = "data-testid"


def test_id_attribute_name() -> str:
    return _test_id_attribute_name


def set_test_id_attribute_name(attribute_name: str) -> None:
    global _test_id_attribute_name
    _test_id_attribute_name = attribute_name


def get_by_test_id_selector(
    test_id_attribute_name: str, test_id: Union[str, Pattern[str]]
) -> str:
    return f"internal:testid=[{test_id_attribute_name}={escape_for_attribute_selector(test_id, True)}]"


def get_by_attribute_text_selector(
    attr_name: str, text: Union[str, Pattern[str]], exact: bool = None
) -> str:
    return f"internal:attr=[{attr_name}={escape_for_attribute_selector(text, exact=exact)}]"


def get_by_label_selector(text: Union[str, Pattern[str]], exact: bool = None) -> str:
    return "internal:label=" + escape_for_text_selector(text, exact=exact)


def get_by_alt_text_selector(text: Union[str, Pattern[str]], exact: bool = None) -> str:
    return get_by_attribute_text_selector("alt", text, exact=exact)


def get_by_title_selector(text: Union[str, Pattern[str]], exact: bool = None) -> str:
    return get_by_attribute_text_selector("title", text, exact=exact)


def get_by_placeholder_selector(
    text: Union[str, Pattern[str]], exact: bool = None
) -> str:
    return get_by_attribute_text_selector("placeholder", text, exact=exact)


def get_by_text_selector(text: Union[str, Pattern[str]], exact: bool = None) -> str:
    return "internal:text=" + escape_for_text_selector(text, exact=exact)


def bool_to_js_bool(value: bool) -> str:
    return "true" if value else "false"


def get_by_role_selector(
    role: AriaRole,
    checked: bool = None,
    disabled: bool = None,
    expanded: bool = None,
    includeHidden: bool = None,
    level: int = None,
    name: Union[str, Pattern[str]] = None,
    pressed: bool = None,
    selected: bool = None,
    exact: bool = None,
) -> str:
    props: List[Tuple[str, str]] = []
    if checked is not None:
        props.append(("checked", bool_to_js_bool(checked)))
    if disabled is not None:
        props.append(("disabled", bool_to_js_bool(disabled)))
    if selected is not None:
        props.append(("selected", bool_to_js_bool(selected)))
    if expanded is not None:
        props.append(("expanded", bool_to_js_bool(expanded)))
    if includeHidden is not None:
        props.append(("include-hidden", bool_to_js_bool(includeHidden)))
    if level is not None:
        props.append(("level", str(level)))
    if name is not None:
        props.append(
            (
                "name",
                escape_for_attribute_selector(name, exact=exact),
            )
        )
    if pressed is not None:
        props.append(("pressed", bool_to_js_bool(pressed)))
    props_str = "".join([f"[{t[0]}={t[1]}]" for t in props])
    return f"internal:role={role}{props_str}"
