"""Client for GeoIP2 and GeoLite2 web services.

The web services are Country, City Plus, and Insights. Each service returns a
different set of data about an IP address, with Country returning the least
data and Insights the most.

Each service is represented by a different model class, and these model
classes in turn contain multiple record classes. The record classes have
attributes which contain data about the IP address.

If the service does not return a particular piece of data for an IP address,
the associated attribute is not populated.

The service may not return any information for an entire record, in which
case all of the attributes for that record class will be empty.

SSL
---

Requests to the web service are always made with SSL.

"""

from __future__ import annotations

import ipaddress
import json
from typing import TYPE_CHECKING, cast

import aiohttp
import aiohttp.http
import requests
import requests.utils

import geoip2
import geoip2.models
from geoip2.errors import (
    AddressNotFoundError,
    AuthenticationError,
    GeoIP2Error,
    HTTPError,
    InvalidRequestError,
    OutOfQueriesError,
    PermissionRequiredError,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from typing_extensions import Self

    from geoip2.models import City, Country, Insights
    from geoip2.types import IPAddress

_AIOHTTP_UA = (
    f"GeoIP2-Python-Client/{geoip2.__version__} {aiohttp.http.SERVER_SOFTWARE}"
)

_REQUEST_UA = (
    f"GeoIP2-Python-Client/{geoip2.__version__} {requests.utils.default_user_agent()}"
)


class BaseClient:
    """Base class for AsyncClient and Client."""

    _account_id: str
    _host: str
    _license_key: str
    _locales: Sequence[str]
    _timeout: float

    def __init__(
        self,
        account_id: int,
        license_key: str,
        host: str,
        locales: Sequence[str] | None,
        timeout: float,
    ) -> None:
        """Construct a Client."""
        if locales is None:
            locales = ["en"]

        self._locales = locales
        # requests 2.12.2 requires that the username passed to auth be bytes
        # or a string, with the former being preferred.
        self._account_id = (
            account_id if isinstance(account_id, bytes) else str(account_id)
        )
        self._license_key = license_key
        self._base_uri = f"https://{host}/geoip/v2.1"
        self._timeout = timeout

    def _uri(self, path: str, ip_address: IPAddress) -> str:
        if ip_address != "me":
            ip_address = ipaddress.ip_address(ip_address)
        return "/".join([self._base_uri, path, str(ip_address)])

    @staticmethod
    def _handle_success(body: str, uri: str) -> dict:
        try:
            return json.loads(body)
        except ValueError as ex:
            raise GeoIP2Error(
                f"Received a 200 response for {uri}"
                " but could not decode the response as "
                "JSON: " + ", ".join(ex.args),
                200,
                uri,
            ) from ex

    def _exception_for_error(
        self,
        status: int,
        content_type: str,
        body: str,
        uri: str,
    ) -> GeoIP2Error:
        if 400 <= status < 500:
            return self._exception_for_4xx_status(status, content_type, body, uri)
        if 500 <= status < 600:
            return self._exception_for_5xx_status(status, uri, body)
        return self._exception_for_non_200_status(status, uri, body)

    def _exception_for_4xx_status(
        self,
        status: int,
        content_type: str,
        body: str,
        uri: str,
    ) -> GeoIP2Error:
        if not body:
            return HTTPError(
                f"Received a {status} error for {uri} with no body.",
                status,
                uri,
                body,
            )
        if content_type.find("json") == -1:
            return HTTPError(
                f"Received a {status} for {uri} with the following body: {body}",
                status,
                uri,
                body,
            )
        try:
            decoded_body = json.loads(body)
        except ValueError as ex:
            return HTTPError(
                (
                    f"Received a {status} error for {uri} but it did not include "
                    f"the expected JSON body: {', '.join(ex.args)}"
                ),
                status,
                uri,
                body,
            )

        if "code" in decoded_body and "error" in decoded_body:
            return self._exception_for_web_service_error(
                decoded_body.get("error"),
                decoded_body.get("code"),
                status,
                uri,
            )
        return HTTPError(
            "Response contains JSON but it does not specify code or error keys",
            status,
            uri,
            body,
        )

    @staticmethod
    def _exception_for_web_service_error(
        message: str,
        code: str,
        status: int,
        uri: str,
    ) -> (
        AuthenticationError
        | AddressNotFoundError
        | PermissionRequiredError
        | OutOfQueriesError
        | InvalidRequestError
    ):
        if code in ("IP_ADDRESS_NOT_FOUND", "IP_ADDRESS_RESERVED"):
            return AddressNotFoundError(message)
        if code in (
            "ACCOUNT_ID_REQUIRED",
            "ACCOUNT_ID_UNKNOWN",
            "AUTHORIZATION_INVALID",
            "LICENSE_KEY_REQUIRED",
            "USER_ID_REQUIRED",
            "USER_ID_UNKNOWN",
        ):
            return AuthenticationError(message)
        if code in ("INSUFFICIENT_FUNDS", "OUT_OF_QUERIES"):
            return OutOfQueriesError(message)
        if code == "PERMISSION_REQUIRED":
            return PermissionRequiredError(message)

        return InvalidRequestError(message, code, status, uri)

    @staticmethod
    def _exception_for_5xx_status(
        status: int,
        uri: str,
        body: str | None,
    ) -> HTTPError:
        return HTTPError(
            f"Received a server error ({status}) for {uri}",
            status,
            uri,
            body,
        )

    @staticmethod
    def _exception_for_non_200_status(
        status: int,
        uri: str,
        body: str | None,
    ) -> HTTPError:
        return HTTPError(
            f"Received a very surprising HTTP status ({status}) for {uri}",
            status,
            uri,
            body,
        )


class AsyncClient(BaseClient):
    """An async GeoIP2 client.

    It accepts the following required arguments:

    :param account_id: Your MaxMind account ID.
    :param license_key: Your MaxMind license key.

    Go to https://www.maxmind.com/en/my_license_key to see your MaxMind
    account ID and license key.

    The following keyword arguments are also accepted:

    :param host: The hostname to make a request against. This defaults to
      "geoip.maxmind.com". To use the GeoLite2 web service instead of the
      GeoIP2 web service, set this to "geolite.info". To use the Sandbox
      GeoIP2 web service instead of the production GeoIP2 web service, set
      this to "sandbox.maxmind.com". The sandbox allows you to experiment
      with the API without affecting your production data.
    :param locales: This is list of locale codes. This argument will be
      passed on to record classes to use when their name properties are
      called. The default value is ['en'].

      The order of the locales is significant. When a record class has
      multiple names (country, city, etc.), its name property will return
      the name in the first locale that has one.

      Note that the only locale which is always present in the GeoIP2
      data is "en". If you do not include this locale, the name property
      may end up returning None even when the record has an English name.

      Currently, the valid locale codes are:

      * de -- German
      * en -- English names may still include accented characters if that is
        the accepted spelling in English. In other words, English does not
        mean ASCII.
      * es -- Spanish
      * fr -- French
      * ja -- Japanese
      * pt-BR -- Brazilian Portuguese
      * ru -- Russian
      * zh-CN -- Simplified Chinese.
    :param timeout: The timeout in seconds to use when waiting on the request.
      This sets both the connect timeout and the read timeout. The default is
      60.
    :param proxy: The URL of an HTTP proxy to use. It may optionally include
      a basic auth username and password, e.g.,
      ``http://username:password@host:port``.

    """

    _existing_session: aiohttp.ClientSession
    _proxy: str | None

    def __init__(  # noqa: PLR0913
        self,
        account_id: int,
        license_key: str,
        host: str = "geoip.maxmind.com",
        locales: Sequence[str] | None = None,
        timeout: float = 60,
        proxy: str | None = None,
    ) -> None:
        """Initialize AsyncClient."""
        super().__init__(
            account_id,
            license_key,
            host,
            locales,
            timeout,
        )
        self._proxy = proxy

    async def city(self, ip_address: IPAddress = "me") -> City:
        """Call City Plus endpoint with the specified IP.

        :param ip_address: IPv4 or IPv6 address as a string. If no
           address is provided, the address that the web service is
           called from will be used.

        :returns: :py:class:`geoip2.models.City` object

        """
        return cast(
            "City",
            await self._response_for("city", geoip2.models.City, ip_address),
        )

    async def country(self, ip_address: IPAddress = "me") -> Country:
        """Call the GeoIP2 Country endpoint with the specified IP.

        :param ip_address: IPv4 or IPv6 address as a string. If no address
          is provided, the address that the web service is called from will
          be used.

        :returns: :py:class:`geoip2.models.Country` object

        """
        return cast(
            "Country",
            await self._response_for("country", geoip2.models.Country, ip_address),
        )

    async def insights(self, ip_address: IPAddress = "me") -> Insights:
        """Call the Insights endpoint with the specified IP.

        Insights is only supported by the GeoIP2 web service. The GeoLite2 web
        service does not support it.

        :param ip_address: IPv4 or IPv6 address as a string. If no address
          is provided, the address that the web service is called from will
          be used.

        :returns: :py:class:`geoip2.models.Insights` object

        """
        return cast(
            "Insights",
            await self._response_for("insights", geoip2.models.Insights, ip_address),
        )

    async def _session(self) -> aiohttp.ClientSession:
        if not hasattr(self, "_existing_session"):
            self._existing_session = aiohttp.ClientSession(
                auth=aiohttp.BasicAuth(self._account_id, self._license_key),
                headers={"Accept": "application/json", "User-Agent": _AIOHTTP_UA},
                timeout=aiohttp.ClientTimeout(total=self._timeout),
            )

        return self._existing_session

    async def _response_for(
        self,
        path: str,
        model_class: type[City | Country | Insights],
        ip_address: IPAddress,
    ) -> Country | City | Insights:
        uri = self._uri(path, ip_address)
        session = await self._session()
        async with await session.get(uri, proxy=self._proxy) as response:
            status = response.status
            content_type = response.content_type
            body = await response.text()
            if status != 200:
                raise self._exception_for_error(status, content_type, body, uri)
            decoded_body = self._handle_success(body, uri)
            return model_class(self._locales, **decoded_body)

    async def close(self) -> None:
        """Close underlying session.

        This will close the session and any associated connections.
        """
        if hasattr(self, "_existing_session"):
            await self._existing_session.close()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: object,
        exc_value: object,
        traceback: object,
    ) -> None:
        await self.close()


