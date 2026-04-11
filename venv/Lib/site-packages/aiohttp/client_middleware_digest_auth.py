"""
Digest authentication middleware for aiohttp client.

This middleware implements HTTP Digest Authentication according to RFC 7616,
providing a more secure alternative to Basic Authentication. It supports all
standard hash algorithms including MD5, SHA, SHA-256, SHA-512 and their session
variants, as well as both 'auth' and 'auth-int' quality of protection (qop) options.
"""

import hashlib
import os
import re
import sys
import time
from typing import (
    Callable,
    Dict,
    Final,
    FrozenSet,
    List,
    Literal,
    Tuple,
    TypedDict,
    Union,
)

from yarl import URL

from . import hdrs
from .client_exceptions import ClientError
from .client_middlewares import ClientHandlerType
from .client_reqrep import ClientRequest, ClientResponse
from .payload import Payload


class DigestAuthChallenge(TypedDict, total=False):
    realm: str
    nonce: str
    qop: str
    algorithm: str
    opaque: str
    domain: str
    stale: str


DigestFunctions: Dict[str, Callable[[bytes], "hashlib._Hash"]] = {
    "MD5": hashlib.md5,
    "MD5-SESS": hashlib.md5,
    "SHA": hashlib.sha1,
    "SHA-SESS": hashlib.sha1,
    "SHA256": hashlib.sha256,
    "SHA256-SESS": hashlib.sha256,
    "SHA-256": hashlib.sha256,
    "SHA-256-SESS": hashlib.sha256,
    "SHA512": hashlib.sha512,
    "SHA512-SESS": hashlib.sha512,
    "SHA-512": hashlib.sha512,
    "SHA-512-SESS": hashlib.sha512,
}


# Compile the regex pattern once at module level for performance
_HEADER_PAIRS_PATTERN = re.compile(
    r'(?:^|\s|,\s*)(\w+)\s*=\s*(?:"((?:[^"\\]|\\.)*)"|([^\s,]+))'
    if sys.version_info < (3, 11)
    else r'(?:^|\s|,\s*)((?>\w+))\s*=\s*(?:"((?:[^"\\]|\\.)*)"|([^\s,]+))'
    # +------------|--------|--|-|-|--|----|------|----|--||-----|-> Match valid start/sep
    #              +--------|--|-|-|--|----|------|----|--||-----|-> alphanumeric key (atomic
    #                       |  | | |  |    |      |    |  ||     |   group reduces backtracking)
    #                       +--|-|-|--|----|------|----|--||-----|-> maybe whitespace
    #                          | | |  |    |      |    |  ||     |
    #                          +-|-|--|----|------|----|--||-----|-> = (delimiter)
    #                            +-|--|----|------|----|--||-----|-> maybe whitespace
    #                              |  |    |      |    |  ||     |
    #                              +--|----|------|----|--||-----|-> group quoted or unquoted
    #                                 |    |      |    |  ||     |
    #                                 +----|------|----|--||-----|-> if quoted...
    #                                      +------|----|--||-----|-> anything but " or \
    #                                             +----|--||-----|-> escaped characters allowed
    #                                                  +--||-----|-> or can be empty string
    #                                                     ||     |
    #                                                     +|-----|-> if unquoted...
    #                                                      +-----|-> anything but , or <space>
    #                                                            +-> at least one char req'd
)


# RFC 7616: Challenge parameters to extract
CHALLENGE_FIELDS: Final[
    Tuple[
        Literal["realm", "nonce", "qop", "algorithm", "opaque", "domain", "stale"], ...
    ]
] = (
    "realm",
    "nonce",
    "qop",
    "algorithm",
    "opaque",
    "domain",
    "stale",
)

# Supported digest authentication algorithms
# Use a tuple of sorted keys for predictable documentation and error messages
SUPPORTED_ALGORITHMS: Final[Tuple[str, ...]] = tuple(sorted(DigestFunctions.keys()))

