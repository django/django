#!/usr/bin/env python

import os, subprocess, sys, traceback
import unittest

import django.contrib as contrib

CONTRIB_DIR_NAME = 'django.contrib'
MODEL_TESTS_DIR_NAME = 'modeltests'
REGRESSION_TESTS_DIR_NAME = 'regressiontests'

TEST_TEMPLATE_DIR = 'templates'

CONTRIB_DIR = os.path.dirname(contrib.__file__)
MODEL_TEST_DIR = os.path.join(os.path.dirname(__file__), MODEL_TESTS_DIR_NAME)
REGRESSION_TEST_DIR = os.path.join(os.path.dirname(__file__), REGRESSION_TESTS_DIR_NAME)

REGRESSION_SUBDIRS_TO_SKIP = ['locale']

ALWAYS_INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'django.contrib.sites',
    'django.contrib.flatpages',
    'django.contrib.redirects',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.comments',
    'django.contrib.admin',
    'django.contrib.admindocs',
]

def get_test_models():
    models = []
    for loc, dirpath in (MODEL_TESTS_DIR_NAME, MODEL_TEST_DIR), (REGRESSION_TESTS_DIR_NAME, REGRESSION_TEST_DIR), (CONTRIB_DIR_NAME, CONTRIB_DIR):
        for f in os.listdir(dirpath):
            if f.startswith('__init__') or f.startswith('.') or \
               f.startswith('sql') or f.startswith('invalid') or \
               os.path.basename(f) in REGRESSION_SUBDIRS_TO_SKIP:
                continue
            models.append((loc, f))
    return models

def get_invalid_models():
    models = []
    for loc, dirpath in (MODEL_TESTS_DIR_NAME, MODEL_TEST_DIR), (REGRESSION_TESTS_DIR_NAME, REGRESSION_TEST_DIR), (CONTRIB_DIR_NAME, CONTRIB_DIR):
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
        from django.core.management.validation import get_validation_errors
        from django.db.models.loading import load_app
        from cStringIO import StringIO

        try:
            module = load_app(self.model_label)
        except Exception, e:
            self.fail('Unable to load invalid model module')

        # Make sure sys.stdout is not a tty so that we get errors without
        # coloring attached (makes matching the results easier). We restore
        # sys.stderr afterwards.
        orig_stdout = sys.stdout
        s = StringIO()
        sys.stdout = s
        count = get_validation_errors(s, module)
        sys.stdout = orig_stdout
        s.seek(0)
        error_log = s.read()
        actual = error_log.split('\n')
        expected = module.model_errors.split('\n')

        unexpected = [err for err in actual if err not in expected]
        missing = [err for err in expected if err not in actual]

        self.assert_(not unexpected, "Unexpected Errors: " + '\n'.join(unexpected))
        self.assert_(not missing, "Missing Errors: " + '\n'.join(missing))

