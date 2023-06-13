from django.contrib.gis.geos import LineString
from django.test import SimpleTestCase


class GEOSCoordSeqTest(SimpleTestCase):
    def test_getitem(self):
        coord_seq = LineString([(x, x) for x in range(2)]).coord_seq
        for i in (0, 1):
            with self.subTest(i):
                self.assertEqual(coord_seq[i], (i, i))
        for i in (-3, 10):
            msg = "invalid GEOS Geometry index: %s" % i
            with self.subTest(i):
                with self.assertRaisesMessage(IndexError, msg):
                    coord_seq[i]
