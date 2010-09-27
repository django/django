from django.test import TestCase

from django.utils.tzinfo import FixedOffset

class TzinfoTests(TestCase):

    def test_fixedoffset(self):
        self.assertEquals(repr(FixedOffset(0)), '+0000')
        self.assertEquals(repr(FixedOffset(60)), '+0100')
        self.assertEquals(repr(FixedOffset(-60)), '-0100')
        self.assertEquals(repr(FixedOffset(280)), '+0440')
        self.assertEquals(repr(FixedOffset(-280)), '-0440')
        self.assertEquals(repr(FixedOffset(-78.4)), '-0118')
        self.assertEquals(repr(FixedOffset(78.4)), '+0118')
        self.assertEquals(repr(FixedOffset(-5.5*60)), '-0530')
        self.assertEquals(repr(FixedOffset(5.5*60)), '+0530')
        self.assertEquals(repr(FixedOffset(-.5*60)), '-0030')
        self.assertEquals(repr(FixedOffset(.5*60)), '+0030')
