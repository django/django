from django.contrib.gis.geos import Point
from django.test import SimpleTestCase, override_settings

from .models import City, site, site_gis, site_gis_custom


@override_settings(ROOT_URLCONF="django.contrib.gis.tests.geoadmin.urls")
class GeoAdminTest(SimpleTestCase):
    admin_site = site  # ModelAdmin

    def test_widget_empty_string(self):
        geoadmin = self.admin_site.get_model_admin(City)
        form = geoadmin.get_changelist_form(None)({"point": ""})
        with self.assertRaisesMessage(AssertionError, "no logs"):
            with self.assertLogs("django.contrib.gis", "WARNING"):
                output = str(form["point"])
        self.assertInHTML(
            '<textarea id="id_point" class="vSerializedField required" cols="150"'
            ' rows="10" name="point" hidden></textarea>',
            output,
        )

    def test_widget_invalid_string(self):
        geoadmin = self.admin_site.get_model_admin(City)
        form = geoadmin.get_changelist_form(None)({"point": "INVALID()"})
        with self.assertLogs("django.contrib.gis", "WARNING") as cm:
            output = str(form["point"])
        self.assertInHTML(
            '<textarea id="id_point" class="vSerializedField required" cols="150"'
            ' rows="10" name="point" hidden></textarea>',
            output,
        )
        self.assertEqual(len(cm.records), 2)
        self.assertEqual(
            cm.records[0].getMessage(),
            "Error creating geometry from value 'INVALID()' (String input "
            "unrecognized as WKT EWKT, and HEXEWKB.)",
        )

    def test_widget_has_changed(self):
        geoadmin = self.admin_site.get_model_admin(City)
        form = geoadmin.get_changelist_form(None)()
        has_changed = form.fields["point"].has_changed

        initial = Point(13.4197458572965953, 52.5194108501149799, srid=4326)
        data_same = "SRID=3857;POINT(1493879.2754093995 6894592.019687599)"
        data_almost_same = "SRID=3857;POINT(1493879.2754093990 6894592.019687590)"
        data_changed = "SRID=3857;POINT(1493884.0527237 6894593.8111804)"

        self.assertIs(has_changed(None, data_changed), True)
        self.assertIs(has_changed(initial, ""), True)
        self.assertIs(has_changed(None, ""), False)
        self.assertIs(has_changed(initial, data_same), False)
        self.assertIs(has_changed(initial, data_almost_same), False)
        self.assertIs(has_changed(initial, data_changed), True)


class GISAdminTests(GeoAdminTest):
    admin_site = site_gis  # GISModelAdmin

    def test_default_gis_widget_kwargs(self):
        geoadmin = self.admin_site.get_model_admin(City)
        form = geoadmin.get_changelist_form(None)()
        widget = form["point"].field.widget
        self.assertEqual(widget.attrs["default_lat"], 47)
        self.assertEqual(widget.attrs["default_lon"], 5)
        self.assertEqual(widget.attrs["default_zoom"], 12)

    def test_custom_gis_widget_kwargs(self):
        geoadmin = site_gis_custom.get_model_admin(City)
        form = geoadmin.get_changelist_form(None)()
        widget = form["point"].field.widget
        self.assertEqual(widget.attrs["default_lat"], 55)
        self.assertEqual(widget.attrs["default_lon"], 37)
        self.assertEqual(widget.attrs["default_zoom"], 12)