# RFC 7616: Fields that require quoting in the Digest auth header
# These fields must be enclosed in double quotes in the Authorization header.
# Algorithm, qop, and nc are never quoted per RFC specifications.
# This frozen set is used by the template-based header construction to
# automatically determine which fields need quotes.
QUOTED_AUTH_FIELDS: Final[FrozenSet[str]] = frozenset(
    {"username", "realm", "nonce", "uri", "response", "opaque", "cnonce"}
)


def escape_quotes(value: str) -> str:
    """Escape double quotes for HTTP header values."""
    return value.replace('"', '\\"')


def unescape_quotes(value: str) -> str:
    """Unescape double quotes in HTTP header values."""
    return value.replace('\\"', '"')


def parse_header_pairs(header: str) -> Dict[str, str]:
    """
    Parse key-value pairs from WWW-Authenticate or similar HTTP headers.

    This function handles the complex format of WWW-Authenticate header values,
    supporting both quoted and unquoted values, proper handling of commas in
    quoted values, and whitespace variations per RFC 7616.

    Examples of supported formats:
      - key1="value1", key2=value2
      - key1 = "value1" , key2="value, with, commas"
      - key1=value1,key2="value2"
      - realm="example.com", nonce="12345", qop="auth"

    Args:
        header: The header value string to parse

    Returns:
        Dictionary mapping parameter names to their values
    """
    return {
        stripped_key: unescape_quotes(quoted_val) if quoted_val else unquoted_val
        for key, quoted_val, unquoted_val in _HEADER_PAIRS_PATTERN.findall(header)
        if (stripped_key := key.strip())
    }


