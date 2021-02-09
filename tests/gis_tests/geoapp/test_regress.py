from datetime import datetime

from django.contrib.gis.db.models import Extent
from django.contrib.gis.shortcuts import render_to_kmz
from django.db.models import Count, Min
from django.test import TestCase, skipUnlessDBFeature

from .models import City, PennsylvaniaCity, State, Truth


class GeoRegressionTests(TestCase):
    fixtures = ['initial']

    def test_update(self):
        "Testing QuerySet.update() (#10411)."
        pueblo = City.objects.get(name='Pueblo')
        bak = pueblo.point.clone()
        pueblo.point.y += 0.005
        pueblo.point.x += 0.005

        City.objects.filter(name='Pueblo').update(point=pueblo.point)
        pueblo.refresh_from_db()
        self.assertAlmostEqual(bak.y + 0.005, pueblo.point.y, 6)
        self.assertAlmostEqual(bak.x + 0.005, pueblo.point.x, 6)
        City.objects.filter(name='Pueblo').update(point=bak)
        pueblo.refresh_from_db()
        self.assertAlmostEqual(bak.y, pueblo.point.y, 6)
        self.assertAlmostEqual(bak.x, pueblo.point.x, 6)

    def test_kmz(self):
        "Testing `render_to_kmz` with non-ASCII data. See #11624."
        name = "Åland Islands"
        places = [{
            'name': name,
            'description': name,
            'kml': '<Point><coordinates>5.0,23.0</coordinates></Point>'
        }]
        render_to_kmz('gis/kml/placemarks.kml', {'places': places})

    @skipUnlessDBFeature("supports_extent_aggr")
    def test_extent(self):
        "Testing `extent` on a table with a single point. See #11827."
        pnt = City.objects.get(name='Pueblo').point
        ref_ext = (pnt.x, pnt.y, pnt.x, pnt.y)
        extent = City.objects.filter(name='Pueblo').aggregate(Extent('point'))['point__extent']
        for ref_val, val in zip(ref_ext, extent):
            self.assertAlmostEqual(ref_val, val, 4)

    def test_unicode_date(self):
        "Testing dates are converted properly, even on SpatiaLite. See #16408."
        founded = datetime(1857, 5, 23)
        PennsylvaniaCity.objects.create(name='Mansfield', county='Tioga', point='POINT(-77.071445 41.823881)',
                                        founded=founded)
        self.assertEqual(founded, PennsylvaniaCity.objects.datetimes('founded', 'day')[0])
        self.assertEqual(founded, PennsylvaniaCity.objects.aggregate(Min('founded'))['founded__min'])

    def test_empty_count(self):
        "Testing that PostGISAdapter.__eq__ does check empty strings. See #13670."
        # contrived example, but need a geo lookup paired with an id__in lookup
        pueblo = City.objects.get(name='Pueblo')
        state = State.objects.filter(poly__contains=pueblo.point)
        cities_within_state = City.objects.filter(id__in=state)

        # .count() should not throw TypeError in __eq__
        self.assertEqual(cities_within_state.count(), 1)

    @skipUnlessDBFeature('allows_group_by_lob')
    def test_defer_or_only_with_annotate(self):
        "Regression for #16409. Make sure defer() and only() work with annotate()"
        self.assertIsInstance(list(City.objects.annotate(Count('point')).defer('name')), list)
        self.assertIsInstance(list(City.objects.annotate(Count('point')).only('name')), list)

    def test_boolean_conversion(self):
        "Testing Boolean value conversion with the spatial backend, see #15169."
        t1 = Truth.objects.create(val=True)
        t2 = Truth.objects.create(val=False)

        val1 = Truth.objects.get(pk=t1.pk).val
        val2 = Truth.objects.get(pk=t2.pk).val
        # verify types -- shouldn't be 0/1
        self.assertIsInstance(val1, bool)
        self.assertIsInstance(val2, bool)
        # verify values
        self.assertIs(val1, True)
        self.assertIs(val2, False)