class Client(BaseClient):
    """A synchronous GeoIP2 client.

    It accepts the following required arguments:

    :param account_id: Your MaxMind account ID.
    :param license_key: Your MaxMind license key.

    Go to https://www.maxmind.com/en/my_license_key to see your MaxMind
    account ID and license key.

    The following keyword arguments are also accepted:

    :param host: The hostname to make a request against. This defaults to
      "geoip.maxmind.com". To use the GeoLite2 web service instead of the
      GeoIP2 web service, set this to "geolite.info". To use the Sandbox
      GeoIP2 web service instead of the production GeoIP2 web service, set
      this to "sandbox.maxmind.com". The sandbox allows you to experiment
      with the API without affecting your production data.
    :param locales: This is list of locale codes. This argument will be
      passed on to record classes to use when their name properties are
      called. The default value is ['en'].

      The order of the locales is significant. When a record class has
      multiple names (country, city, etc.), its name property will return
      the name in the first locale that has one.

      Note that the only locale which is always present in the GeoIP2
      data is "en". If you do not include this locale, the name property
      may end up returning None even when the record has an English name.

      Currently, the valid locale codes are:

      * de -- German
      * en -- English names may still include accented characters if that is
        the accepted spelling in English. In other words, English does not
        mean ASCII.
      * es -- Spanish
      * fr -- French
      * ja -- Japanese
      * pt-BR -- Brazilian Portuguese
      * ru -- Russian
      * zh-CN -- Simplified Chinese.
    :param timeout: The timeout in seconds to use when waiting on the request.
      This sets both the connect timeout and the read timeout. The default is
      60.
    :param proxy: The URL of an HTTP proxy to use. It may optionally include
      a basic auth username and password, e.g.,
      ``http://username:password@host:port``.


    """

    _session: requests.Session
    _proxies: dict[str, str] | None

    def __init__(  # noqa: PLR0913
        self,
        account_id: int,
        license_key: str,
        host: str = "geoip.maxmind.com",
        locales: Sequence[str] | None = None,
        timeout: float = 60,
        proxy: str | None = None,
    ) -> None:
        """Initialize Client."""
        super().__init__(account_id, license_key, host, locales, timeout)
        self._session = requests.Session()
        self._session.auth = (self._account_id, self._license_key)
        self._session.headers["Accept"] = "application/json"
        self._session.headers["User-Agent"] = _REQUEST_UA
        if proxy is None:
            self._proxies = None
        else:
            self._proxies = {"https": proxy}

    def city(self, ip_address: IPAddress = "me") -> City:
        """Call City Plus endpoint with the specified IP.

        :param ip_address: IPv4 or IPv6 address as a string. If no
           address is provided, the address that the web service is
           called from will be used.

        :returns: :py:class:`geoip2.models.City` object

        """
        return cast("City", self._response_for("city", geoip2.models.City, ip_address))

    def country(self, ip_address: IPAddress = "me") -> Country:
        """Call the GeoIP2 Country endpoint with the specified IP.

        :param ip_address: IPv4 or IPv6 address as a string. If no address
          is provided, the address that the web service is called from will
          be used.

        :returns: :py:class:`geoip2.models.Country` object

        """
        return cast(
            "Country",
            self._response_for("country", geoip2.models.Country, ip_address),
        )

    def insights(self, ip_address: IPAddress = "me") -> Insights:
        """Call the Insights endpoint with the specified IP.

        Insights is only supported by the GeoIP2 web service. The GeoLite2 web
        service does not support it.

        :param ip_address: IPv4 or IPv6 address as a string. If no address
          is provided, the address that the web service is called from will
          be used.

        :returns: :py:class:`geoip2.models.Insights` object

        """
        return cast(
            "Insights",
            self._response_for("insights", geoip2.models.Insights, ip_address),
        )

    def _response_for(
        self,
        path: str,
        model_class: type[City | Country | Insights],
        ip_address: IPAddress,
    ) -> Country | City | Insights:
        uri = self._uri(path, ip_address)
        response = self._session.get(uri, proxies=self._proxies, timeout=self._timeout)
        status = response.status_code
        content_type = response.headers["Content-Type"]
        body = response.text
        if status != 200:
            raise self._exception_for_error(status, content_type, body, uri)
        decoded_body = self._handle_success(body, uri)
        return model_class(self._locales, **decoded_body)

    def close(self) -> None:
        """Close underlying session.

        This will close the session and any associated connections.
        """
        self._session.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        self.close()