def setup(verbosity, test_labels):
    from django.conf import settings
    state = {
        'INSTALLED_APPS': settings.INSTALLED_APPS,
        'ROOT_URLCONF': getattr(settings, "ROOT_URLCONF", ""),
        'TEMPLATE_DIRS': settings.TEMPLATE_DIRS,
        'USE_I18N': settings.USE_I18N,
        'LOGIN_URL': settings.LOGIN_URL,
        'LANGUAGE_CODE': settings.LANGUAGE_CODE,
        'MIDDLEWARE_CLASSES': settings.MIDDLEWARE_CLASSES,
    }

    # Redirect some settings for the duration of these tests.
    settings.INSTALLED_APPS = ALWAYS_INSTALLED_APPS
    settings.ROOT_URLCONF = 'urls'
    settings.TEMPLATE_DIRS = (os.path.join(os.path.dirname(__file__), TEST_TEMPLATE_DIR),)
    settings.USE_I18N = True
    settings.LANGUAGE_CODE = 'en'
    settings.LOGIN_URL = '/accounts/login/'
    settings.MIDDLEWARE_CLASSES = (
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        'django.contrib.messages.middleware.MessageMiddleware',
        'django.middleware.common.CommonMiddleware',
    )
    settings.SITE_ID = 1
    # For testing comment-utils, we require the MANAGERS attribute
    # to be set, so that a test email is sent out which we catch
    # in our tests.
    settings.MANAGERS = ("admin@djangoproject.com",)

    # Load all the ALWAYS_INSTALLED_APPS.
    # (This import statement is intentionally delayed until after we
    # access settings because of the USE_I18N dependency.)
    from django.db.models.loading import get_apps, load_app
    get_apps()

    # Load all the test model apps.
    test_labels_set = set([label.split('.')[0] for label in test_labels])
    for model_dir, model_name in get_test_models():
        model_label = '.'.join([model_dir, model_name])
        # if the model was named on the command line, or
        # no models were named (i.e., run all), import
        # this model and add it to the list to test.
        if not test_labels or model_name in test_labels_set:
            if verbosity >= 2:
                print "Importing model %s" % model_name
            mod = load_app(model_label)
            if mod:
                if model_label not in settings.INSTALLED_APPS:
                    settings.INSTALLED_APPS.append(model_label)

    return state

def teardown(state):
    from django.conf import settings
    # Restore the old settings.
    for key, value in state.items():
        setattr(settings, key, value)

def django_tests(verbosity, interactive, failfast, test_labels):
    from django.conf import settings
    state = setup(verbosity, test_labels)

    # Add tests for invalid models.
    extra_tests = []
    for model_dir, model_name in get_invalid_models():
        model_label = '.'.join([model_dir, model_name])
        if not test_labels or model_name in test_labels:
            extra_tests.append(InvalidModelTestCase(model_label))
            try:
                # Invalid models are not working apps, so we cannot pass them into
                # the test runner with the other test_labels
                test_labels.remove(model_name)
            except ValueError:
                pass

    # Run the test suite, including the extra validation tests.
    from django.test.utils import get_runner
    if not hasattr(settings, 'TEST_RUNNER'):
        settings.TEST_RUNNER = 'django.test.simple.DjangoTestSuiteRunner'
    TestRunner = get_runner(settings)

    if hasattr(TestRunner, 'func_name'):
        # Pre 1.2 test runners were just functions,
        # and did not support the 'failfast' option.
        import warnings
        warnings.warn(
            'Function-based test runners are deprecated. Test runners should be classes with a run_tests() method.',
            DeprecationWarning
        )
        failures = TestRunner(test_labels, verbosity=verbosity, interactive=interactive,
            extra_tests=extra_tests)
    else:
        test_runner = TestRunner(verbosity=verbosity, interactive=interactive, failfast=failfast)
        failures = test_runner.run_tests(test_labels, extra_tests=extra_tests)

    teardown(state)
    return failures


def bisect_tests(bisection_label, options, test_labels):
    state = setup(int(options.verbosity), test_labels)

    if not test_labels:
        # Get the full list of test labels to use for bisection
        from django.db.models.loading import get_apps
        test_labels = [app.__name__.split('.')[-2] for app in get_apps()]

    print '***** Bisecting test suite:',' '.join(test_labels)

    # Make sure the bisection point isn't in the test list
    # Also remove tests that need to be run in specific combinations
    for label in [bisection_label, 'model_inheritance_same_model_name']:
        try:
            test_labels.remove(label)
        except ValueError:
            pass

    subprocess_args = ['python','runtests.py', '--settings=%s' % options.settings]
    if options.failfast:
        subprocess_args.append('--failfast')
    if options.verbosity:
        subprocess_args.append('--verbosity=%s' % options.verbosity)
    if not options.interactive:
        subprocess_args.append('--noinput')

    iteration = 1
    while len(test_labels) > 1:
        midpoint = len(test_labels)/2
        test_labels_a = test_labels[:midpoint] + [bisection_label]
        test_labels_b = test_labels[midpoint:] + [bisection_label]
        print '***** Pass %da: Running the first half of the test suite' % iteration
        print '***** Test labels:',' '.join(test_labels_a)
        failures_a = subprocess.call(subprocess_args + test_labels_a)

        print '***** Pass %db: Running the second half of the test suite' % iteration
        print '***** Test labels:',' '.join(test_labels_b)
        print
        failures_b = subprocess.call(subprocess_args + test_labels_b)

        if failures_a and not failures_b:
            print "***** Problem found in first half. Bisecting again..."
            iteration = iteration + 1
            test_labels = test_labels_a[:-1]
        elif failures_b and not failures_a:
            print "***** Problem found in second half. Bisecting again..."
            iteration = iteration + 1
            test_labels = test_labels_b[:-1]
        elif failures_a and failures_b:
            print "***** Multiple sources of failure found"
            break
        else:
            print "***** No source of failure found... try pair execution (--pair)"
            break

    if len(test_labels) == 1:
        print "***** Source of error:",test_labels[0]
    teardown(state)

