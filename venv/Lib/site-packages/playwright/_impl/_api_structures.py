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

from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Sequence, TypedDict, Union

# These are the structures that we like keeping in a JSON form for their potential
# reuse between SDKs / services. They are public and are a part of the
# stable API.

# Explicitly mark optional params as such for the documentation
# If there is at least one optional param, set total=False for better mypy handling.


class Cookie(TypedDict, total=False):
    name: str
    value: str
    domain: str
    path: str
    expires: float
    httpOnly: bool
    secure: bool
    sameSite: Literal["Lax", "None", "Strict"]
    partitionKey: Optional[str]


class StorageStateCookie(TypedDict, total=False):
    name: str
    value: str
    domain: str
    path: str
    expires: float
    httpOnly: bool
    secure: bool
    sameSite: Literal["Lax", "None", "Strict"]


# TODO: We are waiting for PEP705 so SetCookieParam can be readonly and matches Cookie.
class SetCookieParam(TypedDict, total=False):
    name: str
    value: str
    url: Optional[str]
    domain: Optional[str]
    path: Optional[str]
    expires: Optional[float]
    httpOnly: Optional[bool]
    secure: Optional[bool]
    sameSite: Optional[Literal["Lax", "None", "Strict"]]
    partitionKey: Optional[str]


class FloatRect(TypedDict):
    x: float
    y: float
    width: float
    height: float


class Geolocation(TypedDict, total=False):
    latitude: float
    longitude: float
    accuracy: Optional[float]


class HttpCredentials(TypedDict, total=False):
    username: str
    password: str
    origin: Optional[str]
    send: Optional[Literal["always", "unauthorized"]]


class LocalStorageEntry(TypedDict):
    name: str
    value: str


class OriginState(TypedDict):
    origin: str
    localStorage: List[LocalStorageEntry]


class PdfMargins(TypedDict, total=False):
    top: Optional[Union[str, float]]
    right: Optional[Union[str, float]]
    bottom: Optional[Union[str, float]]
    left: Optional[Union[str, float]]


class Position(TypedDict):
    x: float
    y: float


class ProxySettings(TypedDict, total=False):
    server: str
    bypass: Optional[str]
    username: Optional[str]
    password: Optional[str]


class StorageState(TypedDict, total=False):
    cookies: List[StorageStateCookie]
    origins: List[OriginState]


class ClientCertificate(TypedDict, total=False):
    origin: str
    certPath: Optional[Union[str, Path]]
    cert: Optional[bytes]
    keyPath: Optional[Union[str, Path]]
    key: Optional[bytes]
    pfxPath: Optional[Union[str, Path]]
    pfx: Optional[bytes]
    passphrase: Optional[str]


class ResourceTiming(TypedDict):
    startTime: float
    domainLookupStart: float
    domainLookupEnd: float
    connectStart: float
    secureConnectionStart: float
    connectEnd: float
    requestStart: float
    responseStart: float
    responseEnd: float


class RequestSizes(TypedDict):
    requestBodySize: int
    requestHeadersSize: int
    responseBodySize: int
    responseHeadersSize: int


class ViewportSize(TypedDict):
    width: int
    height: int


class SourceLocation(TypedDict):
    url: str
    lineNumber: int
    columnNumber: int


class FilePayload(TypedDict):
    name: str
    mimeType: str
    buffer: bytes


class RemoteAddr(TypedDict):
    ipAddress: str
    port: int


class SecurityDetails(TypedDict):
    issuer: Optional[str]
    protocol: Optional[str]
    subjectName: Optional[str]
    validFrom: Optional[float]
    validTo: Optional[float]


class NameValue(TypedDict):
    name: str
    value: str


HeadersArray = List[NameValue]
Headers = Dict[str, str]


class ServerFilePayload(TypedDict):
    name: str
    mimeType: str
    buffer: str


class FormField(TypedDict, total=False):
    name: str
    value: Optional[str]
    file: Optional[ServerFilePayload]


class ExpectedTextValue(TypedDict, total=False):
    string: str
    regexSource: str
    regexFlags: str
    matchSubstring: bool
    normalizeWhiteSpace: bool
    ignoreCase: Optional[bool]


class FrameExpectOptions(TypedDict, total=False):
    expressionArg: Any
    expectedText: Optional[Sequence[ExpectedTextValue]]
    expectedNumber: Optional[float]
    expectedValue: Optional[Any]
    useInnerText: Optional[bool]
    isNot: bool
    timeout: Optional[float]


class FrameExpectResult(TypedDict):
    matches: bool
    received: Any
    log: List[str]
    errorMessage: Optional[str]


AriaRole = Literal[
    "alert",
    "alertdialog",
    "application",
    "article",
    "banner",
    "blockquote",
    "button",
    "caption",
    "cell",
    "checkbox",
    "code",
    "columnheader",
    "combobox",
    "complementary",
    "contentinfo",
    "definition",
    "deletion",
    "dialog",
    "directory",
    "document",
    "emphasis",
    "feed",
    "figure",
    "form",
    "generic",
    "grid",
    "gridcell",
    "group",
    "heading",
    "img",
    "insertion",
    "link",
    "list",
    "listbox",
    "listitem",
    "log",
    "main",
    "marquee",
    "math",
    "menu",
    "menubar",
    "menuitem",
    "menuitemcheckbox",
    "menuitemradio",
    "meter",
    "navigation",
    "none",
    "note",
    "option",
    "paragraph",
    "presentation",
    "progressbar",
    "radio",
    "radiogroup",
    "region",
    "row",
    "rowgroup",
    "rowheader",
    "scrollbar",
    "search",
    "searchbox",
    "separator",
    "slider",
    "spinbutton",
    "status",
    "strong",
    "subscript",
    "superscript",
    "switch",
    "tab",
    "table",
    "tablist",
    "tabpanel",
    "term",
    "textbox",
    "time",
    "timer",
    "toolbar",
    "tooltip",
    "tree",
    "treegrid",
    "treeitem",
]


class TracingGroupLocation(TypedDict):
    file: str
    line: Optional[int]
    column: Optional[int]
