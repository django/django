import unittest, doctest
from django.conf import settings
from django.core import management
from django.test.utils import setup_test_environment, teardown_test_environment
from django.test.utils import create_test_db, destroy_test_db
from django.utils.translation import gettext as _
from django.test.testcases import OutputChecker, DocTestRunner

# The module name for tests outside models.py
TEST_MODULE = 'tests'
    
doctestOutputChecker = OutputChecker()

def build_suite(app_module):
    "Create a complete Django test suite for the provided application module"
    suite = unittest.TestSuite()
    
    # Load unit and doctests in the models.py file
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
    try:
        app_path = app_module.__name__.split('.')[:-1]
        test_module = __import__('.'.join(app_path + [TEST_MODULE]), {}, {}, TEST_MODULE)
        
        suite.addTest(unittest.defaultTestLoader.loadTestsFromModule(test_module))
        try:            
            suite.addTest(doctest.DocTestSuite(test_module, 
                                               checker=doctestOutputChecker,
                                               runner=DocTestRunner))
        except ValueError:
            # No doc tests in tests.py
            pass
    except ImportError, e:
        # Couldn't import tests.py. Was it due to a missing file, or
        # due to an import error in a tests.py that actually exists?
        import os.path
        from imp import find_module
        try:
            mod = find_module(TEST_MODULE, [os.path.dirname(app_module.__file__)])
        except ImportError:
            # 'tests' module doesn't exist. Move on.
            pass
        else:
            # The module exists, so there must be an import error in the 
            # test module itself. We don't need the module; close the file
            # handle returned by find_module.
            mod[0].close()
            raise
            
    return suite

def run_tests(module_list, verbosity=1, extra_tests=[]):
    """
    Run the unit tests for all the modules in the provided list.
    This testrunner will search each of the modules in the provided list,
    looking for doctests and unittests in models.py or tests.py within
    the module. A list of 'extra' tests may also be provided; these tests
    will be added to the test suite.
    """
    setup_test_environment()
    
    settings.DEBUG = False    
    suite = unittest.TestSuite()
     
    for module in module_list:
        suite.addTest(build_suite(module))
    
    for test in extra_tests:
        suite.addTest(test)

    old_name = settings.DATABASE_NAME
    create_test_db(verbosity)
    management.syncdb(verbosity, interactive=False)
    unittest.TextTestRunner(verbosity=verbosity).run(suite)
    destroy_test_db(old_name, verbosity)
    
    teardown_test_environment()
