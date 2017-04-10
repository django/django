import re

from django.contrib.gis import forms
from django.contrib.gis.geos import GEOSGeometry
from django.forms import ValidationError
from django.test import SimpleTestCase, override_settings, skipUnlessDBFeature
from django.test.utils import patch_logger
from django.utils.html import escape


@skipUnlessDBFeature("gis_enabled")
class GeometryFieldTest(SimpleTestCase):

    def test_init(self):
        "Testing GeometryField initialization with defaults."
        fld = forms.GeometryField()
        for bad_default in ('blah', 3, 'FoO', None, 0):
            with self.assertRaises(ValidationError):
                fld.clean(bad_default)

    def test_srid(self):
        "Testing GeometryField with a SRID set."
        # Input that doesn't specify the SRID is assumed to be in the SRID
        # of the input field.
        fld = forms.GeometryField(srid=4326)
        geom = fld.clean('POINT(5 23)')
        self.assertEqual(4326, geom.srid)
        # Making the field in a different SRID from that of the geometry, and
        # asserting it transforms.
        fld = forms.GeometryField(srid=32140)
        tol = 0.0000001
        xform_geom = GEOSGeometry('POINT (951640.547328465 4219369.26171664)', srid=32140)
        # The cleaned geometry should be transformed to 32140.
        cleaned_geom = fld.clean('SRID=4326;POINT (-95.363151 29.763374)')
        self.assertTrue(xform_geom.equals_exact(cleaned_geom, tol))

    def test_null(self):
        "Testing GeometryField's handling of null (None) geometries."
        # Form fields, by default, are required (`required=True`)
        fld = forms.GeometryField()
        with self.assertRaisesMessage(forms.ValidationError, "No geometry value provided."):
            fld.clean(None)

        # This will clean None as a geometry (See #10660).
        fld = forms.GeometryField(required=False)
        self.assertIsNone(fld.clean(None))

    def test_geom_type(self):
        "Testing GeometryField's handling of different geometry types."
        # By default, all geometry types are allowed.
        fld = forms.GeometryField()
        for wkt in ('POINT(5 23)', 'MULTIPOLYGON(((0 0, 0 1, 1 1, 1 0, 0 0)))', 'LINESTRING(0 0, 1 1)'):
            # `to_python` uses the SRID of OpenLayersWidget if the converted
            # value doesn't have an SRID itself.
            self.assertEqual(GEOSGeometry(wkt, srid=fld.widget.map_srid), fld.clean(wkt))

        pnt_fld = forms.GeometryField(geom_type='POINT')
        self.assertEqual(GEOSGeometry('POINT(5 23)', srid=pnt_fld.widget.map_srid), pnt_fld.clean('POINT(5 23)'))
        # a WKT for any other geom_type will be properly transformed by `to_python`
        self.assertEqual(
            GEOSGeometry('LINESTRING(0 0, 1 1)', srid=pnt_fld.widget.map_srid),
            pnt_fld.to_python('LINESTRING(0 0, 1 1)')
        )
        # but rejected by `clean`
        with self.assertRaises(forms.ValidationError):
            pnt_fld.clean('LINESTRING(0 0, 1 1)')

    def test_to_python(self):
        """
        Testing to_python returns a correct GEOSGeometry object or
        a ValidationError
        """
        fld = forms.GeometryField()
        # to_python returns the same GEOSGeometry for a WKT
        for wkt in ('POINT(5 23)', 'MULTIPOLYGON(((0 0, 0 1, 1 1, 1 0, 0 0)))', 'LINESTRING(0 0, 1 1)'):
            self.assertEqual(GEOSGeometry(wkt, srid=fld.widget.map_srid), fld.to_python(wkt))
        # but raises a ValidationError for any other string
        for wkt in ('POINT(5)', 'MULTI   POLYGON(((0 0, 0 1, 1 1, 1 0, 0 0)))', 'BLAH(0 0, 1 1)'):
            with self.assertRaises(forms.ValidationError):
                fld.to_python(wkt)

    def test_field_with_text_widget(self):
        class PointForm(forms.Form):
            pt = forms.PointField(srid=4326, widget=forms.TextInput)

        form = PointForm()
        cleaned_pt = form.fields['pt'].clean('POINT(5 23)')
        self.assertEqual(cleaned_pt, GEOSGeometry('POINT(5 23)', srid=4326))
        self.assertEqual(4326, cleaned_pt.srid)

        point = GEOSGeometry('SRID=4326;POINT(5 23)')
        form = PointForm(data={'pt': 'POINT(5 23)'}, initial={'pt': point})
        self.assertFalse(form.has_changed())

    def test_field_string_value(self):
        """
        Initialization of a geometry field with a valid/empty/invalid string.
        Only the invalid string should trigger an error log entry.
        """
        class PointForm(forms.Form):
            pt1 = forms.PointField(srid=4326)
            pt2 = forms.PointField(srid=4326)
            pt3 = forms.PointField(srid=4326)

        form = PointForm({
            'pt1': 'SRID=4326;POINT(7.3 44)',  # valid
            'pt2': '',  # empty
            'pt3': 'PNT(0)',  # invalid
        })

        with patch_logger('django.contrib.gis', 'error') as logger_calls:
            output = str(form)

        # The first point can't use assertInHTML() due to non-deterministic
        # ordering of the rendered dictionary.
        pt1_serialized = re.search(r'<textarea [^>]*>({[^<]+})<', output).groups()[0]
        pt1_json = pt1_serialized.replace('&quot;', '"')
        pt1_expected = GEOSGeometry(form.data['pt1']).transform(3857, clone=True)
        self.assertJSONEqual(pt1_json, pt1_expected.json)

        self.assertInHTML(
            '<textarea id="id_pt2" class="vSerializedField required" cols="150"'
            ' rows="10" name="pt2"></textarea>',
            output
        )
        self.assertInHTML(
            '<textarea id="id_pt3" class="vSerializedField required" cols="150"'
            ' rows="10" name="pt3"></textarea>',
            output
        )
        # Only the invalid PNT(0) should trigger an error log entry
        self.assertEqual(len(logger_calls), 1)
        self.assertEqual(
            logger_calls[0],
            "Error creating geometry from value 'PNT(0)' (String input "
            "unrecognized as WKT EWKT, and HEXEWKB.)"
        )


