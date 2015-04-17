# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from unittest import skipUnless

from django.contrib.gis.geos import HAS_GEOS
from django.test import SimpleTestCase
from django.test.utils import modify_settings, override_settings
from django.utils.encoding import force_text

GOOGLE_MAPS_API_KEY = 'XXXX'


@skipUnless(HAS_GEOS, 'Geos is required.')
@modify_settings(
    INSTALLED_APPS={'append': 'django.contrib.gis'},
)
class GoogleMapsTest(SimpleTestCase):

    @override_settings(GOOGLE_MAPS_API_KEY=GOOGLE_MAPS_API_KEY)
    def test_google_map_scripts(self):
        """
        Testing GoogleMap.scripts() output. See #20773.
        """
        from django.contrib.gis.maps.google.gmap import GoogleMap

        google_map = GoogleMap()
        scripts = google_map.scripts
        self.assertIn(GOOGLE_MAPS_API_KEY, scripts)
        self.assertIn("new GMap2", scripts)

    @override_settings(GOOGLE_MAPS_API_KEY=GOOGLE_MAPS_API_KEY)
    def test_unicode_in_google_maps(self):
        """
        Test that GoogleMap doesn't crash with non-ASCII content.
        """
        from django.contrib.gis.geos import Point
        from django.contrib.gis.maps.google.gmap import GoogleMap, GMarker

        center = Point(6.146805, 46.227574)
        marker = GMarker(center,
                         title='En français !')
        google_map = GoogleMap(center=center, zoom=18, markers=[marker])
        self.assertIn("En français", google_map.scripts)

    def test_gevent_html_safe(self):
        from django.contrib.gis.maps.google.overlays import GEvent
        event = GEvent('click', 'function() {location.href = "http://www.google.com"}')
        self.assertTrue(hasattr(GEvent, '__html__'))
        self.assertEqual(force_text(event), event.__html__())

    def test_goverlay_html_safe(self):
        from django.contrib.gis.maps.google.overlays import GOverlayBase
        overlay = GOverlayBase()
        overlay.js_params = '"foo", "bar"'
        self.assertTrue(hasattr(GOverlayBase, '__html__'))
        self.assertEqual(force_text(overlay), overlay.__html__())
