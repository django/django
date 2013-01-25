from __future__ import absolute_import

from django.test import TestCase
from django.contrib.gis import admin
from django.contrib.gis.geos import GEOSGeometry, Point

from .models import City


class GeoAdminTest(TestCase):
    urls = 'django.contrib.gis.tests.geoadmin.urls'

    def test_ensure_geographic_media(self):
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

    def test_olwidget_has_changed(self):
        """ Check that changes are accurately noticed by OpenLayersWidget. """
        geoadmin = admin.site._registry[City]
        form = geoadmin.get_changelist_form(None)()
        has_changed = form.fields['point']._has_changed

        initial = Point(13.4197458572965953, 52.5194108501149799, srid=4326)
        data_same = "SRID=3857;POINT(1493879.2754093995 6894592.019687599)"
        data_almost_same = "SRID=3857;POINT(1493879.2754093990 6894592.019687590)"
        data_changed = "SRID=3857;POINT(1493884.0527237 6894593.8111804)"

        self.assertTrue(has_changed(None, data_changed))
        self.assertTrue(has_changed(initial, ""))
        self.assertFalse(has_changed(None, ""))
        self.assertFalse(has_changed(initial, data_same))
        self.assertFalse(has_changed(initial, data_almost_same))
        self.assertTrue(has_changed(initial, data_changed))
