"""The models for response from th GeoIP2 web service and databases.

The only difference between the City and Insights model classes is which
fields in each record may be populated. See
https://dev.maxmind.com/geoip/docs/web-services?lang=en for more details.
"""

from __future__ import annotations

import datetime
import ipaddress
from abc import ABCMeta
from ipaddress import IPv4Address, IPv6Address
from typing import TYPE_CHECKING, Any

import geoip2.records
from geoip2._internal import Model

if TYPE_CHECKING:
    from collections.abc import Sequence

    from geoip2.types import IPAddress


class Country(Model):
    """Model for the Country web service and Country database."""

    continent: geoip2.records.Continent
    """Continent object for the requested IP address."""

    country: geoip2.records.Country
    """Country object for the requested IP address. This record represents the
    country where MaxMind believes the IP is located.
    """

    maxmind: geoip2.records.MaxMind
    """Information related to your MaxMind account."""

    registered_country: geoip2.records.Country
    """The registered country object for the requested IP address. This record
    represents the country where the ISP has registered a given IP block in
    and may differ from the user's country.
    """

    represented_country: geoip2.records.RepresentedCountry
    """Object for the country represented by the users of the IP address
    when that country is different than the country in ``country``. For
    instance, the country represented by an overseas military base.
    """

    traits: geoip2.records.Traits
    """Object with the traits of the requested IP address."""

    def __init__(
        self,
        locales: Sequence[str] | None,
        *,
        continent: dict[str, Any] | None = None,
        country: dict[str, Any] | None = None,
        ip_address: IPAddress | None = None,
        maxmind: dict[str, Any] | None = None,
        prefix_len: int | None = None,
        registered_country: dict[str, Any] | None = None,
        represented_country: dict[str, Any] | None = None,
        traits: dict[str, Any] | None = None,
        **_: Any,
    ) -> None:
        self._locales = locales
        self.continent = geoip2.records.Continent(locales, **(continent or {}))
        self.country = geoip2.records.Country(locales, **(country or {}))
        self.registered_country = geoip2.records.Country(
            locales,
            **(registered_country or {}),
        )
        self.represented_country = geoip2.records.RepresentedCountry(
            locales,
            **(represented_country or {}),
        )

        self.maxmind = geoip2.records.MaxMind(**(maxmind or {}))

        traits = traits or {}
        if ip_address is not None:
            traits["ip_address"] = ip_address
        if prefix_len is not None:
            traits["prefix_len"] = prefix_len

        self.traits = geoip2.records.Traits(**traits)

    def __repr__(self) -> str:
        return (
            f"{self.__module__}.{self.__class__.__name__}({self._locales!r}, "
            f"{', '.join(f'{k}={v!r}' for k, v in self.to_dict().items())})"
        )


class City(Country):
    """Model for the City Plus web service and the City database."""

    city: geoip2.records.City
    """City object for the requested IP address."""

    location: geoip2.records.Location
    """Location object for the requested IP address."""

    postal: geoip2.records.Postal
    """Postal object for the requested IP address."""

    subdivisions: geoip2.records.Subdivisions
    """Object (tuple) representing the subdivisions of the country to which
    the location of the requested IP address belongs.
    """

    def __init__(
        self,
        locales: Sequence[str] | None,
        *,
        city: dict[str, Any] | None = None,
        continent: dict[str, Any] | None = None,
        country: dict[str, Any] | None = None,
        location: dict[str, Any] | None = None,
        ip_address: IPAddress | None = None,
        maxmind: dict[str, Any] | None = None,
        postal: dict[str, Any] | None = None,
        prefix_len: int | None = None,
        registered_country: dict[str, Any] | None = None,
        represented_country: dict[str, Any] | None = None,
        subdivisions: list[dict[str, Any]] | None = None,
        traits: dict[str, Any] | None = None,
        **_: Any,
    ) -> None:
        super().__init__(
            locales,
            continent=continent,
            country=country,
            ip_address=ip_address,
            maxmind=maxmind,
            prefix_len=prefix_len,
            registered_country=registered_country,
            represented_country=represented_country,
            traits=traits,
        )
        self.city = geoip2.records.City(locales, **(city or {}))
        self.location = geoip2.records.Location(**(location or {}))
        self.postal = geoip2.records.Postal(**(postal or {}))
        self.subdivisions = geoip2.records.Subdivisions(locales, *(subdivisions or []))


