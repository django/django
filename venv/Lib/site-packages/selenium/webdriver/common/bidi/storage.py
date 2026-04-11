# Licensed to the Software Freedom Conservancy (SFC) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The SFC licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from selenium.webdriver.common.bidi.common import command_builder

if TYPE_CHECKING:
    from selenium.webdriver.remote.websocket_connection import WebSocketConnection


class SameSite:
    """Represents the possible same site values for cookies."""

    STRICT = "strict"
    LAX = "lax"
    NONE = "none"
    DEFAULT = "default"


class BytesValue:
    """Represents a bytes value."""

    TYPE_BASE64 = "base64"
    TYPE_STRING = "string"

    def __init__(self, type: str, value: str):
        self.type = type
        self.value = value

    def to_dict(self) -> dict[str, str]:
        """Converts the BytesValue to a dictionary.

        Returns:
            A dictionary representation of the BytesValue.
        """
        return {"type": self.type, "value": self.value}


class Cookie:
    """Represents a cookie."""

    def __init__(
        self,
        name: str,
        value: BytesValue,
        domain: str,
        path: str | None = None,
        size: int | None = None,
        http_only: bool | None = None,
        secure: bool | None = None,
        same_site: str | None = None,
        expiry: int | None = None,
    ):
        self.name = name
        self.value = value
        self.domain = domain
        self.path = path
        self.size = size
        self.http_only = http_only
        self.secure = secure
        self.same_site = same_site
        self.expiry = expiry

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Cookie:
        """Creates a Cookie instance from a dictionary.

        Args:
            data: A dictionary containing the cookie information.

        Returns:
            A new instance of Cookie.
        """
        # Validation for empty strings
        name = data.get("name")
        if not name:
            raise ValueError("name is required and cannot be empty")
        domain = data.get("domain")
        if not domain:
            raise ValueError("domain is required and cannot be empty")

        value = BytesValue(data.get("value", {}).get("type"), data.get("value", {}).get("value"))
        return cls(
            name=str(name),
            value=value,
            domain=str(domain),
            path=data.get("path"),
            size=data.get("size"),
            http_only=data.get("httpOnly"),
            secure=data.get("secure"),
            same_site=data.get("sameSite"),
            expiry=data.get("expiry"),
        )


class CookieFilter:
    """Represents a filter for cookies."""

    def __init__(
        self,
        name: str | None = None,
        value: BytesValue | None = None,
        domain: str | None = None,
        path: str | None = None,
        size: int | None = None,
        http_only: bool | None = None,
        secure: bool | None = None,
        same_site: str | None = None,
        expiry: int | None = None,
    ):
        self.name = name
        self.value = value
        self.domain = domain
        self.path = path
        self.size = size
        self.http_only = http_only
        self.secure = secure
        self.same_site = same_site
        self.expiry = expiry

    def to_dict(self) -> dict[str, Any]:
        """Converts the CookieFilter to a dictionary.

        Returns:
            A dictionary representation of the CookieFilter.
        """
        result: dict[str, Any] = {}
        if self.name is not None:
            result["name"] = self.name
        if self.value is not None:
            result["value"] = self.value.to_dict()
        if self.domain is not None:
            result["domain"] = self.domain
        if self.path is not None:
            result["path"] = self.path
        if self.size is not None:
            result["size"] = self.size
        if self.http_only is not None:
            result["httpOnly"] = self.http_only
        if self.secure is not None:
            result["secure"] = self.secure
        if self.same_site is not None:
            result["sameSite"] = self.same_site
        if self.expiry is not None:
            result["expiry"] = self.expiry
        return result


class PartitionKey:
    """Represents a storage partition key."""

    def __init__(self, user_context: str | None = None, source_origin: str | None = None):
        self.user_context = user_context
        self.source_origin = source_origin

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PartitionKey:
        """Creates a PartitionKey instance from a dictionary.

        Args:
            data: A dictionary containing the partition key information.

        Returns:
            A new instance of PartitionKey.
        """
        return cls(
            user_context=data.get("userContext"),
            source_origin=data.get("sourceOrigin"),
        )


class BrowsingContextPartitionDescriptor:
    """Represents a browsing context partition descriptor."""

    def __init__(self, context: str):
        self.type = "context"
        self.context = context

    def to_dict(self) -> dict[str, str]:
        """Converts the BrowsingContextPartitionDescriptor to a dictionary.

        Returns:
            Dict: A dictionary representation of the BrowsingContextPartitionDescriptor.
        """
        return {"type": self.type, "context": self.context}


class StorageKeyPartitionDescriptor:
    """Represents a storage key partition descriptor."""

    def __init__(self, user_context: str | None = None, source_origin: str | None = None):
        self.type = "storageKey"
        self.user_context = user_context
        self.source_origin = source_origin

    def to_dict(self) -> dict[str, str]:
        """Converts the StorageKeyPartitionDescriptor to a dictionary.

        Returns:
            Dict: A dictionary representation of the StorageKeyPartitionDescriptor.
        """
        result = {"type": self.type}
        if self.user_context is not None:
            result["userContext"] = self.user_context
        if self.source_origin is not None:
            result["sourceOrigin"] = self.source_origin
        return result