@skipUnlessDBFeature("gis_enabled")
class SpecializedFieldTest(SimpleTestCase):
    def setUp(self):
        self.geometries = {
            'point': GEOSGeometry("SRID=4326;POINT(9.052734375 42.451171875)"),
            'multipoint': GEOSGeometry("SRID=4326;MULTIPOINT("
                                       "(13.18634033203125 14.504356384277344),"
                                       "(13.207969665527 14.490966796875),"
                                       "(13.177070617675 14.454917907714))"),
            'linestring': GEOSGeometry("SRID=4326;LINESTRING("
                                       "-8.26171875 -0.52734375,"
                                       "-7.734375 4.21875,"
                                       "6.85546875 3.779296875,"
                                       "5.44921875 -3.515625)"),
            'multilinestring': GEOSGeometry("SRID=4326;MULTILINESTRING("
                                            "(-16.435546875 -2.98828125,"
                                            "-17.2265625 2.98828125,"
                                            "-0.703125 3.515625,"
                                            "-1.494140625 -3.33984375),"
                                            "(-8.0859375 -5.9765625,"
                                            "8.525390625 -8.7890625,"
                                            "12.392578125 -0.87890625,"
                                            "10.01953125 7.646484375))"),
            'polygon': GEOSGeometry("SRID=4326;POLYGON("
                                    "(-1.669921875 6.240234375,"
                                    "-3.8671875 -0.615234375,"
                                    "5.9765625 -3.955078125,"
                                    "18.193359375 3.955078125,"
                                    "9.84375 9.4921875,"
                                    "-1.669921875 6.240234375))"),
            'multipolygon': GEOSGeometry("SRID=4326;MULTIPOLYGON("
                                         "((-17.578125 13.095703125,"
                                         "-17.2265625 10.8984375,"
                                         "-13.974609375 10.1953125,"
                                         "-13.359375 12.744140625,"
                                         "-15.732421875 13.7109375,"
                                         "-17.578125 13.095703125)),"
                                         "((-8.525390625 5.537109375,"
                                         "-8.876953125 2.548828125,"
                                         "-5.888671875 1.93359375,"
                                         "-5.09765625 4.21875,"
                                         "-6.064453125 6.240234375,"
                                         "-8.525390625 5.537109375)))"),
            'geometrycollection': GEOSGeometry("SRID=4326;GEOMETRYCOLLECTION("
                                               "POINT(5.625 -0.263671875),"
                                               "POINT(6.767578125 -3.603515625),"
                                               "POINT(8.525390625 0.087890625),"
                                               "POINT(8.0859375 -2.13134765625),"
                                               "LINESTRING("
                                               "6.273193359375 -1.175537109375,"
                                               "5.77880859375 -1.812744140625,"
                                               "7.27294921875 -2.230224609375,"
                                               "7.657470703125 -1.25244140625))"),
        }

    def assertMapWidget(self, form_instance):
        """
        Make sure the MapWidget js is passed in the form media and a MapWidget
        is actually created
        """
        self.assertTrue(form_instance.is_valid())
        rendered = form_instance.as_p()
        self.assertIn('new MapWidget(options);', rendered)
        self.assertIn('map_srid: 3857,', rendered)
        self.assertIn('gis/js/OLMapWidget.js', str(form_instance.media))

    def assertTextarea(self, geom, rendered):
        """Makes sure the wkt and a textarea are in the content"""

        self.assertIn('<textarea ', rendered)
        self.assertIn('required', rendered)
        ogr = geom.ogr
        ogr.transform(3857)
        self.assertIn(escape(ogr.json), rendered)

    # map_srid in operlayers.html template must not be localized.
    @override_settings(USE_L10N=True, USE_THOUSAND_SEPARATOR=True)
    def test_pointfield(self):
        class PointForm(forms.Form):
            p = forms.PointField()

        geom = self.geometries['point']
        form = PointForm(data={'p': geom})
        self.assertTextarea(geom, form.as_p())
        self.assertMapWidget(form)
        self.assertFalse(PointForm().is_valid())
        invalid = PointForm(data={'p': 'some invalid geom'})
        self.assertFalse(invalid.is_valid())
        self.assertIn('Invalid geometry value', str(invalid.errors))

        for invalid in [geo for key, geo in self.geometries.items() if key != 'point']:
            self.assertFalse(PointForm(data={'p': invalid.wkt}).is_valid())

    def test_multipointfield(self):
        class PointForm(forms.Form):
            p = forms.MultiPointField()

        geom = self.geometries['multipoint']
        form = PointForm(data={'p': geom})
        self.assertTextarea(geom, form.as_p())
        self.assertMapWidget(form)
        self.assertFalse(PointForm().is_valid())

        for invalid in [geo for key, geo in self.geometries.items() if key != 'multipoint']:
            self.assertFalse(PointForm(data={'p': invalid.wkt}).is_valid())

    def test_linestringfield(self):
        class LineStringForm(forms.Form):
            f = forms.LineStringField()

        geom = self.geometries['linestring']
        form = LineStringForm(data={'f': geom})
        self.assertTextarea(geom, form.as_p())
        self.assertMapWidget(form)
        self.assertFalse(LineStringForm().is_valid())

        for invalid in [geo for key, geo in self.geometries.items() if key != 'linestring']:
            self.assertFalse(LineStringForm(data={'p': invalid.wkt}).is_valid())

    def test_multilinestringfield(self):
        class LineStringForm(forms.Form):
            f = forms.MultiLineStringField()

        geom = self.geometries['multilinestring']
        form = LineStringForm(data={'f': geom})
        self.assertTextarea(geom, form.as_p())
        self.assertMapWidget(form)
        self.assertFalse(LineStringForm().is_valid())

        for invalid in [geo for key, geo in self.geometries.items() if key != 'multilinestring']:
            self.assertFalse(LineStringForm(data={'p': invalid.wkt}).is_valid())

    def test_polygonfield(self):
        class PolygonForm(forms.Form):
            p = forms.PolygonField()

        geom = self.geometries['polygon']
        form = PolygonForm(data={'p': geom})
        self.assertTextarea(geom, form.as_p())
        self.assertMapWidget(form)
        self.assertFalse(PolygonForm().is_valid())

        for invalid in [geo for key, geo in self.geometries.items() if key != 'polygon']:
            self.assertFalse(PolygonForm(data={'p': invalid.wkt}).is_valid())

    def test_multipolygonfield(self):
        class PolygonForm(forms.Form):
            p = forms.MultiPolygonField()

        geom = self.geometries['multipolygon']
        form = PolygonForm(data={'p': geom})
        self.assertTextarea(geom, form.as_p())
        self.assertMapWidget(form)
        self.assertFalse(PolygonForm().is_valid())

        for invalid in [geo for key, geo in self.geometries.items() if key != 'multipolygon']:
            self.assertFalse(PolygonForm(data={'p': invalid.wkt}).is_valid())

    def test_geometrycollectionfield(self):
        class GeometryForm(forms.Form):
            g = forms.GeometryCollectionField()

        geom = self.geometries['geometrycollection']
        form = GeometryForm(data={'g': geom})
        self.assertTextarea(geom, form.as_p())
        self.assertMapWidget(form)
        self.assertFalse(GeometryForm().is_valid())

        for invalid in [geo for key, geo in self.geometries.items() if key != 'geometrycollection']:
            self.assertFalse(GeometryForm(data={'g': invalid.wkt}).is_valid())


