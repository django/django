# -*- encoding: utf-8 -*-
from unittest import skipUnless
from django.contrib.gis.geos import HAS_GEOS
from django.contrib.gis.tests.utils import HAS_SPATIAL_DB
from django.test import TestCase
from django.contrib.gis.maps.google.gmap import GoogleMap
from django.test.utils import override_settings

GOOGLE_MAPS_API_KEY = 'XXXX'


@skipUnless(HAS_GEOS and HAS_SPATIAL_DB, "Geos and spatial db are required.")
class GoogleMapRegressionTests(TestCase):

    @override_settings(GOOGLE_MAPS_API_KEY=GOOGLE_MAPS_API_KEY)
    def test_script(self):
        "Testing GoogleMap.script(). See #20773."
        google_map = GoogleMap()
        scripts = google_map.scripts
        self.assertIn(GOOGLE_MAPS_API_KEY, scripts)
        self.assertNotIn("<![CDATA[\n%s//]]>", scripts)
