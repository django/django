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
import math
import uuid
from asyncio.tasks import Task
from typing import Any, Callable, List, Tuple, Union

from pyee import EventEmitter

from playwright._impl._connection import ChannelOwner
from playwright._impl._errors import Error, TimeoutError


class Waiter:
    def __init__(self, channel_owner: ChannelOwner, event: str) -> None:
        self._result: asyncio.Future = asyncio.Future()
        self._wait_id = uuid.uuid4().hex
        self._loop = channel_owner._loop
        self._pending_tasks: List[Task] = []
        self._channel = channel_owner._channel
        self._registered_listeners: List[Tuple[EventEmitter, str, Callable]] = []
        self._logs: List[str] = []
        self._wait_for_event_info_before(self._wait_id, event)

    def _wait_for_event_info_before(self, wait_id: str, event: str) -> None:
        self._channel.send_no_reply(
            "waitForEventInfo",
            None,
            {
                "info": {
                    "waitId": wait_id,
                    "phase": "before",
                    "event": event,
                }
            },
        )

    def _wait_for_event_info_after(self, wait_id: str, error: Exception = None) -> None:
        self._channel._connection.wrap_api_call_sync(
            lambda: self._channel.send_no_reply(
                "waitForEventInfo",
                None,
                {
                    "info": {
                        "waitId": wait_id,
                        "phase": "after",
                        **({"error": str(error)} if error else {}),
                    },
                },
            ),
            True,
        )

    def reject_on_event(
        self,
        emitter: EventEmitter,
        event: str,
        error: Union[Error, Callable[..., Error]],
        predicate: Callable = None,
    ) -> None:
        def listener(event_data: Any = None) -> None:
            if not predicate or predicate(event_data):
                self._reject(error() if callable(error) else error)

        emitter.on(event, listener)
        self._registered_listeners.append((emitter, event, listener))

    def reject_on_timeout(self, timeout: float, message: str) -> None:
        if timeout == 0:
            return

        async def reject() -> None:
            await asyncio.sleep(timeout / 1000)
            self._reject(TimeoutError(message))

        self._pending_tasks.append(self._loop.create_task(reject()))

    def _cleanup(self) -> None:
        for task in self._pending_tasks:
            if not task.done():
                task.cancel()
        for listener in self._registered_listeners:
            listener[0].remove_listener(listener[1], listener[2])

    def _fulfill(self, result: Any) -> None:
        self._cleanup()
        if not self._result.done():
            self._result.set_result(result)
        self._wait_for_event_info_after(self._wait_id)

    def _reject(self, exception: Exception) -> None:
        self._cleanup()
        if exception:
            base_class = TimeoutError if isinstance(exception, TimeoutError) else Error
            exception = base_class(str(exception) + format_log_recording(self._logs))
        if not self._result.done():
            self._result.set_exception(exception)
        self._wait_for_event_info_after(self._wait_id, exception)

    def wait_for_event(
        self,
        emitter: EventEmitter,
        event: str,
        predicate: Callable = None,
    ) -> None:
        def listener(event_data: Any = None) -> None:
            if not predicate or predicate(event_data):
                self._fulfill(event_data)

        emitter.on(event, listener)
        self._registered_listeners.append((emitter, event, listener))

    def result(self) -> asyncio.Future:
        return self._result

    def log(self, message: str) -> None:
        self._logs.append(message)
        try:
            self._channel._connection.wrap_api_call_sync(
                lambda: self._channel.send_no_reply(
                    "waitForEventInfo",
                    None,
                    {
                        "info": {
                            "waitId": self._wait_id,
                            "phase": "log",
                            "message": message,
                        },
                    },
                ),
                True,
            )
        except Exception:
            pass


def throw_on_timeout(timeout: float, exception: Exception) -> asyncio.Task:
    async def throw() -> None:
        await asyncio.sleep(timeout / 1000)
        raise exception

    return asyncio.create_task(throw())


def format_log_recording(log: List[str]) -> str:
    if not log:
        return ""
    header = " logs "
    header_length = 60
    left_length = math.floor((header_length - len(header)) / 2)
    right_length = header_length - len(header) - left_length
    new_line = "\n"
    return f"{new_line}{'=' * left_length}{header}{'=' * right_length}{new_line}{new_line.join(log)}{new_line}{'=' * header_length}"
