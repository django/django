from django.forms import ValidationError
from django.contrib.gis.gdal import HAS_GDAL
from django.contrib.gis.tests.utils import HAS_SPATIALREFSYS
from django.utils import unittest


if HAS_SPATIALREFSYS:
    from django.contrib.gis import forms
    from django.contrib.gis.geos import GEOSGeometry

@unittest.skipUnless(HAS_GDAL and HAS_SPATIALREFSYS, "GeometryFieldTest needs gdal support and a spatial database")
class GeometryFieldTest(unittest.TestCase):

    def test00_init(self):
        "Testing GeometryField initialization with defaults."
        fld = forms.GeometryField()
        for bad_default in ('blah', 3, 'FoO', None, 0):
            self.assertRaises(ValidationError, fld.clean, bad_default)

    def test01_srid(self):
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

    def test02_null(self):
        "Testing GeometryField's handling of null (None) geometries."
        # Form fields, by default, are required (`required=True`)
        fld = forms.GeometryField()
        self.assertRaises(forms.ValidationError, fld.clean, None)

        # Still not allowed if `null=False`.
        fld = forms.GeometryField(required=False, null=False)
        self.assertRaises(forms.ValidationError, fld.clean, None)

        # This will clean None as a geometry (See #10660).
        fld = forms.GeometryField(required=False)
        self.assertEqual(None, fld.clean(None))

    def test03_geom_type(self):
        "Testing GeometryField's handling of different geometry types."
        # By default, all geometry types are allowed.
        fld = forms.GeometryField()
        for wkt in ('POINT(5 23)', 'MULTIPOLYGON(((0 0, 0 1, 1 1, 1 0, 0 0)))', 'LINESTRING(0 0, 1 1)'):
            self.assertEqual(GEOSGeometry(wkt), fld.clean(wkt))

        pnt_fld = forms.GeometryField(geom_type='POINT')
        self.assertEqual(GEOSGeometry('POINT(5 23)'), pnt_fld.clean('POINT(5 23)'))
        # a WKT for any other geom_type will be properly transformed by `to_python`
        self.assertEqual(GEOSGeometry('LINESTRING(0 0, 1 1)'), pnt_fld.to_python('LINESTRING(0 0, 1 1)'))
        # but rejected by `clean`
        self.assertRaises(forms.ValidationError, pnt_fld.clean, 'LINESTRING(0 0, 1 1)')

    def test04_to_python(self):
        """
        Testing to_python returns a correct GEOSGeometry object or
        a ValidationError
        """
        fld = forms.GeometryField()
        # to_python returns the same GEOSGeometry for a WKT
        for wkt in ('POINT(5 23)', 'MULTIPOLYGON(((0 0, 0 1, 1 1, 1 0, 0 0)))', 'LINESTRING(0 0, 1 1)'):
            self.assertEqual(GEOSGeometry(wkt), fld.to_python(wkt))
        # but raises a ValidationError for any other string
        for wkt in ('POINT(5)', 'MULTI   POLYGON(((0 0, 0 1, 1 1, 1 0, 0 0)))', 'BLAH(0 0, 1 1)'):
            self.assertRaises(forms.ValidationError, fld.to_python, wkt)


def suite():
    s = unittest.TestSuite()
    s.addTest(unittest.makeSuite(GeometryFieldTest))
    return s

def run(verbosity=2):
    unittest.TextTestRunner(verbosity=verbosity).run(suite())

if __name__=="__main__":
    run()
