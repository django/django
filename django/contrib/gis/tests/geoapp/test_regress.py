import os, unittest
from django.contrib.gis.db.backend import SpatialBackend
from django.contrib.gis.tests.utils import no_mysql, no_oracle, no_postgis
from models import City

class GeoRegressionTests(unittest.TestCase):

    def test01_update(self):
        "Testing GeoQuerySet.update(), see #10411."
        pnt = City.objects.get(name='Pueblo').point
        bak = pnt.clone()
        pnt.y += 0.005
        pnt.x += 0.005

        City.objects.filter(name='Pueblo').update(point=pnt)
        self.assertEqual(pnt, City.objects.get(name='Pueblo').point)
        City.objects.filter(name='Pueblo').update(point=bak)
        self.assertEqual(bak, City.objects.get(name='Pueblo').point)
