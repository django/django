import os, unittest
from django.contrib.gis.db.backend import SpatialBackend
from django.contrib.gis.tests.utils import no_mysql, no_oracle, no_postgis, no_spatialite
from django.contrib.gis.shortcuts import render_to_kmz
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

    def test02_kmz(self):
        "Testing `render_to_kmz` with non-ASCII data, see #11624."
        name = '\xc3\x85land Islands'.decode('iso-8859-1')
        places = [{'name' : name,
                  'description' : name,
                  'kml' : '<Point><coordinates>5.0,23.0</coordinates></Point>'
                  }]
        kmz = render_to_kmz('gis/kml/placemarks.kml', {'places' : places})

    @no_spatialite
    def test03_extent(self):
        "Testing `extent` on a table with a single point, see #11827."
        pnt = City.objects.get(name='Pueblo').point
        ref_ext = (pnt.x, pnt.y, pnt.x, pnt.y)
        self.assertEqual(ref_ext, City.objects.filter(name='Pueblo').extent())
