from __future__ import annotations

import base64
import gzip
import json
import ssl
import zlib
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional, Tuple, Union
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen

__all__ = ["HttpClient", "HttpResponse", "HttpError", "DEFAULT_TIMEOUT"]

from redis.backoff import ExponentialWithJitterBackoff
from redis.retry import Retry
from redis.utils import dummy_fail

DEFAULT_USER_AGENT = "HttpClient/1.0 (+https://example.invalid)"
DEFAULT_TIMEOUT = 30.0
RETRY_STATUS_CODES = {429, 500, 502, 503, 504}


@dataclass
class HttpResponse:
    status: int
    headers: Dict[str, str]
    url: str
    content: bytes

    def text(self, encoding: Optional[str] = None) -> str:
        enc = encoding or self._get_encoding()
        return self.content.decode(enc, errors="replace")

    def json(self) -> Any:
        return json.loads(self.text(encoding=self._get_encoding()))

    def _get_encoding(self) -> str:
        # Try to infer encoding from headers; default to utf-8
        ctype = self.headers.get("content-type", "")
        # Example: application/json; charset=utf-8
        for part in ctype.split(";"):
            p = part.strip()
            if p.lower().startswith("charset="):
                return p.split("=", 1)[1].strip() or "utf-8"
        return "utf-8"


class HttpError(Exception):
    def __init__(self, status: int, url: str, message: Optional[str] = None):
        self.status = status
        self.url = url
        self.message = message or f"HTTP {status} for {url}"
        super().__init__(self.message)


