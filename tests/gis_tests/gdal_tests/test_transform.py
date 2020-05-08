from unittest import skipIf

from django.contrib.gis.gdal import (
    CoordTransform, OGRGeometry, SpatialReference,
    GDAL_VERSION
)
from django.test import SimpleTestCase


class PointTransformTest(SimpleTestCase):

    @skipIf(GDAL_VERSION[0] < 3, 'Tests OSRSetAxisMappingStrategy of GDAL 3')
    def test_point_transform(self):
        "Testing transform for GDAL 3()."
        orig = OGRGeometry('POINT (-104.609 38.255)', 4326)
        trans = OGRGeometry('POINT (992385.4472045 481455.4944650)', 2774)

        # Using an srid, a SpatialReference object, and a CoordTransform object
        # or transformations.
        t1, t2, t3 = orig.clone(), orig.clone(), orig.clone()
        t1.transform(trans.srid, strategy=0)
        t2.transform(SpatialReference('EPSG:2774'), strategy=0)
        source = SpatialReference('WGS84')
        source.set_axis_mapping_strategy(0)
        ct = CoordTransform(source, SpatialReference(2774))
        t3.transform(ct)

        # Testing use of the `clone` keyword.
        k1 = orig.clone()
        k2 = k1.transform(trans.srid, clone=True, strategy=0)
        self.assertEqual(k1, orig)
        self.assertNotEqual(k1, k2)

        prec = 3
        for p in (t1, t2, t3, k2):
            self.assertAlmostEqual(trans.x, p.x, prec)
            self.assertAlmostEqual(trans.y, p.y, prec)
