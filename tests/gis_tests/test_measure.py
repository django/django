"""
Distance and Area objects to allow for sensible and convenient calculation
and conversions. Here are some tests.
"""

import unittest

from django.contrib.gis.measure import (
    A, Area, D, Distance, V, Volume, W, Weight,
)


class DistanceTest(unittest.TestCase):
    "Testing the Distance object"

    def testInit(self):
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

    def testInitInvalid(self):
        "Testing initialization from invalid units"
        with self.assertRaises(AttributeError):
            D(banana=100)

    def testAccess(self):
        "Testing access in different units"
        d = D(m=100)
        self.assertEqual(d.km, 0.1)
        self.assertAlmostEqual(d.ft, 328.084, 3)

    def testAccessInvalid(self):
        "Testing access in invalid units"
        d = D(m=100)
        self.assertFalse(hasattr(d, 'banana'))

    def testAddition(self):
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

    def testMultiplication(self):
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

    def testUnitConversions(self):
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

    def testComparisons(self):
        "Testing comparisons"
        d1 = D(m=100)
        d2 = D(km=1)
        d3 = D(km=0)

        self.assertGreater(d2, d1)
        self.assertEqual(d1, d1)
        self.assertLess(d1, d2)
        self.assertFalse(d3)

    def testUnitsStr(self):
        "Testing conversion to strings"
        d1 = D(m=100)
        d2 = D(km=3.5)

        self.assertEqual(str(d1), '100.0 m')
        self.assertEqual(str(d2), '3.5 km')
        self.assertEqual(repr(d1), 'Distance(m=100.0)')
        self.assertEqual(repr(d2), 'Distance(km=3.5)')

    def testUnitAttName(self):
        "Testing the `unit_attname` class method"
        unit_tuple = [('Yard', 'yd'), ('Nautical Mile', 'nm'), ('German legal metre', 'german_m'),
                      ('Indian yard', 'indian_yd'), ('Chain (Sears)', 'chain_sears'), ('Chain', 'chain')]
        for nm, att in unit_tuple:
            with self.subTest(nm=nm):
                self.assertEqual(att, D.unit_attname(nm))


class AreaTest(unittest.TestCase):
    "Testing the Area object"

    def testInit(self):
        "Testing initialization from valid units"
        a = Area(sq_m=100)
        self.assertEqual(a.sq_m, 100)

        a = A(sq_m=100)
        self.assertEqual(a.sq_m, 100)

        a = A(sq_mi=100)
        self.assertEqual(a.sq_m, 258998811.0336)

    def testInitInvaliA(self):
        "Testing initialization from invalid units"
        with self.assertRaises(AttributeError):
            A(banana=100)

    def testAccess(self):
        "Testing access in different units"
        a = A(sq_m=100)
        self.assertEqual(a.sq_km, 0.0001)
        self.assertAlmostEqual(a.sq_ft, 1076.391, 3)

    def testAccessInvaliA(self):
        "Testing access in invalid units"
        a = A(sq_m=100)
        self.assertFalse(hasattr(a, 'banana'))

    def testAddition(self):
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

    def testMultiplication(self):
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

    def testUnitConversions(self):
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

    def testComparisons(self):
        "Testing comparisons"
        a1 = A(sq_m=100)
        a2 = A(sq_km=1)
        a3 = A(sq_km=0)

        self.assertGreater(a2, a1)
        self.assertEqual(a1, a1)
        self.assertLess(a1, a2)
        self.assertFalse(a3)

    def testUnitsStr(self):
        "Testing conversion to strings"
        a1 = A(sq_m=100)
        a2 = A(sq_km=3.5)

        self.assertEqual(str(a1), '100.0 sq_m')
        self.assertEqual(str(a2), '3.5 sq_km')
        self.assertEqual(repr(a1), 'Area(sq_m=100.0)')
        self.assertEqual(repr(a2), 'Area(sq_km=3.5)')


