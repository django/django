"""

Records
=======

"""
# pylint:disable=too-many-arguments,too-many-instance-attributes,too-many-locals

import ipaddress

# pylint:disable=R0903
from abc import ABCMeta
from typing import Dict, List, Optional, Type, Union

from geoip2.mixins import SimpleEquality


class Record(SimpleEquality, metaclass=ABCMeta):
    """All records are subclasses of the abstract class ``Record``."""

    def __repr__(self) -> str:
        args = ", ".join(f"{k}={v!r}" for k, v in self.__dict__.items())
        return f"{self.__module__}.{self.__class__.__name__}({args})"


class PlaceRecord(Record, metaclass=ABCMeta):
    """All records with :py:attr:`names` subclass :py:class:`PlaceRecord`."""

    names: Dict[str, str]
    _locales: List[str]

    def __init__(
        self,
        locales: Optional[List[str]] = None,
        names: Optional[Dict[str, str]] = None,
    ) -> None:
        if locales is None:
            locales = ["en"]
        self._locales = locales
        if names is None:
            names = {}
        self.names = names

    @property
    def name(self) -> Optional[str]:
        """Dict with locale codes as keys and localized name as value."""
        # pylint:disable=E1101
        return next((self.names.get(x) for x in self._locales if x in self.names), None)


class City(PlaceRecord):
    """Contains data for the city record associated with an IP address.

    This class contains the city-level data associated with an IP address.

    This record is returned by ``city``, ``enterprise``, and ``insights``.

    Attributes:

    .. attribute:: confidence

      A value from 0-100 indicating MaxMind's
      confidence that the city is correct. This attribute is only available
      from the Insights end point and the Enterprise database.

      :type: int

    .. attribute:: geoname_id

      The GeoName ID for the city.

      :type: int

    .. attribute:: name

      The name of the city based on the locales list passed to the
      constructor.

      :type: str

    .. attribute:: names

      A dictionary where the keys are locale codes
      and the values are names.

      :type: dict

    """

    confidence: Optional[int]
    geoname_id: Optional[int]

    def __init__(
        self,
        locales: Optional[List[str]] = None,
        confidence: Optional[int] = None,
        geoname_id: Optional[int] = None,
        names: Optional[Dict[str, str]] = None,
        **_,
    ) -> None:
        self.confidence = confidence
        self.geoname_id = geoname_id
        super().__init__(locales, names)


class Continent(PlaceRecord):
    """Contains data for the continent record associated with an IP address.

    This class contains the continent-level data associated with an IP
    address.

    Attributes:


    .. attribute:: code

      A two character continent code like "NA" (North America)
      or "OC" (Oceania).

      :type: str

    .. attribute:: geoname_id

      The GeoName ID for the continent.

      :type: int

    .. attribute:: name

      Returns the name of the continent based on the locales list passed to
      the constructor.

      :type: str

    .. attribute:: names

      A dictionary where the keys are locale codes
      and the values are names.

      :type: dict

    """

    code: Optional[str]
    geoname_id: Optional[int]

    def __init__(
        self,
        locales: Optional[List[str]] = None,
        code: Optional[str] = None,
        geoname_id: Optional[int] = None,
        names: Optional[Dict[str, str]] = None,
        **_,
    ) -> None:
        self.code = code
        self.geoname_id = geoname_id
        super().__init__(locales, names)


