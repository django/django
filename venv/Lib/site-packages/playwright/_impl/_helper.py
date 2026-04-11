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
import os
import re
import time
import traceback
from pathlib import Path
from types import TracebackType
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Literal,
    Optional,
    Pattern,
    Set,
    Tuple,
    TypedDict,
    TypeVar,
    Union,
    cast,
)
from urllib.parse import ParseResult, urljoin, urlparse, urlunparse

from playwright._impl._api_structures import NameValue
from playwright._impl._errors import (
    Error,
    TargetClosedError,
    TimeoutError,
    is_target_closed_error,
    rewrite_error,
)
from playwright._impl._glob import glob_to_regex_pattern
from playwright._impl._greenlets import RouteGreenlet
from playwright._impl._str_utils import escape_regex_flags

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl._api_structures import HeadersArray
    from playwright._impl._network import Request, Response, Route, WebSocketRoute

URLMatch = Union[str, Pattern[str], Callable[[str], bool]]
URLMatchRequest = Union[str, Pattern[str], Callable[["Request"], bool]]
URLMatchResponse = Union[str, Pattern[str], Callable[["Response"], bool]]
RouteHandlerCallback = Union[
    Callable[["Route"], Any], Callable[["Route", "Request"], Any]
]
WebSocketRouteHandlerCallback = Callable[["WebSocketRoute"], Any]

ColorScheme = Literal["dark", "light", "no-preference", "null"]
ForcedColors = Literal["active", "none", "null"]
Contrast = Literal["more", "no-preference", "null"]
ReducedMotion = Literal["no-preference", "null", "reduce"]
DocumentLoadState = Literal["commit", "domcontentloaded", "load", "networkidle"]
KeyboardModifier = Literal["Alt", "Control", "ControlOrMeta", "Meta", "Shift"]
MouseButton = Literal["left", "middle", "right"]
ServiceWorkersPolicy = Literal["allow", "block"]
HarMode = Literal["full", "minimal"]
HarContentPolicy = Literal["attach", "embed", "omit"]
RouteFromHarNotFoundPolicy = Literal["abort", "fallback"]


class ErrorPayload(TypedDict, total=False):
    message: str
    name: str
    stack: str
    value: Optional[Any]


class HarRecordingMetadata(TypedDict, total=False):
    path: str
    content: Optional[HarContentPolicy]


def prepare_record_har_options(params: Dict) -> Dict[str, Any]:
    out_params: Dict[str, Any] = {"path": str(params["recordHarPath"])}
    if "recordHarUrlFilter" in params:
        opt = params["recordHarUrlFilter"]
        if isinstance(opt, str):
            out_params["urlGlob"] = opt
        if isinstance(opt, Pattern):
            out_params["urlRegexSource"] = opt.pattern
            out_params["urlRegexFlags"] = escape_regex_flags(opt)
        del params["recordHarUrlFilter"]
    if "recordHarMode" in params:
        out_params["mode"] = params["recordHarMode"]
        del params["recordHarMode"]

    new_content_api = None
    old_content_api = None
    if "recordHarContent" in params:
        new_content_api = params["recordHarContent"]
        del params["recordHarContent"]
    if "recordHarOmitContent" in params:
        old_content_api = params["recordHarOmitContent"]
        del params["recordHarOmitContent"]
    content = new_content_api or ("omit" if old_content_api else None)
    if content:
        out_params["content"] = content

    return out_params


class ParsedMessageParams(TypedDict):
    type: str
    guid: str
    initializer: Dict


class ParsedMessagePayload(TypedDict, total=False):
    id: int
    guid: str
    method: str
    params: ParsedMessageParams
    result: Any
    error: ErrorPayload


class Document(TypedDict):
    request: Optional[Any]


class FrameNavigatedEvent(TypedDict):
    url: str
    name: str
    newDocument: Optional[Document]
    error: Optional[str]


Env = Dict[str, Union[str, float, bool]]


def url_matches(
    base_url: Optional[str],
    url_string: str,
    match: Optional[URLMatch],
    websocket_url: bool = None,
) -> bool:
    if not match:
        return True
    if isinstance(match, str):
        match = re.compile(
            resolve_glob_to_regex_pattern(base_url, match, websocket_url)
        )
    if isinstance(match, Pattern):
        return bool(match.search(url_string))
    return match(url_string)


