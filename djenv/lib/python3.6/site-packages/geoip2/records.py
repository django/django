"""

Records
=======

"""

# pylint:disable=R0903
from abc import ABCMeta

from geoip2.mixins import SimpleEquality


class Record(SimpleEquality):
    """All records are subclasses of the abstract class ``Record``."""

    __metaclass__ = ABCMeta

    _valid_attributes = set()

    def __init__(self, **kwargs):
        valid_args = dict((k, kwargs.get(k)) for k in self._valid_attributes)
        self.__dict__.update(valid_args)

    def __setattr__(self, name, value):
        raise AttributeError("can't set attribute")

    def __repr__(self):
        args = ', '.join('%s=%r' % x for x in self.__dict__.items())
        return '{module}.{class_name}({data})'.format(
            module=self.__module__,
            class_name=self.__class__.__name__,
            data=args)


class PlaceRecord(Record):
    """All records with :py:attr:`names` subclass :py:class:`PlaceRecord`."""

    __metaclass__ = ABCMeta

    def __init__(self, locales=None, **kwargs):
        if locales is None:
            locales = ['en']
        if kwargs.get('names') is None:
            kwargs['names'] = {}
        object.__setattr__(self, '_locales', locales)
        super(PlaceRecord, self).__init__(**kwargs)

    @property
    def name(self):
        """Dict with locale codes as keys and localized name as value."""
        # pylint:disable=E1101
        return next((self.names.get(x) for x in self._locales
                     if x in self.names), None)


class City(PlaceRecord):
    """Contains data for the city record associated with an IP address.

    This class contains the city-level data associated with an IP address.

    This record is returned by ``city``, ``enterprise``, and ``insights``.

    Attributes:

    .. attribute:: confidence

      A value from 0-100 indicating MaxMind's
      confidence that the city is correct. This attribute is only available
      from the Insights end point and the GeoIP2 Enterprise database.

      :type: int

    .. attribute:: geoname_id

      The GeoName ID for the city.

      :type: int

    .. attribute:: name

      The name of the city based on the locales list passed to the
      constructor.

      :type: unicode

    .. attribute:: names

      A dictionary where the keys are locale codes
      and the values are names.

      :type: dict

    """

    _valid_attributes = set(['confidence', 'geoname_id', 'names'])


class Continent(PlaceRecord):
    """Contains data for the continent record associated with an IP address.

    This class contains the continent-level data associated with an IP
    address.

    Attributes:


    .. attribute:: code

      A two character continent code like "NA" (North America)
      or "OC" (Oceania).

      :type: unicode

    .. attribute:: geoname_id

      The GeoName ID for the continent.

      :type: int

    .. attribute:: name

      Returns the name of the continent based on the locales list passed to
      the constructor.

      :type: unicode

    .. attribute:: names

      A dictionary where the keys are locale codes
      and the values are names.

      :type: dict

    """

    _valid_attributes = set(['code', 'geoname_id', 'names'])


class Country(PlaceRecord):
    """Contains data for the country record associated with an IP address.

    This class contains the country-level data associated with an IP address.

    Attributes:


    .. attribute:: confidence

      A value from 0-100 indicating MaxMind's confidence that
      the country is correct. This attribute is only available from the
      Insights end point and the GeoIP2 Enterprise database.

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

      :type: unicode

    .. attribute:: name

      The name of the country based on the locales list passed to the
      constructor.

      :type: unicode

    .. attribute:: names

      A dictionary where the keys are locale codes and the values
      are names.

      :type: dict

    """

    _valid_attributes = set([
        'confidence', 'geoname_id', 'is_in_european_union', 'iso_code', 'names'
    ])

    def __init__(self, locales=None, **kwargs):
        if 'is_in_european_union' not in kwargs:
            kwargs['is_in_european_union'] = False
        super(Country, self).__init__(locales, **kwargs)


