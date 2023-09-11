"""
Models
======

These classes provide models for the data returned by the GeoIP2
web service and databases.

The only difference between the City and Insights model classes is which
fields in each record may be populated. See
https://dev.maxmind.com/geoip/docs/web-services?lang=en for more details.

"""
# pylint: disable=too-many-instance-attributes,too-few-public-methods
import ipaddress
from abc import ABCMeta
from typing import Any, cast, Dict, List, Optional, Union

import geoip2.records
from geoip2.mixins import SimpleEquality


class Country(SimpleEquality):
    """Model for the Country web service and Country database.

    This class provides the following attributes:

    .. attribute:: continent

      Continent object for the requested IP address.

      :type: :py:class:`geoip2.records.Continent`

    .. attribute:: country

      Country object for the requested IP address. This record represents the
      country where MaxMind believes the IP is located.

      :type: :py:class:`geoip2.records.Country`

    .. attribute:: maxmind

      Information related to your MaxMind account.

      :type: :py:class:`geoip2.records.MaxMind`

    .. attribute:: registered_country

      The registered country object for the requested IP address. This record
      represents the country where the ISP has registered a given IP block in
      and may differ from the user's country.

      :type: :py:class:`geoip2.records.Country`

    .. attribute:: represented_country

      Object for the country represented by the users of the IP address
      when that country is different than the country in ``country``. For
      instance, the country represented by an overseas military base.

      :type: :py:class:`geoip2.records.RepresentedCountry`

    .. attribute:: traits

      Object with the traits of the requested IP address.

      :type: :py:class:`geoip2.records.Traits`

    """

    continent: geoip2.records.Continent
    country: geoip2.records.Country
    maxmind: geoip2.records.MaxMind
    registered_country: geoip2.records.Country
    represented_country: geoip2.records.RepresentedCountry
    traits: geoip2.records.Traits

    def __init__(
        self, raw_response: Dict[str, Any], locales: Optional[List[str]] = None
    ) -> None:
        if locales is None:
            locales = ["en"]
        self._locales = locales
        self.continent = geoip2.records.Continent(
            locales, **raw_response.get("continent", {})
        )
        self.country = geoip2.records.Country(
            locales, **raw_response.get("country", {})
        )
        self.registered_country = geoip2.records.Country(
            locales, **raw_response.get("registered_country", {})
        )
        self.represented_country = geoip2.records.RepresentedCountry(
            locales, **raw_response.get("represented_country", {})
        )

        self.maxmind = geoip2.records.MaxMind(**raw_response.get("maxmind", {}))

        self.traits = geoip2.records.Traits(**raw_response.get("traits", {}))
        self.raw = raw_response

    def __repr__(self) -> str:
        return (
            f"{self.__module__}.{self.__class__.__name__}({self.raw}, {self._locales})"
        )


