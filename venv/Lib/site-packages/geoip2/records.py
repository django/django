"""Record classes used within the response models."""

from __future__ import annotations

import datetime
import ipaddress
from abc import ABCMeta
from ipaddress import IPv4Address, IPv6Address
from typing import TYPE_CHECKING, Any

from geoip2._internal import Model

if TYPE_CHECKING:
    from collections.abc import Sequence

    from typing_extensions import Self

    from geoip2.types import IPAddress


class Record(Model, metaclass=ABCMeta):
    """All records are subclasses of the abstract class ``Record``."""

    def __repr__(self) -> str:
        args = ", ".join(f"{k}={v!r}" for k, v in self.to_dict().items())
        return f"{self.__module__}.{self.__class__.__name__}({args})"


class PlaceRecord(Record, metaclass=ABCMeta):
    """All records with :py:attr:`names` subclass :py:class:`PlaceRecord`."""

    names: dict[str, str]
    """A dictionary where the keys are locale codes and the values are names."""
    _locales: Sequence[str]

    def __init__(
        self,
        locales: Sequence[str] | None,
        names: dict[str, str] | None,
    ) -> None:
        if locales is None:
            locales = ["en"]
        self._locales = locales
        if names is None:
            names = {}
        self.names = names

    @property
    def name(self) -> str | None:
        """The name based on the locales list passed to the constructor."""
        return next((self.names.get(x) for x in self._locales if x in self.names), None)


class City(PlaceRecord):
    """Contains data for the city record associated with an IP address.

    This class contains the city-level data associated with an IP address.

    This record is returned by ``city``, ``enterprise``, and ``insights``.
    """

    confidence: int | None
    """A value from 0-100 indicating MaxMind's
    confidence that the city is correct. This attribute is only available
    from the Insights end point and the Enterprise database.
    """
    geoname_id: int | None
    """The GeoName ID for the city."""

    def __init__(
        self,
        locales: Sequence[str] | None,
        *,
        confidence: int | None = None,
        geoname_id: int | None = None,
        names: dict[str, str] | None = None,
        **_: Any,
    ) -> None:
        self.confidence = confidence
        self.geoname_id = geoname_id
        super().__init__(locales, names)


class Continent(PlaceRecord):
    """Contains data for the continent record associated with an IP address.

    This class contains the continent-level data associated with an IP
    address.
    """

    code: str | None
    """A two character continent code like "NA" (North America)
    or "OC" (Oceania).
    """
    geoname_id: int | None
    """The GeoName ID for the continent."""

    def __init__(
        self,
        locales: Sequence[str] | None,
        *,
        code: str | None = None,
        geoname_id: int | None = None,
        names: dict[str, str] | None = None,
        **_: Any,
    ) -> None:
        self.code = code
        self.geoname_id = geoname_id
        super().__init__(locales, names)


class Country(PlaceRecord):
    """Contains data for the country record associated with an IP address.

    This class contains the country-level data associated with an IP address.
    """

    confidence: int | None
    """A value from 0-100 indicating MaxMind's confidence that
    the country is correct. This attribute is only available from the
    Insights end point and the Enterprise database.
    """
    geoname_id: int | None
    """The GeoName ID for the country."""
    is_in_european_union: bool
    """This is true if the country is a member state of the European Union."""
    iso_code: str | None
    """The two-character `ISO 3166-1
    <https://en.wikipedia.org/wiki/ISO_3166-1>`_ alpha code for the
    country.
    """

    def __init__(
        self,
        locales: Sequence[str] | None,
        *,
        confidence: int | None = None,
        geoname_id: int | None = None,
        is_in_european_union: bool = False,
        iso_code: str | None = None,
        names: dict[str, str] | None = None,
        **_: Any,
    ) -> None:
        self.confidence = confidence
        self.geoname_id = geoname_id
        self.is_in_european_union = is_in_european_union
        self.iso_code = iso_code
        super().__init__(locales, names)


class RepresentedCountry(Country):
    """Contains data for the represented country associated with an IP address.

    This class contains the country-level data associated with an IP address
    for the IP's represented country. The represented country is the country
    represented by something like a military base.
    """

    type: str | None
    """A string indicating the type of entity that is representing the
    country. Currently we only return ``military`` but this could expand to
    include other types in the future.
    """

    def __init__(
        self,
        locales: Sequence[str] | None,
        *,
        confidence: int | None = None,
        geoname_id: int | None = None,
        is_in_european_union: bool = False,
        iso_code: str | None = None,
        names: dict[str, str] | None = None,
        type: str | None = None,  # noqa: A002
        **_: Any,
    ) -> None:
        self.type = type
        super().__init__(
            locales,
            confidence=confidence,
            geoname_id=geoname_id,
            is_in_european_union=is_in_european_union,
            iso_code=iso_code,
            names=names,
        )


