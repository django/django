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
import collections.abc
import contextvars
import datetime
import inspect
import sys
import traceback
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Mapping,
    Optional,
    TypedDict,
    Union,
    cast,
)

from pyee import EventEmitter
from pyee.asyncio import AsyncIOEventEmitter

import playwright
import playwright._impl._impl_to_api_mapping
from playwright._impl._errors import TargetClosedError, rewrite_error
from playwright._impl._greenlets import EventGreenlet
from playwright._impl._helper import Error, ParsedMessagePayload, parse_error
from playwright._impl._transport import Transport

if TYPE_CHECKING:
    from playwright._impl._local_utils import LocalUtils
    from playwright._impl._playwright import Playwright

TimeoutCalculator = Optional[Callable[[Optional[float]], float]]


class Channel(AsyncIOEventEmitter):
    def __init__(self, connection: "Connection", object: "ChannelOwner") -> None:
        super().__init__()
        self._connection = connection
        self._guid = object._guid
        self._object = object
        self.on("error", lambda exc: self._connection._on_event_listener_error(exc))

    async def send(
        self,
        method: str,
        timeout_calculator: TimeoutCalculator,
        params: Dict = None,
        is_internal: bool = False,
        title: str = None,
    ) -> Any:
        return await self._connection.wrap_api_call(
            lambda: self._inner_send(method, timeout_calculator, params, False),
            is_internal,
            title,
        )

    async def send_return_as_dict(
        self,
        method: str,
        timeout_calculator: TimeoutCalculator,
        params: Dict = None,
        is_internal: bool = False,
        title: str = None,
    ) -> Any:
        return await self._connection.wrap_api_call(
            lambda: self._inner_send(method, timeout_calculator, params, True),
            is_internal,
            title,
        )

    def send_no_reply(
        self,
        method: str,
        timeout_calculator: TimeoutCalculator,
        params: Dict = None,
        is_internal: bool = False,
        title: str = None,
    ) -> None:
        # No reply messages are used to e.g. waitForEventInfo(after).
        self._connection.wrap_api_call_sync(
            lambda: self._connection._send_message_to_server(
                self._object,
                method,
                _augment_params(params, timeout_calculator),
                True,
            ),
            is_internal,
            title,
        )

    async def _inner_send(
        self,
        method: str,
        timeout_calculator: TimeoutCalculator,
        params: Optional[Dict],
        return_as_dict: bool,
    ) -> Any:
        if self._connection._error:
            error = self._connection._error
            self._connection._error = None
            raise error
        callback = self._connection._send_message_to_server(
            self._object, method, _augment_params(params, timeout_calculator)
        )
        done, _ = await asyncio.wait(
            {
                self._connection._transport.on_error_future,
                callback.future,
            },
            return_when=asyncio.FIRST_COMPLETED,
        )
        if not callback.future.done():
            callback.future.cancel()
        result = next(iter(done)).result()
        # Protocol now has named return values, assume result is one level deeper unless
        # there is explicit ambiguity.
        if not result:
            return None
        assert isinstance(result, dict)
        if return_as_dict:
            return result
        if len(result) == 0:
            return None
        assert len(result) == 1
        key = next(iter(result))
        return result[key]