class WeightTest(unittest.TestCase):
    "Testing the Weight object"

    def testInit(self):
        "Testing initialization from valid units"
        w = Weight(kg=100)
        self.assertEqual(w.kg, 100)

        w1, w2, w3 = W(kg=100), W(kilogram=100), W(kilogramme=100)
        for w in (w1, w2, w3):
            self.assertEqual(w.kg, 100)

        w = W(g=1)
        self.assertEqual(w.kg, 0.001)

        lb1, lb2, = W(lb=100), W(pound=100)
        for w in (lb1, lb2):
            self.assertEqual(w.lb, 100)

        g1, g2, g3 = W(g=1000), W(gram=1000), W(GrAmMe=1000)
        for w in (g1, g2, g3):
            self.assertEqual(w.kg, 1.0)
            self.assertEqual(w.g, 1000.0)

    def testInitInvalid(self):
        "Testing initialization from invalid units"
        with self.assertRaises(AttributeError):
            W(banana=100)

    def testAccess(self):
        "Testing access in different units"
        w1 = W(kg=1)
        self.assertEqual(w1.mg, float(1000000))
        w2 = W(oz=1)
        self.assertAlmostEqual(w2.kg, 35.274, 3)

    def testAccessInvalid(self):
        "Testing access in invalid units"
        w = W(kg=100)
        self.assertFalse(hasattr(w, 'banana'))

    def testAddition(self):
        "Test addition"
        w1 = W(kg=100)
        w2 = W(kg=200)

        w3 = w1 + w2
        self.assertEqual(w3.kg, 300)
        w3 += w1
        self.assertEqual(w3.kg, 400)

        with self.assertRaises(TypeError):
            w1 + 1

        with self.assertRaises(TypeError):
            w1 += 1

    def testSubtraction(self):
        "Test subtraction"
        w1 = W(kg=100)
        w2 = W(kg=200)

        w4 = w1 - w2
        self.assertEqual(w4.kg, -100)
        w4 -= w1
        self.assertEqual(w4.kg, -200)

        with self.assertRaises(TypeError):
            w1 - 1

        with self.assertRaises(TypeError):
            w1 -= 1

    def testMultiplication(self):
        "Test multiplication"
        w1 = W(kg=100)

        w2 = w1 * 2
        self.assertEqual(w2.kg, 200)
        w2 = 2 * w1
        self.assertEqual(w2.kg, 200)
        w2 *= 5
        self.assertEqual(w2.kg, 1000)

        with self.assertRaises(TypeError):
            w1 = w1 * W(kg=10)

        with self.assertRaises(TypeError):
            w1 *= W(kg=1)

    def testDivision(self):
        "Test division"
        w1 = W(kg=100)

        w2 = w1 / 2
        self.assertEqual(w2.kg, 50)
        w2 /= 5
        self.assertEqual(w2.kg, 10)
        w3 = w1 / W(kg=2)
        self.assertEqual(w3, 50)

        with self.assertRaises(TypeError):
            w1 /= W(kg=1)

    def testUnitConversions(self):
        "Testing default units during maths"
        w1 = W(g=100)
        w2 = W(kg=1)

        w3 = w1 + w2
        self.assertEqual(w3._default_unit, 'g')
        w4 = w2 + w1
        self.assertEqual(w4._default_unit, 'kg')
        w5 = w1 * 2
        self.assertEqual(w5._default_unit, 'g')
        w6 = w1 / 2
        self.assertEqual(w6._default_unit, 'g')

    def testComparisons(self):
        "Testing comparisons"
        w1 = W(g=100)
        w2 = W(kg=1)
        w3 = W(kg=0)

        self.assertGreater(w2, w1)
        self.assertEqual(w1, w1)
        self.assertLess(w1, w2)
        self.assertFalse(w3)

    def testUnitsStr(self):
        "Testing conversion to strings"
        w1 = W(g=100)
        w2 = W(kg=3.5)

        self.assertEqual(str(w1), '100.0 g')
        self.assertEqual(str(w2), '3.5 kg')
        self.assertEqual(repr(w1), 'Weight(g=100.0)')
        self.assertEqual(repr(w2), 'Weight(kg=3.5)')