class PartialCookie:
    """Represents a partial cookie for setting."""

    def __init__(
        self,
        name: str,
        value: BytesValue,
        domain: str,
        path: str | None = None,
        http_only: bool | None = None,
        secure: bool | None = None,
        same_site: str | None = None,
        expiry: int | None = None,
    ):
        self.name = name
        self.value = value
        self.domain = domain
        self.path = path
        self.http_only = http_only
        self.secure = secure
        self.same_site = same_site
        self.expiry = expiry

    def to_dict(self) -> dict[str, Any]:
        """Converts the PartialCookie to a dictionary.

        Returns:
        -------
            Dict: A dictionary representation of the PartialCookie.
        """
        result: dict[str, Any] = {
            "name": self.name,
            "value": self.value.to_dict(),
            "domain": self.domain,
        }
        if self.path is not None:
            result["path"] = self.path
        if self.http_only is not None:
            result["httpOnly"] = self.http_only
        if self.secure is not None:
            result["secure"] = self.secure
        if self.same_site is not None:
            result["sameSite"] = self.same_site
        if self.expiry is not None:
            result["expiry"] = self.expiry
        return result


class GetCookiesResult:
    """Represents the result of a getCookies command."""

    def __init__(self, cookies: list[Cookie], partition_key: PartitionKey):
        self.cookies = cookies
        self.partition_key = partition_key

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GetCookiesResult:
        """Creates a GetCookiesResult instance from a dictionary.

        Args:
            data: A dictionary containing the get cookies result information.

        Returns:
            A new instance of GetCookiesResult.
        """
        cookies = [Cookie.from_dict(cookie) for cookie in data.get("cookies", [])]
        partition_key = PartitionKey.from_dict(data.get("partitionKey", {}))
        return cls(cookies=cookies, partition_key=partition_key)


class SetCookieResult:
    """Represents the result of a setCookie command."""

    def __init__(self, partition_key: PartitionKey):
        self.partition_key = partition_key

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SetCookieResult:
        """Creates a SetCookieResult instance from a dictionary.

        Args:
            data: A dictionary containing the set cookie result information.

        Returns:
            A new instance of SetCookieResult.
        """
        partition_key = PartitionKey.from_dict(data.get("partitionKey", {}))
        return cls(partition_key=partition_key)


class DeleteCookiesResult:
    """Represents the result of a deleteCookies command."""

    def __init__(self, partition_key: PartitionKey):
        self.partition_key = partition_key

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DeleteCookiesResult:
        """Creates a DeleteCookiesResult instance from a dictionary.

        Args:
            data: A dictionary containing the delete cookies result information.

        Returns:
            A new instance of DeleteCookiesResult.
        """
        partition_key = PartitionKey.from_dict(data.get("partitionKey", {}))
        return cls(partition_key=partition_key)


class Storage:
    """BiDi implementation of the storage module."""

    def __init__(self, conn: WebSocketConnection) -> None:
        self.conn = conn

    def get_cookies(
        self,
        filter: CookieFilter | None = None,
        partition: BrowsingContextPartitionDescriptor | StorageKeyPartitionDescriptor | None = None,
    ) -> GetCookiesResult:
        """Gets cookies matching the specified filter.

        Args:
            filter: Optional filter to specify which cookies to retrieve.
            partition: Optional partition key to limit the scope of the operation.

        Returns:
            A GetCookiesResult containing the cookies and partition key.

        Example:
            result = await storage.get_cookies(
                filter=CookieFilter(name="sessionId"),
                partition=PartitionKey(...)
            )
        """
        params = {}
        if filter is not None:
            params["filter"] = filter.to_dict()
        if partition is not None:
            params["partition"] = partition.to_dict()

        result = self.conn.execute(command_builder("storage.getCookies", params))
        return GetCookiesResult.from_dict(result)

    def set_cookie(
        self,
        cookie: PartialCookie,
        partition: BrowsingContextPartitionDescriptor | StorageKeyPartitionDescriptor | None = None,
    ) -> SetCookieResult:
        """Sets a cookie in the browser.

        Args:
            cookie: The cookie to set.
            partition: Optional partition descriptor.

        Returns:
            The result of the set cookie command.
        """
        params = {"cookie": cookie.to_dict()}
        if partition is not None:
            params["partition"] = partition.to_dict()

        result = self.conn.execute(command_builder("storage.setCookie", params))
        return SetCookieResult.from_dict(result)

    def delete_cookies(
        self,
        filter: CookieFilter | None = None,
        partition: BrowsingContextPartitionDescriptor | StorageKeyPartitionDescriptor | None = None,
    ) -> DeleteCookiesResult:
        """Deletes cookies that match the given parameters.

        Args:
            filter: Optional filter to match cookies to delete.
            partition: Optional partition descriptor.

        Returns:
            The result of the delete cookies command.
        """
        params = {}
        if filter is not None:
            params["filter"] = filter.to_dict()
        if partition is not None:
            params["partition"] = partition.to_dict()

        result = self.conn.execute(command_builder("storage.deleteCookies", params))
        return DeleteCookiesResult.from_dict(result)