class RepresentedCountry(Country):
    """Contains data for the represented country associated with an IP address.

    This class contains the country-level data associated with an IP address
    for the IP's represented country. The represented country is the country
    represented by something like a military base.

    Attributes:


    .. attribute:: confidence

      A value from 0-100 indicating MaxMind's confidence that
      the country is correct. This attribute is only available from the
      Insights end point and the GeoIP2 Enterprise database.

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

      :type: unicode

    .. attribute:: name

      The name of the country based on the locales list passed to the
      constructor.

      :type: unicode

    .. attribute:: names

      A dictionary where the keys are locale codes and the values
      are names.

      :type: dict


    .. attribute:: type

      A string indicating the type of entity that is representing the
      country. Currently we only return ``military`` but this could expand to
      include other types in the future.

      :type: unicode

    """

    _valid_attributes = set([
        'confidence', 'geoname_id', 'is_in_european_union', 'iso_code',
        'names', 'type'
    ])


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

      :type: unicode

    """

    _valid_attributes = set([
        'average_income', 'accuracy_radius', 'latitude', 'longitude',
        'metro_code', 'population_density', 'postal_code', 'postal_confidence',
        'time_zone'
    ])


class MaxMind(Record):
    """Contains data related to your MaxMind account.

    Attributes:

    .. attribute:: queries_remaining

      The number of remaining queries you have
      for the end point you are calling.

      :type: int

    """

    _valid_attributes = set(['queries_remaining'])


class Postal(Record):
    """Contains data for the postal record associated with an IP address.

    This class contains the postal data associated with an IP address.

    This attribute is returned by ``city``, ``enterprise``, and ``insights``.

    Attributes:

    .. attribute:: code

      The postal code of the location. Postal
      codes are not available for all countries. In some countries, this will
      only contain part of the postal code.

      :type: unicode

    .. attribute:: confidence

      A value from 0-100 indicating
      MaxMind's confidence that the postal code is correct. This attribute is
      only available from the Insights end point and the GeoIP2 Enterprise
      database.

      :type: int

    """

    _valid_attributes = set(['code', 'confidence'])


class Subdivision(PlaceRecord):
    """Contains data for the subdivisions associated with an IP address.

    This class contains the subdivision data associated with an IP address.

    This attribute is returned by ``city``, ``enterprise``, and ``insights``.

    Attributes:

    .. attribute:: confidence

      This is a value from 0-100 indicating MaxMind's
      confidence that the subdivision is correct. This attribute is only
      available from the Insights end point and the GeoIP2 Enterprise
      database.

      :type: int

    .. attribute:: geoname_id

      This is a GeoName ID for the subdivision.

      :type: int

    .. attribute:: iso_code

      This is a string up to three characters long
      contain the subdivision portion of the `ISO 3166-2 code
      <http://en.wikipedia.org/wiki/ISO_3166-2>`_.

      :type: unicode

    .. attribute:: name

      The name of the subdivision based on the locales list passed to the
      constructor.

      :type: unicode

    .. attribute:: names

      A dictionary where the keys are locale codes and the
      values are names

      :type: dict

    """

    _valid_attributes = set(['confidence', 'geoname_id', 'iso_code', 'names'])


class Subdivisions(tuple):
    """A tuple-like collection of subdivisions associated with an IP address.

    This class contains the subdivisions of the country associated with the
    IP address from largest to smallest.

    For instance, the response for Oxford in the United Kingdom would have
    England as the first element and Oxfordshire as the second element.

    This attribute is returned by ``city``, ``enterprise``, and ``insights``.
    """

    def __new__(cls, locales, *subdivisions):
        subdivisions = [Subdivision(locales, **x) for x in subdivisions]
        obj = super(cls, Subdivisions).__new__(cls, subdivisions)
        return obj

    def __init__(self, locales, *subdivisions):  # pylint:disable=W0613
        self._locales = locales
        super(Subdivisions, self).__init__()

    @property
    def most_specific(self):
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
      the City and Insights web service end points and the GeoIP2 Enterprise
      database.

      :type: int

    .. attribute:: autonomous_system_organization

      The organization associated with the registered `autonomous system
      number <http://en.wikipedia.org/wiki/Autonomous_system_(Internet)>`_ for
      the IP address. This attribute is only available from the City and
      Insights web service end points and the GeoIP2 Enterprise database.

      :type: unicode

    .. attribute:: connection_type

      The connection type may take the following values:

      - Dialup
      - Cable/DSL
      - Corporate
      - Cellular

      Additional values may be added in the future.

      This attribute is only available in the GeoIP2 Enterprise database.

      :type: unicode

    .. attribute:: domain

      The second level domain associated with the
      IP address. This will be something like "example.com" or
      "example.co.uk", not "foo.example.com". This attribute is only available
      from the City and Insights web service end points and the GeoIP2
      Enterprise database.

      :type: unicode

    .. attribute:: ip_address

      The IP address that the data in the model
      is for. If you performed a "me" lookup against the web service, this
      will be the externally routable IP address for the system the code is
      running on. If the system is behind a NAT, this may differ from the IP
      address locally assigned to it.

      :type: unicode

    .. attribute:: is_anonymous

      This is true if the IP address belongs to any sort of anonymous network.
      This attribute is only available from GeoIP2 Precision Insights.

      :type: bool

    .. attribute:: is_anonymous_proxy

      This is true if the IP is an anonymous
      proxy. See http://dev.maxmind.com/faq/geoip#anonproxy for further
      details.

      :type: bool

      .. deprecated:: 2.2.0
        Use our our `GeoIP2 Anonymous IP database
        <https://www.maxmind.com/en/geoip2-anonymous-ip-database GeoIP2>`_
        instead.

    .. attribute:: is_anonymous_vpn

      This is true if the IP address belongs to an anonymous VPN system.
      This attribute is only available from GeoIP2 Precision Insights.

      :type: bool

    .. attribute:: is_hosting_provider

      This is true if the IP address belongs to a hosting provider.
      This attribute is only available from GeoIP2 Precision Insights.

      :type: bool

    .. attribute:: is_legitimate_proxy

      This attribute is true if MaxMind believes this IP address to be a
      legitimate proxy, such as an internal VPN used by a corporation. This
      attribute is only available in the GeoIP2 Enterprise database.

      :type: bool

    .. attribute:: is_public_proxy

      This is true if the IP address belongs to a public proxy. This attribute
      is only available from GeoIP2 Precision Insights.

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

      This is true if the IP address is a Tor exit node.  This attribute is
      only available from GeoIP2 Precision Insights.

      :type: bool

    .. attribute:: isp

      The name of the ISP associated with the IP address. This attribute is
      only available from the City and Insights web service end points and the
      GeoIP2 Enterprise database.

      :type: unicode

    .. attribute:: organization

      The name of the organization associated with the IP address. This
      attribute is only available from the City and Insights web service end
      points and the GeoIP2 Enterprise database.

      :type: unicode

    .. attribute:: user_type

      The user type associated with the IP
      address. This can be one of the following values:

      * business
      * cafe
      * cellular
      * college
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
      GeoIP2 Enterprise database.

      :type: unicode

    """

    _valid_attributes = set([
        'autonomous_system_number', 'autonomous_system_organization',
        'connection_type', 'domain', 'is_anonymous', 'is_anonymous_proxy',
        'is_anonymous_vpn', 'is_hosting_provider', 'is_legitimate_proxy',
        'is_public_proxy', 'is_satellite_provider', 'is_tor_exit_node',
        'is_satellite_provider', 'isp', 'ip_address', 'organization',
        'user_type'
    ])

    def __init__(self, **kwargs):
        for k in [
                'is_anonymous',
                'is_anonymous_proxy',
                'is_anonymous_vpn',
                'is_hosting_provider',
                'is_legitimate_proxy',
                'is_public_proxy',
                'is_satellite_provider',
                'is_tor_exit_node',
        ]:
            kwargs[k] = bool(kwargs.get(k, False))
        super(Traits, self).__init__(**kwargs)
