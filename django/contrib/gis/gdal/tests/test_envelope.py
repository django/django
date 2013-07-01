import unittest
from unittest import skipUnless

from django.contrib.gis.gdal import HAS_GDAL

if HAS_GDAL:
    from django.contrib.gis.gdal import Envelope, OGRException


class TestPoint(object):
    def __init__(self, x, y):
        self.x = x
        self.y = y


@skipUnless(HAS_GDAL, "GDAL is required")
class EnvelopeTest(unittest.TestCase):

    def setUp(self):
        self.e = Envelope(0, 0, 5, 5)

    def test01_init(self):
        "Testing Envelope initilization."
        e1 = Envelope((0, 0, 5, 5))
        e2 = Envelope(0, 0, 5, 5)
        e3 = Envelope(0, '0', '5', 5) # Thanks to ww for this
        e4 = Envelope(e1._envelope)
        self.assertRaises(OGRException, Envelope, (5, 5, 0, 0))
        self.assertRaises(OGRException, Envelope, 5, 5, 0, 0)
        self.assertRaises(OGRException, Envelope, (0, 0, 5, 5, 3))
        self.assertRaises(OGRException, Envelope, ())
        self.assertRaises(ValueError, Envelope, 0, 'a', 5, 5)
        self.assertRaises(TypeError, Envelope, 'foo')
        self.assertRaises(OGRException, Envelope, (1, 1, 0, 0))
        try:
            Envelope(0, 0, 0, 0)
        except OGRException:
            self.fail("shouldn't raise an exception for min_x == max_x or min_y == max_y")

    def test02_properties(self):
        "Testing Envelope properties."
        e = Envelope(0, 0, 2, 3)
        self.assertEqual(0, e.min_x)
        self.assertEqual(0, e.min_y)
        self.assertEqual(2, e.max_x)
        self.assertEqual(3, e.max_y)
        self.assertEqual((0, 0), e.ll)
        self.assertEqual((2, 3), e.ur)
        self.assertEqual((0, 0, 2, 3), e.tuple)
        self.assertEqual('POLYGON((0.0 0.0,0.0 3.0,2.0 3.0,2.0 0.0,0.0 0.0))', e.wkt)
        self.assertEqual('(0.0, 0.0, 2.0, 3.0)', str(e))

    def test03_equivalence(self):
        "Testing Envelope equivalence."
        e1 = Envelope(0.523, 0.217, 253.23, 523.69)
        e2 = Envelope((0.523, 0.217, 253.23, 523.69))
        self.assertEqual(e1, e2)
        self.assertEqual((0.523, 0.217, 253.23, 523.69), e1)

    def test04_expand_to_include_pt_2_params(self):
        "Testing Envelope expand_to_include -- point as two parameters."
        self.e.expand_to_include(2, 6)
        self.assertEqual((0, 0, 5, 6), self.e)
        self.e.expand_to_include(-1, -1)
        self.assertEqual((-1, -1, 5, 6), self.e)

    def test05_expand_to_include_pt_2_tuple(self):
        "Testing Envelope expand_to_include -- point as a single 2-tuple parameter."
        self.e.expand_to_include((10, 10))
        self.assertEqual((0, 0, 10, 10), self.e)
        self.e.expand_to_include((-10, -10))
        self.assertEqual((-10, -10, 10, 10), self.e)

    def test06_expand_to_include_extent_4_params(self):
        "Testing Envelope expand_to_include -- extent as 4 parameters."
        self.e.expand_to_include(-1, 1, 3, 7)
        self.assertEqual((-1, 0, 5, 7), self.e)

    def test06_expand_to_include_extent_4_tuple(self):
        "Testing Envelope expand_to_include -- extent as a single 4-tuple parameter."
        self.e.expand_to_include((-1, 1, 3, 7))
        self.assertEqual((-1, 0, 5, 7), self.e)

    def test07_expand_to_include_envelope(self):
        "Testing Envelope expand_to_include with Envelope as parameter."
        self.e.expand_to_include(Envelope(-1, 1, 3, 7))
        self.assertEqual((-1, 0, 5, 7), self.e)

    def test08_expand_to_include_point(self):
        "Testing Envelope expand_to_include with Point as parameter."
        self.e.expand_to_include(TestPoint(-1, 1))
        self.assertEqual((-1, 0, 5, 5), self.e)
        self.e.expand_to_include(TestPoint(10, 10))
        self.assertEqual((-1, 0, 10, 10), self.e)
