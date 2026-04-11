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

import asyncio
from contextlib import AbstractAsyncContextManager
from types import TracebackType
from typing import Any, Callable, Generic, Optional, Type, TypeVar, Union

from playwright._impl._impl_to_api_mapping import ImplToApiMapping, ImplWrapper

mapping = ImplToApiMapping()


T = TypeVar("T")
Self = TypeVar("Self", bound="AsyncContextManager")


class AsyncEventInfo(Generic[T]):
    def __init__(self, future: "asyncio.Future[T]") -> None:
        self._future = future

    @property
    async def value(self) -> T:
        return mapping.from_maybe_impl(await self._future)

    def _cancel(self) -> None:
        self._future.cancel()

    def is_done(self) -> bool:
        return self._future.done()


class AsyncEventContextManager(Generic[T], AbstractAsyncContextManager):
    def __init__(self, future: "asyncio.Future[T]") -> None:
        self._event = AsyncEventInfo[T](future)

    async def __aenter__(self) -> AsyncEventInfo[T]:
        return self._event

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        if exc_val:
            self._event._cancel()
        else:
            await self._event.value


class AsyncBase(ImplWrapper):
    def __init__(self, impl_obj: Any) -> None:
        super().__init__(impl_obj)
        self._loop = impl_obj._loop

    def __str__(self) -> str:
        return self._impl_obj.__str__()

    def _wrap_handler(
        self, handler: Union[Callable[..., Any], Any]
    ) -> Callable[..., None]:
        if callable(handler):
            return mapping.wrap_handler(handler)
        return handler

    def on(self, event: Any, f: Any) -> None:
        """Registers the function ``f`` to the event name ``event``."""
        self._impl_obj.on(event, self._wrap_handler(f))

    def once(self, event: Any, f: Any) -> None:
        """The same as ``self.on``, except that the listener is automatically
        removed after being called.
        """
        self._impl_obj.once(event, self._wrap_handler(f))

    def remove_listener(self, event: Any, f: Any) -> None:
        """Removes the function ``f`` from ``event``."""
        self._impl_obj.remove_listener(event, self._wrap_handler(f))


class AsyncContextManager(AsyncBase):
    async def __aenter__(self: Self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        await self.close()

    async def close(self) -> None: ...
