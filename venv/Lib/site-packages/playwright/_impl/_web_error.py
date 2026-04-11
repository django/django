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
from typing import Any, Optional

from playwright._impl._helper import Error
from playwright._impl._page import Page


class WebError:
    def __init__(
        self,
        loop: AbstractEventLoop,
        dispatcher_fiber: Any,
        page: Optional[Page],
        error: Error,
    ) -> None:
        self._loop = loop
        self._dispatcher_fiber = dispatcher_fiber
        self._page = page
        self._error = error

    @property
    def page(self) -> Optional[Page]:
        return self._page

    @property
    def error(self) -> Error:
        return self._error
