import unittest
from django.conf import settings
from django.db.models import get_app, get_apps
from django.test import _doctest as doctest
from django.test.utils import setup_test_environment, teardown_test_environment
from django.test.testcases import OutputChecker, DocTestRunner, TestCase

# The module name for tests outside models.py
TEST_MODULE = 'tests'
    
doctestOutputChecker = OutputChecker()

def get_tests(app_module):
    try:
        app_path = app_module.__name__.split('.')[:-1]
        test_module = __import__('.'.join(app_path + [TEST_MODULE]), {}, {}, TEST_MODULE)
    except ImportError, e:
        # Couldn't import tests.py. Was it due to a missing file, or
        # due to an import error in a tests.py that actually exists?
        import os.path
        from imp import find_module
        try:
            mod = find_module(TEST_MODULE, [os.path.dirname(app_module.__file__)])
        except ImportError:
            # 'tests' module doesn't exist. Move on.
            test_module = None
        else:
            # The module exists, so there must be an import error in the 
            # test module itself. We don't need the module; so if the
            # module was a single file module (i.e., tests.py), close the file
            # handle returned by find_module. Otherwise, the test module
            # is a directory, and there is nothing to close.
            if mod[0]:
                mod[0].close()
            raise
    return test_module
    
def build_suite(app_module):
    "Create a complete Django test suite for the provided application module"
    suite = unittest.TestSuite()
    
    # Load unit and doctests in the models.py module. If module has
    # a suite() method, use it. Otherwise build the test suite ourselves.
    if hasattr(app_module, 'suite'):
        suite.addTest(app_module.suite())
    else:
        suite.addTest(unittest.defaultTestLoader.loadTestsFromModule(app_module))
        try:
            suite.addTest(doctest.DocTestSuite(app_module,
                                               checker=doctestOutputChecker,
                                               runner=DocTestRunner))
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
            suite.addTest(unittest.defaultTestLoader.loadTestsFromModule(test_module))
            try:            
                suite.addTest(doctest.DocTestSuite(test_module, 
                                                   checker=doctestOutputChecker,
                                                   runner=DocTestRunner))
            except ValueError:
                # No doc tests in tests.py
                pass
    return suite

def build_test(label):
    """Construct a test case a test with the specified label. Label should 
    be of the form model.TestClass or model.TestClass.test_method. Returns
    an instantiated test or test suite corresponding to the label provided.
        
    """
    parts = label.split('.')
    if len(parts) < 2 or len(parts) > 3:
        raise ValueError("Test label '%s' should be of the form app.TestCase or app.TestCase.test_method" % label)
    
    app_module = get_app(parts[0])
    TestClass = getattr(app_module, parts[1], None)

    # Couldn't find the test class in models.py; look in tests.py
    if TestClass is None:
        test_module = get_tests(app_module)
        if test_module:
            TestClass = getattr(test_module, parts[1], None)

    if len(parts) == 2: # label is app.TestClass
        try:
            return unittest.TestLoader().loadTestsFromTestCase(TestClass)
        except TypeError:
            raise ValueError("Test label '%s' does not refer to a test class" % label)            
    else: # label is app.TestClass.test_method
        return TestClass(parts[2])

# Python 2.3 compatibility: TestSuites were made iterable in 2.4.
# We need to iterate over them, so we add the missing method when
# necessary.    
try:
    getattr(unittest.TestSuite, '__iter__')
except AttributeError:
    setattr(unittest.TestSuite, '__iter__', lambda s: iter(s._tests))

def partition_suite(suite, classes, bins):
    """
    Partitions a test suite by test type.
    
    classes is a sequence of types
    bins is a sequence of TestSuites, one more than classes
    
    Tests of type classes[i] are added to bins[i], 
    tests with no match found in classes are place in bins[-1]
    """
    for test in suite:
        if isinstance(test, unittest.TestSuite):
            partition_suite(test, classes, bins)
        else:
            for i in range(len(classes)):
                if isinstance(test, classes[i]):
                    bins[i].addTest(test)
                    break
            else:
                bins[-1].addTest(test)
            
def reorder_suite(suite, classes):
    """
    Reorders a test suite by test type.
    
    classes is a sequence of types
    
    All tests of type clases[0] are placed first, then tests of type classes[1], etc.
    Tests with no match in classes are placed last.
    """
    class_count = len(classes)
    bins = [unittest.TestSuite() for i in range(class_count+1)]
    partition_suite(suite, classes, bins)
    for i in range(class_count):
        bins[0].addTests(bins[i+1])
    return bins[0]

def run_tests(test_labels, verbosity=1, interactive=True, extra_tests=[]):
    """
    Run the unit tests for all the test labels in the provided list.
    Labels must be of the form:
     - app.TestClass.test_method
        Run a single specific test method
     - app.TestClass
        Run all the test methods in a given class
     - app
        Search for doctests and unittests in the named application.

    When looking for tests, the test runner will look in the models and
    tests modules for the application.
    
    A list of 'extra' tests may also be provided; these tests
    will be added to the test suite.
    
    Returns the number of tests that failed.
    """
    setup_test_environment()
    
    settings.DEBUG = False    
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
    
    for test in extra_tests:
        suite.addTest(test)

    suite = reorder_suite(suite, (TestCase,))

    old_name = settings.DATABASE_NAME
    from django.db import connection
    connection.creation.create_test_db(verbosity, autoclobber=not interactive)
    result = unittest.TextTestRunner(verbosity=verbosity).run(suite)
    connection.creation.destroy_test_db(old_name, verbosity)
    
    teardown_test_environment()
    
    return len(result.failures) + len(result.errors)
