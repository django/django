# from __future__ import annotations

from datetime import datetime, timedelta
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Iterable,
    Mapping,
    Protocol,
    Type,
    TypeVar,
    Union,
)

if TYPE_CHECKING:
    from redis._parsers import Encoder
    from redis.event import EventDispatcherInterface


Number = Union[int, float]
EncodedT = Union[bytes, bytearray, memoryview]
DecodedT = Union[str, int, float]
EncodableT = Union[EncodedT, DecodedT]
AbsExpiryT = Union[int, datetime]
ExpiryT = Union[int, timedelta]
ZScoreBoundT = Union[float, str]  # str allows for the [ or ( prefix
BitfieldOffsetT = Union[int, str]  # str allows for #x syntax
_StringLikeT = Union[bytes, str, memoryview]
KeyT = _StringLikeT  # Main redis key space
PatternT = _StringLikeT  # Patterns matched against keys, fields etc
FieldT = EncodableT  # Fields within hash tables, streams and geo commands
KeysT = Union[KeyT, Iterable[KeyT]]
ResponseT = Union[Awaitable[Any], Any]
ChannelT = _StringLikeT
GroupT = _StringLikeT  # Consumer group
ConsumerT = _StringLikeT  # Consumer name
StreamIdT = Union[int, _StringLikeT]
ScriptTextT = _StringLikeT
TimeoutSecT = Union[int, float, _StringLikeT]
# Mapping is not covariant in the key type, which prevents
# Mapping[_StringLikeT, X] from accepting arguments of type Dict[str, X]. Using
# a TypeVar instead of a Union allows mappings with any of the permitted types
# to be passed. Care is needed if there is more than one such mapping in a
# type signature because they will all be required to be the same key type.
AnyKeyT = TypeVar("AnyKeyT", bytes, str, memoryview)
AnyFieldT = TypeVar("AnyFieldT", bytes, str, memoryview)
AnyChannelT = TypeVar("AnyChannelT", bytes, str, memoryview)

ExceptionMappingT = Mapping[str, Union[Type[Exception], Mapping[str, Type[Exception]]]]


class CommandsProtocol(Protocol):
    _event_dispatcher: "EventDispatcherInterface"

    def execute_command(self, *args, **options) -> ResponseT: ...


class ClusterCommandsProtocol(CommandsProtocol):
    encoder: "Encoder"