class City(Country):
    """Model for the City Plus web service and the City database.

    .. attribute:: city

      City object for the requested IP address.

      :type: :py:class:`geoip2.records.City`

    .. attribute:: continent

      Continent object for the requested IP address.

      :type: :py:class:`geoip2.records.Continent`

    .. attribute:: country

      Country object for the requested IP address. This record represents the
      country where MaxMind believes the IP is located.

      :type: :py:class:`geoip2.records.Country`

    .. attribute:: location

      Location object for the requested IP address.

      :type: :py:class:`geoip2.records.Location`

    .. attribute:: maxmind

      Information related to your MaxMind account.

      :type: :py:class:`geoip2.records.MaxMind`

    .. attribute:: postal

      Postal object for the requested IP address.

      :type: :py:class:`geoip2.records.Postal`

    .. attribute:: registered_country

      The registered country object for the requested IP address. This record
      represents the country where the ISP has registered a given IP block in
      and may differ from the user's country.

      :type: :py:class:`geoip2.records.Country`

    .. attribute:: represented_country

      Object for the country represented by the users of the IP address
      when that country is different than the country in ``country``. For
      instance, the country represented by an overseas military base.

      :type: :py:class:`geoip2.records.RepresentedCountry`

    .. attribute:: subdivisions

      Object (tuple) representing the subdivisions of the country to which
      the location of the requested IP address belongs.

      :type: :py:class:`geoip2.records.Subdivisions`

    .. attribute:: traits

      Object with the traits of the requested IP address.

      :type: :py:class:`geoip2.records.Traits`

    """

    city: geoip2.records.City
    location: geoip2.records.Location
    postal: geoip2.records.Postal
    subdivisions: geoip2.records.Subdivisions

    def __init__(
        self, raw_response: Dict[str, Any], locales: Optional[List[str]] = None
    ) -> None:
        super().__init__(raw_response, locales)
        self.city = geoip2.records.City(locales, **raw_response.get("city", {}))
        self.location = geoip2.records.Location(**raw_response.get("location", {}))
        self.postal = geoip2.records.Postal(**raw_response.get("postal", {}))
        self.subdivisions = geoip2.records.Subdivisions(
            locales, *raw_response.get("subdivisions", [])
        )


class Insights(City):
    """Model for the GeoIP2 Insights web service.

    .. attribute:: city

      City object for the requested IP address.

      :type: :py:class:`geoip2.records.City`

    .. attribute:: continent

      Continent object for the requested IP address.

      :type: :py:class:`geoip2.records.Continent`

    .. attribute:: country

      Country object for the requested IP address. This record represents the
      country where MaxMind believes the IP is located.

      :type: :py:class:`geoip2.records.Country`

    .. attribute:: location

      Location object for the requested IP address.

    .. attribute:: maxmind

      Information related to your MaxMind account.

      :type: :py:class:`geoip2.records.MaxMind`

    .. attribute:: registered_country

      The registered country object for the requested IP address. This record
      represents the country where the ISP has registered a given IP block in
      and may differ from the user's country.

      :type: :py:class:`geoip2.records.Country`

    .. attribute:: represented_country

      Object for the country represented by the users of the IP address
      when that country is different than the country in ``country``. For
      instance, the country represented by an overseas military base.

      :type: :py:class:`geoip2.records.RepresentedCountry`

    .. attribute:: subdivisions

      Object (tuple) representing the subdivisions of the country to which
      the location of the requested IP address belongs.

      :type: :py:class:`geoip2.records.Subdivisions`

    .. attribute:: traits

      Object with the traits of the requested IP address.

      :type: :py:class:`geoip2.records.Traits`

    """


class Enterprise(City):
    """Model for the GeoIP2 Enterprise database.

    .. attribute:: city

      City object for the requested IP address.

      :type: :py:class:`geoip2.records.City`

    .. attribute:: continent

      Continent object for the requested IP address.

      :type: :py:class:`geoip2.records.Continent`

    .. attribute:: country

      Country object for the requested IP address. This record represents the
      country where MaxMind believes the IP is located.

      :type: :py:class:`geoip2.records.Country`

    .. attribute:: location

      Location object for the requested IP address.

    .. attribute:: maxmind

      Information related to your MaxMind account.

      :type: :py:class:`geoip2.records.MaxMind`

    .. attribute:: registered_country

      The registered country object for the requested IP address. This record
      represents the country where the ISP has registered a given IP block in
      and may differ from the user's country.

      :type: :py:class:`geoip2.records.Country`

    .. attribute:: represented_country

      Object for the country represented by the users of the IP address
      when that country is different than the country in ``country``. For
      instance, the country represented by an overseas military base.

      :type: :py:class:`geoip2.records.RepresentedCountry`

    .. attribute:: subdivisions

      Object (tuple) representing the subdivisions of the country to which
      the location of the requested IP address belongs.

      :type: :py:class:`geoip2.records.Subdivisions`

    .. attribute:: traits

      Object with the traits of the requested IP address.

      :type: :py:class:`geoip2.records.Traits`

    """