class ChannelOwner(AsyncIOEventEmitter):
    def __init__(
        self,
        parent: Union["ChannelOwner", "Connection"],
        type: str,
        guid: str,
        initializer: Dict,
    ) -> None:
        super().__init__(loop=parent._loop)
        self._loop: asyncio.AbstractEventLoop = parent._loop
        self._dispatcher_fiber: Any = parent._dispatcher_fiber
        self._type = type
        self._guid: str = guid
        self._connection: Connection = (
            parent._connection if isinstance(parent, ChannelOwner) else parent
        )
        self._parent: Optional[ChannelOwner] = (
            parent if isinstance(parent, ChannelOwner) else None
        )
        self._objects: Dict[str, "ChannelOwner"] = {}
        self._channel: Channel = Channel(self._connection, self)
        self._initializer = initializer
        self._was_collected = False

        self._connection._objects[guid] = self
        if self._parent:
            self._parent._objects[guid] = self

        self._event_to_subscription_mapping: Dict[str, str] = {}

    def _dispose(self, reason: Optional[str]) -> None:
        # Clean up from parent and connection.
        if self._parent:
            del self._parent._objects[self._guid]
        del self._connection._objects[self._guid]
        self._was_collected = reason == "gc"

        # Dispose all children.
        for object in list(self._objects.values()):
            object._dispose(reason)
        self._objects.clear()

    def _adopt(self, child: "ChannelOwner") -> None:
        del cast("ChannelOwner", child._parent)._objects[child._guid]
        self._objects[child._guid] = child
        child._parent = self

    def _set_event_to_subscription_mapping(self, mapping: Dict[str, str]) -> None:
        self._event_to_subscription_mapping = mapping

    def _update_subscription(self, event: str, enabled: bool) -> None:
        protocol_event = self._event_to_subscription_mapping.get(event)
        if protocol_event:
            self._connection.wrap_api_call_sync(
                lambda: self._channel.send_no_reply(
                    "updateSubscription",
                    None,
                    {"event": protocol_event, "enabled": enabled},
                ),
                True,
            )

    def _add_event_handler(self, event: str, k: Any, v: Any) -> None:
        if not self.listeners(event):
            self._update_subscription(event, True)
        super()._add_event_handler(event, k, v)

    def remove_listener(self, event: str, f: Any) -> None:
        super().remove_listener(event, f)
        if not self.listeners(event):
            self._update_subscription(event, False)


class ProtocolCallback:
    def __init__(self, loop: asyncio.AbstractEventLoop, no_reply: bool = False) -> None:
        self.stack_trace: traceback.StackSummary
        self.no_reply = no_reply
        self.future = loop.create_future()
        if no_reply:
            self.future.set_result(None)
        # The outer task can get cancelled by the user, this forwards the cancellation to the inner task.
        current_task = asyncio.current_task()

        def cb(task: asyncio.Task) -> None:
            if current_task:
                current_task.remove_done_callback(cb)
            if task.cancelled():
                self.future.cancel()

        if current_task:
            current_task.add_done_callback(cb)
            self.future.add_done_callback(
                lambda _: (
                    current_task.remove_done_callback(cb) if current_task else None
                )
            )


class RootChannelOwner(ChannelOwner):
    def __init__(self, connection: "Connection") -> None:
        super().__init__(connection, "Root", "", {})

    async def initialize(self) -> "Playwright":
        return from_channel(
            await self._channel.send(
                "initialize",
                None,
                {
                    "sdkLanguage": "python",
                },
            )
        )


