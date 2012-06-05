from __future__ import absolute_import

from django.test import TestCase
from django.contrib.gis import admin
from django.contrib.gis.geos import Point

from .models import City


class GeoAdminTest(TestCase):
    urls = 'django.contrib.gis.tests.geoadmin.urls'

    def test01_ensure_geographic_media(self):
        geoadmin = admin.site._registry[City]
        admin_js = geoadmin.media.render_js()
        self.assertTrue(any([geoadmin.openlayers_url in js for js in admin_js]))

    def test_olmap_OSM_rendering(self):
        geoadmin = admin.site._registry[City]
        result = geoadmin.get_map_widget(City._meta.get_field('point'))(
            ).render('point', Point(-79.460734, 40.18476))
        self.assertIn(
            """geodjango_point.layers.base = new OpenLayers.Layer.OSM("OpenStreetMap (Mapnik)");""",
            result)

    def test_olmap_WMS_rendering(self):
        admin.site.unregister(City)
        admin.site.register(City, admin.GeoModelAdmin)

        geoadmin = admin.site._registry[City]
        result = geoadmin.get_map_widget(City._meta.get_field('point'))(
            ).render('point', Point(-79.460734, 40.18476))
        self.assertIn(
            """geodjango_point.layers.base = new OpenLayers.Layer.WMS("OpenLayers WMS", "http://vmap0.tiles.osgeo.org/wms/vmap0", {layers: \'basic\', format: 'image/jpeg'});""",
            result)
