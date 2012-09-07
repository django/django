import warnings

import django.contrib.gis.geos
import django.contrib.gis.geos.base

from django.utils import unittest


class NumpyTestCase():
    """LineString returns lists instead of numpy.ndarrays without numpy

    In the absence of numpy .array will issue a warning; this behavior
    is incorrect because ndarray and list have substantially different
    semantics when it comes to even basic operations like comparison.
    If the user wants a list they can obtain one by list(LineString);
    silently returning a list instead of an ndarray when .array is
    called is most likely to occur when an application is developed in
    an environment with numpy installed and deployed on an environment
    without.  This user should be warned when this happens.

    django.contrib.gis.geos.base will always have a variable numpy;
    when numpy is installed this contains a reference to the numpy
    module.  When numpy is not installed this will evaluate to false.

    Users of this TestCase should assign to cls.NUMPY whichever object
    should replace the django.contrib.gis.geos.base for the test and
    cls.EXPECTED_CLASS whichever type numpy.ndarray is expected to
    create.

    See http://code.djangoproject.com/ticket/18887 for more information.
    """
    def setUp(self):
        import django.contrib.gis.geos.base
        django.contrib.gis.geos.base.numpy = self.NUMPY
        reload(django.contrib.gis.geos.linestring)
        self.linestring = django.contrib.gis.geos.linestring.LineString(
            (0, 0), (3, 3))

    def tearDown(self):
        reload(django.contrib.gis.geos.base)
        reload(django.contrib.gis.geos.linestring)

    def test_numpy_array_return_type(self):
        self.assertTrue(isinstance(self.linestring.array, self.EXPECTED_CLASS))


class WithNumpyTest(NumpyTestCase, unittest.TestCase):
    """Tests LineString in the presense of numpy.

    If numpy is not installed this test will monkey patch a dummy
    numpy with enough implementation to get these tests to pass.
    """
    try:
        import numpy
        NUMPY = numpy
    except ImportError:
        class NUMPY():
            class ndarray():
                pass

            class array(ndarray):
                def __init__(self, *args, **kwargs):
                    pass

    EXPECTED_CLASS = NUMPY.ndarray


class WithoutNumpyTest(NumpyTestCase, unittest.TestCase):
    '"Uninstalls" numpy to validate the behavior of LineString in its absence.'
    EXPECTED_CLASS = list
    NUMPY = None

    def test_numpy_is_false(self):
        self.assertFalse(django.contrib.gis.geos.base.numpy)

    def setUp(self):
        reload(warnings)
        NumpyTestCase.setUp(self)
        unittest.TestCase.setUp(self)

    def tearDown(self):
        reload(warnings)
        NumpyTestCase.tearDown(self)
        unittest.TestCase.tearDown(self)

    def test_issues_warning(self):
        """Calls to LineString.array issue a warning.

        In the absence of numpy the use of LineString.array will issue
        a warning and erroneously return a list.
        """
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            self.linestring.array
            self.assertEquals(len(w), 1)
            self.assertEquals(w[-1].category, DeprecationWarning)
            self.assertTrue('numpy is not installed' in str(w[-1].message))

    def test_warnings_work(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            warnings.warn('hello', DeprecationWarning)
            self.assertEquals(len(w), 1)


def suite():
    s = unittest.TestSuite()
    s.addTest(unittest.makeSuite(WithNumpyTest))
    s.addTest(unittest.makeSuite(WithoutNumpyTest))
    return s


def run(verbosity=2):
    unittest.TextTestRunner(verbosity=verbosity).run(suite())
