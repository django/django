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
import inspect
import traceback
from contextlib import AbstractContextManager
from types import TracebackType
from typing import (
    Any,
    Callable,
    Coroutine,
    Generator,
    Generic,
    Optional,
    Type,
    TypeVar,
    Union,
    cast,
)

import greenlet

from playwright._impl._helper import Error
from playwright._impl._impl_to_api_mapping import ImplToApiMapping, ImplWrapper

mapping = ImplToApiMapping()


T = TypeVar("T")
Self = TypeVar("Self", bound="SyncContextManager")


class EventInfo(Generic[T]):
    def __init__(self, sync_base: "SyncBase", future: "asyncio.Future[T]") -> None:
        self._sync_base = sync_base
        self._future = future
        g_self = greenlet.getcurrent()
        self._future.add_done_callback(lambda _: g_self.switch())

    @property
    def value(self) -> T:
        while not self._future.done():
            self._sync_base._dispatcher_fiber.switch()
        asyncio._set_running_loop(self._sync_base._loop)
        exception = self._future.exception()
        if exception:
            raise exception
        return cast(T, mapping.from_maybe_impl(self._future.result()))

    def _cancel(self) -> None:
        self._future.cancel()

    def is_done(self) -> bool:
        return self._future.done()


class EventContextManager(Generic[T], AbstractContextManager):
    def __init__(self, sync_base: "SyncBase", future: "asyncio.Future[T]") -> None:
        self._event = EventInfo[T](sync_base, future)

    def __enter__(self) -> EventInfo[T]:
        return self._event

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        if exc_val:
            self._event._cancel()
        else:
            self._event.value


class SyncBase(ImplWrapper):
    def __init__(self, impl_obj: Any) -> None:
        super().__init__(impl_obj)
        self._loop: asyncio.AbstractEventLoop = impl_obj._loop
        self._dispatcher_fiber = impl_obj._dispatcher_fiber

    def __str__(self) -> str:
        return self._impl_obj.__str__()

    def _sync(
        self,
        coro: Union[Coroutine[Any, Any, Any], Generator[Any, Any, Any]],
    ) -> Any:
        __tracebackhide__ = True
        if self._loop.is_closed():
            coro.close()
            raise Error("Event loop is closed! Is Playwright already stopped?")

        g_self = greenlet.getcurrent()
        task: asyncio.tasks.Task[Any] = self._loop.create_task(coro)
        setattr(task, "__pw_stack__", inspect.stack(0))
        setattr(task, "__pw_stack_trace__", traceback.extract_stack(limit=10))

        task.add_done_callback(lambda _: g_self.switch())
        while not task.done():
            self._dispatcher_fiber.switch()
        asyncio._set_running_loop(self._loop)
        return task.result()

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


class SyncContextManager(SyncBase):
    def __enter__(self: Self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        _traceback: Optional[TracebackType],
    ) -> None:
        self.close()

    def close(self) -> None: ...
