import itertools
import pathlib
from unittest import mock, skipUnless

from django.conf import settings
from django.contrib.gis.geoip2 import HAS_GEOIP2
from django.contrib.gis.geos import GEOSGeometry
from django.test import SimpleTestCase, override_settings
from django.utils.deprecation import RemovedInDjango60Warning

if HAS_GEOIP2:
    import geoip2

    from django.contrib.gis.geoip2 import GeoIP2, GeoIP2Exception


def build_geoip_path(*parts):
    return pathlib.Path(__file__).parent.joinpath("data/geoip2", *parts).resolve()


@skipUnless(HAS_GEOIP2, "GeoIP2 is required.")
@override_settings(
    GEOIP_CITY="GeoLite2-City-Test.mmdb",
    GEOIP_COUNTRY="GeoLite2-Country-Test.mmdb",
)
class GeoLite2Test(SimpleTestCase):
    fqdn = "sky.uk"
    ipv4 = "2.125.160.216"
    ipv6 = "::ffff:027d:a0d8"

    @classmethod
    def setUpClass(cls):
        # Avoid referencing __file__ at module level.
        cls.enterClassContext(override_settings(GEOIP_PATH=build_geoip_path()))
        # Always mock host lookup to avoid test breakage if DNS changes.
        cls.enterClassContext(mock.patch("socket.gethostbyname", return_value=cls.ipv4))

        super().setUpClass()

    def test_init(self):
        # Everything inferred from GeoIP path.
        g1 = GeoIP2()
        # Path passed explicitly.
        g2 = GeoIP2(settings.GEOIP_PATH, GeoIP2.MODE_AUTO)
        # Path provided as a string.
        g3 = GeoIP2(str(settings.GEOIP_PATH))
        for g in (g1, g2, g3):
            self.assertTrue(g._country)
            self.assertTrue(g._city)

        # Only passing in the location of one database.
        g4 = GeoIP2(settings.GEOIP_PATH / settings.GEOIP_CITY, country="")
        self.assertTrue(g4._city)
        self.assertIsNone(g4._country)
        g5 = GeoIP2(settings.GEOIP_PATH / settings.GEOIP_COUNTRY, city="")
        self.assertTrue(g5._country)
        self.assertIsNone(g5._city)

        # Improper parameters.
        bad_params = (23, "foo", 15.23)
        for bad in bad_params:
            with self.assertRaises(GeoIP2Exception):
                GeoIP2(cache=bad)
            if isinstance(bad, str):
                e = GeoIP2Exception
            else:
                e = TypeError
            with self.assertRaises(e):
                GeoIP2(bad, GeoIP2.MODE_AUTO)

    def test_no_database_file(self):
        invalid_path = pathlib.Path(__file__).parent.joinpath("data/invalid").resolve()
        msg = f"Could not load a database from {invalid_path}."
        with self.assertRaisesMessage(GeoIP2Exception, msg):
            GeoIP2(invalid_path)

    def test_bad_query(self):
        g = GeoIP2(city="<invalid>")

        functions = (g.city, g.geos, g.lat_lon, g.lon_lat)
        msg = "Invalid GeoIP city data file: "
        for function in functions:
            with self.subTest(function=function.__qualname__):
                with self.assertRaisesMessage(GeoIP2Exception, msg):
                    function("example.com")

        functions += (g.country, g.country_code, g.country_name)
        values = (123, 123.45, b"", (), [], {}, set(), frozenset(), GeoIP2)
        msg = "GeoIP query must be a string, not type"
        for function, value in itertools.product(functions, values):
            with self.subTest(function=function.__qualname__, type=type(value)):
                with self.assertRaisesMessage(TypeError, msg):
                    function(value)

    def test_country(self):
        g = GeoIP2(city="<invalid>")
        for query in (self.fqdn, self.ipv4, self.ipv6):
            with self.subTest(query=query):
                self.assertEqual(
                    g.country(query),
                    {
                        "country_code": "GB",
                        "country_name": "United Kingdom",
                    },
                )
                self.assertEqual(g.country_code(query), "GB")
                self.assertEqual(g.country_name(query), "United Kingdom")

    def test_city(self):
        g = GeoIP2(country="<invalid>")
        for query in (self.fqdn, self.ipv4, self.ipv6):
            with self.subTest(query=query):
                self.assertEqual(
                    g.city(query),
                    {
                        "city": "Boxford",
                        "continent_code": "EU",
                        "continent_name": "Europe",
                        "country_code": "GB",
                        "country_name": "United Kingdom",
                        "dma_code": None,
                        "is_in_european_union": False,
                        "latitude": 51.75,
                        "longitude": -1.25,
                        "postal_code": "OX1",
                        "region": "ENG",
                        "time_zone": "Europe/London",
                    },
                )

                geom = g.geos(query)
                self.assertIsInstance(geom, GEOSGeometry)
                self.assertEqual(geom.srid, 4326)
                self.assertEqual(geom.tuple, (-1.25, 51.75))

                self.assertEqual(g.lat_lon(query), (51.75, -1.25))
                self.assertEqual(g.lon_lat(query), (-1.25, 51.75))
                # Country queries should still work.
                self.assertEqual(
                    g.country(query),
                    {
                        "country_code": "GB",
                        "country_name": "United Kingdom",
                    },
                )
                self.assertEqual(g.country_code(query), "GB")
                self.assertEqual(g.country_name(query), "United Kingdom")

    def test_not_found(self):
        g1 = GeoIP2(city="<invalid>")
        g2 = GeoIP2(country="<invalid>")
        for function, query in itertools.product(
            (g1.country, g2.city), ("127.0.0.1", "::1")
        ):
            with self.subTest(function=function.__qualname__, query=query):
                msg = f"The address {query} is not in the database."
                with self.assertRaisesMessage(geoip2.errors.AddressNotFoundError, msg):
                    function(query)

    def test_del(self):
        g = GeoIP2()
        city = g._city
        country = g._country
        self.assertIs(city._db_reader.closed, False)
        self.assertIs(country._db_reader.closed, False)
        del g
        self.assertIs(city._db_reader.closed, True)
        self.assertIs(country._db_reader.closed, True)

    def test_repr(self):
        g = GeoIP2()
        meta = g._reader.metadata()
        version = "%s.%s" % (
            meta.binary_format_major_version,
            meta.binary_format_minor_version,
        )
        country_path = g._country_file
        city_path = g._city_file
        expected = (
            '<GeoIP2 [v%(version)s] _country_file="%(country)s", _city_file="%(city)s">'
            % {
                "version": version,
                "country": country_path,
                "city": city_path,
            }
        )
        self.assertEqual(repr(g), expected)

    def test_check_query(self):
        g = GeoIP2()
        self.assertEqual(g._check_query(self.ipv4), self.ipv4)
        self.assertEqual(g._check_query(self.ipv6), self.ipv6)
        self.assertEqual(g._check_query(self.fqdn), self.ipv4)

    def test_coords_deprecation_warning(self):
        g = GeoIP2()
        msg = "GeoIP2.coords() is deprecated. Use GeoIP2.lon_lat() instead."
        with self.assertWarnsMessage(RemovedInDjango60Warning, msg):
            e1, e2 = g.coords(self.ipv4)
        self.assertIsInstance(e1, float)
        self.assertIsInstance(e2, float)

    def test_open_deprecation_warning(self):
        msg = "GeoIP2.open() is deprecated. Use GeoIP2() instead."
        with self.assertWarnsMessage(RemovedInDjango60Warning, msg):
            g = GeoIP2.open(settings.GEOIP_PATH, GeoIP2.MODE_AUTO)
        self.assertTrue(g._country)
        self.assertTrue(g._city)


@skipUnless(HAS_GEOIP2, "GeoIP2 is required.")
@override_settings(
    GEOIP_CITY="GeoIP2-City-Test.mmdb",
    GEOIP_COUNTRY="GeoIP2-Country-Test.mmdb",
)
class GeoIP2Test(GeoLite2Test):
    """Non-free GeoIP2 databases are supported."""


@skipUnless(HAS_GEOIP2, "GeoIP2 is required.")
class ErrorTest(SimpleTestCase):
    def test_missing_path(self):
        msg = "GeoIP path must be provided via parameter or the GEOIP_PATH setting."
        with self.settings(GEOIP_PATH=None):
            with self.assertRaisesMessage(GeoIP2Exception, msg):
                GeoIP2()

    def test_unsupported_database(self):
        msg = "Unable to recognize database edition: GeoLite2-ASN"
        with self.settings(GEOIP_PATH=build_geoip_path("GeoLite2-ASN-Test.mmdb")):
            with self.assertRaisesMessage(GeoIP2Exception, msg):
                GeoIP2()
