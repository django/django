"""
Errors
======

"""

import ipaddress

from typing import Optional, Union


class GeoIP2Error(RuntimeError):
    """There was a generic error in GeoIP2.

    This class represents a generic error. It extends :py:exc:`RuntimeError`
    and does not add any additional attributes.

    """


class AddressNotFoundError(GeoIP2Error):
    """The address you were looking up was not found.

    .. attribute:: ip_address

      The IP address used in the lookup. This is only available for database
      lookups.

      :type: str

    .. attribute:: network

      The network associated with the error. In particular, this is the
      largest network where no address would be found. This is only
      available for database lookups.

      :type: ipaddress.IPv4Network or ipaddress.IPv6Network

    """

    ip_address: Optional[str]
    _prefix_len: Optional[int]

    def __init__(
        self,
        message: str,
        ip_address: Optional[str] = None,
        prefix_len: Optional[int] = None,
    ) -> None:
        super().__init__(message)
        self.ip_address = ip_address
        self._prefix_len = prefix_len

    @property
    def network(self) -> Optional[Union[ipaddress.IPv4Network, ipaddress.IPv6Network]]:
        """The network for the error"""

        if self.ip_address is None or self._prefix_len is None:
            return None
        return ipaddress.ip_network(f"{self.ip_address}/{self._prefix_len}", False)


class AuthenticationError(GeoIP2Error):
    """There was a problem authenticating the request."""


class HTTPError(GeoIP2Error):
    """There was an error when making your HTTP request.

    This class represents an HTTP transport error. It extends
    :py:exc:`GeoIP2Error` and adds attributes of its own.

    :ivar http_status: The HTTP status code returned
    :ivar uri: The URI queried
    :ivar decoded_content: The decoded response content

    """

    def __init__(
        self,
        message: str,
        http_status: Optional[int] = None,
        uri: Optional[str] = None,
        decoded_content: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.http_status = http_status
        self.uri = uri
        self.decoded_content = decoded_content


class InvalidRequestError(GeoIP2Error):
    """The request was invalid."""


class OutOfQueriesError(GeoIP2Error):
    """Your account is out of funds for the service queried."""


class PermissionRequiredError(GeoIP2Error):
    """Your account does not have permission to access this service."""