class Insights(City):
    """Model for the GeoIP2 Insights web service."""

    anonymizer: geoip2.records.Anonymizer
    """Anonymizer object for the requested IP address. This object contains
    information about VPN and proxy usage.
    """

    def __init__(
        self,
        locales: Sequence[str] | None,
        *,
        anonymizer: dict[str, Any] | None = None,
        city: dict[str, Any] | None = None,
        continent: dict[str, Any] | None = None,
        country: dict[str, Any] | None = None,
        location: dict[str, Any] | None = None,
        ip_address: IPAddress | None = None,
        maxmind: dict[str, Any] | None = None,
        postal: dict[str, Any] | None = None,
        prefix_len: int | None = None,
        registered_country: dict[str, Any] | None = None,
        represented_country: dict[str, Any] | None = None,
        subdivisions: list[dict[str, Any]] | None = None,
        traits: dict[str, Any] | None = None,
        **_: Any,
    ) -> None:
        super().__init__(
            locales,
            city=city,
            continent=continent,
            country=country,
            location=location,
            ip_address=ip_address,
            maxmind=maxmind,
            postal=postal,
            prefix_len=prefix_len,
            registered_country=registered_country,
            represented_country=represented_country,
            subdivisions=subdivisions,
            traits=traits,
        )
        self.anonymizer = geoip2.records.Anonymizer(**(anonymizer or {}))


class Enterprise(City):
    """Model for the GeoIP2 Enterprise database."""


class SimpleModel(Model, metaclass=ABCMeta):
    """Provides basic methods for non-location models."""

    _ip_address: IPAddress
    _network: ipaddress.IPv4Network | ipaddress.IPv6Network | None
    _prefix_len: int | None

    def __init__(
        self,
        ip_address: IPAddress,
        network: str | None,
        prefix_len: int | None,
    ) -> None:
        if network:
            self._network = ipaddress.ip_network(network, strict=False)
            self._prefix_len = self._network.prefixlen
        else:
            # This case is for MMDB lookups where performance is paramount.
            # This is why we don't generate the network unless .network is
            # used.
            self._network = None
            self._prefix_len = prefix_len
        self._ip_address = ip_address

    def __repr__(self) -> str:
        d = self.to_dict()
        d.pop("ip_address", None)
        return (
            f"{self.__module__}.{self.__class__.__name__}("
            + repr(str(self._ip_address))
            + ", "
            + ", ".join(f"{k}={v!r}" for k, v in d.items())
            + ")"
        )

    @property
    def ip_address(self) -> IPv4Address | IPv6Address:
        """The IP address for the record."""
        if not isinstance(self._ip_address, (IPv4Address, IPv6Address)):
            self._ip_address = ipaddress.ip_address(self._ip_address)
        return self._ip_address

    @property
    def network(self) -> ipaddress.IPv4Network | ipaddress.IPv6Network | None:
        """The network associated with the record.

        In particular, this is the largest network where all of the fields besides
        ``ip_address`` have the same value.
        """
        # This code is duplicated for performance reasons
        network = self._network
        if network is not None:
            return network

        ip_address = self.ip_address
        prefix_len = self._prefix_len
        if ip_address is None or prefix_len is None:
            return None
        network = ipaddress.ip_network(f"{ip_address}/{prefix_len}", strict=False)
        self._network = network
        return network


class AnonymousIP(SimpleModel):
    """Model class for the GeoIP2 Anonymous IP."""

    is_anonymous: bool
    """This is true if the IP address belongs to any sort of anonymous network."""

    is_anonymous_vpn: bool
    """This is true if the IP address is registered to an anonymous VPN
    provider.

    If a VPN provider does not register subnets under names associated with
    them, we will likely only flag their IP ranges using the
    ``is_hosting_provider`` attribute.
    """

    is_hosting_provider: bool
    """This is true if the IP address belongs to a hosting or VPN provider
    (see description of ``is_anonymous_vpn`` attribute).
    """

    is_public_proxy: bool
    """This is true if the IP address belongs to a public proxy."""

    is_residential_proxy: bool
    """This is true if the IP address is on a suspected anonymizing network
    and belongs to a residential ISP.
    """

    is_tor_exit_node: bool
    """This is true if the IP address is a Tor exit node."""

    def __init__(
        self,
        ip_address: IPAddress,
        *,
        is_anonymous: bool = False,
        is_anonymous_vpn: bool = False,
        is_hosting_provider: bool = False,
        is_public_proxy: bool = False,
        is_residential_proxy: bool = False,
        is_tor_exit_node: bool = False,
        network: str | None = None,
        prefix_len: int | None = None,
        **_: Any,
    ) -> None:
        super().__init__(ip_address, network, prefix_len)
        self.is_anonymous = is_anonymous
        self.is_anonymous_vpn = is_anonymous_vpn
        self.is_hosting_provider = is_hosting_provider
        self.is_public_proxy = is_public_proxy
        self.is_residential_proxy = is_residential_proxy
        self.is_tor_exit_node = is_tor_exit_node


