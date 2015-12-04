from __future__ import unicode_literals

from unittest import skipUnless

from django.contrib.gis import admin
from django.contrib.gis.gdal import HAS_GDAL
from django.contrib.gis.geos import Point
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase, mock, override_settings, skipUnlessDBFeature

from .admin import UnmodifiableAdmin
from .models import City, CityMercator, site


@skipUnlessDBFeature("gis_enabled")
@override_settings(ROOT_URLCONF='django.contrib.gis.tests.geoadmin.urls')
class GeoAdminTest(TestCase):

    def test_ensure_geographic_media(self):
        geoadmin = site._registry[City]
        admin_js = geoadmin.media.render_js()
        self.assertTrue(any(geoadmin.openlayers_url in js for js in admin_js))

    def test_olmap_OSM_rendering(self):
        delete_all_btn = """<a href="javascript:geodjango_point.clearFeatures()">Delete all Features</a>"""

        original_geoadmin = site._registry[City]
        params = original_geoadmin.get_map_widget(City._meta.get_field('point')).params
        result = original_geoadmin.get_map_widget(City._meta.get_field('point'))(
        ).render('point', Point(-79.460734, 40.18476), params)
        self.assertIn(
            """geodjango_point.layers.base = new OpenLayers.Layer.OSM("OpenStreetMap (Mapnik)");""",
            result)

        self.assertIn(delete_all_btn, result)

        site.unregister(City)
        site.register(City, UnmodifiableAdmin)
        try:
            geoadmin = site._registry[City]
            params = geoadmin.get_map_widget(City._meta.get_field('point')).params
            result = geoadmin.get_map_widget(City._meta.get_field('point'))(
            ).render('point', Point(-79.460734, 40.18476), params)

            self.assertNotIn(delete_all_btn, result)
        finally:
            site.unregister(City)
            site.register(City, original_geoadmin.__class__)

    def test_olmap_WMS_rendering(self):
        geoadmin = admin.GeoModelAdmin(City, site)
        result = geoadmin.get_map_widget(City._meta.get_field('point'))(
        ).render('point', Point(-79.460734, 40.18476))
        self.assertIn(
            """geodjango_point.layers.base = new OpenLayers.Layer.WMS("OpenLayers WMS", """
            """"http://vmap0.tiles.osgeo.org/wms/vmap0", {layers: 'basic', format: 'image/jpeg'});""",
            result)

    @mock.patch('django.contrib.gis.admin.options.HAS_GDAL', False)
    def test_no_gdal_admin_model_diffent_srid(self):
        msg = (
            'Map SRID is 3857 and SRID of `geoadmin.City.point` is 4326. '
            'GDAL must be installed to perform the transformation.'
        )
        with self.assertRaisesMessage(ImproperlyConfigured, msg):
            geoadmin = site._registry[City]
            geoadmin.get_changelist_form(None)()

    @mock.patch('django.contrib.gis.admin.options.HAS_GDAL', False)
    def test_no_gdal_admin_model_same_srid(self):
        geoadmin = site._registry[CityMercator]
        geoadmin.get_changelist_form(None)()

    @skipUnless(HAS_GDAL, "GDAL is required.")
    def test_olwidget_has_changed(self):
        """
        Check that changes are accurately noticed by OpenLayersWidget.
        """
        geoadmin = site._registry[City]
        form = geoadmin.get_changelist_form(None)()
        has_changed = form.fields['point'].has_changed

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