class SimpleModel(SimpleEquality, metaclass=ABCMeta):
    """Provides basic methods for non-location models"""

    raw: Dict[str, Union[bool, str, int]]
    ip_address: str
    _network: Optional[Union[ipaddress.IPv4Network, ipaddress.IPv6Network]]
    _prefix_len: int

    def __init__(self, raw: Dict[str, Union[bool, str, int]]) -> None:
        self.raw = raw
        self._network = None
        self._prefix_len = cast(int, raw.get("prefix_len"))
        self.ip_address = cast(str, raw.get("ip_address"))

    def __repr__(self) -> str:
        return f"{self.__module__}.{self.__class__.__name__}({self.raw})"

    @property
    def network(self) -> Optional[Union[ipaddress.IPv4Network, ipaddress.IPv6Network]]:
        """The network for the record"""
        # This code is duplicated for performance reasons
        network = self._network
        if network is not None:
            return network

        ip_address = self.ip_address
        prefix_len = self._prefix_len
        if ip_address is None or prefix_len is None:
            return None
        network = ipaddress.ip_network(f"{ip_address}/{prefix_len}", False)
        self._network = network
        return network


class AnonymousIP(SimpleModel):
    """Model class for the GeoIP2 Anonymous IP.

    This class provides the following attribute:

    .. attribute:: is_anonymous

      This is true if the IP address belongs to any sort of anonymous network.

      :type: bool

    .. attribute:: is_anonymous_vpn

      This is true if the IP address is registered to an anonymous VPN
      provider.

      If a VPN provider does not register subnets under names associated with
      them, we will likely only flag their IP ranges using the
      ``is_hosting_provider`` attribute.

      :type: bool

    .. attribute:: is_hosting_provider

      This is true if the IP address belongs to a hosting or VPN provider
      (see description of ``is_anonymous_vpn`` attribute).

      :type: bool

    .. attribute:: is_public_proxy

      This is true if the IP address belongs to a public proxy.

      :type: bool

    .. attribute:: is_residential_proxy

      This is true if the IP address is on a suspected anonymizing network
      and belongs to a residential ISP.

      :type: bool

    .. attribute:: is_tor_exit_node

      This is true if the IP address is a Tor exit node.

      :type: bool

    .. attribute:: ip_address

      The IP address used in the lookup.

      :type: str

    .. attribute:: network

      The network associated with the record. In particular, this is the
      largest network where all of the fields besides ip_address have the same
      value.

      :type: ipaddress.IPv4Network or ipaddress.IPv6Network
    """

    is_anonymous: bool
    is_anonymous_vpn: bool
    is_hosting_provider: bool
    is_public_proxy: bool
    is_residential_proxy: bool
    is_tor_exit_node: bool

    def __init__(self, raw: Dict[str, bool]) -> None:
        super().__init__(raw)  # type: ignore
        self.is_anonymous = raw.get("is_anonymous", False)
        self.is_anonymous_vpn = raw.get("is_anonymous_vpn", False)
        self.is_hosting_provider = raw.get("is_hosting_provider", False)
        self.is_public_proxy = raw.get("is_public_proxy", False)
        self.is_residential_proxy = raw.get("is_residential_proxy", False)
        self.is_tor_exit_node = raw.get("is_tor_exit_node", False)


