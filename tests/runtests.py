#!/usr/bin/env python

import os, sys, traceback
import unittest

MODEL_TESTS_DIR_NAME = 'modeltests'
REGRESSION_TESTS_DIR_NAME = 'regressiontests'
TEST_DATABASE_NAME = 'django_test_db'

MODEL_TEST_DIR = os.path.join(os.path.dirname(__file__), MODEL_TESTS_DIR_NAME)
REGRESSION_TEST_DIR = os.path.join(os.path.dirname(__file__), REGRESSION_TESTS_DIR_NAME)

ALWAYS_INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'django.contrib.sites',
    'django.contrib.flatpages',
    'django.contrib.redirects',
    'django.contrib.sessions',
    'django.contrib.comments',
    'django.contrib.admin',
]

def get_test_models():
    models = []
    for loc, dirpath in (MODEL_TESTS_DIR_NAME, MODEL_TEST_DIR), (REGRESSION_TESTS_DIR_NAME, REGRESSION_TEST_DIR):
        for f in os.listdir(dirpath):
            if f.startswith('__init__') or f.startswith('.') or f.startswith('sql') or f.startswith('invalid'):
                continue
            models.append((loc, f))
    return models

def get_invalid_models():
    models = []
    for loc, dirpath in (MODEL_TESTS_DIR_NAME, MODEL_TEST_DIR), (REGRESSION_TESTS_DIR_NAME, REGRESSION_TEST_DIR):
        for f in os.listdir(dirpath):
            if f.startswith('__init__') or f.startswith('.') or f.startswith('sql'):
                continue
            if f.startswith('invalid'):
                models.append((loc, f))
    return models
                
class InvalidModelTestCase(unittest.TestCase):
    def __init__(self, model_label):
        unittest.TestCase.__init__(self)
        self.model_label = model_label
        
    def runTest(self):
        from django.core import management
        from django.db.models.loading import load_app
        from cStringIO import StringIO

        try:
            module = load_app(self.model_label)
        except Exception, e:
            self.fail('Unable to load invalid model module')
        
        s = StringIO()
        count = management.get_validation_errors(s, module)
        s.seek(0)
        error_log = s.read()
        actual = error_log.split('\n')
        expected = module.model_errors.split('\n')

        unexpected = [err for err in actual if err not in expected]
        missing = [err for err in expected if err not in actual]

        self.assert_(not unexpected, "Unexpected Errors: " + '\n'.join(unexpected))
        self.assert_(not missing, "Missing Errors: " + '\n'.join(missing))

def django_tests(verbosity, tests_to_run):
    from django.conf import settings
    from django.db.models.loading import get_apps, load_app
    old_installed_apps = settings.INSTALLED_APPS
    old_test_database_name = settings.TEST_DATABASE_NAME
    
    settings.TEST_DATABASE_NAME = TEST_DATABASE_NAME
    settings.INSTALLED_APPS = ALWAYS_INSTALLED_APPS

    # load all the ALWAYS_INSTALLED_APPS
    get_apps()
    
    test_models = []
    # Load all the test model apps
    for model_dir, model_name in get_test_models():        
        model_label = '.'.join([model_dir, model_name])
        try:
            # if the model was named on the command line, or
            # no models were named (i.e., run all), import 
            # this model and add it to the list to test.
            if not tests_to_run or model_name in tests_to_run:
                if verbosity >= 1:
                    print "Importing model %s" % model_name
                mod = load_app(model_label)
                settings.INSTALLED_APPS.append(model_label)        
                test_models.append(mod)
        except Exception, e:
            sys.stderr.write("Error while importing %s:" % model_name + ''.join(traceback.format_exception(*sys.exc_info())[1:]))
            continue    

    # Add tests for invalid models
    extra_tests = []
    for model_dir, model_name in get_invalid_models():
        model_label = '.'.join([model_dir, model_name])
        if not tests_to_run or model_name in tests_to_run:
            extra_tests.append(InvalidModelTestCase(model_label))
    
    # Run the test suite, including the extra validation tests.
    from django.test.simple import run_tests
    run_tests(test_models, verbosity, extra_tests=extra_tests)
  
    # Restore the old settings
    settings.INSTALLED_APPS = old_installed_apps
    settings.TESTS_DATABASE_NAME = old_test_database_name
if __name__ == "__main__":
    from optparse import OptionParser
    usage = "%prog [options] [model model model ...]"
    parser = OptionParser(usage=usage)
    parser.add_option('-v','--verbosity', action='store', dest='verbosity', default='0',
        type='choice', choices=['0', '1', '2'],
        help='Verbosity level; 0=minimal output, 1=normal output, 2=all output')    
    parser.add_option('--settings',
        help='Python path to settings module, e.g. "myproject.settings". If this isn\'t provided, the DJANGO_SETTINGS_MODULE environment variable will be used.')
    options, args = parser.parse_args()
    if options.settings:
        os.environ['DJANGO_SETTINGS_MODULE'] = options.settings
        
    django_tests(int(options.verbosity), args)
