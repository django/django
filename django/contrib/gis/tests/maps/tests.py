# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from unittest import skipUnless

from django.contrib.gis.geos import HAS_GEOS, Point
from django.test import TestCase
from django.test.utils import override_settings

GOOGLE_MAPS_API_KEY = 'XXXX'


@skipUnless(HAS_GEOS, 'Geos is required.')
class GoogleMapsTest(TestCase):

    @override_settings(GOOGLE_MAPS_API_KEY=GOOGLE_MAPS_API_KEY)
    def test_unicode_in_google_maps(self):
        """
        Unicode or not unicode.
        """
        from django.contrib.gis.maps.google.gmap import GoogleMap, GMarker
        from django.template import Context, Template
        center = Point(6.146805, 46.227574)
        marker = GMarker(center, title='Le français peut-être dangereux pour la santé, à consommer avec modération !')
        google = GoogleMap(center=center, zoom=18, markers=[marker])
        Template('{{ google.scripts }}').render(Context({'google': google}))
