from django.test import TestCase
from django.contrib.gis import admin
from models import City

class GeoAdminTest(TestCase):
    urls = 'django.contrib.gis.tests.geoadmin.urls'

    def test01_ensure_geographic_media(self):
        geoadmin = admin.site._registry[City]
        admin_js = geoadmin.media.render_js()
        osm_url = geoadmin.extra_js[0]
        self.assertTrue(any([geoadmin.openlayers_url in js for js in admin_js]))
        self.assertTrue(any([osm_url in js for js in admin_js]))
        