class HttpClient:
    """
    A lightweight HTTP client for REST API calls.
    """

    def __init__(
        self,
        base_url: str = "",
        headers: Optional[Mapping[str, str]] = None,
        timeout: float = DEFAULT_TIMEOUT,
        retry: Retry = Retry(
            backoff=ExponentialWithJitterBackoff(base=1, cap=10), retries=3
        ),
        verify_tls: bool = True,
        # TLS verification (server) options
        ca_file: Optional[str] = None,
        ca_path: Optional[str] = None,
        ca_data: Optional[Union[str, bytes]] = None,
        # Mutual TLS (client cert) options
        client_cert_file: Optional[str] = None,
        client_key_file: Optional[str] = None,
        client_key_password: Optional[str] = None,
        auth_basic: Optional[Tuple[str, str]] = None,  # (username, password)
        user_agent: str = DEFAULT_USER_AGENT,
    ) -> None:
        """
        Initialize a new HTTP client instance.

        Args:
            base_url: Base URL for all requests. Will be prefixed to all paths.
            headers: Default headers to include in all requests.
            timeout: Default timeout in seconds for requests.
            retry: Retry configuration for failed requests.
            verify_tls: Whether to verify TLS certificates.
            ca_file: Path to CA certificate file for TLS verification.
            ca_path: Path to a directory containing CA certificates.
            ca_data: CA certificate data as string or bytes.
            client_cert_file: Path to client certificate for mutual TLS.
            client_key_file: Path to a client private key for mutual TLS.
            client_key_password: Password for an encrypted client private key.
            auth_basic: Tuple of (username, password) for HTTP basic auth.
            user_agent: User-Agent header value for requests.

        The client supports both regular HTTPS with server verification and mutual TLS
        authentication. For server verification, provide CA certificate information via
        ca_file, ca_path or ca_data. For mutual TLS, additionally provide a client
        certificate and key via client_cert_file and client_key_file.
        """
        self.base_url = (
            base_url.rstrip() + "/"
            if base_url and not base_url.endswith("/")
            else base_url
        )
        self._default_headers = {k.lower(): v for k, v in (headers or {}).items()}
        self.timeout = timeout
        self.retry = retry
        self.retry.update_supported_errors((HTTPError, URLError, ssl.SSLError))
        self.verify_tls = verify_tls

        # TLS settings
        self.ca_file = ca_file
        self.ca_path = ca_path
        self.ca_data = ca_data
        self.client_cert_file = client_cert_file
        self.client_key_file = client_key_file
        self.client_key_password = client_key_password

        self.auth_basic = auth_basic
        self.user_agent = user_agent

    # Public JSON-centric helpers
    def get(
        self,
        path: str,
        params: Optional[
            Mapping[str, Union[None, str, int, float, bool, list, tuple]]
        ] = None,
        headers: Optional[Mapping[str, str]] = None,
        timeout: Optional[float] = None,
        expect_json: bool = True,
    ) -> Union[HttpResponse, Any]:
        return self._json_call(
            "GET",
            path,
            params=params,
            headers=headers,
            timeout=timeout,
            body=None,
            expect_json=expect_json,
        )

    def delete(
        self,
        path: str,
        params: Optional[
            Mapping[str, Union[None, str, int, float, bool, list, tuple]]
        ] = None,
        headers: Optional[Mapping[str, str]] = None,
        timeout: Optional[float] = None,
        expect_json: bool = True,
    ) -> Union[HttpResponse, Any]:
        return self._json_call(
            "DELETE",
            path,
            params=params,
            headers=headers,
            timeout=timeout,
            body=None,
            expect_json=expect_json,
        )

    def post(
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
        return self._json_call(
            "POST",
            path,
            params=params,
            headers=headers,
            timeout=timeout,
            body=self._prepare_body(json_body=json_body, data=data),
            expect_json=expect_json,
        )

    def put(
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
        return self._json_call(
            "PUT",
            path,
            params=params,
            headers=headers,
            timeout=timeout,
            body=self._prepare_body(json_body=json_body, data=data),
            expect_json=expect_json,
        )

    def patch(
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
        return self._json_call(
            "PATCH",
            path,
            params=params,
            headers=headers,
            timeout=timeout,
            body=self._prepare_body(json_body=json_body, data=data),
            expect_json=expect_json,
        )

    # Low-level request
    def request(
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
        url = self._build_url(path, params)
        all_headers = self._prepare_headers(headers, body)
        data = body.encode("utf-8") if isinstance(body, str) else body

        req = Request(url=url, method=method.upper(), data=data, headers=all_headers)

        context: Optional[ssl.SSLContext] = None
        if url.lower().startswith("https"):
            if self.verify_tls:
                # Use provided CA material if any; fall back to system defaults
                context = ssl.create_default_context(
                    cafile=self.ca_file,
                    capath=self.ca_path,
                    cadata=self.ca_data,
                )
                # Load client certificate for mTLS if configured
                if self.client_cert_file:
                    context.load_cert_chain(
                        certfile=self.client_cert_file,
                        keyfile=self.client_key_file,
                        password=self.client_key_password,
                    )
            else:
                # Verification disabled
                context = ssl.create_default_context()
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE

        try:
            return self.retry.call_with_retry(
                lambda: self._make_request(req, context=context, timeout=timeout),
                lambda _: dummy_fail(),
                lambda error: self._is_retryable_http_error(error),
            )
        except HTTPError as e:
            # Read error body, build response, and decide on retry
            err_body = b""
            try:
                err_body = e.read()
            except Exception:
                pass
            headers_map = {k.lower(): v for k, v in (e.headers or {}).items()}
            err_body = self._maybe_decompress(err_body, headers_map)
            status = getattr(e, "code", 0) or 0
            response = HttpResponse(
                status=status,
                headers=headers_map,
                url=url,
                content=err_body,
            )
            return response

    def _make_request(
        self,
        request: Request,
        context: Optional[ssl.SSLContext] = None,
        timeout: Optional[float] = None,
    ):
        with urlopen(request, timeout=timeout or self.timeout, context=context) as resp:
            raw = resp.read()
            headers_map = {k.lower(): v for k, v in resp.headers.items()}
            raw = self._maybe_decompress(raw, headers_map)
            return HttpResponse(
                status=resp.status,
                headers=headers_map,
                url=resp.geturl(),
                content=raw,
            )

    def _is_retryable_http_error(self, error: Exception) -> bool:
        if isinstance(error, HTTPError):
            return self._should_retry_status(error.code)
        return False

    # Internal utilities
    def _json_call(
        self,
        method: str,
        path: str,
        params: Optional[
            Mapping[str, Union[None, str, int, float, bool, list, tuple]]
        ] = None,
        headers: Optional[Mapping[str, str]] = None,
        timeout: Optional[float] = None,
        body: Optional[Union[bytes, str]] = None,
        expect_json: bool = True,
    ) -> Union[HttpResponse, Any]:
        resp = self.request(
            method=method,
            path=path,
            params=params,
            headers=headers,
            body=body,
            timeout=timeout,
        )
        if not (200 <= resp.status < 400):
            raise HttpError(resp.status, resp.url, resp.text())
        if expect_json:
            return resp.json()
        return resp

    def _prepare_body(
        self, json_body: Optional[Any] = None, data: Optional[Union[bytes, str]] = None
    ) -> Optional[Union[bytes, str]]:
        if json_body is not None and data is not None:
            raise ValueError("Provide either json_body or data, not both.")
        if json_body is not None:
            return json.dumps(json_body, ensure_ascii=False, separators=(",", ":"))
        return data

    def _build_url(
        self,
        path: str,
        params: Optional[
            Mapping[str, Union[None, str, int, float, bool, list, tuple]]
        ] = None,
    ) -> str:
        url = urljoin(self.base_url or "", path)
        if params:
            # urlencode with doseq=True supports list/tuple values
            query = urlencode(
                {k: v for k, v in params.items() if v is not None}, doseq=True
            )
            separator = "&" if ("?" in url) else "?"
            url = f"{url}{separator}{query}" if query else url
        return url

    def _prepare_headers(
        self, headers: Optional[Mapping[str, str]], body: Optional[Union[bytes, str]]
    ) -> Dict[str, str]:
        # Start with defaults
        prepared: Dict[str, str] = {}
        prepared.update(self._default_headers)

        # Standard defaults for JSON REST usage
        prepared.setdefault("accept", "application/json")
        prepared.setdefault("user-agent", self.user_agent)
        # We will send gzip accept-encoding; handle decompression manually
        prepared.setdefault("accept-encoding", "gzip, deflate")

        # If we have a string body and content-type not specified, assume JSON
        if body is not None and isinstance(body, str):
            prepared.setdefault("content-type", "application/json; charset=utf-8")

        # Basic authentication if provided and not overridden
        if self.auth_basic and "authorization" not in prepared:
            user, pwd = self.auth_basic
            token = base64.b64encode(f"{user}:{pwd}".encode("utf-8")).decode("ascii")
            prepared["authorization"] = f"Basic {token}"

        # Merge per-call headers (case-insensitive)
        if headers:
            for k, v in headers.items():
                prepared[k.lower()] = v

        # urllib expects header keys in canonical capitalization sometimes; but it’s tolerant.
        # We'll return as provided; urllib will handle it.
        return prepared

    def _should_retry_status(self, status: int) -> bool:
        return status in RETRY_STATUS_CODES

    def _maybe_decompress(self, content: bytes, headers: Mapping[str, str]) -> bytes:
        if not content:
            return content
        encoding = (headers.get("content-encoding") or "").lower()
        try:
            if "gzip" in encoding:
                return gzip.decompress(content)
            if "deflate" in encoding:
                # Try raw deflate, then zlib-wrapped
                try:
                    return zlib.decompress(content, -zlib.MAX_WBITS)
                except zlib.error:
                    return zlib.decompress(content)
        except Exception:
            # If decompression fails, return original bytes
            return content
        return content