class Location(Record):
    """Contains data for the location record associated with an IP address.

    This class contains the location data associated with an IP address.

    This record is returned by ``city``, ``enterprise``, and ``insights``.
    """

    average_income: int | None
    """The average income in US dollars associated with the requested IP
    address. This attribute is only available from the Insights end point.
    """
    accuracy_radius: int | None
    """The approximate accuracy radius in kilometers around the latitude and
    longitude for the IP address. This is the radius where we have a 67%
    confidence that the device using the IP address resides within the
    circle centered at the latitude and longitude with the provided radius.
    """
    latitude: float | None
    """The approximate latitude of the location associated with the IP
    address. This value is not precise and should not be used to identify a
    particular address or household.
    """
    longitude: float | None
    """The approximate longitude of the location associated with the IP
    address. This value is not precise and should not be used to identify a
    particular address or household.
    """
    metro_code: int | None
    """The metro code is a no-longer-maintained code for targeting
    advertisements in Google.

    .. deprecated:: 4.9.0
    """
    population_density: int | None
    """The estimated population per square kilometer associated with the IP
    address. This attribute is only available from the Insights end point.
    """
    time_zone: str | None
    """The time zone associated with location, as specified by the `IANA Time
    Zone Database <https://www.iana.org/time-zones>`_, e.g.,
    "America/New_York".
    """

    def __init__(
        self,
        *,
        average_income: int | None = None,
        accuracy_radius: int | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
        metro_code: int | None = None,
        population_density: int | None = None,
        time_zone: str | None = None,
        **_: Any,
    ) -> None:
        self.average_income = average_income
        self.accuracy_radius = accuracy_radius
        self.latitude = latitude
        self.longitude = longitude
        self.metro_code = metro_code
        self.population_density = population_density
        self.time_zone = time_zone


class MaxMind(Record):
    """Contains data related to your MaxMind account."""

    queries_remaining: int | None
    """The number of remaining queries you have for the end point you are
    calling.
    """

    def __init__(self, *, queries_remaining: int | None = None, **_: Any) -> None:
        self.queries_remaining = queries_remaining


class Anonymizer(Record):
    """Contains data for the anonymizer record associated with an IP address.

    This class contains the anonymizer data associated with an IP address.

    This record is returned by ``insights``.
    """

    confidence: int | None
    """A score ranging from 1 to 99 that represents our percent confidence that
    the network is currently part of an actively used VPN service. Currently
    only values 30 and 99 are provided. This attribute is only available from
    the Insights end point.
    """

    network_last_seen: datetime.date | None
    """The last day that the network was sighted in our analysis of anonymized
    networks. This attribute is only available from the Insights end point.
    """

    provider_name: str | None
    """The name of the VPN provider (e.g., NordVPN, SurfShark, etc.) associated
    with the network. This attribute is only available from the Insights end
    point.
    """

    is_anonymous: bool
    """This is true if the IP address belongs to any sort of anonymous network.
    This attribute is only available from the Insights end point.
    """

    is_anonymous_vpn: bool
    """This is true if the IP address is registered to an anonymous VPN provider.

    If a VPN provider does not register subnets under names associated with
    them, we will likely only flag their IP ranges using the
    ``is_hosting_provider`` attribute.

    This attribute is only available from the Insights end point.
    """

    is_hosting_provider: bool
    """This is true if the IP address belongs to a hosting or VPN provider
    (see description of ``is_anonymous_vpn`` attribute). This attribute is only
    available from the Insights end point.
    """

    is_public_proxy: bool
    """This is true if the IP address belongs to a public proxy. This attribute
    is only available from the Insights end point.
    """

    is_residential_proxy: bool
    """This is true if the IP address is on a suspected anonymizing network
    and belongs to a residential ISP. This attribute is only available from the
    Insights end point.
    """

    is_tor_exit_node: bool
    """This is true if the IP address is a Tor exit node. This attribute is only
    available from the Insights end point.
    """

    def __init__(
        self,
        *,
        confidence: int | None = None,
        is_anonymous: bool = False,
        is_anonymous_vpn: bool = False,
        is_hosting_provider: bool = False,
        is_public_proxy: bool = False,
        is_residential_proxy: bool = False,
        is_tor_exit_node: bool = False,
        network_last_seen: str | None = None,
        provider_name: str | None = None,
        **_: Any,
    ) -> None:
        self.confidence = confidence
        self.is_anonymous = is_anonymous
        self.is_anonymous_vpn = is_anonymous_vpn
        self.is_hosting_provider = is_hosting_provider
        self.is_public_proxy = is_public_proxy
        self.is_residential_proxy = is_residential_proxy
        self.is_tor_exit_node = is_tor_exit_node
        self.network_last_seen = (
            datetime.date.fromisoformat(network_last_seen)
            if network_last_seen
            else None
        )
        self.provider_name = provider_name


