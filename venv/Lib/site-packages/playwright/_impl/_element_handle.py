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

import base64
import mimetypes
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Literal,
    Optional,
    Sequence,
    Union,
    cast,
)

from playwright._impl._api_structures import FilePayload, FloatRect, Position
from playwright._impl._connection import ChannelOwner, from_nullable_channel
from playwright._impl._helper import (
    Error,
    KeyboardModifier,
    MouseButton,
    async_writefile,
    locals_to_params,
    make_dirs_for_file,
)
from playwright._impl._js_handle import (
    JSHandle,
    Serializable,
    parse_result,
    serialize_argument,
)
from playwright._impl._set_input_files_helpers import convert_input_files

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl._frame import Frame
    from playwright._impl._locator import Locator


class ElementHandle(JSHandle):
    def __init__(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        self._frame = cast("Frame", parent)

    async def _createSelectorForTest(self, name: str) -> Optional[str]:
        return await self._channel.send(
            "createSelectorForTest", self._frame._timeout, dict(name=name)
        )

    def as_element(self) -> Optional["ElementHandle"]:
        return self

    async def owner_frame(self) -> Optional["Frame"]:
        return from_nullable_channel(await self._channel.send("ownerFrame", None))

    async def content_frame(self) -> Optional["Frame"]:
        return from_nullable_channel(await self._channel.send("contentFrame", None))

    async def get_attribute(self, name: str) -> Optional[str]:
        return await self._channel.send("getAttribute", None, dict(name=name))

    async def text_content(self) -> Optional[str]:
        return await self._channel.send("textContent", None)

    async def inner_text(self) -> str:
        return await self._channel.send("innerText", None)

    async def inner_html(self) -> str:
        return await self._channel.send("innerHTML", None)

    async def is_checked(self) -> bool:
        return await self._channel.send("isChecked", None)

    async def is_disabled(self) -> bool:
        return await self._channel.send("isDisabled", None)

    async def is_editable(self) -> bool:
        return await self._channel.send("isEditable", None)

    async def is_enabled(self) -> bool:
        return await self._channel.send("isEnabled", None)

    async def is_hidden(self) -> bool:
        return await self._channel.send("isHidden", None)

    async def is_visible(self) -> bool:
        return await self._channel.send("isVisible", None)

    async def dispatch_event(self, type: str, eventInit: Dict = None) -> None:
        await self._channel.send(
            "dispatchEvent",
            None,
            dict(type=type, eventInit=serialize_argument(eventInit)),
        )

    async def scroll_into_view_if_needed(self, timeout: float = None) -> None:
        await self._channel.send(
            "scrollIntoViewIfNeeded", self._frame._timeout, locals_to_params(locals())
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
        await self._channel.send(
            "hover", self._frame._timeout, locals_to_params(locals())
        )

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
        await self._channel.send(
            "click", self._frame._timeout, locals_to_params(locals())
        )

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
        await self._channel.send(
            "dblclick", self._frame._timeout, locals_to_params(locals())
        )

    async def select_option(
        self,
        value: Union[str, Sequence[str]] = None,
        index: Union[int, Sequence[int]] = None,
        label: Union[str, Sequence[str]] = None,
        element: Union["ElementHandle", Sequence["ElementHandle"]] = None,
        timeout: float = None,
        force: bool = None,
        noWaitAfter: bool = None,
    ) -> List[str]:
        params = locals_to_params(
            dict(
                timeout=timeout,
                force=force,
                **convert_select_option_values(value, index, label, element),
            )
        )
        return await self._channel.send("selectOption", self._frame._timeout, params)

    async def tap(
        self,
        modifiers: Sequence[KeyboardModifier] = None,
        position: Position = None,
        timeout: float = None,
        force: bool = None,
        noWaitAfter: bool = None,
        trial: bool = None,
    ) -> None:
        await self._channel.send(
            "tap", self._frame._timeout, locals_to_params(locals())
        )

    async def fill(
        self,
        value: str,
        timeout: float = None,
        noWaitAfter: bool = None,
        force: bool = None,
    ) -> None:
        await self._channel.send(
            "fill", self._frame._timeout, locals_to_params(locals())
        )

    async def select_text(self, force: bool = None, timeout: float = None) -> None:
        await self._channel.send(
            "selectText", self._frame._timeout, locals_to_params(locals())
        )

    async def input_value(self, timeout: float = None) -> str:
        return await self._channel.send(
            "inputValue", self._frame._timeout, locals_to_params(locals())
        )

    async def set_input_files(
        self,
        files: Union[
            str, Path, FilePayload, Sequence[Union[str, Path]], Sequence[FilePayload]
        ],
        timeout: float = None,
        noWaitAfter: bool = None,
    ) -> None:
        frame = await self.owner_frame()
        if not frame:
            raise Error("Cannot set input files to detached element")
        converted = await convert_input_files(files, frame.page.context)
        await self._channel.send(
            "setInputFiles",
            self._frame._timeout,
            {
                "timeout": timeout,
                **converted,
            },
        )

    async def focus(self) -> None:
        await self._channel.send("focus", None)

    async def type(
        self,
        text: str,
        delay: float = None,
        timeout: float = None,
        noWaitAfter: bool = None,
    ) -> None:
        await self._channel.send(
            "type", self._frame._timeout, locals_to_params(locals())
        )

    async def press(
        self,
        key: str,
        delay: float = None,
        timeout: float = None,
        noWaitAfter: bool = None,
    ) -> None:
        await self._channel.send(
            "press", self._frame._timeout, locals_to_params(locals())
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

    async def check(
        self,
        position: Position = None,
        timeout: float = None,
        force: bool = None,
        noWaitAfter: bool = None,
        trial: bool = None,
    ) -> None:
        await self._channel.send(
            "check", self._frame._timeout, locals_to_params(locals())
        )

    async def uncheck(
        self,
        position: Position = None,
        timeout: float = None,
        force: bool = None,
        noWaitAfter: bool = None,
        trial: bool = None,
    ) -> None:
        await self._channel.send(
            "uncheck", self._frame._timeout, locals_to_params(locals())
        )

    async def bounding_box(self) -> Optional[FloatRect]:
        return await self._channel.send("boundingBox", None)

    async def screenshot(
        self,
        timeout: float = None,
        type: Literal["jpeg", "png"] = None,
        path: Union[str, Path] = None,
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
        if "path" in params:
            if "type" not in params:
                params["type"] = determine_screenshot_type(params["path"])
            del params["path"]
        if "mask" in params:
            params["mask"] = list(
                map(
                    lambda locator: (
                        {
                            "frame": locator._frame._channel,
                            "selector": locator._selector,
                        }
                    ),
                    params["mask"],
                )
            )
        encoded_binary = await self._channel.send(
            "screenshot", self._frame._timeout, params
        )
        decoded_binary = base64.b64decode(encoded_binary)
        if path:
            make_dirs_for_file(path)
            await async_writefile(path, decoded_binary)
        return decoded_binary

    async def query_selector(self, selector: str) -> Optional["ElementHandle"]:
        return from_nullable_channel(
            await self._channel.send("querySelector", None, dict(selector=selector))
        )

    async def query_selector_all(self, selector: str) -> List["ElementHandle"]:
        return list(
            map(
                cast(Callable[[Any], Any], from_nullable_channel),
                await self._channel.send(
                    "querySelectorAll", None, dict(selector=selector)
                ),
            )
        )

    async def eval_on_selector(
        self,
        selector: str,
        expression: str,
        arg: Serializable = None,
    ) -> Any:
        return parse_result(
            await self._channel.send(
                "evalOnSelector",
                None,
                dict(
                    selector=selector,
                    expression=expression,
                    arg=serialize_argument(arg),
                ),
            )
        )

    async def eval_on_selector_all(
        self,
        selector: str,
        expression: str,
        arg: Serializable = None,
    ) -> Any:
        return parse_result(
            await self._channel.send(
                "evalOnSelectorAll",
                None,
                dict(
                    selector=selector,
                    expression=expression,
                    arg=serialize_argument(arg),
                ),
            )
        )

    async def wait_for_element_state(
        self,
        state: Literal[
            "disabled", "editable", "enabled", "hidden", "stable", "visible"
        ],
        timeout: float = None,
    ) -> None:
        await self._channel.send(
            "waitForElementState", self._frame._timeout, locals_to_params(locals())
        )

    async def wait_for_selector(
        self,
        selector: str,
        state: Literal["attached", "detached", "hidden", "visible"] = None,
        timeout: float = None,
        strict: bool = None,
    ) -> Optional["ElementHandle"]:
        return from_nullable_channel(
            await self._channel.send(
                "waitForSelector", self._frame._timeout, locals_to_params(locals())
            )
        )


def convert_select_option_values(
    value: Union[str, Sequence[str]] = None,
    index: Union[int, Sequence[int]] = None,
    label: Union[str, Sequence[str]] = None,
    element: Union["ElementHandle", Sequence["ElementHandle"]] = None,
) -> Any:
    if value is None and index is None and label is None and element is None:
        return {}

    options: Any = None
    elements: Any = None
    if value is not None:
        if isinstance(value, str):
            value = [value]
        options = (options or []) + list(map(lambda e: dict(valueOrLabel=e), value))
    if index is not None:
        if isinstance(index, int):
            index = [index]
        options = (options or []) + list(map(lambda e: dict(index=e), index))
    if label is not None:
        if isinstance(label, str):
            label = [label]
        options = (options or []) + list(map(lambda e: dict(label=e), label))
    if element:
        if isinstance(element, ElementHandle):
            element = [element]
        elements = list(map(lambda e: e._channel, element))

    return dict(options=options, elements=elements)


def determine_screenshot_type(path: Union[str, Path]) -> Literal["jpeg", "png"]:
    mime_type, _ = mimetypes.guess_type(path)
    if mime_type == "image/png":
        return "png"
    if mime_type == "image/jpeg":
        return "jpeg"
    raise Error(f'Unsupported screenshot mime type for path "{path}": {mime_type}')
