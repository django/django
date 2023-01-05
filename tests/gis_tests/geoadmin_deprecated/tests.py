from django.contrib.gis import admin
from django.contrib.gis.geos import Point
from django.test import SimpleTestCase, ignore_warnings, override_settings
from django.utils.deprecation import RemovedInDjango50Warning

from .admin import UnmodifiableAdmin
from .models import City, site


@ignore_warnings(category=RemovedInDjango50Warning)
@override_settings(ROOT_URLCONF="django.contrib.gis.tests.geoadmin.urls")
class GeoAdminTest(SimpleTestCase):
    def test_ensure_geographic_media(self):
        geoadmin = site._registry[City]
        admin_js = geoadmin.media.render_js()
        self.assertTrue(any(geoadmin.openlayers_url in js for js in admin_js))

    def test_olmap_OSM_rendering(self):
        delete_all_btn = (
            '<a href="javascript:geodjango_point.clearFeatures()">Delete all Features'
            "</a>"
        )
        original_geoadmin = site._registry[City]
        params = original_geoadmin.get_map_widget(City._meta.get_field("point")).params
        result = original_geoadmin.get_map_widget(
            City._meta.get_field("point")
        )().render("point", Point(-79.460734, 40.18476), params)
        self.assertIn(
            "geodjango_point.layers.base = "
            'new OpenLayers.Layer.OSM("OpenStreetMap (Mapnik)");',
            result,
        )

        self.assertIn(delete_all_btn, result)

        site.unregister(City)
        site.register(City, UnmodifiableAdmin)
        try:
            geoadmin = site._registry[City]
            params = geoadmin.get_map_widget(City._meta.get_field("point")).params
            result = geoadmin.get_map_widget(City._meta.get_field("point"))().render(
                "point", Point(-79.460734, 40.18476), params
            )

            self.assertNotIn(delete_all_btn, result)
        finally:
            site.unregister(City)
            site.register(City, original_geoadmin.__class__)

    def test_olmap_WMS_rendering(self):
        geoadmin = admin.GeoModelAdmin(City, site)
        result = geoadmin.get_map_widget(City._meta.get_field("point"))().render(
            "point", Point(-79.460734, 40.18476)
        )
        self.assertIn(
            'geodjango_point.layers.base = new OpenLayers.Layer.WMS("OpenLayers WMS", '
            '"http://vmap0.tiles.osgeo.org/wms/vmap0", '
            "{layers: 'basic', format: 'image/jpeg'});",
            result,
        )

    def test_olwidget_has_changed(self):
        """
        Changes are accurately noticed by OpenLayersWidget.
        """
        geoadmin = site._registry[City]
        form = geoadmin.get_changelist_form(None)()
        has_changed = form.fields["point"].has_changed

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

    def test_olwidget_empty_string(self):
        geoadmin = site._registry[City]
        form = geoadmin.get_changelist_form(None)({"point": ""})
        with self.assertNoLogs("django.contrib.gis", "ERROR"):
            output = str(form["point"])
        self.assertInHTML(
            '<textarea id="id_point" class="vWKTField required" cols="150"'
            ' rows="10" name="point"></textarea>',
            output,
        )

    def test_olwidget_invalid_string(self):
        geoadmin = site._registry[City]
        form = geoadmin.get_changelist_form(None)({"point": "INVALID()"})
        with self.assertLogs("django.contrib.gis", "ERROR") as cm:
            output = str(form["point"])
        self.assertInHTML(
            '<textarea id="id_point" class="vWKTField required" cols="150"'
            ' rows="10" name="point"></textarea>',
            output,
        )
        self.assertEqual(len(cm.records), 1)
        self.assertEqual(
            cm.records[0].getMessage(),
            "Error creating geometry from value 'INVALID()' (String input "
            "unrecognized as WKT EWKT, and HEXEWKB.)",
        )


class DeprecationTests(SimpleTestCase):
    def test_warning(self):
        class DeprecatedOSMGeoAdmin(admin.OSMGeoAdmin):
            pass

        class DeprecatedGeoModelAdmin(admin.GeoModelAdmin):
            pass

        msg = (
            "django.contrib.gis.admin.GeoModelAdmin and OSMGeoAdmin are "
            "deprecated in favor of django.contrib.admin.ModelAdmin and "
            "django.contrib.gis.admin.GISModelAdmin."
        )
        with self.assertRaisesMessage(RemovedInDjango50Warning, msg):
            DeprecatedOSMGeoAdmin(City, site)
        with self.assertRaisesMessage(RemovedInDjango50Warning, msg):
            DeprecatedGeoModelAdmin(City, site)

    def test_openlayerswidget_warning(self):
        msg = "django.contrib.gis.admin.OpenLayersWidget is deprecated."
        with self.assertRaisesMessage(RemovedInDjango50Warning, msg):
            admin.OpenLayersWidget()