@skipUnlessDBFeature("gis_enabled")
class OSMWidgetTest(SimpleTestCase):
    def setUp(self):
        self.geometries = {
            'point': GEOSGeometry("SRID=4326;POINT(9.052734375 42.451171875)"),
        }

    def test_osm_widget(self):
        class PointForm(forms.Form):
            p = forms.PointField(widget=forms.OSMWidget)

        geom = self.geometries['point']
        form = PointForm(data={'p': geom})
        rendered = form.as_p()

        self.assertIn("ol.source.OSM()", rendered)
        self.assertIn("id: 'id_p',", rendered)

    def test_default_lat_lon(self):
        class PointForm(forms.Form):
            p = forms.PointField(
                widget=forms.OSMWidget(attrs={
                    'default_lon': 20, 'default_lat': 30
                }),
            )

        form = PointForm()
        rendered = form.as_p()

        self.assertIn("options['default_lon'] = 20;", rendered)
        self.assertIn("options['default_lat'] = 30;", rendered)
        if forms.OSMWidget.default_lon != 20:
            self.assertNotIn(
                "options['default_lon'] = %d;" % forms.OSMWidget.default_lon,
                rendered)
        if forms.OSMWidget.default_lat != 30:
            self.assertNotIn(
                "options['default_lat'] = %d;" % forms.OSMWidget.default_lat,
                rendered)


