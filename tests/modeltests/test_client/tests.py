# Validate that you can override the default test suite

from django.utils import unittest


def suite():
    """
    Define a suite that deliberately ignores a test defined in
    this module.
    """

    testSuite = unittest.TestSuite()
    testSuite.addTest(SampleTests('testGoodStuff'))
    return testSuite

class SampleTests(unittest.TestCase):
    def testGoodStuff(self):
        pass

    def testBadStuff(self):
        self.fail("This test shouldn't run")
