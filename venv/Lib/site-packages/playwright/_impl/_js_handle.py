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
import collections.abc
import datetime
import math
import struct
import traceback
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union
from urllib.parse import ParseResult, urlparse, urlunparse

from playwright._impl._connection import Channel, ChannelOwner, from_channel
from playwright._impl._errors import Error, is_target_closed_error
from playwright._impl._map import Map

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl._element_handle import ElementHandle


Serializable = Any


class VisitorInfo:
    visited: Map[Any, int]
    last_id: int

    def __init__(self) -> None:
        self.visited = Map()
        self.last_id = 0

    def visit(self, obj: Any) -> int:
        assert obj not in self.visited
        self.last_id += 1
        self.visited[obj] = self.last_id
        return self.last_id


class JSHandle(ChannelOwner):
    def __init__(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        self._preview = self._initializer["preview"]
        self._channel.on(
            "previewUpdated", lambda params: self._on_preview_updated(params["preview"])
        )

    def __repr__(self) -> str:
        return f"<JSHandle preview={self._preview}>"

    def __str__(self) -> str:
        return self._preview

    def _on_preview_updated(self, preview: str) -> None:
        self._preview = preview

    async def evaluate(self, expression: str, arg: Serializable = None) -> Any:
        return parse_result(
            await self._channel.send(
                "evaluateExpression",
                None,
                dict(
                    expression=expression,
                    arg=serialize_argument(arg),
                ),
            )
        )

    async def evaluate_handle(
        self, expression: str, arg: Serializable = None
    ) -> "JSHandle":
        return from_channel(
            await self._channel.send(
                "evaluateExpressionHandle",
                None,
                dict(
                    expression=expression,
                    arg=serialize_argument(arg),
                ),
            )
        )

    async def get_property(self, propertyName: str) -> "JSHandle":
        return from_channel(
            await self._channel.send("getProperty", None, dict(name=propertyName))
        )

    async def get_properties(self) -> Dict[str, "JSHandle"]:
        return {
            prop["name"]: from_channel(prop["value"])
            for prop in await self._channel.send(
                "getPropertyList",
                None,
            )
        }

    def as_element(self) -> Optional["ElementHandle"]:
        return None

    async def dispose(self) -> None:
        try:
            await self._channel.send(
                "dispose",
                None,
            )
        except Exception as e:
            if not is_target_closed_error(e):
                raise e

    async def json_value(self) -> Any:
        return parse_result(
            await self._channel.send(
                "jsonValue",
                None,
            )
        )


def serialize_value(
    value: Any, handles: List[Channel], visitor_info: Optional[VisitorInfo] = None
) -> Any:
    if visitor_info is None:
        visitor_info = VisitorInfo()
    if isinstance(value, JSHandle):
        h = len(handles)
        handles.append(value._channel)
        return dict(h=h)
    if value is None:
        return dict(v="null")
    if isinstance(value, float):
        if value == float("inf"):
            return dict(v="Infinity")
        if value == float("-inf"):
            return dict(v="-Infinity")
        if value == float("-0"):
            return dict(v="-0")
        if math.isnan(value):
            return dict(v="NaN")
    if isinstance(value, datetime.datetime):
        # Node.js Date objects are always in UTC.
        return {
            "d": datetime.datetime.strftime(
                value.astimezone(datetime.timezone.utc), "%Y-%m-%dT%H:%M:%S.%fZ"
            )
        }
    if isinstance(value, Exception):
        return {
            "e": {
                "m": str(value),
                "n": (
                    (value.name or "")
                    if isinstance(value, Error)
                    else value.__class__.__name__
                ),
                "s": (
                    (value.stack or "")
                    if isinstance(value, Error)
                    else "".join(
                        traceback.format_exception(type(value), value=value, tb=None)
                    )
                ),
            }
        }
    if isinstance(value, bool):
        return {"b": value}
    if isinstance(value, (int, float)):
        return {"n": value}
    if isinstance(value, str):
        return {"s": value}
    if isinstance(value, ParseResult):
        return {"u": urlunparse(value)}

    if value in visitor_info.visited:
        return dict(ref=visitor_info.visited[value])

    if isinstance(value, collections.abc.Sequence) and not isinstance(value, str):
        id = visitor_info.visit(value)
        a = []
        for e in value:
            a.append(serialize_value(e, handles, visitor_info))
        return dict(a=a, id=id)

    if isinstance(value, dict):
        id = visitor_info.visit(value)
        o = []
        for name in value:
            o.append(
                {"k": name, "v": serialize_value(value[name], handles, visitor_info)}
            )
        return dict(o=o, id=id)
    return dict(v="undefined")


def serialize_argument(arg: Serializable = None) -> Any:
    handles: List[Channel] = []
    value = serialize_value(arg, handles)
    return dict(value=value, handles=handles)


def parse_value(value: Any, refs: Optional[Dict[int, Any]] = None) -> Any:
    if refs is None:
        refs = {}
    if value is None:
        return None
    if isinstance(value, dict):
        if "ref" in value:
            return refs[value["ref"]]

        if "v" in value:
            v = value["v"]
            if v == "Infinity":
                return float("inf")
            if v == "-Infinity":
                return float("-inf")
            if v == "-0":
                return float("-0")
            if v == "NaN":
                return float("nan")
            if v == "undefined":
                return None
            if v == "null":
                return None
            return v

        if "u" in value:
            return urlparse(value["u"])

        if "bi" in value:
            return int(value["bi"])

        if "e" in value:
            error = Error(value["e"]["m"])
            error._name = value["e"]["n"]
            error._stack = value["e"]["s"]
            return error

        if "a" in value:
            a: List = []
            refs[value["id"]] = a
            for e in value["a"]:
                a.append(parse_value(e, refs))
            return a

        if "d" in value:
            # Node.js Date objects are always in UTC.
            return datetime.datetime.strptime(
                value["d"], "%Y-%m-%dT%H:%M:%S.%fZ"
            ).replace(tzinfo=datetime.timezone.utc)

        if "o" in value:
            o: Dict = {}
            refs[value["id"]] = o
            for e in value["o"]:
                o[e["k"]] = parse_value(e["v"], refs)
            return o

        if "n" in value:
            return value["n"]

        if "s" in value:
            return value["s"]

        if "b" in value:
            return value["b"]

        if "ta" in value:
            encoded_bytes = value["ta"]["b"]
            decoded_bytes = base64.b64decode(encoded_bytes)
            array_type = value["ta"]["k"]
            if array_type == "i8":
                word_size = 1
                fmt = "b"
            elif array_type == "ui8" or array_type == "ui8c":
                word_size = 1
                fmt = "B"
            elif array_type == "i16":
                word_size = 2
                fmt = "h"
            elif array_type == "ui16":
                word_size = 2
                fmt = "H"
            elif array_type == "i32":
                word_size = 4
                fmt = "i"
            elif array_type == "ui32":
                word_size = 4
                fmt = "I"
            elif array_type == "f32":
                word_size = 4
                fmt = "f"
            elif array_type == "f64":
                word_size = 8
                fmt = "d"
            elif array_type == "bi64":
                word_size = 8
                fmt = "q"
            elif array_type == "bui64":
                word_size = 8
                fmt = "Q"
            else:
                raise ValueError(f"Unsupported array type: {array_type}")

            byte_len = len(decoded_bytes)
            if byte_len % word_size != 0:
                raise ValueError(
                    f"Decoded bytes length {byte_len} is not a multiple of word size {word_size}"
                )

            if byte_len == 0:
                return []
            array_len = byte_len // word_size
            # "<" denotes little-endian
            format_string = f"<{array_len}{fmt}"
            return list(struct.unpack(format_string, decoded_bytes))
    return value


def parse_result(result: Any) -> Any:
    return parse_value(result)


def add_source_url_to_script(source: str, path: Union[str, Path]) -> str:
    return source + "\n//# sourceURL=" + str(path).replace("\n", "")