class ASN(SimpleModel):
    """Model class for the GeoLite2 ASN.

    This class provides the following attribute:

    .. attribute:: autonomous_system_number

      The autonomous system number associated with the IP address.

      :type: int

    .. attribute:: autonomous_system_organization

      The organization associated with the registered autonomous system number
      for the IP address.

      :type: str

    .. attribute:: ip_address

      The IP address used in the lookup.

      :type: str

    .. attribute:: network

      The network associated with the record. In particular, this is the
      largest network where all of the fields besides ip_address have the same
      value.

      :type: ipaddress.IPv4Network or ipaddress.IPv6Network
    """

    autonomous_system_number: Optional[int]
    autonomous_system_organization: Optional[str]

    # pylint:disable=too-many-arguments
    def __init__(self, raw: Dict[str, Union[str, int]]) -> None:
        super().__init__(raw)
        self.autonomous_system_number = cast(
            Optional[int], raw.get("autonomous_system_number")
        )
        self.autonomous_system_organization = cast(
            Optional[str], raw.get("autonomous_system_organization")
        )


class ConnectionType(SimpleModel):
    """Model class for the GeoIP2 Connection-Type.

    This class provides the following attribute:

    .. attribute:: connection_type

      The connection type may take the following values:

      - Dialup
      - Cable/DSL
      - Corporate
      - Cellular

      Additional values may be added in the future.

      :type: str

    .. attribute:: ip_address

      The IP address used in the lookup.

      :type: str

    .. attribute:: network

      The network associated with the record. In particular, this is the
      largest network where all of the fields besides ip_address have the same
      value.

      :type: ipaddress.IPv4Network or ipaddress.IPv6Network
    """

    connection_type: Optional[str]

    def __init__(self, raw: Dict[str, Union[str, int]]) -> None:
        super().__init__(raw)
        self.connection_type = cast(Optional[str], raw.get("connection_type"))


class Domain(SimpleModel):
    """Model class for the GeoIP2 Domain.

    This class provides the following attribute:

    .. attribute:: domain

      The domain associated with the IP address.

      :type: str

    .. attribute:: ip_address

      The IP address used in the lookup.

      :type: str

    .. attribute:: network

      The network associated with the record. In particular, this is the
      largest network where all of the fields besides ip_address have the same
      value.

      :type: ipaddress.IPv4Network or ipaddress.IPv6Network

    """

    domain: Optional[str]

    def __init__(self, raw: Dict[str, Union[str, int]]) -> None:
        super().__init__(raw)
        self.domain = cast(Optional[str], raw.get("domain"))


class ISP(ASN):
    """Model class for the GeoIP2 ISP.

    This class provides the following attribute:

    .. attribute:: autonomous_system_number

      The autonomous system number associated with the IP address.

      :type: int

    .. attribute:: autonomous_system_organization

      The organization associated with the registered autonomous system number
      for the IP address.

      :type: str

    .. attribute:: isp

      The name of the ISP associated with the IP address.

      :type: str

    .. attribute: mobile_country_code

      The `mobile country code (MCC)
      <https://en.wikipedia.org/wiki/Mobile_country_code>`_ associated with the
      IP address and ISP.

      :type: str

    .. attribute: mobile_network_code

      The `mobile network code (MNC)
      <https://en.wikipedia.org/wiki/Mobile_country_code>`_ associated with the
      IP address and ISP.

      :type: str

    .. attribute:: organization

      The name of the organization associated with the IP address.

      :type: str

    .. attribute:: ip_address

      The IP address used in the lookup.

      :type: str

    .. attribute:: network

      The network associated with the record. In particular, this is the
      largest network where all of the fields besides ip_address have the same
      value.

      :type: ipaddress.IPv4Network or ipaddress.IPv6Network
    """

    isp: Optional[str]
    mobile_country_code: Optional[str]
    mobile_network_code: Optional[str]
    organization: Optional[str]

    # pylint:disable=too-many-arguments
    def __init__(self, raw: Dict[str, Union[str, int]]) -> None:
        super().__init__(raw)
        self.isp = cast(Optional[str], raw.get("isp"))
        self.mobile_country_code = cast(Optional[str], raw.get("mobile_country_code"))
        self.mobile_network_code = cast(Optional[str], raw.get("mobile_network_code"))
        self.organization = cast(Optional[str], raw.get("organization"))
