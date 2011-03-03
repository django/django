import unittest

from django.utils.tzinfo import FixedOffset

class TzinfoTests(unittest.TestCase):

    def test_fixedoffset(self):
        self.assertEqual(repr(FixedOffset(0)), '+0000')
        self.assertEqual(repr(FixedOffset(60)), '+0100')
        self.assertEqual(repr(FixedOffset(-60)), '-0100')
        self.assertEqual(repr(FixedOffset(280)), '+0440')
        self.assertEqual(repr(FixedOffset(-280)), '-0440')
        self.assertEqual(repr(FixedOffset(-78.4)), '-0118')
        self.assertEqual(repr(FixedOffset(78.4)), '+0118')
        self.assertEqual(repr(FixedOffset(-5.5*60)), '-0530')
        self.assertEqual(repr(FixedOffset(5.5*60)), '+0530')
        self.assertEqual(repr(FixedOffset(-.5*60)), '-0030')
        self.assertEqual(repr(FixedOffset(.5*60)), '+0030')
