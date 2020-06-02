"""
Distance and Area objects to allow for sensible and convenient calculation
and conversions. Here are some tests.
"""

import unittest

from django.contrib.gis.measure import A, Area, D, Distance


class DistanceTest(unittest.TestCase):
    "Testing the Distance object"

    def test_init(self):
        "Testing initialization from valid units"
        d = Distance(m=100)
        self.assertEqual(d.m, 100)

        d1, d2, d3 = D(m=100), D(meter=100), D(metre=100)
        for d in (d1, d2, d3):
            self.assertEqual(d.m, 100)

        d = D(nm=100)
        self.assertEqual(d.m, 185200)

        y1, y2, y3 = D(yd=100), D(yard=100), D(Yard=100)
        for d in (y1, y2, y3):
            self.assertEqual(d.yd, 100)

        mm1, mm2 = D(millimeter=1000), D(MiLLiMeTeR=1000)
        for d in (mm1, mm2):
            self.assertEqual(d.m, 1.0)
            self.assertEqual(d.mm, 1000.0)

    def test_init_invalid(self):
        "Testing initialization from invalid units"
        with self.assertRaises(AttributeError):
            D(banana=100)

    def test_access(self):
        "Testing access in different units"
        d = D(m=100)
        self.assertEqual(d.km, 0.1)
        self.assertAlmostEqual(d.ft, 328.084, 3)

    def test_access_invalid(self):
        "Testing access in invalid units"
        d = D(m=100)
        self.assertFalse(hasattr(d, 'banana'))

    def test_addition(self):
        "Test addition & subtraction"
        d1 = D(m=100)
        d2 = D(m=200)

        d3 = d1 + d2
        self.assertEqual(d3.m, 300)
        d3 += d1
        self.assertEqual(d3.m, 400)

        d4 = d1 - d2
        self.assertEqual(d4.m, -100)
        d4 -= d1
        self.assertEqual(d4.m, -200)

        with self.assertRaises(TypeError):
            d1 + 1

        with self.assertRaises(TypeError):
            d1 - 1

        with self.assertRaises(TypeError):
            d1 += 1

        with self.assertRaises(TypeError):
            d1 -= 1

    def test_multiplication(self):
        "Test multiplication & division"
        d1 = D(m=100)

        d3 = d1 * 2
        self.assertEqual(d3.m, 200)
        d3 = 2 * d1
        self.assertEqual(d3.m, 200)
        d3 *= 5
        self.assertEqual(d3.m, 1000)

        d4 = d1 / 2
        self.assertEqual(d4.m, 50)
        d4 /= 5
        self.assertEqual(d4.m, 10)
        d5 = d1 / D(m=2)
        self.assertEqual(d5, 50)

        a5 = d1 * D(m=10)
        self.assertIsInstance(a5, Area)
        self.assertEqual(a5.sq_m, 100 * 10)

        with self.assertRaises(TypeError):
            d1 *= D(m=1)

        with self.assertRaises(TypeError):
            d1 /= D(m=1)

    def test_unit_conversions(self):
        "Testing default units during maths"
        d1 = D(m=100)
        d2 = D(km=1)

        d3 = d1 + d2
        self.assertEqual(d3._default_unit, 'm')
        d4 = d2 + d1
        self.assertEqual(d4._default_unit, 'km')
        d5 = d1 * 2
        self.assertEqual(d5._default_unit, 'm')
        d6 = d1 / 2
        self.assertEqual(d6._default_unit, 'm')

    def test_comparisons(self):
        "Testing comparisons"
        d1 = D(m=100)
        d2 = D(km=1)
        d3 = D(km=0)

        self.assertGreater(d2, d1)
        self.assertEqual(d1, d1)
        self.assertLess(d1, d2)
        self.assertFalse(d3)

    def test_units_str(self):
        "Testing conversion to strings"
        d1 = D(m=100)
        d2 = D(km=3.5)

        self.assertEqual(str(d1), '100.0 m')
        self.assertEqual(str(d2), '3.5 km')
        self.assertEqual(repr(d1), 'Distance(m=100.0)')
        self.assertEqual(repr(d2), 'Distance(km=3.5)')

    def test_furlong(self):
        d = D(m=201.168)
        self.assertEqual(d.furlong, 1)

    def test_unit_att_name(self):
        "Testing the `unit_attname` class method"
        unit_tuple = [('Yard', 'yd'), ('Nautical Mile', 'nm'), ('German legal metre', 'german_m'),
                      ('Indian yard', 'indian_yd'), ('Chain (Sears)', 'chain_sears'), ('Chain', 'chain'),
                      ('Furrow Long', 'furlong')]
        for nm, att in unit_tuple:
            with self.subTest(nm=nm):
                self.assertEqual(att, D.unit_attname(nm))


