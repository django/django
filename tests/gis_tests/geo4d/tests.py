import time
from unittest import skipIf

from django.contrib.gis.geos import GEOSGeometry, LineString, Point
from django.contrib.gis.geos.libgeos import geos_version_tuple
from django.test import TestCase, skipUnlessDBFeature

from ..geo3d.models import Interstate3D, InterstateProj3D
from ..geo3d.tests import city_data, interstate_data
from .models import City4D, Interstate4D, InterstateProj4D

epoch_time = int(time.time())


class GeoLoadingHelper:
    def _load_interstate_data(self):
        # Interstate (3D / 4D and Geographic/Projected variants)
        for name, line, _ in interstate_data:
            line_3d = GEOSGeometry(line, srid=4269)
            line_4d = LineString(
                [(*coord, epoch_time) for coord in line_3d.coords], srid=4269
            )

            # Creating a geographic and projected version of the
            # interstate in both 3D and 4D.
            Interstate3D.objects.create(name=name, line=line_3d)
            InterstateProj3D.objects.create(name=name, line=line_3d)
            Interstate4D.objects.create(name=name, line=line_4d)
            InterstateProj4D.objects.create(name=name, line=line_4d)

    def _load_city_data(self):
        for name, pnt_data in city_data:
            City4D.objects.create(
                name=name,
                point=Point(*pnt_data, epoch_time, srid=4326),
                pointg=Point(*pnt_data, epoch_time, srid=4326),
            )


@skipUnlessDBFeature("supports_4d_storage")
@skipIf(geos_version_tuple() < (3, 12), "GEOS >= 3.12.0 is required")
class Geo4DTest(GeoLoadingHelper, TestCase):
    """
    Only a subset of the PostGIS routines are 4D-enabled, and this TestCase
    tries to test the features that can handle 4D and that are also
    available within GeoDjango.
    """

    def test_4d_linestring(self):
        """
        Make sure data is 4D linestirng and has expected M values -- shouldn't change
        because of coordinate system.
        """
        self._load_interstate_data()
        for name, _, z in interstate_data:
            interstate = Interstate4D.objects.get(name=name)
            interstate_proj = InterstateProj4D.objects.get(name=name)
            for i in [interstate, interstate_proj]:
                m = tuple(i.line.m)
                self.assertTrue(i.line.hasm)
                self.assertTrue(all(x == epoch_time for x in m))
                self.assertEqual(len(z), len(m))

    def test_4d_point(self):
        """
        Make sure data is 4D point and has expected M values -- shouldn't change
        because of coordinate system.
        """
        self._load_city_data()
        for name, _ in city_data:
            city = City4D.objects.get(name=name)
            # Testing both geometry and geography fields
            self.assertTrue(city.point.hasm)
            self.assertTrue(city.pointg.hasm)
            self.assertEqual(city.point.m, epoch_time)
            self.assertEqual(city.pointg.m, epoch_time)
