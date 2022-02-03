import os
import pathlib
from unittest import mock, skipUnless

from django.conf import settings
from django.contrib.gis.geoip2 import HAS_GEOIP2
from django.contrib.gis.geos import GEOSGeometry
from django.test import SimpleTestCase

if HAS_GEOIP2:
    from django.contrib.gis.geoip2 import GeoIP2, GeoIP2Exception


# Note: Requires both the GeoIP country and city datasets.
# The GEOIP_DATA path should be the only setting set (the directory
# should contain links or the actual database files 'GeoLite2-City.mmdb' and
# 'GeoLite2-City.mmdb'.
@skipUnless(
    HAS_GEOIP2 and getattr(settings, "GEOIP_PATH", None),
    "GeoIP is required along with the GEOIP_PATH setting.",
)
class GeoIPTest(SimpleTestCase):
    addr = "129.237.192.1"
    fqdn = "ku.edu"

    def test01_init(self):
        "GeoIP initialization."
        g1 = GeoIP2()  # Everything inferred from GeoIP path
        path = settings.GEOIP_PATH
        g2 = GeoIP2(path, 0)  # Passing in data path explicitly.
        g3 = GeoIP2.open(path, 0)  # MaxMind Python API syntax.
        # path accepts str and pathlib.Path.
        if isinstance(path, str):
            g4 = GeoIP2(pathlib.Path(path))
        else:
            g4 = GeoIP2(str(path))

        for g in (g1, g2, g3, g4):
            self.assertTrue(g._country)
            self.assertTrue(g._city)

        # Only passing in the location of one database.
        city = os.path.join(path, "GeoLite2-City.mmdb")
        cntry = os.path.join(path, "GeoLite2-Country.mmdb")
        g4 = GeoIP2(city, country="")
        self.assertIsNone(g4._country)
        g5 = GeoIP2(cntry, city="")
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
                GeoIP2(bad, 0)

    def test_no_database_file(self):
        invalid_path = os.path.join(os.path.dirname(__file__), "data")
        msg = "Could not load a database from %s." % invalid_path
        with self.assertRaisesMessage(GeoIP2Exception, msg):
            GeoIP2(invalid_path)

    def test02_bad_query(self):
        "GeoIP query parameter checking."
        cntry_g = GeoIP2(city="<foo>")
        # No city database available, these calls should fail.
        with self.assertRaises(GeoIP2Exception):
            cntry_g.city("tmc.edu")
        with self.assertRaises(GeoIP2Exception):
            cntry_g.coords("tmc.edu")

        # Non-string query should raise TypeError
        with self.assertRaises(TypeError):
            cntry_g.country_code(17)
        with self.assertRaises(TypeError):
            cntry_g.country_name(GeoIP2)

    @mock.patch("socket.gethostbyname")
    def test03_country(self, gethostbyname):
        "GeoIP country querying methods."
        gethostbyname.return_value = "128.249.1.1"
        g = GeoIP2(city="<foo>")

        for query in (self.fqdn, self.addr):
            self.assertEqual(
                "US",
                g.country_code(query),
                "Failed for func country_code and query %s" % query,
            )
            self.assertEqual(
                "United States",
                g.country_name(query),
                "Failed for func country_name and query %s" % query,
            )
            self.assertEqual(
                {"country_code": "US", "country_name": "United States"},
                g.country(query),
            )

    @mock.patch("socket.gethostbyname")
    def test04_city(self, gethostbyname):
        "GeoIP city querying methods."
        gethostbyname.return_value = "129.237.192.1"
        g = GeoIP2(country="<foo>")

        for query in (self.fqdn, self.addr):
            # Country queries should still work.
            self.assertEqual(
                "US",
                g.country_code(query),
                "Failed for func country_code and query %s" % query,
            )
            self.assertEqual(
                "United States",
                g.country_name(query),
                "Failed for func country_name and query %s" % query,
            )
            self.assertEqual(
                {"country_code": "US", "country_name": "United States"},
                g.country(query),
            )

            # City information dictionary.
            d = g.city(query)
            self.assertEqual("NA", d["continent_code"])
            self.assertEqual("North America", d["continent_name"])
            self.assertEqual("US", d["country_code"])
            self.assertEqual("Lawrence", d["city"])
            self.assertEqual("KS", d["region"])
            self.assertEqual("America/Chicago", d["time_zone"])
            self.assertFalse(d["is_in_european_union"])
            geom = g.geos(query)
            self.assertIsInstance(geom, GEOSGeometry)

            for e1, e2 in (
                geom.tuple,
                g.coords(query),
                g.lon_lat(query),
                g.lat_lon(query),
            ):
                self.assertIsInstance(e1, float)
                self.assertIsInstance(e2, float)

    def test06_ipv6_query(self):
        "GeoIP can lookup IPv6 addresses."
        g = GeoIP2()
        d = g.city("2002:81ed:c9a5::81ed:c9a5")  # IPv6 address for www.nhm.ku.edu
        self.assertEqual("US", d["country_code"])
        self.assertEqual("Lawrence", d["city"])
        self.assertEqual("KS", d["region"])

    def test_repr(self):
        path = settings.GEOIP_PATH
        g = GeoIP2(path=path)
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

    @mock.patch("socket.gethostbyname", return_value="expected")
    def test_check_query(self, gethostbyname):
        g = GeoIP2()
        self.assertEqual(g._check_query("127.0.0.1"), "127.0.0.1")
        self.assertEqual(
            g._check_query("2002:81ed:c9a5::81ed:c9a5"), "2002:81ed:c9a5::81ed:c9a5"
        )
        self.assertEqual(g._check_query("invalid-ip-address"), "expected")