class DigestAuthMiddleware:
    """
    HTTP digest authentication middleware for aiohttp client.

    This middleware intercepts 401 Unauthorized responses containing a Digest
    authentication challenge, calculates the appropriate digest credentials,
    and automatically retries the request with the proper Authorization header.

    Features:
    - Handles all aspects of Digest authentication handshake automatically
    - Supports all standard hash algorithms:
      - MD5, MD5-SESS
      - SHA, SHA-SESS
      - SHA256, SHA256-SESS, SHA-256, SHA-256-SESS
      - SHA512, SHA512-SESS, SHA-512, SHA-512-SESS
    - Supports 'auth' and 'auth-int' quality of protection modes
    - Properly handles quoted strings and parameter parsing
    - Includes replay attack protection with client nonce count tracking
    - Supports preemptive authentication per RFC 7616 Section 3.6

    Standards compliance:
    - RFC 7616: HTTP Digest Access Authentication (primary reference)
    - RFC 2617: HTTP Authentication (deprecated by RFC 7616)
    - RFC 1945: Section 11.1 (username restrictions)

    Implementation notes:
    The core digest calculation is inspired by the implementation in
    https://github.com/requests/requests/blob/v2.18.4/requests/auth.py
    with added support for modern digest auth features and error handling.
    """

    def __init__(
        self,
        login: str,
        password: str,
        preemptive: bool = True,
    ) -> None:
        if login is None:
            raise ValueError("None is not allowed as login value")

        if password is None:
            raise ValueError("None is not allowed as password value")

        if ":" in login:
            raise ValueError('A ":" is not allowed in username (RFC 1945#section-11.1)')

        self._login_str: Final[str] = login
        self._login_bytes: Final[bytes] = login.encode("utf-8")
        self._password_bytes: Final[bytes] = password.encode("utf-8")

        self._last_nonce_bytes = b""
        self._nonce_count = 0
        self._challenge: DigestAuthChallenge = {}
        self._preemptive: bool = preemptive
        # Set of URLs defining the protection space
        self._protection_space: List[str] = []

    async def _encode(
        self, method: str, url: URL, body: Union[Payload, Literal[b""]]
    ) -> str:
        """
        Build digest authorization header for the current challenge.

        Args:
            method: The HTTP method (GET, POST, etc.)
            url: The request URL
            body: The request body (used for qop=auth-int)

        Returns:
            A fully formatted Digest authorization header string

        Raises:
            ClientError: If the challenge is missing required parameters or
                         contains unsupported values

        """
        challenge = self._challenge
        if "realm" not in challenge:
            raise ClientError(
                "Malformed Digest auth challenge: Missing 'realm' parameter"
            )

        if "nonce" not in challenge:
            raise ClientError(
                "Malformed Digest auth challenge: Missing 'nonce' parameter"
            )

        # Empty realm values are allowed per RFC 7616 (SHOULD, not MUST, contain host name)
        realm = challenge["realm"]
        nonce = challenge["nonce"]

        # Empty nonce values are not allowed as they are security-critical for replay protection
        if not nonce:
            raise ClientError(
                "Security issue: Digest auth challenge contains empty 'nonce' value"
            )

        qop_raw = challenge.get("qop", "")
        # Preserve original algorithm case for response while using uppercase for processing
        algorithm_original = challenge.get("algorithm", "MD5")
        algorithm = algorithm_original.upper()
        opaque = challenge.get("opaque", "")

        # Convert string values to bytes once
        nonce_bytes = nonce.encode("utf-8")
        realm_bytes = realm.encode("utf-8")
        path = URL(url).path_qs

        # Process QoP
        qop = ""
        qop_bytes = b""
        if qop_raw:
            valid_qops = {"auth", "auth-int"}.intersection(
                {q.strip() for q in qop_raw.split(",") if q.strip()}
            )
            if not valid_qops:
                raise ClientError(
                    f"Digest auth error: Unsupported Quality of Protection (qop) value(s): {qop_raw}"
                )

            qop = "auth-int" if "auth-int" in valid_qops else "auth"
            qop_bytes = qop.encode("utf-8")

        if algorithm not in DigestFunctions:
            raise ClientError(
                f"Digest auth error: Unsupported hash algorithm: {algorithm}. "
                f"Supported algorithms: {', '.join(SUPPORTED_ALGORITHMS)}"
            )
        hash_fn: Final = DigestFunctions[algorithm]

        def H(x: bytes) -> bytes:
            """RFC 7616 Section 3: Hash function H(data) = hex(hash(data))."""
            return hash_fn(x).hexdigest().encode()

        def KD(s: bytes, d: bytes) -> bytes:
            """RFC 7616 Section 3: KD(secret, data) = H(concat(secret, ":", data))."""
            return H(b":".join((s, d)))

        # Calculate A1 and A2
        A1 = b":".join((self._login_bytes, realm_bytes, self._password_bytes))
        A2 = f"{method.upper()}:{path}".encode()
        if qop == "auth-int":
            if isinstance(body, Payload):  # will always be empty bytes unless Payload
                entity_bytes = await body.as_bytes()  # Get bytes from Payload
            else:
                entity_bytes = body
            entity_hash = H(entity_bytes)
            A2 = b":".join((A2, entity_hash))

        HA1 = H(A1)
        HA2 = H(A2)

        # Nonce count handling
        if nonce_bytes == self._last_nonce_bytes:
            self._nonce_count += 1
        else:
            self._nonce_count = 1

        self._last_nonce_bytes = nonce_bytes
        ncvalue = f"{self._nonce_count:08x}"
        ncvalue_bytes = ncvalue.encode("utf-8")

        # Generate client nonce
        cnonce = hashlib.sha1(
            b"".join(
                [
                    str(self._nonce_count).encode("utf-8"),
                    nonce_bytes,
                    time.ctime().encode("utf-8"),
                    os.urandom(8),
                ]
            )
        ).hexdigest()[:16]
        cnonce_bytes = cnonce.encode("utf-8")

        # Special handling for session-based algorithms
        if algorithm.upper().endswith("-SESS"):
            HA1 = H(b":".join((HA1, nonce_bytes, cnonce_bytes)))

        # Calculate the response digest
        if qop:
            noncebit = b":".join(
                (nonce_bytes, ncvalue_bytes, cnonce_bytes, qop_bytes, HA2)
            )
            response_digest = KD(HA1, noncebit)
        else:
            response_digest = KD(HA1, b":".join((nonce_bytes, HA2)))

        # Define a dict mapping of header fields to their values
        # Group fields into always-present, optional, and qop-dependent
        header_fields = {
            # Always present fields
            "username": escape_quotes(self._login_str),
            "realm": escape_quotes(realm),
            "nonce": escape_quotes(nonce),
            "uri": path,
            "response": response_digest.decode(),
            "algorithm": algorithm_original,
        }

        # Optional fields
        if opaque:
            header_fields["opaque"] = escape_quotes(opaque)

        # QoP-dependent fields
        if qop:
            header_fields["qop"] = qop
            header_fields["nc"] = ncvalue
            header_fields["cnonce"] = cnonce

        # Build header using templates for each field type
        pairs: List[str] = []
        for field, value in header_fields.items():
            if field in QUOTED_AUTH_FIELDS:
                pairs.append(f'{field}="{value}"')
            else:
                pairs.append(f"{field}={value}")

        return f"Digest {', '.join(pairs)}"

    def _in_protection_space(self, url: URL) -> bool:
        """
        Check if the given URL is within the current protection space.

        According to RFC 7616, a URI is in the protection space if any URI
        in the protection space is a prefix of it (after both have been made absolute).
        """
        request_str = str(url)
        for space_str in self._protection_space:
            # Check if request starts with space URL
            if not request_str.startswith(space_str):
                continue
            # Exact match or space ends with / (proper directory prefix)
            if len(request_str) == len(space_str) or space_str[-1] == "/":
                return True
            # Check next char is / to ensure proper path boundary
            if request_str[len(space_str)] == "/":
                return True
        return False

    def _authenticate(self, response: ClientResponse) -> bool:
        """
        Takes the given response and tries digest-auth, if needed.

        Returns true if the original request must be resent.
        """
        if response.status != 401:
            return False

        auth_header = response.headers.get("www-authenticate", "")
        if not auth_header:
            return False  # No authentication header present

        method, sep, headers = auth_header.partition(" ")
        if not sep:
            # No space found in www-authenticate header
            return False  # Malformed auth header, missing scheme separator

        if method.lower() != "digest":
            # Not a digest auth challenge (could be Basic, Bearer, etc.)
            return False

        if not headers:
            # We have a digest scheme but no parameters
            return False  # Malformed digest header, missing parameters

        # We have a digest auth header with content
        if not (header_pairs := parse_header_pairs(headers)):
            # Failed to parse any key-value pairs
            return False  # Malformed digest header, no valid parameters

        # Extract challenge parameters
        self._challenge = {}
        for field in CHALLENGE_FIELDS:
            if value := header_pairs.get(field):
                self._challenge[field] = value

        # Update protection space based on domain parameter or default to origin
        origin = response.url.origin()

        if domain := self._challenge.get("domain"):
            # Parse space-separated list of URIs
            self._protection_space = []
            for uri in domain.split():
                # Remove quotes if present
                uri = uri.strip('"')
                if uri.startswith("/"):
                    # Path-absolute, relative to origin
                    self._protection_space.append(str(origin.join(URL(uri))))
                else:
                    # Absolute URI
                    self._protection_space.append(str(URL(uri)))
        else:
            # No domain specified, protection space is entire origin
            self._protection_space = [str(origin)]

        # Return True only if we found at least one challenge parameter
        return bool(self._challenge)

    async def __call__(
        self, request: ClientRequest, handler: ClientHandlerType
    ) -> ClientResponse:
        """Run the digest auth middleware."""
        response = None
        for retry_count in range(2):
            # Apply authorization header if:
            # 1. This is a retry after 401 (retry_count > 0), OR
            # 2. Preemptive auth is enabled AND we have a challenge AND the URL is in protection space
            if retry_count > 0 or (
                self._preemptive
                and self._challenge
                and self._in_protection_space(request.url)
            ):
                request.headers[hdrs.AUTHORIZATION] = await self._encode(
                    request.method, request.url, request.body
                )

            # Send the request
            response = await handler(request)

            # Check if we need to authenticate
            if not self._authenticate(response):
                break

        # At this point, response is guaranteed to be defined
        assert response is not None
        return response
