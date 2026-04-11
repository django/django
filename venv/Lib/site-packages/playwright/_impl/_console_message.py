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

from asyncio import AbstractEventLoop
from typing import TYPE_CHECKING, Any, Dict, List, Literal, Optional, Union

from playwright._impl._api_structures import SourceLocation
from playwright._impl._connection import from_channel, from_nullable_channel
from playwright._impl._js_handle import JSHandle

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl._page import Page
    from playwright._impl._worker import Worker


class ConsoleMessage:
    def __init__(
        self, event: Dict, loop: AbstractEventLoop, dispatcher_fiber: Any
    ) -> None:
        self._event = event
        self._loop = loop
        self._dispatcher_fiber = dispatcher_fiber
        self._page: Optional["Page"] = from_nullable_channel(event.get("page"))
        self._worker: Optional["Worker"] = from_nullable_channel(event.get("worker"))

    def __repr__(self) -> str:
        return f"<ConsoleMessage type={self.type} text={self.text}>"

    def __str__(self) -> str:
        return self.text

    @property
    def type(self) -> Union[
        Literal["assert"],
        Literal["clear"],
        Literal["count"],
        Literal["debug"],
        Literal["dir"],
        Literal["dirxml"],
        Literal["endGroup"],
        Literal["error"],
        Literal["info"],
        Literal["log"],
        Literal["profile"],
        Literal["profileEnd"],
        Literal["startGroup"],
        Literal["startGroupCollapsed"],
        Literal["table"],
        Literal["time"],
        Literal["timeEnd"],
        Literal["trace"],
        Literal["warning"],
    ]:
        return self._event["type"]

    @property
    def text(self) -> str:
        return self._event["text"]

    @property
    def args(self) -> List[JSHandle]:
        return list(map(from_channel, self._event["args"]))

    @property
    def location(self) -> SourceLocation:
        return self._event["location"]

    @property
    def page(self) -> Optional["Page"]:
        return self._page

    @property
    def worker(self) -> Optional["Worker"]:
        return self._worker