class Postal(Record):
    """Contains data for the postal record associated with an IP address.

    This class contains the postal data associated with an IP address.

    This attribute is returned by ``city``, ``enterprise``, and ``insights``.
    """

    code: str | None
    """The postal code of the location. Postal codes are not available for
    all countries. In some countries, this will only contain part of the
    postal code.
    """
    confidence: int | None
    """A value from 0-100 indicating MaxMind's confidence that the postal code
    is correct. This attribute is only available from the Insights end point
    and the Enterprise database.
    """

    def __init__(
        self,
        *,
        code: str | None = None,
        confidence: int | None = None,
        **_: Any,
    ) -> None:
        self.code = code
        self.confidence = confidence


class Subdivision(PlaceRecord):
    """Contains data for the subdivisions associated with an IP address.

    This class contains the subdivision data associated with an IP address.

    This attribute is returned by ``city``, ``enterprise``, and ``insights``.
    """

    confidence: int | None
    """This is a value from 0-100 indicating MaxMind's confidence that the
    subdivision is correct. This attribute is only available from the Insights
    end point and the Enterprise database.
    """
    geoname_id: int | None
    """This is a GeoName ID for the subdivision."""
    iso_code: str | None
    """This is a string up to three characters long contain the subdivision
    portion of the `ISO 3166-2 code <https://en.wikipedia.org/wiki/ISO_3166-2>`_.
    """

    def __init__(
        self,
        locales: Sequence[str] | None,
        *,
        confidence: int | None = None,
        geoname_id: int | None = None,
        iso_code: str | None = None,
        names: dict[str, str] | None = None,
        **_: Any,
    ) -> None:
        self.confidence = confidence
        self.geoname_id = geoname_id
        self.iso_code = iso_code
        super().__init__(locales, names)


class Subdivisions(tuple):  # noqa: SLOT001
    """A tuple-like collection of subdivisions associated with an IP address.

    This class contains the subdivisions of the country associated with the
    IP address from largest to smallest.

    For instance, the response for Oxford in the United Kingdom would have
    England as the first element and Oxfordshire as the second element.

    This attribute is returned by ``city``, ``enterprise``, and ``insights``.
    """

    def __new__(
        cls: type[Self],
        locales: Sequence[str] | None,
        *subdivisions: dict[str, Any],
    ) -> Self:
        """Create a new Subdivisions instance.

        This method constructs the tuple with Subdivision objects created
        from the provided dictionaries.

        Arguments:
            cls: The class to instantiate (Subdivisions).
            locales: A sequence of locale strings (e.g., ['en', 'fr'])
                or None, passed to each Subdivision object.
            *subdivisions: A variable number of dictionaries, where each
                dictionary contains the data for a single :py:class:`Subdivision`
                object (e.g., name, iso_code).

        Returns:
            A new instance of Subdivisions containing :py:class:`Subdivision` objects.

        """
        subobjs = tuple(Subdivision(locales, **x) for x in subdivisions)
        return super().__new__(cls, subobjs)

    def __init__(
        self,
        locales: Sequence[str] | None,
        *_: dict[str, Any],
    ) -> None:
        """Initialize the Subdivisions instance."""
        self._locales = locales
        super().__init__()

    @property
    def most_specific(self) -> Subdivision:
        """The most specific (smallest) subdivision available.

        If there are no :py:class:`Subdivision` objects for the response,
        this returns an empty :py:class:`Subdivision`.
        """
        try:
            return self[-1]
        except IndexError:
            return Subdivision(self._locales)


