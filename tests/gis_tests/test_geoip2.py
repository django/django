import ipaddress
import itertools
import pathlib
from unittest import mock, skipUnless

import geoip2

from django.conf import settings
from django.contrib.gis.geoip2 import HAS_GEOIP2
from django.contrib.gis.geos import GEOSGeometry
from django.test import SimpleTestCase, override_settings
from django.utils.deprecation import RemovedInDjango50Warning

if HAS_GEOIP2:
    from django.contrib.gis.geoip2 import GeoIP2, GeoIP2Exception

GEOIP_PATH = pathlib.Path(__file__).parent.joinpath('data/geoip2').resolve()


@skipUnless(HAS_GEOIP2, 'GeoIP2 is required.')
@override_settings(
    GEOIP_CITY='GeoLite2-City-Test.mmdb',
    GEOIP_COUNTRY='GeoLite2-Country-Test.mmdb',
    GEOIP_PATH=GEOIP_PATH,
)
class GeoLite2Test(SimpleTestCase):
    fqdn = 'sky.uk'
    ipv4_str = '2.125.160.216'
    ipv6_str = '::ffff:027d:a0d8'  # 2.125.160.216 as an IPv4 mapped IPv6 address.
    ipv4_addr = ipaddress.ip_address(ipv4_str)
    ipv6_addr = ipaddress.ip_address(ipv6_str)

    def test_init(self):
        path = settings.GEOIP_PATH

        g1 = GeoIP2()  # Everything inferred from GeoIP path
        g2 = GeoIP2(path, 0)  # Passing in data path explicitly.
        g3 = GeoIP2(str(path))  # path accepts str instead of pathlib.Path.
        # Only passing in the location of one database.
        g4 = GeoIP2(path / 'GeoLite2-City-Test.mmdb', country='')
        g5 = GeoIP2(path / 'GeoLite2-Country-Test.mmdb', city='')
        for g in (g1, g2, g3, g4, g5):
            self.assertTrue(g._reader)

        # Improper parameters.
        bad_params = (23, 'foo', 15.23)
        for bad in bad_params:
            with self.assertRaises(GeoIP2Exception):
                GeoIP2(cache=bad)
            if isinstance(bad, str):
                e = GeoIP2Exception
            else:
                e = TypeError
            with self.assertRaises(e):
                GeoIP2(bad, 0)

    # XXX: def test_no_database_file(self):
    # XXX:     invalid_path = pathlib.Path(__file__).parent.joinpath('data/invalid').resolve()
    # XXX:     msg = 'Could not load a database from %s.' % invalid_path
    # XXX:     with self.assertRaisesMessage(GeoIP2Exception, msg):
    # XXX:         GeoIP2(invalid_path)

    def test_bad_query(self):
        """GeoIP query parameter checking."""
        g = GeoIP2(city='<invalid>')

        functions = (g.city, g.coords, g.geos, g.lat_lon, g.lon_lat)
        values = (123, 123.45, b'', (), [], {}, set(), frozenset(), GeoIP2)

        msg = 'Invalid GeoIP city data file: '
        for function in functions:
            with self.subTest(function=function.__qualname__):
                with self.assertRaisesMessage(GeoIP2Exception, msg):
                    function('example.com')

        functions += (g.country, g.country_code, g.country_name)

        msg = 'GeoIP query must be a string or instance of IPv4Address or IPv6Address, not type'
        for function, value in itertools.product(functions, values):
            with self.subTest(function=function.__qualname__, type=type(value)):
                with self.assertRaisesMessage(TypeError, msg):
                    function(value)

    @mock.patch('socket.gethostbyname')
    def test_country(self, gethostbyname):
        gethostbyname.return_value = '2.125.160.216'
        g = GeoIP2(city='<invalid>')

        for query in (self.fqdn, self.ipv4_str, self.ipv6_str, self.ipv4_addr, self.ipv6_addr):
            with self.subTest(query=query):
                self.assertEqual(g.country(query), {
                    'continent_code': 'EU',
                    'continent_name': 'Europe',
                    'country_code': 'GB',
                    'country_name': 'United Kingdom',
                    'is_in_european_union': False,
                })
                self.assertEqual(g.country_code(query), 'GB')
                self.assertEqual(g.country_name(query), 'United Kingdom')

    @mock.patch('socket.gethostbyname')
    def test_city(self, gethostbyname):
        gethostbyname.return_value = '2.125.160.216'
        g = GeoIP2(country='<invalid>')

        for query in (self.fqdn, self.ipv4_str, self.ipv6_str, self.ipv4_addr, self.ipv6_addr):
            with self.subTest(query=query):
                self.assertEqual(g.city(query), {
                    'accuracy_radius': 100,
                    'city': 'Boxford',
                    'continent_code': 'EU',
                    'continent_name': 'Europe',
                    'country_code': 'GB',
                    'country_name': 'United Kingdom',
                    'is_in_european_union': False,
                    'latitude': 51.75,
                    'longitude': -1.25,
                    'metro_code': None,
                    'postal_code': 'OX1',
                    'region_code': 'ENG',
                    'region_name': 'England',
                    'time_zone': 'Europe/London',
                    'dma_code': None,
                    'region': 'ENG',
                })

                geom = g.geos(query)
                self.assertIsInstance(geom, GEOSGeometry)
                self.assertEqual(geom.srid, 4326)
                self.assertEqual(geom.tuple, (-1.25, 51.75))

                self.assertEqual(g.coords(query), (-1.25, 51.75))
                self.assertEqual(g.lat_lon(query), (51.75, -1.25))
                self.assertEqual(g.lon_lat(query), (-1.25, 51.75))

                # Country queries should still work.
                self.assertEqual(g.country(query), {
                    'continent_code': 'EU',
                    'continent_name': 'Europe',
                    'country_code': 'GB',
                    'country_name': 'United Kingdom',
                    'is_in_european_union': False,
                })
                self.assertEqual(g.country_code(query), 'GB')
                self.assertEqual(g.country_name(query), 'United Kingdom')

    def test_not_found(self):
        g1 = GeoIP2(city='<invalid>')
        g2 = GeoIP2(country='<invalid>')
        for function, query in itertools.product((g1.country, g2.city), ('127.0.0.1', '::1')):
            with self.subTest(function=function.__qualname__, query=query):
                msg = f'The address {query} is not in the database.'
                with self.assertRaisesMessage(geoip2.errors.AddressNotFoundError, msg):
                    function(query)

    def test_del(self):
        g = GeoIP2()
        reader = g._reader
        self.assertIs(reader._db_reader.closed, False)
        del g
        self.assertIs(reader._db_reader.closed, True)

    def test_repr(self):
        g = GeoIP2()
        m = g._metadata
        expected = "<GeoIP2 [v%(version)s] _path='%(path)s'>" % {
            'version': '%s.%s' % (m.binary_format_major_version, m.binary_format_minor_version),
            'path': g._path,
        }
        self.assertEqual(repr(g), expected)

    # XXX: @mock.patch('socket.gethostbyname', return_value='expected')
    # XXX: def test_check_query(self, gethostbyname):
    # XXX:     g = GeoIP2()
    # XXX:     self.assertEqual(g._check_query('127.0.0.1'), '127.0.0.1')
    # XXX:     self.assertEqual(g._check_query('2002:81ed:c9a5::81ed:c9a5'), '2002:81ed:c9a5::81ed:c9a5')
    # XXX:     self.assertEqual(g._check_query('invalid-ip-address'), 'expected')

    def test_open_deprecation_warning(self):
        msg = 'The GeoIP2.open() class method has been deprecated in favor of using GeoIP2() directly.'
        with self.assertWarnsMessage(RemovedInDjango50Warning, msg):
            GeoIP2.open(settings.GEOIP_PATH / settings.GEOIP_CITY, 0)


@skipUnless(HAS_GEOIP2, 'GeoIP2 is required.')
@override_settings(
    GEOIP_CITY='GeoIP2-City-Test.mmdb',
    GEOIP_COUNTRY='GeoIP2-Country-Test.mmdb',
    GEOIP_PATH=GEOIP_PATH,
)
class GeoIP2Test(GeoLite2Test):
    """Test that the non-free GeoIP2 databases are supported."""


@skipUnless(HAS_GEOIP2, 'GeoIP2 is required.')
@override_settings(GEOIP_PATH=GEOIP_PATH / 'GeoLite2-ASN-Test.mmdb')
class UnsupportedDatabaseTest(SimpleTestCase):
    def test_unsupported_database(self):
        msg = 'Unable to handle database edition: GeoLite2-ASN'
        with self.assertRaisesMessage(GeoIP2Exception, msg):
            GeoIP2()
