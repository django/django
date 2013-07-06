"""
This module is pending deprecation as of Django 1.6 and will be removed in
version 1.8.

"""
import json
import re
import unittest as real_unittest
import warnings

from django.db.models import get_app, get_apps
from django.test import _doctest as doctest
from django.test import runner
from django.test.utils import compare_xml, strip_quotes
# django.utils.unittest is deprecated, but so is django.test.simple,
# and the latter will be removed before the former.
from django.utils import unittest
from django.utils.importlib import import_module
from django.utils.module_loading import module_has_submodule

__all__ = ('DjangoTestSuiteRunner',)

warnings.warn(
    "The django.test.simple module and DjangoTestSuiteRunner are deprecated; "
    "use django.test.runner.DiscoverRunner instead.",
    DeprecationWarning)

# The module name for tests outside models.py
TEST_MODULE = 'tests'


normalize_long_ints = lambda s: re.sub(r'(?<![\w])(\d+)L(?![\w])', '\\1', s)
normalize_decimals = lambda s: re.sub(r"Decimal\('(\d+(\.\d*)?)'\)",
                                lambda m: "Decimal(\"%s\")" % m.groups()[0], s)


class OutputChecker(doctest.OutputChecker):
    def check_output(self, want, got, optionflags):
        """
        The entry method for doctest output checking. Defers to a sequence of
        child checkers
        """
        checks = (self.check_output_default,
                  self.check_output_numeric,
                  self.check_output_xml,
                  self.check_output_json)
        for check in checks:
            if check(want, got, optionflags):
                return True
        return False

    def check_output_default(self, want, got, optionflags):
        """
        The default comparator provided by doctest - not perfect, but good for
        most purposes
        """
        return doctest.OutputChecker.check_output(self, want, got, optionflags)

    def check_output_numeric(self, want, got, optionflags):
        """Doctest does an exact string comparison of output, which means that
        some numerically equivalent values aren't equal. This check normalizes
         * long integers (22L) so that they equal normal integers. (22)
         * Decimals so that they are comparable, regardless of the change
           made to __repr__ in Python 2.6.
        """
        return doctest.OutputChecker.check_output(self,
            normalize_decimals(normalize_long_ints(want)),
            normalize_decimals(normalize_long_ints(got)),
            optionflags)

    def check_output_xml(self, want, got, optionsflags):
        try:
            return compare_xml(want, got)
        except Exception:
            return False

    def check_output_json(self, want, got, optionsflags):
        """
        Tries to compare want and got as if they were JSON-encoded data
        """
        want, got = strip_quotes(want, got)
        try:
            want_json = json.loads(want)
            got_json = json.loads(got)
        except Exception:
            return False
        return want_json == got_json


class DocTestRunner(doctest.DocTestRunner):
    def __init__(self, *args, **kwargs):
        doctest.DocTestRunner.__init__(self, *args, **kwargs)
        self.optionflags = doctest.ELLIPSIS


doctestOutputChecker = OutputChecker()


def get_tests(app_module):
    parts = app_module.__name__.split('.')
    prefix, last = parts[:-1], parts[-1]
    try:
        test_module = import_module('.'.join(prefix + [TEST_MODULE]))
    except ImportError:
        # Couldn't import tests.py. Was it due to a missing file, or
        # due to an import error in a tests.py that actually exists?
        # app_module either points to a models.py file, or models/__init__.py
        # Tests are therefore either in same directory, or one level up
        if last == 'models':
            app_root = import_module('.'.join(prefix))
        else:
            app_root = app_module

        if not module_has_submodule(app_root, TEST_MODULE):
            test_module = None
        else:
            # The module exists, so there must be an import error in the test
            # module itself.
            raise
    return test_module


def make_doctest(module):
    return doctest.DocTestSuite(module,
       checker=doctestOutputChecker,
       runner=DocTestRunner,
    )


def build_suite(app_module):
    """
    Create a complete Django test suite for the provided application module.
    """
    suite = unittest.TestSuite()

    # Load unit and doctests in the models.py module. If module has
    # a suite() method, use it. Otherwise build the test suite ourselves.
    if hasattr(app_module, 'suite'):
        suite.addTest(app_module.suite())
    else:
        suite.addTest(unittest.defaultTestLoader.loadTestsFromModule(
            app_module))
        try:
            suite.addTest(make_doctest(app_module))
        except ValueError:
            # No doc tests in models.py
            pass

    # Check to see if a separate 'tests' module exists parallel to the
    # models module
    test_module = get_tests(app_module)
    if test_module:
        # Load unit and doctests in the tests.py module. If module has
        # a suite() method, use it. Otherwise build the test suite ourselves.
        if hasattr(test_module, 'suite'):
            suite.addTest(test_module.suite())
        else:
            suite.addTest(unittest.defaultTestLoader.loadTestsFromModule(
                test_module))
            try:
                suite.addTest(make_doctest(test_module))
            except ValueError:
                # No doc tests in tests.py
                pass
    return suite


def build_test(label):
    """
    Construct a test case with the specified label. Label should be of the
    form model.TestClass or model.TestClass.test_method. Returns an
    instantiated test or test suite corresponding to the label provided.

    """
    parts = label.split('.')
    if len(parts) < 2 or len(parts) > 3:
        raise ValueError("Test label '%s' should be of the form app.TestCase "
                         "or app.TestCase.test_method" % label)

    #
    # First, look for TestCase instances with a name that matches
    #
    app_module = get_app(parts[0])
    test_module = get_tests(app_module)
    TestClass = getattr(app_module, parts[1], None)

    # Couldn't find the test class in models.py; look in tests.py
    if TestClass is None:
        if test_module:
            TestClass = getattr(test_module, parts[1], None)

    try:
        if issubclass(TestClass, (unittest.TestCase, real_unittest.TestCase)):
            if len(parts) == 2: # label is app.TestClass
                try:
                    return unittest.TestLoader().loadTestsFromTestCase(
                        TestClass)
                except TypeError:
                    raise ValueError(
                        "Test label '%s' does not refer to a test class"
                        % label)
            else: # label is app.TestClass.test_method
                return TestClass(parts[2])
    except TypeError:
        # TestClass isn't a TestClass - it must be a method or normal class
        pass

    #
    # If there isn't a TestCase, look for a doctest that matches
    #
    tests = []
    for module in app_module, test_module:
        try:
            doctests = make_doctest(module)
            # Now iterate over the suite, looking for doctests whose name
            # matches the pattern that was given
            for test in doctests:
                if test._dt_test.name in (
                        '%s.%s' % (module.__name__, '.'.join(parts[1:])),
                        '%s.__test__.%s' % (
                            module.__name__, '.'.join(parts[1:]))):
                    tests.append(test)
        except ValueError:
            # No doctests found.
            pass

    # If no tests were found, then we were given a bad test label.
    if not tests:
        raise ValueError("Test label '%s' does not refer to a test" % label)

    # Construct a suite out of the tests that matched.
    return unittest.TestSuite(tests)


class DjangoTestSuiteRunner(runner.DiscoverRunner):

    def build_suite(self, test_labels, extra_tests=None, **kwargs):
        suite = unittest.TestSuite()

        if test_labels:
            for label in test_labels:
                if '.' in label:
                    suite.addTest(build_test(label))
                else:
                    app = get_app(label)
                    suite.addTest(build_suite(app))
        else:
            for app in get_apps():
                suite.addTest(build_suite(app))

        if extra_tests:
            for test in extra_tests:
                suite.addTest(test)

        return runner.reorder_suite(suite, (unittest.TestCase,))