class VolumeTest(unittest.TestCase):
    "Testing the Volume object"

    def testInit(self):
        "Testing initialization from valid units"
        v = Volume(ml=1000)
        self.assertEqual(v.ml, 1000)

        v1, v2, v3 = V(ml=100), V(milliliter=100), V(millilitre=100)
        for v in (v1, v2, v3):
            self.assertEqual(v.ml, 100)

        v = V(ul=1)
        self.assertEqual(v.ml, 0.001)

        pt1, pt2, = V(pt=100), V(pint=100)
        for v in (pt1, pt2):
            self.assertEqual(v.pt, 100)

        f1, f2, f3 = V(fo=1000), V(floz=1000), V(FluiD_OunCe=1000)
        for v in (f1, f2, f3):
            self.assertEqual(round(v.tsp), 4800)
            self.assertEqual(round(v.cup), 100)

    def testInitInvalid(self):
        "Testing initialization from invalid units"
        with self.assertRaises(AttributeError):
            V(banana=100)

    def testAccess(self):
        "Testing access in different units"
        v1 = V(ml=1)
        self.assertEqual(round(v1.nl), 1000000)
        v2 = V(pint=6)
        self.assertAlmostEqual(v2.ml, 3409.566, 5)

    def testAccessInvalid(self):
        "Testing access in invalid units"
        v = V(ml=100)
        self.assertFalse(hasattr(v, 'banana'))

    def testAddition(self):
        "Test addition"
        v1 = V(ml=100)
        v2 = V(ml=200)

        v3 = v1 + v2
        self.assertEqual(round(v3.ml), 300)
        v3 += v1
        self.assertEqual(v3.ml, 400)

        with self.assertRaises(TypeError):
            v1 + 1

        with self.assertRaises(TypeError):
            v1 += 1

    def testSubtraction(self):
        "Test subtraction"
        v1 = V(ml=100)
        v2 = V(ml=200)

        v3 = v1 - v2
        self.assertEqual(v3.ml, -100)
        v3 -= v1
        self.assertEqual(v3.ml, -200)

        with self.assertRaises(TypeError):
            v1 - 1

        with self.assertRaises(TypeError):
            v1 -= 1

    def testMultiplication(self):
        "Test multiplication"
        v1 = V(ml=100)

        v2 = v1 * 2
        self.assertEqual(v2.ml, 200)
        v2 = 2 * v1
        self.assertEqual(v2.ml, 200)
        v2 *= 5
        self.assertEqual(v2.ml, 1000)

        with self.assertRaises(TypeError):
            v1 = v1 * V(ml=10)

        with self.assertRaises(TypeError):
            v1 *= V(ml=1)

    def testDivision(self):
        "Test division"
        v1 = V(ml=100)

        v2 = v1 / 2
        self.assertEqual(v2.ml, 50)
        v2 /= 5
        self.assertEqual(v2.ml, 10)
        v3 = v1 / V(ml=2)
        self.assertEqual(v3, 50)

        with self.assertRaises(TypeError):
            v1 /= V(ml=1)

    def testUnitConversions(self):
        "Testing default units during maths"
        v1 = V(ul=1000)
        v2 = V(ml=1)

        v3 = v1 + v2
        self.assertEqual(v3._default_unit, 'ul')
        w4 = v2 + v1
        self.assertEqual(w4._default_unit, 'ml')
        w5 = v1 * 2
        self.assertEqual(w5._default_unit, 'ul')
        w6 = v1 / 2
        self.assertEqual(w6._default_unit, 'ul')

    def testComparisons(self):
        "Testing comparisons"
        v1 = V(ul=100)
        v2 = V(ml=1)
        v3 = V(ml=0)

        self.assertGreater(v2, v1)
        self.assertEqual(v1, v1)
        self.assertLess(v1, v2)
        self.assertFalse(v3)

    def testUnitsStr(self):
        "Testing conversion to strings"
        v1 = V(ul=100)
        v2 = V(ml=3.5)

        self.assertEqual(str(v1), '100.0 ul')
        self.assertEqual(str(v2), '3.5 ml')
        self.assertEqual(repr(v1), 'Volume(ul=100.0)')
        self.assertEqual(repr(v2), 'Volume(ml=3.5)')


def suite():
    s = unittest.TestSuite()
    s.addTest(unittest.makeSuite(DistanceTest))
    s.addTest(unittest.makeSuite(AreaTest))
    return s


def run(verbosity=2):
    unittest.TextTestRunner(verbosity=verbosity).run(suite())


if __name__ == "__main__":
    run()