class Connection(EventEmitter):
    def __init__(
        self,
        dispatcher_fiber: Any,
        object_factory: Callable[[ChannelOwner, str, str, Dict], ChannelOwner],
        transport: Transport,
        loop: asyncio.AbstractEventLoop,
        local_utils: Optional["LocalUtils"] = None,
    ) -> None:
        super().__init__()
        self._dispatcher_fiber = dispatcher_fiber
        self._transport = transport
        self._transport.on_message = lambda msg: self.dispatch(msg)
        self._waiting_for_object: Dict[str, Callable[[ChannelOwner], None]] = {}
        self._last_id = 0
        self._objects: Dict[str, ChannelOwner] = {}
        self._callbacks: Dict[int, ProtocolCallback] = {}
        self._object_factory = object_factory
        self._is_sync = False
        self._child_ws_connections: List["Connection"] = []
        self._loop = loop
        self.playwright_future: asyncio.Future["Playwright"] = loop.create_future()
        self._error: Optional[BaseException] = None
        self.is_remote = False
        self._init_task: Optional[asyncio.Task] = None
        self._api_zone: contextvars.ContextVar[Optional[ParsedStackTrace]] = (
            contextvars.ContextVar("ApiZone", default=None)
        )
        self._local_utils: Optional["LocalUtils"] = local_utils
        self._tracing_count = 0
        self._closed_error: Optional[Exception] = None

    @property
    def local_utils(self) -> "LocalUtils":
        assert self._local_utils
        return self._local_utils

    def mark_as_remote(self) -> None:
        self.is_remote = True

    async def run_as_sync(self) -> None:
        self._is_sync = True
        await self.run()

    async def run(self) -> None:
        self._loop = asyncio.get_running_loop()
        self._root_object = RootChannelOwner(self)

        async def init() -> None:
            self.playwright_future.set_result(await self._root_object.initialize())

        await self._transport.connect()
        self._init_task = self._loop.create_task(init())
        await self._transport.run()

    def stop_sync(self) -> None:
        self._transport.request_stop()
        self._dispatcher_fiber.switch()
        self._loop.run_until_complete(self._transport.wait_until_stopped())
        self.cleanup()

    async def stop_async(self) -> None:
        self._transport.request_stop()
        await self._transport.wait_until_stopped()
        self.cleanup()

    def cleanup(self, cause: str = None) -> None:
        self._closed_error = TargetClosedError(cause) if cause else TargetClosedError()
        if self._init_task and not self._init_task.done():
            self._init_task.cancel()
        for ws_connection in self._child_ws_connections:
            ws_connection._transport.dispose()
        for callback in self._callbacks.values():
            # To prevent 'Future exception was never retrieved' we ignore all callbacks that are no_reply.
            if callback.no_reply:
                continue
            if callback.future.cancelled():
                continue
            callback.future.set_exception(self._closed_error)
        self._callbacks.clear()
        self.emit("close")

    def call_on_object_with_known_name(
        self, guid: str, callback: Callable[[ChannelOwner], None]
    ) -> None:
        self._waiting_for_object[guid] = callback

    def set_is_tracing(self, is_tracing: bool) -> None:
        if is_tracing:
            self._tracing_count += 1
        else:
            self._tracing_count -= 1

    def _send_message_to_server(
        self, object: ChannelOwner, method: str, params: Dict, no_reply: bool = False
    ) -> ProtocolCallback:
        if self._closed_error:
            raise self._closed_error
        if object._was_collected:
            raise Error(
                "The object has been collected to prevent unbounded heap growth."
            )
        self._last_id += 1
        id = self._last_id
        callback = ProtocolCallback(self._loop, no_reply=no_reply)
        task = asyncio.current_task(self._loop)
        callback.stack_trace = cast(
            traceback.StackSummary,
            getattr(task, "__pw_stack_trace__", traceback.extract_stack(limit=10)),
        )
        callback.no_reply = no_reply
        stack_trace_information = cast(ParsedStackTrace, self._api_zone.get())
        frames = stack_trace_information.get("frames", [])
        location = (
            {
                "file": frames[0]["file"],
                "line": frames[0]["line"],
                "column": frames[0]["column"],
            }
            if frames
            else None
        )
        metadata = {
            "wallTime": int(datetime.datetime.now().timestamp() * 1000),
            "apiName": stack_trace_information["apiName"],
            "internal": not stack_trace_information["apiName"],
        }
        if location:
            metadata["location"] = location  # type: ignore
        title = stack_trace_information["title"]
        if title:
            metadata["title"] = title
        message = {
            "id": id,
            "guid": object._guid,
            "method": method,
            "params": self._replace_channels_with_guids(params),
            "metadata": metadata,
        }
        if self._tracing_count > 0 and frames and object._guid != "localUtils":
            self.local_utils.add_stack_to_tracing_no_reply(id, frames)

        self._callbacks[id] = callback
        self._transport.send(message)

        return callback

    def dispatch(self, msg: ParsedMessagePayload) -> None:
        if self._closed_error:
            return
        id = msg.get("id")
        if id:
            callback = self._callbacks.pop(id)
            if callback.future.cancelled():
                return
            # No reply messages are used to e.g. waitForEventInfo(after) which returns exceptions on page close.
            # To prevent 'Future exception was never retrieved' we just ignore such messages.
            if callback.no_reply:
                return
            error = msg.get("error")
            if error and not msg.get("result"):
                parsed_error = parse_error(
                    error["error"], format_call_log(msg.get("log"))  # type: ignore
                )
                parsed_error._stack = "".join(callback.stack_trace.format())
                callback.future.set_exception(parsed_error)
            else:
                result = self._replace_guids_with_channels(msg.get("result"))
                callback.future.set_result(result)
            return

        guid = msg["guid"]
        method = msg["method"]
        params = msg.get("params")
        if method == "__create__":
            assert params
            parent = self._objects[guid]
            self._create_remote_object(
                parent, params["type"], params["guid"], params["initializer"]
            )
            return

        object = self._objects.get(guid)
        if not object:
            raise Exception(f'Cannot find object to "{method}": {guid}')

        if method == "__adopt__":
            child_guid = cast(Dict[str, str], params)["guid"]
            child = self._objects.get(child_guid)
            if not child:
                raise Exception(f"Unknown new child: {child_guid}")
            object._adopt(child)
            return

        if method == "__dispose__":
            assert isinstance(params, dict)
            self._objects[guid]._dispose(cast(Optional[str], params.get("reason")))
            return
        object = self._objects[guid]
        should_replace_guids_with_channels = "jsonPipe@" not in guid
        try:
            if self._is_sync:
                for listener in object._channel.listeners(method):
                    # Event handlers like route/locatorHandlerTriggered require us to perform async work.
                    # In order to report their potential errors to the user, we need to catch it and store it in the connection
                    def _done_callback(future: asyncio.Future) -> None:
                        exc = future.exception()
                        if exc:
                            self._on_event_listener_error(exc)

                    def _listener_with_error_handler_attached(params: Any) -> None:
                        potential_future = listener(params)
                        if asyncio.isfuture(potential_future):
                            potential_future.add_done_callback(_done_callback)

                    # Each event handler is a potentilly blocking context, create a fiber for each
                    # and switch to them in order, until they block inside and pass control to each
                    # other and then eventually back to dispatcher as listener functions return.
                    g = EventGreenlet(_listener_with_error_handler_attached)
                    if should_replace_guids_with_channels:
                        g.switch(self._replace_guids_with_channels(params))
                    else:
                        g.switch(params)
            else:
                if should_replace_guids_with_channels:
                    object._channel.emit(
                        method, self._replace_guids_with_channels(params)
                    )
                else:
                    object._channel.emit(method, params)
        except BaseException as exc:
            self._on_event_listener_error(exc)

    def _on_event_listener_error(self, exc: BaseException) -> None:
        print("Error occurred in event listener", file=sys.stderr)
        traceback.print_exception(type(exc), exc, exc.__traceback__, file=sys.stderr)
        # Save the error to throw at the next API call. This "replicates" unhandled rejection in Node.js.
        self._error = exc

    def _create_remote_object(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> ChannelOwner:
        initializer = self._replace_guids_with_channels(initializer)
        result = self._object_factory(parent, type, guid, initializer)
        if guid in self._waiting_for_object:
            self._waiting_for_object.pop(guid)(result)
        return result

    def _replace_channels_with_guids(
        self,
        payload: Any,
    ) -> Any:
        if payload is None:
            return payload
        if isinstance(payload, Path):
            return str(payload)
        if isinstance(payload, collections.abc.Sequence) and not isinstance(
            payload, str
        ):
            return list(map(self._replace_channels_with_guids, payload))
        if isinstance(payload, Channel):
            return dict(guid=payload._guid)
        if isinstance(payload, dict):
            result = {}
            for key, value in payload.items():
                result[key] = self._replace_channels_with_guids(value)
            return result
        return payload

    def _replace_guids_with_channels(self, payload: Any) -> Any:
        if payload is None:
            return payload
        if isinstance(payload, list):
            return list(map(self._replace_guids_with_channels, payload))
        if isinstance(payload, dict):
            if payload.get("guid") in self._objects:
                return self._objects[payload["guid"]]._channel
            result = {}
            for key, value in payload.items():
                result[key] = self._replace_guids_with_channels(value)
            return result
        return payload

    async def wrap_api_call(
        self, cb: Callable[[], Any], is_internal: bool = False, title: str = None
    ) -> Any:
        if self._api_zone.get():
            return await cb()
        task = asyncio.current_task(self._loop)
        st: List[inspect.FrameInfo] = getattr(
            task, "__pw_stack__", None
        ) or inspect.stack(0)

        parsed_st = _extract_stack_trace_information_from_stack(st, is_internal, title)
        self._api_zone.set(parsed_st)
        try:
            return await cb()
        except Exception as error:
            raise rewrite_error(error, f"{parsed_st['apiName']}: {error}") from None
        finally:
            self._api_zone.set(None)

    def wrap_api_call_sync(
        self, cb: Callable[[], Any], is_internal: bool = False, title: str = None
    ) -> Any:
        if self._api_zone.get():
            return cb()
        task = asyncio.current_task(self._loop)
        st: List[inspect.FrameInfo] = getattr(
            task, "__pw_stack__", None
        ) or inspect.stack(0)
        parsed_st = _extract_stack_trace_information_from_stack(st, is_internal, title)
        self._api_zone.set(parsed_st)
        try:
            return cb()
        except Exception as error:
            raise rewrite_error(error, f"{parsed_st['apiName']}: {error}") from None
        finally:
            self._api_zone.set(None)


def from_channel(channel: Channel) -> Any:
    return channel._object


def from_nullable_channel(channel: Optional[Channel]) -> Optional[Any]:
    return channel._object if channel else None


class StackFrame(TypedDict):
    file: str
    line: int
    column: int
    function: Optional[str]


class ParsedStackTrace(TypedDict):
    frames: List[StackFrame]
    apiName: Optional[str]
    title: Optional[str]


def _extract_stack_trace_information_from_stack(
    st: List[inspect.FrameInfo], is_internal: bool, title: str = None
) -> ParsedStackTrace:
    playwright_module_path = str(Path(playwright.__file__).parents[0])
    last_internal_api_name = ""
    api_name = ""
    parsed_frames: List[StackFrame] = []
    for frame in st:
        # Sync and Async implementations can have event handlers. When these are sync, they
        # get evaluated in the context of the event loop, so they contain the stack trace of when
        # the message was received. _impl_to_api_mapping is glue between the user-code and internal
        # code to translate impl classes to api classes. We want to ignore these frames.
        if playwright._impl._impl_to_api_mapping.__file__ == frame.filename:
            continue
        is_playwright_internal = frame.filename.startswith(playwright_module_path)

        method_name = ""
        if "self" in frame[0].f_locals:
            method_name = frame[0].f_locals["self"].__class__.__name__ + "."
        method_name += frame[0].f_code.co_name

        if not is_playwright_internal:
            parsed_frames.append(
                {
                    "file": frame.filename,
                    "line": frame.lineno,
                    "column": 0,
                    "function": method_name,
                }
            )
        if is_playwright_internal:
            last_internal_api_name = method_name
        elif last_internal_api_name:
            api_name = last_internal_api_name
            last_internal_api_name = ""
    if not api_name:
        api_name = last_internal_api_name

    return {
        "frames": parsed_frames,
        "apiName": "" if is_internal else api_name,
        "title": title,
    }


def _augment_params(
    params: Optional[Dict],
    timeout_calculator: Optional[Callable[[Optional[float]], float]],
) -> Dict:
    if params is None:
        params = {}
    if timeout_calculator:
        params["timeout"] = timeout_calculator(params.get("timeout"))
    return _filter_none(params)


def _filter_none(d: Mapping) -> Dict:
    result = {}
    for k, v in d.items():
        if v is None:
            continue
        result[k] = _filter_none(v) if isinstance(v, dict) else v
    return result


def format_call_log(log: Optional[List[str]]) -> str:
    if not log:
        return ""
    if len(list(filter(lambda x: x.strip(), log))) == 0:
        return ""
    return "\nCall log:\n" + "\n".join(log) + "\n"
