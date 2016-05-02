# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import socket
import unittest
import warnings
from unittest import skipUnless

from django.conf import settings
from django.contrib.gis.geoip import HAS_GEOIP
from django.contrib.gis.geos import HAS_GEOS, GEOSGeometry
from django.test import ignore_warnings
from django.utils import six
from django.utils.deprecation import RemovedInDjango20Warning
from django.utils.encoding import force_text

if HAS_GEOIP:
    from django.contrib.gis.geoip import GeoIP, GeoIPException
    from django.contrib.gis.geoip.prototypes import GeoIP_lib_version


# Note: Requires use of both the GeoIP country and city datasets.
# The GEOIP_DATA path should be the only setting set (the directory
# should contain links or the actual database files 'GeoIP.dat' and
# 'GeoLiteCity.dat'.


@skipUnless(
    HAS_GEOIP and getattr(settings, "GEOIP_PATH", None),
    "GeoIP is required along with the GEOIP_PATH setting."
)
@ignore_warnings(category=RemovedInDjango20Warning)
class GeoIPTest(unittest.TestCase):
    addr = '128.249.1.1'
    fqdn = 'tmc.edu'

    def _is_dns_available(self, domain):
        # Naive check to see if there is DNS available to use.
        # Used to conditionally skip fqdn geoip checks.
        # See #25407 for details.
        ErrClass = socket.error if six.PY2 else OSError
        try:
            socket.gethostbyname(domain)
            return True
        except ErrClass:
            return False

    def test01_init(self):
        "Testing GeoIP initialization."
        g1 = GeoIP()  # Everything inferred from GeoIP path
        path = settings.GEOIP_PATH
        g2 = GeoIP(path, 0)  # Passing in data path explicitly.
        g3 = GeoIP.open(path, 0)  # MaxMind Python API syntax.

        for g in (g1, g2, g3):
            self.assertTrue(g._country)
            self.assertTrue(g._city)

        # Only passing in the location of one database.
        city = os.path.join(path, 'GeoLiteCity.dat')
        cntry = os.path.join(path, 'GeoIP.dat')
        g4 = GeoIP(city, country='')
        self.assertIsNone(g4._country)
        g5 = GeoIP(cntry, city='')
        self.assertIsNone(g5._city)

        # Improper parameters.
        bad_params = (23, 'foo', 15.23)
        for bad in bad_params:
            with self.assertRaises(GeoIPException):
                GeoIP(cache=bad)
            if isinstance(bad, six.string_types):
                e = GeoIPException
            else:
                e = TypeError
            with self.assertRaises(e):
                GeoIP(bad, 0)

    def test02_bad_query(self):
        "Testing GeoIP query parameter checking."
        cntry_g = GeoIP(city='<foo>')
        # No city database available, these calls should fail.
        with self.assertRaises(GeoIPException):
            cntry_g.city('google.com')
        with self.assertRaises(GeoIPException):
            cntry_g.coords('yahoo.com')

        # Non-string query should raise TypeError
        with self.assertRaises(TypeError):
            cntry_g.country_code(17)
        with self.assertRaises(TypeError):
            cntry_g.country_name(GeoIP)

    def test03_country(self):
        "Testing GeoIP country querying methods."
        g = GeoIP(city='<foo>')

        queries = [self.addr]
        if self._is_dns_available(self.fqdn):
            queries.append(self.fqdn)
        for query in queries:
            for func in (g.country_code, g.country_code_by_addr, g.country_code_by_name):
                self.assertEqual('US', func(query), 'Failed for func %s and query %s' % (func, query))
            for func in (g.country_name, g.country_name_by_addr, g.country_name_by_name):
                self.assertEqual('United States', func(query), 'Failed for func %s and query %s' % (func, query))
            self.assertEqual({'country_code': 'US', 'country_name': 'United States'},
                             g.country(query))

    @skipUnless(HAS_GEOS, "Geos is required")
    def test04_city(self):
        "Testing GeoIP city querying methods."
        g = GeoIP(country='<foo>')

        queries = [self.addr]
        if self._is_dns_available(self.fqdn):
            queries.append(self.fqdn)
        for query in queries:
            # Country queries should still work.
            for func in (g.country_code, g.country_code_by_addr, g.country_code_by_name):
                self.assertEqual('US', func(query))
            for func in (g.country_name, g.country_name_by_addr, g.country_name_by_name):
                self.assertEqual('United States', func(query))
            self.assertEqual({'country_code': 'US', 'country_name': 'United States'},
                             g.country(query))

            # City information dictionary.
            d = g.city(query)
            self.assertEqual('USA', d['country_code3'])
            self.assertEqual('Houston', d['city'])
            self.assertEqual('TX', d['region'])
            self.assertEqual(713, d['area_code'])
            geom = g.geos(query)
            self.assertIsInstance(geom, GEOSGeometry)
            lon, lat = (-95.4010, 29.7079)
            lat_lon = g.lat_lon(query)
            lat_lon = (lat_lon[1], lat_lon[0])
            for tup in (geom.tuple, g.coords(query), g.lon_lat(query), lat_lon):
                self.assertAlmostEqual(lon, tup[0], 4)
                self.assertAlmostEqual(lat, tup[1], 4)

    def test05_unicode_response(self):
        "Testing that GeoIP strings are properly encoded, see #16553."
        g = GeoIP()
        fqdn = "duesseldorf.de"
        if self._is_dns_available(fqdn):
            d = g.city(fqdn)
            self.assertEqual('Düsseldorf', d['city'])
        d = g.country('200.26.205.1')
        # Some databases have only unaccented countries
        self.assertIn(d['country_name'], ('Curaçao', 'Curacao'))

    def test_deprecation_warning(self):
        with warnings.catch_warnings(record=True) as warns:
            warnings.simplefilter('always')
            GeoIP()

        self.assertEqual(len(warns), 1)
        msg = str(warns[0].message)
        self.assertIn('django.contrib.gis.geoip is deprecated', msg)

    def test_repr(self):
        path = settings.GEOIP_PATH
        g = GeoIP(path=path)
        country_path = g._country_file
        city_path = g._city_file
        if GeoIP_lib_version:
            expected = '<GeoIP [v%(version)s] _country_file="%(country)s", _city_file="%(city)s">' % {
                'version': force_text(GeoIP_lib_version()),
                'country': country_path,
                'city': city_path,
            }
        else:
            expected = '<GeoIP _country_file="%(country)s", _city_file="%(city)s">' % {
                'country': country_path,
                'city': city_path,
            }
        self.assertEqual(repr(g), expected)