class Country(PlaceRecord):
    """Contains data for the country record associated with an IP address.

    This class contains the country-level data associated with an IP address.

    Attributes:


    .. attribute:: confidence

      A value from 0-100 indicating MaxMind's confidence that
      the country is correct. This attribute is only available from the
      Insights end point and the Enterprise database.

      :type: int

    .. attribute:: geoname_id

      The GeoName ID for the country.

      :type: int

    .. attribute:: is_in_european_union

      This is true if the country is a member state of the European Union.

      :type: bool

    .. attribute:: iso_code

      The two-character `ISO 3166-1
      <http://en.wikipedia.org/wiki/ISO_3166-1>`_ alpha code for the
      country.

      :type: str

    .. attribute:: name

      The name of the country based on the locales list passed to the
      constructor.

      :type: str

    .. attribute:: names

      A dictionary where the keys are locale codes and the values
      are names.

      :type: dict

    """

    confidence: Optional[int]
    geoname_id: Optional[int]
    is_in_european_union: bool
    iso_code: Optional[str]

    def __init__(
        self,
        locales: Optional[List[str]] = None,
        confidence: Optional[int] = None,
        geoname_id: Optional[int] = None,
        is_in_european_union: bool = False,
        iso_code: Optional[str] = None,
        names: Optional[Dict[str, str]] = None,
        **_,
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

    Attributes:


    .. attribute:: confidence

      A value from 0-100 indicating MaxMind's confidence that
      the country is correct. This attribute is only available from the
      Insights end point and the Enterprise database.

      :type: int

    .. attribute:: geoname_id

      The GeoName ID for the country.

      :type: int

    .. attribute:: is_in_european_union

      This is true if the country is a member state of the European Union.

      :type: bool

    .. attribute:: iso_code

      The two-character `ISO 3166-1
      <http://en.wikipedia.org/wiki/ISO_3166-1>`_ alpha code for the country.

      :type: str

    .. attribute:: name

      The name of the country based on the locales list passed to the
      constructor.

      :type: str

    .. attribute:: names

      A dictionary where the keys are locale codes and the values
      are names.

      :type: dict


    .. attribute:: type

      A string indicating the type of entity that is representing the
      country. Currently we only return ``military`` but this could expand to
      include other types in the future.

      :type: str

    """

    type: Optional[str]

    def __init__(
        self,
        locales: Optional[List[str]] = None,
        confidence: Optional[int] = None,
        geoname_id: Optional[int] = None,
        is_in_european_union: bool = False,
        iso_code: Optional[str] = None,
        names: Optional[Dict[str, str]] = None,
        # pylint:disable=redefined-builtin
        type: Optional[str] = None,
        **_,
    ) -> None:
        self.type = type
        super().__init__(
            locales, confidence, geoname_id, is_in_european_union, iso_code, names
        )


class Location(Record):
    """Contains data for the location record associated with an IP address.

    This class contains the location data associated with an IP address.

    This record is returned by ``city``, ``enterprise``, and ``insights``.

    Attributes:

    .. attribute:: average_income

      The average income in US dollars associated with the requested IP
      address. This attribute is only available from the Insights end point.

      :type: int

    .. attribute:: accuracy_radius

      The approximate accuracy radius in kilometers around the latitude and
      longitude for the IP address. This is the radius where we have a 67%
      confidence that the device using the IP address resides within the
      circle centered at the latitude and longitude with the provided radius.

      :type: int

    .. attribute:: latitude

      The approximate latitude of the location associated with the IP
      address. This value is not precise and should not be used to identify a
      particular address or household.

      :type: float

    .. attribute:: longitude

      The approximate longitude of the location associated with the IP
      address. This value is not precise and should not be used to identify a
      particular address or household.

      :type: float

    .. attribute:: metro_code

      The metro code of the location if the
      location is in the US. MaxMind returns the same metro codes as the
      `Google AdWords API
      <https://developers.google.com/adwords/api/docs/appendix/cities-DMAregions>`_.

      :type: int

      .. attribute:: population_density

      The estimated population per square kilometer associated with the IP
      address. This attribute is only available from the Insights end point.

      :type: int

    .. attribute:: time_zone

      The time zone associated with location, as specified by the `IANA Time
      Zone Database <http://www.iana.org/time-zones>`_, e.g.,
      "America/New_York".

      :type: str

    """

    average_income: Optional[int]
    accuracy_radius: Optional[int]
    latitude: Optional[float]
    longitude: Optional[float]
    metro_code: Optional[int]
    population_density: Optional[int]
    time_zone: Optional[str]

    def __init__(
        self,
        average_income: Optional[int] = None,
        accuracy_radius: Optional[int] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        metro_code: Optional[int] = None,
        population_density: Optional[int] = None,
        time_zone: Optional[str] = None,
        **_,
    ) -> None:
        self.average_income = average_income
        self.accuracy_radius = accuracy_radius
        self.latitude = latitude
        self.longitude = longitude
        self.metro_code = metro_code
        self.population_density = population_density
        self.time_zone = time_zone


class MaxMind(Record):
    """Contains data related to your MaxMind account.

    Attributes:

    .. attribute:: queries_remaining

      The number of remaining queries you have
      for the end point you are calling.

      :type: int

    """

    queries_remaining: Optional[int]

    def __init__(self, queries_remaining: Optional[int] = None, **_) -> None:
        self.queries_remaining = queries_remaining


class Postal(Record):
    """Contains data for the postal record associated with an IP address.

    This class contains the postal data associated with an IP address.

    This attribute is returned by ``city``, ``enterprise``, and ``insights``.

    Attributes:

    .. attribute:: code

      The postal code of the location. Postal
      codes are not available for all countries. In some countries, this will
      only contain part of the postal code.

      :type: str

    .. attribute:: confidence

      A value from 0-100 indicating
      MaxMind's confidence that the postal code is correct. This attribute is
      only available from the Insights end point and the Enterprise database.

      :type: int

    """

    code: Optional[str]
    confidence: Optional[int]

    def __init__(
        self, code: Optional[str] = None, confidence: Optional[int] = None, **_
    ) -> None:
        self.code = code
        self.confidence = confidence


class Subdivision(PlaceRecord):
    """Contains data for the subdivisions associated with an IP address.

    This class contains the subdivision data associated with an IP address.

    This attribute is returned by ``city``, ``enterprise``, and ``insights``.

    Attributes:

    .. attribute:: confidence

      This is a value from 0-100 indicating MaxMind's
      confidence that the subdivision is correct. This attribute is only
      available from the Insights end point and the Enterprise database.

      :type: int

    .. attribute:: geoname_id

      This is a GeoName ID for the subdivision.

      :type: int

    .. attribute:: iso_code

      This is a string up to three characters long
      contain the subdivision portion of the `ISO 3166-2 code
      <http://en.wikipedia.org/wiki/ISO_3166-2>`_.

      :type: str

    .. attribute:: name

      The name of the subdivision based on the locales list passed to the
      constructor.

      :type: str

    .. attribute:: names

      A dictionary where the keys are locale codes and the
      values are names

      :type: dict

    """

    confidence: Optional[int]
    geoname_id: Optional[int]
    iso_code: Optional[str]

    def __init__(
        self,
        locales: Optional[List[str]] = None,
        confidence: Optional[int] = None,
        geoname_id: Optional[int] = None,
        iso_code: Optional[str] = None,
        names: Optional[Dict[str, str]] = None,
        **_,
    ) -> None:
        self.confidence = confidence
        self.geoname_id = geoname_id
        self.iso_code = iso_code
        super().__init__(locales, names)


class Subdivisions(tuple):
    """A tuple-like collection of subdivisions associated with an IP address.

    This class contains the subdivisions of the country associated with the
    IP address from largest to smallest.

    For instance, the response for Oxford in the United Kingdom would have
    England as the first element and Oxfordshire as the second element.

    This attribute is returned by ``city``, ``enterprise``, and ``insights``.
    """

    def __new__(
        cls: Type["Subdivisions"], locales: Optional[List[str]], *subdivisions
    ) -> "Subdivisions":
        subobjs = tuple(Subdivision(locales, **x) for x in subdivisions)
        obj = super().__new__(cls, subobjs)  # type: ignore
        return obj

    def __init__(
        self, locales: Optional[List[str]], *subdivisions  # pylint:disable=W0613
    ) -> None:
        self._locales = locales
        super().__init__()

    @property
    def most_specific(self) -> Subdivision:
        """The most specific (smallest) subdivision available.

        If there are no :py:class:`Subdivision` objects for the response,
        this returns an empty :py:class:`Subdivision`.

        :type: :py:class:`Subdivision`
        """
        try:
            return self[-1]
        except IndexError:
            return Subdivision(self._locales)


class Traits(Record):
    """Contains data for the traits record associated with an IP address.

    This class contains the traits data associated with an IP address.

    This class has the following attributes:


    .. attribute:: autonomous_system_number

      The `autonomous system
      number <http://en.wikipedia.org/wiki/Autonomous_system_(Internet)>`_
      associated with the IP address. This attribute is only available from
      the City Plus and Insights web services and the Enterprise database.

      :type: int

    .. attribute:: autonomous_system_organization

      The organization associated with the registered `autonomous system
      number <http://en.wikipedia.org/wiki/Autonomous_system_(Internet)>`_ for
      the IP address. This attribute is only available from the City Plus and
      Insights web service end points and the Enterprise database.

      :type: str

    .. attribute:: connection_type

      The connection type may take the following values:

      - Dialup
      - Cable/DSL
      - Corporate
      - Cellular

      Additional values may be added in the future.

      This attribute is only available in the Enterprise database.

      :type: str

    .. attribute:: domain

      The second level domain associated with the
      IP address. This will be something like "example.com" or
      "example.co.uk", not "foo.example.com". This attribute is only available
      from the City Plus and Insights web service end points and the
      Enterprise database.

      :type: str

    .. attribute:: ip_address

      The IP address that the data in the model
      is for. If you performed a "me" lookup against the web service, this
      will be the externally routable IP address for the system the code is
      running on. If the system is behind a NAT, this may differ from the IP
      address locally assigned to it.

      :type: str

    .. attribute:: is_anonymous

      This is true if the IP address belongs to any sort of anonymous network.
      This attribute is only available from Insights.

      :type: bool

    .. attribute:: is_anonymous_proxy

      This is true if the IP is an anonymous proxy.

      :type: bool

      .. deprecated:: 2.2.0
        Use our our `GeoIP2 Anonymous IP database
        <https://www.maxmind.com/en/geoip2-anonymous-ip-database GeoIP2>`_
        instead.

    .. attribute:: is_anonymous_vpn

      This is true if the IP address is registered to an anonymous VPN
      provider.

      If a VPN provider does not register subnets under names associated with
      them, we will likely only flag their IP ranges using the
      ``is_hosting_provider`` attribute.

      This attribute is only available from Insights.

      :type: bool

    .. attribute:: is_hosting_provider

      This is true if the IP address belongs to a hosting or VPN provider
      (see description of ``is_anonymous_vpn`` attribute).
      This attribute is only available from Insights.

      :type: bool

    .. attribute:: is_legitimate_proxy

      This attribute is true if MaxMind believes this IP address to be a
      legitimate proxy, such as an internal VPN used by a corporation. This
      attribute is only available in the Enterprise database.

      :type: bool

    .. attribute:: is_public_proxy

      This is true if the IP address belongs to a public proxy. This attribute
      is only available from Insights.

      :type: bool

    .. attribute:: is_residential_proxy

      This is true if the IP address is on a suspected anonymizing network
      and belongs to a residential ISP. This attribute is only available from
      Insights.

      :type: bool


    .. attribute:: is_satellite_provider

      This is true if the IP address is from a satellite provider that
      provides service to multiple countries.

      :type: bool

      .. deprecated:: 2.2.0
        Due to the increased coverage by mobile carriers, very few
        satellite providers now serve multiple countries. As a result, the
        output does not provide sufficiently relevant data for us to maintain
        it.

    .. attribute:: is_tor_exit_node

      This is true if the IP address is a Tor exit node. This attribute is
      only available from Insights.

      :type: bool

    .. attribute:: isp

      The name of the ISP associated with the IP address. This attribute is
      only available from the City Plus and Insights web services and the
      Enterprise database.

      :type: str

    .. attribute: mobile_country_code

      The `mobile country code (MCC)
      <https://en.wikipedia.org/wiki/Mobile_country_code>`_ associated with the
      IP address and ISP. This attribute is available from the City Plus and
      Insights web services and the Enterprise database.

      :type: str

    .. attribute: mobile_network_code

      The `mobile network code (MNC)
      <https://en.wikipedia.org/wiki/Mobile_country_code>`_ associated with the
      IP address and ISP. This attribute is available from the City Plus and
      Insights web services and the Enterprise database.

      :type: str

    .. attribute:: network

      The network associated with the record. In particular, this is the
      largest network where all of the fields besides ip_address have the same
      value.

      :type: ipaddress.IPv4Network or ipaddress.IPv6Network

    .. attribute:: organization

      The name of the organization associated with the IP address. This
      attribute is only available from the City Plus and Insights web services
      and the Enterprise database.

      :type: str

    .. attribute:: static_ip_score

      An indicator of how static or dynamic an IP address is. The value ranges
      from 0 to 99.99 with higher values meaning a greater static association.
      For example, many IP addresses with a user_type of cellular have a
      lifetime under one. Static Cable/DSL IPs typically have a lifetime above
      thirty.

      This indicator can be useful for deciding whether an IP address represents
      the same user over time. This attribute is only available from
      Insights.

      :type: float

    .. attribute:: user_count

      The estimated number of users sharing the IP/network during the past 24
      hours. For IPv4, the count is for the individual IP. For IPv6, the count
      is for the /64 network. This attribute is only available from
      Insights.

      :type: int

    .. attribute:: user_type

      The user type associated with the IP
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

      :type: str

    """

    autonomous_system_number: Optional[int]
    autonomous_system_organization: Optional[str]
    connection_type: Optional[str]
    domain: Optional[str]
    is_anonymous: bool
    is_anonymous_proxy: bool
    is_anonymous_vpn: bool
    is_hosting_provider: bool
    is_legitimate_proxy: bool
    is_public_proxy: bool
    is_residential_proxy: bool
    is_satellite_provider: bool
    is_tor_exit_node: bool
    isp: Optional[str]
    ip_address: Optional[str]
    mobile_country_code: Optional[str]
    mobile_network_code: Optional[str]
    organization: Optional[str]
    static_ip_score: Optional[float]
    user_count: Optional[int]
    user_type: Optional[str]
    _network: Optional[Union[ipaddress.IPv4Network, ipaddress.IPv6Network]]
    _prefix_len: Optional[int]

    def __init__(
        self,
        autonomous_system_number: Optional[int] = None,
        autonomous_system_organization: Optional[str] = None,
        connection_type: Optional[str] = None,
        domain: Optional[str] = None,
        is_anonymous: bool = False,
        is_anonymous_proxy: bool = False,
        is_anonymous_vpn: bool = False,
        is_hosting_provider: bool = False,
        is_legitimate_proxy: bool = False,
        is_public_proxy: bool = False,
        is_residential_proxy: bool = False,
        is_satellite_provider: bool = False,
        is_tor_exit_node: bool = False,
        isp: Optional[str] = None,
        ip_address: Optional[str] = None,
        network: Optional[str] = None,
        organization: Optional[str] = None,
        prefix_len: Optional[int] = None,
        static_ip_score: Optional[float] = None,
        user_count: Optional[int] = None,
        user_type: Optional[str] = None,
        mobile_country_code: Optional[str] = None,
        mobile_network_code: Optional[str] = None,
        **_,
    ) -> None:
        self.autonomous_system_number = autonomous_system_number
        self.autonomous_system_organization = autonomous_system_organization
        self.connection_type = connection_type
        self.domain = domain
        self.is_anonymous = is_anonymous
        self.is_anonymous_proxy = is_anonymous_proxy
        self.is_anonymous_vpn = is_anonymous_vpn
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
        self.ip_address = ip_address
        if network is None:
            self._network = None
        else:
            self._network = ipaddress.ip_network(network, False)
        # We don't construct the network using prefix_len here as that is
        # for database lookups. Customers using the database tend to be
        # much more performance sensitive than web service users.
        self._prefix_len = prefix_len

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