class AnonymousPlus(AnonymousIP):
    """Model class for the GeoIP Anonymous Plus."""

    anonymizer_confidence: int | None
    """A score ranging from 1 to 99 that is our percent confidence that the
    network is currently part of an actively used VPN service.
    """

    network_last_seen: datetime.date | None
    """The last day that the network was sighted in our analysis of anonymized
    networks.
    """

    provider_name: str | None
    """The name of the VPN provider (e.g., NordVPN, SurfShark, etc.) associated
    with the network.
    """

    def __init__(
        self,
        ip_address: IPAddress,
        *,
        anonymizer_confidence: int | None = None,
        is_anonymous: bool = False,
        is_anonymous_vpn: bool = False,
        is_hosting_provider: bool = False,
        is_public_proxy: bool = False,
        is_residential_proxy: bool = False,
        is_tor_exit_node: bool = False,
        network: str | None = None,
        network_last_seen: str | None = None,
        prefix_len: int | None = None,
        provider_name: str | None = None,
        **_: Any,
    ) -> None:
        super().__init__(
            is_anonymous=is_anonymous,
            is_anonymous_vpn=is_anonymous_vpn,
            is_hosting_provider=is_hosting_provider,
            is_public_proxy=is_public_proxy,
            is_residential_proxy=is_residential_proxy,
            is_tor_exit_node=is_tor_exit_node,
            ip_address=ip_address,
            network=network,
            prefix_len=prefix_len,
        )
        self.anonymizer_confidence = anonymizer_confidence
        if network_last_seen is not None:
            self.network_last_seen = datetime.date.fromisoformat(network_last_seen)
        self.provider_name = provider_name


class ASN(SimpleModel):
    """Model class for the GeoLite2 ASN."""

    autonomous_system_number: int | None
    """The autonomous system number associated with the IP address."""

    autonomous_system_organization: str | None
    """The organization associated with the registered autonomous system number
    for the IP address.
    """

    def __init__(
        self,
        ip_address: IPAddress,
        *,
        autonomous_system_number: int | None = None,
        autonomous_system_organization: str | None = None,
        network: str | None = None,
        prefix_len: int | None = None,
        **_: Any,
    ) -> None:
        super().__init__(ip_address, network, prefix_len)
        self.autonomous_system_number = autonomous_system_number
        self.autonomous_system_organization = autonomous_system_organization


class ConnectionType(SimpleModel):
    """Model class for the GeoIP2 Connection-Type."""

    connection_type: str | None
    """The connection type may take the following values:

    - Dialup
    - Cable/DSL
    - Corporate
    - Cellular
    - Satellite

    Additional values may be added in the future.
    """

    def __init__(
        self,
        ip_address: IPAddress,
        *,
        connection_type: str | None = None,
        network: str | None = None,
        prefix_len: int | None = None,
        **_: Any,
    ) -> None:
        super().__init__(ip_address, network, prefix_len)
        self.connection_type = connection_type


class Domain(SimpleModel):
    """Model class for the GeoIP2 Domain."""

    domain: str | None
    """The domain associated with the IP address."""

    def __init__(
        self,
        ip_address: IPAddress,
        *,
        domain: str | None = None,
        network: str | None = None,
        prefix_len: int | None = None,
        **_: Any,
    ) -> None:
        super().__init__(ip_address, network, prefix_len)
        self.domain = domain


class ISP(ASN):
    """Model class for the GeoIP2 ISP."""

    isp: str | None
    """The name of the ISP associated with the IP address."""

    mobile_country_code: str | None
    """The `mobile country code (MCC)
    <https://en.wikipedia.org/wiki/Mobile_country_code>`_ associated with the
    IP address and ISP.
    """

    mobile_network_code: str | None
    """The `mobile network code (MNC)
    <https://en.wikipedia.org/wiki/Mobile_country_code>`_ associated with the
    IP address and ISP.
    """

    organization: str | None
    """The name of the organization associated with the IP address."""

    def __init__(
        self,
        ip_address: IPAddress,
        *,
        autonomous_system_number: int | None = None,
        autonomous_system_organization: str | None = None,
        isp: str | None = None,
        mobile_country_code: str | None = None,
        mobile_network_code: str | None = None,
        organization: str | None = None,
        network: str | None = None,
        prefix_len: int | None = None,
        **_: Any,
    ) -> None:
        super().__init__(
            autonomous_system_number=autonomous_system_number,
            autonomous_system_organization=autonomous_system_organization,
            ip_address=ip_address,
            network=network,
            prefix_len=prefix_len,
        )
        self.isp = isp
        self.mobile_country_code = mobile_country_code
        self.mobile_network_code = mobile_network_code
        self.organization = organization