@skipUnlessDBFeature("gis_enabled")
class GeometryWidgetTests(SimpleTestCase):

    def test_subwidgets(self):
        widget = forms.BaseGeometryWidget()
        self.assertEqual(
            list(widget.subwidgets('name', 'value')),
            [{
                'is_hidden': False,
                'attrs': {
                    'map_srid': 4326,
                    'map_width': 600,
                    'geom_type': 'GEOMETRY',
                    'map_height': 400,
                    'display_raw': False,
                },
                'name': 'name',
                'template_name': '',
                'value': 'value',
                'required': False,
            }]
        )

    def test_custom_serialization_widget(self):
        class CustomGeometryWidget(forms.BaseGeometryWidget):
            template_name = 'gis/openlayers.html'
            deserialize_called = 0

            def serialize(self, value):
                return value.json if value else ''

            def deserialize(self, value):
                self.deserialize_called += 1
                return GEOSGeometry(value)

        class PointForm(forms.Form):
            p = forms.PointField(widget=CustomGeometryWidget)

        point = GEOSGeometry("SRID=4326;POINT(9.052734375 42.451171875)")
        form = PointForm(data={'p': point})
        self.assertIn(escape(point.json), form.as_p())

        CustomGeometryWidget.called = 0
        widget = form.fields['p'].widget
        # Force deserialize use due to a string value
        self.assertIn(escape(point.json), widget.render('p', point.json))
        self.assertEqual(widget.deserialize_called, 1)

        form = PointForm(data={'p': point.json})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['p'].srid, 4326)
