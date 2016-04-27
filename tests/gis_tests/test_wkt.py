from unittest import skipUnless

from django.contrib.gis.geos import HAS_GEOS, GEOSGeometry
from django.contrib.gis.utils.wkt import precision_wkt
from django.test import SimpleTestCase, ignore_warnings
from django.utils.deprecation import RemovedInDjango20Warning


@skipUnless(HAS_GEOS, "Requires GEOS support")
class WktTest(SimpleTestCase):

    @ignore_warnings(category=RemovedInDjango20Warning)
    def test_wkt(self):
        point = GEOSGeometry('POINT (951640.547328465 4219369.26171664)')
        self.assertEqual('POINT(951640.547328 4219369.261717)', precision_wkt(point, 6))
        self.assertEqual('POINT(951640.5473 4219369.2617)', precision_wkt(point, '%.4f'))

        multipoint = GEOSGeometry(
            "SRID=4326;MULTIPOINT((13.18634033203125 14.504356384277344),"
            "(13.207969665527 14.490966796875),(13.177070617675 14.454917907714))"
        )
        self.assertEqual(
            "MULTIPOINT(13.186340332031 14.504356384277,"
            "13.207969665527 14.490966796875,13.177070617675 14.454917907714)",
            precision_wkt(multipoint, 12)
        )