class Traits(Record):
    """Contains data for the traits record associated with an IP address.

    This class contains the traits data associated with an IP address.
    """

    autonomous_system_number: int | None
    """The `autonomous system
    number <https://en.wikipedia.org/wiki/Autonomous_system_(Internet)>`_
    associated with the IP address. This attribute is only available from
    the City Plus and Insights web services and the Enterprise database.
    """
    autonomous_system_organization: str | None
    """The organization associated with the registered `autonomous system
    number <https://en.wikipedia.org/wiki/Autonomous_system_(Internet)>`_ for
    the IP address. This attribute is only available from the City Plus and
    Insights web service end points and the Enterprise database.
    """
    connection_type: str | None
    """The connection type may take the following values:

    - Dialup
    - Cable/DSL
    - Corporate
    - Cellular
    - Satellite

    Additional values may be added in the future.

    This attribute is only available from the City Plus and Insights web
    service end points and the Enterprise database.
    """
    domain: str | None
    """The second level domain associated with the
    IP address. This will be something like "example.com" or
    "example.co.uk", not "foo.example.com". This attribute is only available
    from the City Plus and Insights web service end points and the
    Enterprise database.
    """
    ip_risk_snapshot: float | None
    """The risk associated with the IP address. The value ranges from 0.01 to
    99. A higher score indicates a higher risk.

    Please note that the IP risk score provided in GeoIP products and services
    is more static than the IP risk score provided in minFraud and is not
    responsive to traffic on your network. If you need realtime IP risk scoring
    based on behavioral signals on your own network, please use minFraud.

    This attribute is only available from the Insights end point.
    """
    _ip_address: IPAddress | None
    is_anonymous: bool
    """This is true if the IP address belongs to any sort of anonymous network.
    This attribute is only available from Insights.

    .. deprecated:: 5.2.0
       Use the ``anonymizer`` object in the ``Insights`` model instead.
    """
    is_anonymous_proxy: bool
    """This is true if the IP is an anonymous proxy.

    .. deprecated:: 2.2.0
       Use our `GeoIP2 Anonymous IP database
       <https://www.maxmind.com/en/geoip2-anonymous-ip-database GeoIP2>`_
       instead.
    """
    is_anonymous_vpn: bool
    """This is true if the IP address is registered to an anonymous VPN
    provider.

    If a VPN provider does not register subnets under names associated with
    them, we will likely only flag their IP ranges using the
    ``is_hosting_provider`` attribute.

    This attribute is only available from Insights.

    .. deprecated:: 5.2.0
       Use the ``anonymizer`` object in the ``Insights`` model instead.
    """
    is_anycast: bool
    """This returns true if the IP address belongs to an
    `anycast network <https://en.wikipedia.org/wiki/Anycast>`_.
    This is available for the GeoIP2 Country, City Plus, and Insights
    web services and the GeoIP2 Country, City, and Enterprise databases.
    """
    is_hosting_provider: bool
    """This is true if the IP address belongs to a hosting or VPN provider
    (see description of ``is_anonymous_vpn`` attribute).
    This attribute is only available from Insights.

    .. deprecated:: 5.2.0
       Use the ``anonymizer`` object in the ``Insights`` model instead.
    """
    is_legitimate_proxy: bool
    """This attribute is true if MaxMind believes this IP address to be a
    legitimate proxy, such as an internal VPN used by a corporation. This
    attribute is only available in the Enterprise database.
    """
    is_public_proxy: bool
    """This is true if the IP address belongs to a public proxy. This attribute
    is only available from Insights.

    .. deprecated:: 5.2.0
       Use the ``anonymizer`` object in the ``Insights`` model instead.
    """
    is_residential_proxy: bool
    """This is true if the IP address is on a suspected anonymizing network
    and belongs to a residential ISP. This attribute is only available from
    Insights.

    .. deprecated:: 5.2.0
       Use the ``anonymizer`` object in the ``Insights`` model instead.
    """
    is_satellite_provider: bool
    """This is true if the IP address is from a satellite provider that
    provides service to multiple countries.

    .. deprecated:: 2.2.0
       Due to the increased coverage by mobile carriers, very few
       satellite providers now serve multiple countries. As a result, the
       output does not provide sufficiently relevant data for us to maintain
       it.
    """
    is_tor_exit_node: bool
    """This is true if the IP address is a Tor exit node. This attribute is
    only available from Insights.

    .. deprecated:: 5.2.0
       Use the ``anonymizer`` object in the ``Insights`` model instead.
    """
    isp: str | None
    """The name of the ISP associated with the IP address. This attribute is
    only available from the City Plus and Insights web services and the
    Enterprise database.
    """
    mobile_country_code: str | None
    """The `mobile country code (MCC)
    <https://en.wikipedia.org/wiki/Mobile_country_code>`_ associated with the
    IP address and ISP. This attribute is available from the City Plus and
    Insights web services and the Enterprise database.
    """
    mobile_network_code: str | None
    """The `mobile network code (MNC)
    <https://en.wikipedia.org/wiki/Mobile_country_code>`_ associated with the
    IP address and ISP. This attribute is available from the City Plus and
    Insights web services and the Enterprise database.
    """
    organization: str | None
    """The name of the organization associated with the IP address. This
    attribute is only available from the City Plus and Insights web services
    and the Enterprise database.
    """
    static_ip_score: float | None
    """An indicator of how static or dynamic an IP address is. The value ranges
    from 0 to 99.99 with higher values meaning a greater static association.
    For example, many IP addresses with a user_type of cellular have a
    lifetime under one. Static Cable/DSL IPs typically have a lifetime above
    thirty.

    This indicator can be useful for deciding whether an IP address represents
    the same user over time. This attribute is only available from
    Insights.
    """
    user_count: int | None
    """The estimated number of users sharing the IP/network during the past 24
    hours. For IPv4, the count is for the individual IP. For IPv6, the count
    is for the /64 network. This attribute is only available from
    Insights.
    """
    user_type: str | None
    """The user type associated with the IP
    address. This can be one of the following values:

    * business
    * cafe
    * cellular
    * college
    * consumer_privacy_network
    * content_delivery_network
    * dialup
    * government
    * hosting
    * library
    * military
    * residential
    * router
    * school
    * search_engine_spider
    * traveler

    This attribute is only available from the Insights end point and the
    Enterprise database.
    """
    _network: ipaddress.IPv4Network | ipaddress.IPv6Network | None
    _prefix_len: int | None

    def __init__(
        self,
        *,
        autonomous_system_number: int | None = None,
        autonomous_system_organization: str | None = None,
        connection_type: str | None = None,
        domain: str | None = None,
        ip_risk_snapshot: float | None = None,
        is_anonymous: bool = False,
        is_anonymous_proxy: bool = False,
        is_anonymous_vpn: bool = False,
        is_hosting_provider: bool = False,
        is_legitimate_proxy: bool = False,
        is_public_proxy: bool = False,
        is_residential_proxy: bool = False,
        is_satellite_provider: bool = False,
        is_tor_exit_node: bool = False,
        isp: str | None = None,
        ip_address: str | None = None,
        network: str | None = None,
        organization: str | None = None,
        prefix_len: int | None = None,
        static_ip_score: float | None = None,
        user_count: int | None = None,
        user_type: str | None = None,
        mobile_country_code: str | None = None,
        mobile_network_code: str | None = None,
        is_anycast: bool = False,
        **_: Any,
    ) -> None:
        self.autonomous_system_number = autonomous_system_number
        self.autonomous_system_organization = autonomous_system_organization
        self.connection_type = connection_type
        self.domain = domain
        self.ip_risk_snapshot = ip_risk_snapshot
        self.is_anonymous = is_anonymous
        self.is_anonymous_proxy = is_anonymous_proxy
        self.is_anonymous_vpn = is_anonymous_vpn
        self.is_anycast = is_anycast
        self.is_hosting_provider = is_hosting_provider
        self.is_legitimate_proxy = is_legitimate_proxy
        self.is_public_proxy = is_public_proxy
        self.is_residential_proxy = is_residential_proxy
        self.is_satellite_provider = is_satellite_provider
        self.is_tor_exit_node = is_tor_exit_node
        self.isp = isp
        self.mobile_country_code = mobile_country_code
        self.mobile_network_code = mobile_network_code
        self.organization = organization
        self.static_ip_score = static_ip_score
        self.user_type = user_type
        self.user_count = user_count
        self._ip_address = ip_address
        if network is None:
            self._network = None
        else:
            self._network = ipaddress.ip_network(network, strict=False)
        # We don't construct the network using prefix_len here as that is
        # for database lookups. Customers using the database tend to be
        # much more performance sensitive than web service users.
        self._prefix_len = prefix_len

    @property
    def ip_address(self) -> IPv4Address | IPv6Address | None:
        """The IP address that the data in the model is for.

        If you performed a "me" lookup against the web service, this will be
        the externally routable IP address for the system the code is running
        on. If the system is behind a NAT, this may differ from the IP address
        locally assigned to it.
        """
        ip_address = self._ip_address
        if ip_address is None:
            return None

        if not isinstance(ip_address, (IPv4Address, IPv6Address)):
            ip_address = ipaddress.ip_address(ip_address)
            self._ip_address = ip_address
        return ip_address

    @property
    def network(self) -> ipaddress.IPv4Network | ipaddress.IPv6Network | None:
        """The network associated with the record.

        In particular, this is the largest network where all of the fields besides
        ip_address have the same value.
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