def resolve_glob_to_regex_pattern(
    base_url: Optional[str], glob: str, websocket_url: bool = None
) -> str:
    if websocket_url:
        base_url = to_websocket_base_url(base_url)
    glob = resolve_glob_base(base_url, glob)
    return glob_to_regex_pattern(glob)


def to_websocket_base_url(base_url: Optional[str]) -> Optional[str]:
    if base_url is not None and re.match(r"^https?://", base_url):
        base_url = re.sub(r"^http", "ws", base_url)
    return base_url


def resolve_glob_base(base_url: Optional[str], match: str) -> str:
    if match[0] == "*":
        return match

    token_map: Dict[str, str] = {}

    def map_token(original: str, replacement: str) -> str:
        if len(original) == 0:
            return ""
        token_map[replacement] = original
        return replacement

    # Escaped `\\?` behaves the same as `?` in our glob patterns.
    match = match.replace(r"\\?", "?")
    # Special case about: URLs as they are not relative to base_url
    if (
        match.startswith("about:")
        or match.startswith("data:")
        or match.startswith("chrome:")
        or match.startswith("edge:")
        or match.startswith("file:")
    ):
        # about: and data: URLs are not relative to base_url, so we return them as is.
        return match
    # Glob symbols may be escaped in the URL and some of them such as ? affect resolution,
    # so we replace them with safe components first.
    processed_parts = []
    for index, token in enumerate(match.split("/")):
        if token in (".", "..", ""):
            processed_parts.append(token)
            continue
        # Handle special case of http*://, note that the new schema has to be
        # a web schema so that slashes are properly inserted after domain.
        if index == 0 and token.endswith(":"):
            # Replace any pattern with http:
            if "*" in token or "{" in token:
                processed_parts.append(map_token(token, "http:"))
            else:
                # Preserve explicit schema as is as it may affect trailing slashes after domain.
                processed_parts.append(token)
            continue
        question_index = token.find("?")
        if question_index == -1:
            processed_parts.append(map_token(token, f"$_{index}_$"))
        else:
            new_prefix = map_token(token[:question_index], f"$_{index}_$")
            new_suffix = map_token(token[question_index:], f"?$_{index}_$")
            processed_parts.append(new_prefix + new_suffix)

    relative_path = "/".join(processed_parts)
    resolved, case_insensitive_part = resolve_base_url(base_url, relative_path)

    for token, original in token_map.items():
        normalize = case_insensitive_part and token in case_insensitive_part
        resolved = resolved.replace(
            token, original.lower() if normalize else original, 1
        )

    return resolved


def resolve_base_url(
    base_url: Optional[str], given_url: str
) -> Tuple[str, Optional[str]]:
    try:
        url = nodelike_urlparse(
            urljoin(base_url if base_url is not None else "", given_url)
        )
        resolved = urlunparse(url)
        # Schema and domain are case-insensitive.
        hostname_port = (
            url.hostname or ""
        )  # can't use parsed.netloc because it includes userinfo (username:password)
        if url.port:
            hostname_port += f":{url.port}"
        case_insensitive_prefix = f"{url.scheme}://{hostname_port}"
        return resolved, case_insensitive_prefix
    except Exception:
        return given_url, None


def nodelike_urlparse(url: str) -> ParseResult:
    parsed = urlparse(url, allow_fragments=True)

    # https://url.spec.whatwg.org/#special-scheme
    is_special_url = parsed.scheme in ["http", "https", "ws", "wss", "ftp", "file"]
    if is_special_url:
        # special urls have a list path, list paths are serialized as follows: https://url.spec.whatwg.org/#url-path-serializer
        # urllib diverges, so we patch it here
        if parsed.path == "":
            parsed = parsed._replace(path="/")

    return parsed


class HarLookupResult(TypedDict, total=False):
    action: Literal["error", "redirect", "fulfill", "noentry"]
    message: Optional[str]
    redirectURL: Optional[str]
    status: Optional[int]
    headers: Optional["HeadersArray"]
    body: Optional[str]


DEFAULT_PLAYWRIGHT_TIMEOUT_IN_MILLISECONDS = 30000
DEFAULT_PLAYWRIGHT_LAUNCH_TIMEOUT_IN_MILLISECONDS = 180000
PLAYWRIGHT_MAX_DEADLINE = 2147483647  # 2^31-1


