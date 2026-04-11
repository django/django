import asyncio
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Mapping, Optional, Union

from redis.http.http_client import HttpClient, HttpResponse

DEFAULT_USER_AGENT = "HttpClient/1.0 (+https://example.invalid)"
DEFAULT_TIMEOUT = 30.0
RETRY_STATUS_CODES = {429, 500, 502, 503, 504}


class AsyncHTTPClient(ABC):
    @abstractmethod
    async def get(
        self,
        path: str,
        params: Optional[
            Mapping[str, Union[None, str, int, float, bool, list, tuple]]
        ] = None,
        headers: Optional[Mapping[str, str]] = None,
        timeout: Optional[float] = None,
        expect_json: bool = True,
    ) -> Union[HttpResponse, Any]:
        """
        Invoke HTTP GET request."""
        pass

    @abstractmethod
    async def delete(
        self,
        path: str,
        params: Optional[
            Mapping[str, Union[None, str, int, float, bool, list, tuple]]
        ] = None,
        headers: Optional[Mapping[str, str]] = None,
        timeout: Optional[float] = None,
        expect_json: bool = True,
    ) -> Union[HttpResponse, Any]:
        """
        Invoke HTTP DELETE request."""
        pass

    @abstractmethod
    async def post(
        self,
        path: str,
        json_body: Optional[Any] = None,
        data: Optional[Union[bytes, str]] = None,
        params: Optional[
            Mapping[str, Union[None, str, int, float, bool, list, tuple]]
        ] = None,
        headers: Optional[Mapping[str, str]] = None,
        timeout: Optional[float] = None,
        expect_json: bool = True,
    ) -> Union[HttpResponse, Any]:
        """
        Invoke HTTP POST request."""
        pass

    @abstractmethod
    async def put(
        self,
        path: str,
        json_body: Optional[Any] = None,
        data: Optional[Union[bytes, str]] = None,
        params: Optional[
            Mapping[str, Union[None, str, int, float, bool, list, tuple]]
        ] = None,
        headers: Optional[Mapping[str, str]] = None,
        timeout: Optional[float] = None,
        expect_json: bool = True,
    ) -> Union[HttpResponse, Any]:
        """
        Invoke HTTP PUT request."""
        pass

    @abstractmethod
    async def patch(
        self,
        path: str,
        json_body: Optional[Any] = None,
        data: Optional[Union[bytes, str]] = None,
        params: Optional[
            Mapping[str, Union[None, str, int, float, bool, list, tuple]]
        ] = None,
        headers: Optional[Mapping[str, str]] = None,
        timeout: Optional[float] = None,
        expect_json: bool = True,
    ) -> Union[HttpResponse, Any]:
        """
        Invoke HTTP PATCH request."""
        pass

    @abstractmethod
    async def request(
        self,
        method: str,
        path: str,
        params: Optional[
            Mapping[str, Union[None, str, int, float, bool, list, tuple]]
        ] = None,
        headers: Optional[Mapping[str, str]] = None,
        body: Optional[Union[bytes, str]] = None,
        timeout: Optional[float] = None,
    ) -> HttpResponse:
        """
        Invoke HTTP request with given method."""
        pass


class AsyncHTTPClientWrapper(AsyncHTTPClient):
    """
    An async wrapper around sync HTTP client with thread pool execution.
    """

    def __init__(self, client: HttpClient, max_workers: int = 10) -> None:
        """
        Initialize a new HTTP client instance.

        Args:
            client: Sync HTTP client instance.
            max_workers: Maximum number of concurrent requests.

        The client supports both regular HTTPS with server verification and mutual TLS
        authentication. For server verification, provide CA certificate information via
        ca_file, ca_path or ca_data. For mutual TLS, additionally provide a client
        certificate and key via client_cert_file and client_key_file.
        """
        self.client = client
        self._executor = ThreadPoolExecutor(max_workers=max_workers)

    async def get(
        self,
        path: str,
        params: Optional[
            Mapping[str, Union[None, str, int, float, bool, list, tuple]]
        ] = None,
        headers: Optional[Mapping[str, str]] = None,
        timeout: Optional[float] = None,
        expect_json: bool = True,
    ) -> Union[HttpResponse, Any]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor, self.client.get, path, params, headers, timeout, expect_json
        )

    async def delete(
        self,
        path: str,
        params: Optional[
            Mapping[str, Union[None, str, int, float, bool, list, tuple]]
        ] = None,
        headers: Optional[Mapping[str, str]] = None,
        timeout: Optional[float] = None,
        expect_json: bool = True,
    ) -> Union[HttpResponse, Any]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor,
            self.client.delete,
            path,
            params,
            headers,
            timeout,
            expect_json,
        )

    async def post(
        self,
        path: str,
        json_body: Optional[Any] = None,
        data: Optional[Union[bytes, str]] = None,
        params: Optional[
            Mapping[str, Union[None, str, int, float, bool, list, tuple]]
        ] = None,
        headers: Optional[Mapping[str, str]] = None,
        timeout: Optional[float] = None,
        expect_json: bool = True,
    ) -> Union[HttpResponse, Any]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor,
            self.client.post,
            path,
            json_body,
            data,
            params,
            headers,
            timeout,
            expect_json,
        )

    async def put(
        self,
        path: str,
        json_body: Optional[Any] = None,
        data: Optional[Union[bytes, str]] = None,
        params: Optional[
            Mapping[str, Union[None, str, int, float, bool, list, tuple]]
        ] = None,
        headers: Optional[Mapping[str, str]] = None,
        timeout: Optional[float] = None,
        expect_json: bool = True,
    ) -> Union[HttpResponse, Any]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor,
            self.client.put,
            path,
            json_body,
            data,
            params,
            headers,
            timeout,
            expect_json,
        )

    async def patch(
        self,
        path: str,
        json_body: Optional[Any] = None,
        data: Optional[Union[bytes, str]] = None,
        params: Optional[
            Mapping[str, Union[None, str, int, float, bool, list, tuple]]
        ] = None,
        headers: Optional[Mapping[str, str]] = None,
        timeout: Optional[float] = None,
        expect_json: bool = True,
    ) -> Union[HttpResponse, Any]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor,
            self.client.patch,
            path,
            json_body,
            data,
            params,
            headers,
            timeout,
            expect_json,
        )

    async def request(
        self,
        method: str,
        path: str,
        params: Optional[
            Mapping[str, Union[None, str, int, float, bool, list, tuple]]
        ] = None,
        headers: Optional[Mapping[str, str]] = None,
        body: Optional[Union[bytes, str]] = None,
        timeout: Optional[float] = None,
    ) -> HttpResponse:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor,
            self.client.request,
            method,
            path,
            params,
            headers,
            body,
            timeout,
        )