def paired_tests(paired_test, options, test_labels):
    state = setup(int(options.verbosity), test_labels)

    if not test_labels:
        print ""
        # Get the full list of test labels to use for bisection
        from django.db.models.loading import get_apps
        test_labels = [app.__name__.split('.')[-2] for app in get_apps()]

    print '***** Trying paired execution'

    # Make sure the bisection point isn't in the test list
    # Also remove tests that need to be run in specific combinations
    for label in [paired_test, 'model_inheritance_same_model_name']:
        try:
            test_labels.remove(label)
        except ValueError:
            pass

    subprocess_args = ['python','runtests.py', '--settings=%s' % options.settings]
    if options.failfast:
        subprocess_args.append('--failfast')
    if options.verbosity:
        subprocess_args.append('--verbosity=%s' % options.verbosity)
    if not options.interactive:
        subprocess_args.append('--noinput')

    for i, label in enumerate(test_labels):
        print '***** %d of %d: Check test pairing with %s' % (i+1, len(test_labels), label)
        failures = subprocess.call(subprocess_args + [label, paired_test])
        if failures:
            print '***** Found problem pair with',label
            return

    print '***** No problem pair found'
    teardown(state)

if __name__ == "__main__":
    from optparse import OptionParser
    usage = "%prog [options] [model model model ...]"
    parser = OptionParser(usage=usage)
    parser.add_option('-v','--verbosity', action='store', dest='verbosity', default='1',
        type='choice', choices=['0', '1', '2', '3'],
        help='Verbosity level; 0=minimal output, 1=normal output, 2=all output')
    parser.add_option('--noinput', action='store_false', dest='interactive', default=True,
        help='Tells Django to NOT prompt the user for input of any kind.')
    parser.add_option('--failfast', action='store_true', dest='failfast', default=False,
        help='Tells Django to stop running the test suite after first failed test.')
    parser.add_option('--settings',
        help='Python path to settings module, e.g. "myproject.settings". If this isn\'t provided, the DJANGO_SETTINGS_MODULE environment variable will be used.')
    parser.add_option('--bisect', action='store', dest='bisect', default=None,
        help="Bisect the test suite to discover a test that causes a test failure when combined with the named test.")
    parser.add_option('--pair', action='store', dest='pair', default=None,
        help="Run the test suite in pairs with the named test to find problem pairs.")
    options, args = parser.parse_args()
    if options.settings:
        os.environ['DJANGO_SETTINGS_MODULE'] = options.settings
    elif "DJANGO_SETTINGS_MODULE" not in os.environ:
        parser.error("DJANGO_SETTINGS_MODULE is not set in the environment. "
                      "Set it or use --settings.")

    if options.bisect:
        bisect_tests(options.bisect, options, args)
    elif options.pair:
        paired_tests(options.pair, options, args)
    else:
        failures = django_tests(int(options.verbosity), options.interactive, options.failfast, args)
        if failures:
            sys.exit(bool(failures))