class TimeoutSettings:

    @staticmethod
    def launch_timeout(timeout: Optional[float] = None) -> float:
        return (
            timeout
            if timeout is not None
            else DEFAULT_PLAYWRIGHT_LAUNCH_TIMEOUT_IN_MILLISECONDS
        )

    def __init__(self, parent: Optional["TimeoutSettings"]) -> None:
        self._parent = parent
        self._default_timeout: Optional[float] = None
        self._default_navigation_timeout: Optional[float] = None

    def set_default_timeout(self, timeout: Optional[float]) -> None:
        self._default_timeout = timeout

    def timeout(self, timeout: float = None) -> float:
        if timeout is not None:
            return timeout
        if self._default_timeout is not None:
            return self._default_timeout
        if self._parent:
            return self._parent.timeout()
        return DEFAULT_PLAYWRIGHT_TIMEOUT_IN_MILLISECONDS

    def set_default_navigation_timeout(
        self, navigation_timeout: Optional[float]
    ) -> None:
        self._default_navigation_timeout = navigation_timeout

    def default_navigation_timeout(self) -> Optional[float]:
        return self._default_navigation_timeout

    def default_timeout(self) -> Optional[float]:
        return self._default_timeout

    def navigation_timeout(self, timeout: float = None) -> float:
        if timeout is not None:
            return timeout
        if self._default_navigation_timeout is not None:
            return self._default_navigation_timeout
        if self._default_timeout is not None:
            return self._default_timeout
        if self._parent:
            return self._parent.navigation_timeout()
        return DEFAULT_PLAYWRIGHT_TIMEOUT_IN_MILLISECONDS


def serialize_error(ex: Exception, tb: Optional[TracebackType]) -> ErrorPayload:
    return ErrorPayload(
        message=str(ex), name="Error", stack="".join(traceback.format_tb(tb))
    )


def parse_error(error: ErrorPayload, log: Optional[str] = None) -> Error:
    base_error_class = Error
    if error.get("name") == "TimeoutError":
        base_error_class = TimeoutError
    if error.get("name") == "TargetClosedError":
        base_error_class = TargetClosedError
    if not log:
        log = ""
    exc = base_error_class(patch_error_message(error["message"]) + log)
    exc._name = error["name"]
    exc._stack = error["stack"]
    return exc


def patch_error_message(message: str) -> str:
    match = re.match(r"(\w+)(: expected .*)", message)
    if match:
        message = to_snake_case(match.group(1)) + match.group(2)
    message = message.replace(
        "Pass { acceptDownloads: true }", "Pass 'accept_downloads=True'"
    )
    return message


def locals_to_params(args: Dict) -> Dict:
    copy = {}
    for key in args:
        if key == "self":
            continue
        if args[key] is not None:
            copy[key] = (
                args[key]
                if not isinstance(args[key], Dict)
                else locals_to_params(args[key])
            )
    return copy


def monotonic_time() -> int:
    return math.floor(time.monotonic() * 1000)


class RouteHandlerInvocation:
    complete: "asyncio.Future"
    route: "Route"

    def __init__(self, complete: "asyncio.Future", route: "Route") -> None:
        self.complete = complete
        self.route = route


