# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
from django.conf import settings
from django.contrib.gis.geos import HAS_GEOS
from django.contrib.gis.geoip import HAS_GEOIP
from django.utils import unittest
from django.utils.unittest import skipUnless

from django.utils import six

if HAS_GEOIP:
    from . import GeoIP, GeoIPException

if HAS_GEOS:
    from ..geos import GEOSGeometry


# Note: Requires use of both the GeoIP country and city datasets.
# The GEOIP_DATA path should be the only setting set (the directory
# should contain links or the actual database files 'GeoIP.dat' and
# 'GeoLiteCity.dat'.


@skipUnless(HAS_GEOIP and getattr(settings, "GEOIP_PATH", None),
    "GeoIP is required along with the GEOIP_DATA setting.")
class GeoIPTest(unittest.TestCase):

    def test01_init(self):
        "Testing GeoIP initialization."
        g1 = GeoIP() # Everything inferred from GeoIP path
        path = settings.GEOIP_PATH
        g2 = GeoIP(path, 0) # Passing in data path explicitly.
        g3 = GeoIP.open(path, 0) # MaxMind Python API syntax.

        for g in (g1, g2, g3):
            self.assertEqual(True, bool(g._country))
            self.assertEqual(True, bool(g._city))

        # Only passing in the location of one database.
        city = os.path.join(path, 'GeoLiteCity.dat')
        cntry = os.path.join(path, 'GeoIP.dat')
        g4 = GeoIP(city, country='')
        self.assertEqual(None, g4._country)
        g5 = GeoIP(cntry, city='')
        self.assertEqual(None, g5._city)

        # Improper parameters.
        bad_params = (23, 'foo', 15.23)
        for bad in bad_params:
            self.assertRaises(GeoIPException, GeoIP, cache=bad)
            if isinstance(bad, six.string_types):
                e = GeoIPException
            else:
                e = TypeError
            self.assertRaises(e, GeoIP, bad, 0)

    def test02_bad_query(self):
        "Testing GeoIP query parameter checking."
        cntry_g = GeoIP(city='<foo>')
        # No city database available, these calls should fail.
        self.assertRaises(GeoIPException, cntry_g.city, 'google.com')
        self.assertRaises(GeoIPException, cntry_g.coords, 'yahoo.com')

        # Non-string query should raise TypeError
        self.assertRaises(TypeError, cntry_g.country_code, 17)
        self.assertRaises(TypeError, cntry_g.country_name, GeoIP)

    def test03_country(self):
        "Testing GeoIP country querying methods."
        g = GeoIP(city='<foo>')

        fqdn = 'www.google.com'
        addr = '12.215.42.19'

        for query in (fqdn, addr):
            for func in (g.country_code, g.country_code_by_addr, g.country_code_by_name):
                self.assertEqual('US', func(query))
            for func in (g.country_name, g.country_name_by_addr, g.country_name_by_name):
                self.assertEqual('United States', func(query))
            self.assertEqual({'country_code' : 'US', 'country_name' : 'United States'},
                             g.country(query))

    @skipUnless(HAS_GEOS, "Geos is required")
    def test04_city(self):
        "Testing GeoIP city querying methods."
        g = GeoIP(country='<foo>')

        addr = '128.249.1.1'
        fqdn = 'tmc.edu'
        for query in (fqdn, addr):
            # Country queries should still work.
            for func in (g.country_code, g.country_code_by_addr, g.country_code_by_name):
                self.assertEqual('US', func(query))
            for func in (g.country_name, g.country_name_by_addr, g.country_name_by_name):
                self.assertEqual('United States', func(query))
            self.assertEqual({'country_code' : 'US', 'country_name' : 'United States'},
                             g.country(query))

            # City information dictionary.
            d = g.city(query)
            self.assertEqual('USA', d['country_code3'])
            self.assertEqual('Houston', d['city'])
            self.assertEqual('TX', d['region'])
            self.assertEqual(713, d['area_code'])
            geom = g.geos(query)
            self.assertTrue(isinstance(geom, GEOSGeometry))
            lon, lat = (-95.4010, 29.7079)
            lat_lon = g.lat_lon(query)
            lat_lon = (lat_lon[1], lat_lon[0])
            for tup in (geom.tuple, g.coords(query), g.lon_lat(query), lat_lon):
                self.assertAlmostEqual(lon, tup[0], 4)
                self.assertAlmostEqual(lat, tup[1], 4)

    def test05_unicode_response(self):
        "Testing that GeoIP strings are properly encoded, see #16553."
        g = GeoIP()
        d = g.city("www.osnabrueck.de")
        self.assertEqual('Osnabrück', d['city'])