class AreaTest(unittest.TestCase):
    "Testing the Area object"

    def test_init(self):
        "Testing initialization from valid units"
        a = Area(sq_m=100)
        self.assertEqual(a.sq_m, 100)

        a = A(sq_m=100)
        self.assertEqual(a.sq_m, 100)

        a = A(sq_mi=100)
        self.assertEqual(a.sq_m, 258998811.0336)

    def test_init_invalid_a(self):
        "Testing initialization from invalid units"
        with self.assertRaises(AttributeError):
            A(banana=100)

    def test_access(self):
        "Testing access in different units"
        a = A(sq_m=100)
        self.assertEqual(a.sq_km, 0.0001)
        self.assertAlmostEqual(a.sq_ft, 1076.391, 3)

    def test_access_invalid_a(self):
        "Testing access in invalid units"
        a = A(sq_m=100)
        self.assertFalse(hasattr(a, 'banana'))

    def test_addition(self):
        "Test addition & subtraction"
        a1 = A(sq_m=100)
        a2 = A(sq_m=200)

        a3 = a1 + a2
        self.assertEqual(a3.sq_m, 300)
        a3 += a1
        self.assertEqual(a3.sq_m, 400)

        a4 = a1 - a2
        self.assertEqual(a4.sq_m, -100)
        a4 -= a1
        self.assertEqual(a4.sq_m, -200)

        with self.assertRaises(TypeError):
            a1 + 1

        with self.assertRaises(TypeError):
            a1 - 1

        with self.assertRaises(TypeError):
            a1 += 1

        with self.assertRaises(TypeError):
            a1 -= 1

    def test_multiplication(self):
        "Test multiplication & division"
        a1 = A(sq_m=100)

        a3 = a1 * 2
        self.assertEqual(a3.sq_m, 200)
        a3 = 2 * a1
        self.assertEqual(a3.sq_m, 200)
        a3 *= 5
        self.assertEqual(a3.sq_m, 1000)

        a4 = a1 / 2
        self.assertEqual(a4.sq_m, 50)
        a4 /= 5
        self.assertEqual(a4.sq_m, 10)

        with self.assertRaises(TypeError):
            a1 * A(sq_m=1)

        with self.assertRaises(TypeError):
            a1 *= A(sq_m=1)

        with self.assertRaises(TypeError):
            a1 / A(sq_m=1)

        with self.assertRaises(TypeError):
            a1 /= A(sq_m=1)

    def test_unit_conversions(self):
        "Testing default units during maths"
        a1 = A(sq_m=100)
        a2 = A(sq_km=1)

        a3 = a1 + a2
        self.assertEqual(a3._default_unit, 'sq_m')
        a4 = a2 + a1
        self.assertEqual(a4._default_unit, 'sq_km')
        a5 = a1 * 2
        self.assertEqual(a5._default_unit, 'sq_m')
        a6 = a1 / 2
        self.assertEqual(a6._default_unit, 'sq_m')

    def test_comparisons(self):
        "Testing comparisons"
        a1 = A(sq_m=100)
        a2 = A(sq_km=1)
        a3 = A(sq_km=0)

        self.assertGreater(a2, a1)
        self.assertEqual(a1, a1)
        self.assertLess(a1, a2)
        self.assertFalse(a3)

    def test_units_str(self):
        "Testing conversion to strings"
        a1 = A(sq_m=100)
        a2 = A(sq_km=3.5)

        self.assertEqual(str(a1), '100.0 sq_m')
        self.assertEqual(str(a2), '3.5 sq_km')
        self.assertEqual(repr(a1), 'Area(sq_m=100.0)')
        self.assertEqual(repr(a2), 'Area(sq_km=3.5)')


def suite():
    s = unittest.TestSuite()
    s.addTest(unittest.makeSuite(DistanceTest))
    s.addTest(unittest.makeSuite(AreaTest))
    return s


def run(verbosity=2):
    unittest.TextTestRunner(verbosity=verbosity).run(suite())


if __name__ == "__main__":
    run()