class RouteHandler:
    def __init__(
        self,
        base_url: Optional[str],
        url: URLMatch,
        handler: RouteHandlerCallback,
        is_sync: bool,
        times: Optional[int] = None,
    ):
        self._base_url = base_url
        self.url = url
        self.handler = handler
        self._times = times if times else math.inf
        self._handled_count = 0
        self._is_sync = is_sync
        self._ignore_exception = False
        self._active_invocations: Set[RouteHandlerInvocation] = set()

    def matches(self, request_url: str) -> bool:
        return url_matches(self._base_url, request_url, self.url)

    async def handle(self, route: "Route") -> bool:
        handler_invocation = RouteHandlerInvocation(
            asyncio.get_running_loop().create_future(), route
        )
        self._active_invocations.add(handler_invocation)
        try:
            return await self._handle_internal(route)
        except Exception as e:
            # If the handler was stopped (without waiting for completion), we ignore all exceptions.
            if self._ignore_exception:
                return False
            if is_target_closed_error(e):
                # We are failing in the handler because the target has closed.
                # Give user a hint!
                optional_async_prefix = "await " if not self._is_sync else ""
                raise rewrite_error(
                    e,
                    f"\"{str(e)}\" while running route callback.\nConsider awaiting `{optional_async_prefix}page.unroute_all(behavior='ignoreErrors')`\nbefore the end of the test to ignore remaining routes in flight.",
                )
            raise e
        finally:
            handler_invocation.complete.set_result(None)
            self._active_invocations.remove(handler_invocation)

    async def _handle_internal(self, route: "Route") -> bool:
        handled_future = route._start_handling()

        self._handled_count += 1
        if self._is_sync:
            handler_finished_future = route._loop.create_future()

            def _handler() -> None:
                try:
                    self.handler(route, route.request)  # type: ignore
                    handler_finished_future.set_result(None)
                except Exception as e:
                    handler_finished_future.set_exception(e)

            # As with event handlers, each route handler is a potentially blocking context
            # so it needs a fiber.
            g = RouteGreenlet(_handler)
            g.switch()
            await handler_finished_future
        else:
            coro_or_future = self.handler(route, route.request)  # type: ignore
            if coro_or_future:
                # separate task so that we get a proper stack trace for exceptions / tracing api_name extraction
                await asyncio.ensure_future(coro_or_future)
        return await handled_future

    async def stop(self, behavior: Literal["ignoreErrors", "wait"]) -> None:
        # When a handler is manually unrouted or its page/context is closed we either
        # - wait for the current handler invocations to finish
        # - or do not wait, if the user opted out of it, but swallow all exceptions
        #   that happen after the unroute/close.
        if behavior == "ignoreErrors":
            self._ignore_exception = True
        else:
            tasks = []
            for activation in self._active_invocations:
                if not activation.route._did_throw:
                    tasks.append(activation.complete)
            await asyncio.gather(*tasks)

    @property
    def will_expire(self) -> bool:
        return self._handled_count + 1 >= self._times

    @staticmethod
    def prepare_interception_patterns(
        handlers: List["RouteHandler"],
    ) -> List[Dict[str, str]]:
        patterns = []
        all = False
        for handler in handlers:
            if isinstance(handler.url, str):
                patterns.append({"glob": handler.url})
            elif isinstance(handler.url, re.Pattern):
                patterns.append(
                    {
                        "regexSource": handler.url.pattern,
                        "regexFlags": escape_regex_flags(handler.url),
                    }
                )
            else:
                all = True
        if all:
            return [{"glob": "**/*"}]
        return patterns


to_snake_case_regex = re.compile("((?<=[a-z0-9])[A-Z]|(?!^)[A-Z](?=[a-z]))")


def to_snake_case(name: str) -> str:
    return to_snake_case_regex.sub(r"_\1", name).lower()


def make_dirs_for_file(path: Union[Path, str]) -> None:
    if not os.path.isabs(path):
        path = Path.cwd() / path
    os.makedirs(os.path.dirname(path), exist_ok=True)


async def async_writefile(file: Union[str, Path], data: Union[str, bytes]) -> None:
    def inner() -> None:
        with open(file, "w" if isinstance(data, str) else "wb") as fh:
            fh.write(data)

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, inner)


async def async_readfile(file: Union[str, Path]) -> bytes:
    def inner() -> bytes:
        with open(file, "rb") as fh:
            return fh.read()

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, inner)


T = TypeVar("T")


def to_impl(obj: T) -> T:
    if hasattr(obj, "_impl_obj"):
        return cast(Any, obj)._impl_obj
    return obj


def object_to_array(obj: Optional[Dict]) -> Optional[List[NameValue]]:
    if not obj:
        return None
    result = []
    for key, value in obj.items():
        result.append(NameValue(name=key, value=str(value)))
    return result


def is_file_payload(value: Optional[Any]) -> bool:
    return (
        isinstance(value, dict)
        and "name" in value
        and "mimeType" in value
        and "buffer" in value
    )


TEXTUAL_MIME_TYPE = re.compile(
    r"^(text\/.*?|application\/(json|(x-)?javascript|xml.*?|ecmascript|graphql|x-www-form-urlencoded)|image\/svg(\+xml)?|application\/.*?(\+json|\+xml))(;\s*charset=.*)?$"
)


def is_textual_mime_type(mime_type: str) -> bool:
    return bool(TEXTUAL_MIME_TYPE.match(mime_type))
