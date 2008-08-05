import unittest
from django.contrib.gis.gdal import Envelope, OGRException

class EnvelopeTest(unittest.TestCase):

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
        self.assertRaises(TypeError, Envelope, u'foo')

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

def suite():
    s = unittest.TestSuite()
    s.addTest(unittest.makeSuite(EnvelopeTest))
    return s

def run(verbosity=2):
    unittest.TextTestRunner(verbosity=verbosity).run(suite())
