#!/usr/bin/env python
import os
import shutil
import subprocess
import sys
import tempfile
import warnings

from django import contrib
from django.utils._os import upath
from django.utils import six

# databrowse is deprecated, but we still want to run its tests
warnings.filterwarnings('ignore', "The Databrowse contrib app is deprecated",
                        DeprecationWarning, 'django.contrib.databrowse')

CONTRIB_DIR_NAME = 'django.contrib'
MODEL_TESTS_DIR_NAME = 'modeltests'
REGRESSION_TESTS_DIR_NAME = 'regressiontests'

TEST_TEMPLATE_DIR = 'templates'

RUNTESTS_DIR = os.path.dirname(upath(__file__))
CONTRIB_DIR = os.path.dirname(upath(contrib.__file__))
MODEL_TEST_DIR = os.path.join(RUNTESTS_DIR, MODEL_TESTS_DIR_NAME)
REGRESSION_TEST_DIR = os.path.join(RUNTESTS_DIR, REGRESSION_TESTS_DIR_NAME)
TEMP_DIR = tempfile.mkdtemp(prefix='django_')
os.environ['DJANGO_TEST_TEMP_DIR'] = TEMP_DIR

REGRESSION_SUBDIRS_TO_SKIP = []

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
    'django.contrib.databrowse',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'regressiontests.staticfiles_tests',
    'regressiontests.staticfiles_tests.apps.test',
    'regressiontests.staticfiles_tests.apps.no_label',
]

def geodjango(settings):
    # All databases must have spatial backends to run GeoDjango tests.
    spatial_dbs = [name for name, db_dict in settings.DATABASES.items()
                   if db_dict['ENGINE'].startswith('django.contrib.gis')]
    return len(spatial_dbs) == len(settings.DATABASES)

def get_test_modules():
    modules = []
    for loc, dirpath in (
        (MODEL_TESTS_DIR_NAME, MODEL_TEST_DIR),
        (REGRESSION_TESTS_DIR_NAME, REGRESSION_TEST_DIR),
        (CONTRIB_DIR_NAME, CONTRIB_DIR)):
        for f in os.listdir(dirpath):
            if (f.startswith('__init__') or
                f.startswith('.') or
                # Python 3 byte code dirs (PEP 3147)
                f == '__pycache__' or
                f.startswith('sql') or
                os.path.basename(f) in REGRESSION_SUBDIRS_TO_SKIP):
                continue
            modules.append((loc, f))
    return modules

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
        'STATIC_URL': settings.STATIC_URL,
        'STATIC_ROOT': settings.STATIC_ROOT,
    }

    # Redirect some settings for the duration of these tests.
    settings.INSTALLED_APPS = ALWAYS_INSTALLED_APPS
    settings.ROOT_URLCONF = 'urls'
    settings.STATIC_URL = '/static/'
    settings.STATIC_ROOT = os.path.join(TEMP_DIR, 'static')
    settings.TEMPLATE_DIRS = (os.path.join(RUNTESTS_DIR, TEST_TEMPLATE_DIR),)
    settings.USE_I18N = True
    settings.LANGUAGE_CODE = 'en'
    settings.LOGIN_URL = 'django.contrib.auth.views.login'
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
    test_modules = get_test_modules()

    # If GeoDjango, then we'll want to add in the test applications
    # that are a part of its test suite.
    if geodjango(settings):
        from django.contrib.gis.tests import geo_apps
        test_modules.extend(geo_apps(runtests=True))
        settings.INSTALLED_APPS.extend(['django.contrib.gis', 'django.contrib.sitemaps'])

    for module_dir, module_name in test_modules:
        module_label = '.'.join([module_dir, module_name])
        # if the module was named on the command line, or
        # no modules were named (i.e., run all), import
        # this module and add it to the list to test.
        if not test_labels or module_name in test_labels_set:
            if verbosity >= 2:
                print("Importing application %s" % module_name)
            mod = load_app(module_label)
            if mod:
                if module_label not in settings.INSTALLED_APPS:
                    settings.INSTALLED_APPS.append(module_label)

    return state

def teardown(state):
    from django.conf import settings
    # Removing the temporary TEMP_DIR. Ensure we pass in unicode
    # so that it will successfully remove temp trees containing
    # non-ASCII filenames on Windows. (We're assuming the temp dir
    # name itself does not contain non-ASCII characters.)
    shutil.rmtree(six.text_type(TEMP_DIR))
    # Restore the old settings.
    for key, value in state.items():
        setattr(settings, key, value)

def django_tests(verbosity, interactive, failfast, test_labels):
    from django.conf import settings
    state = setup(verbosity, test_labels)
    extra_tests = []

    # If GeoDjango is used, add it's tests that aren't a part of
    # an application (e.g., GEOS, GDAL, Distance objects).
    if geodjango(settings) and (not test_labels or 'gis' in test_labels):
        from django.contrib.gis.tests import geodjango_suite
        extra_tests.append(geodjango_suite(apps=False))

    # Run the test suite, including the extra validation tests.
    from django.test.utils import get_runner
    if not hasattr(settings, 'TEST_RUNNER'):
        settings.TEST_RUNNER = 'django.test.simple.DjangoTestSuiteRunner'
    TestRunner = get_runner(settings)

    test_runner = TestRunner(verbosity=verbosity, interactive=interactive,
        failfast=failfast)
    failures = test_runner.run_tests(test_labels, extra_tests=extra_tests)

    teardown(state)
    return failures


def bisect_tests(bisection_label, options, test_labels):
    state = setup(int(options.verbosity), test_labels)

    if not test_labels:
        # Get the full list of test labels to use for bisection
        from django.db.models.loading import get_apps
        test_labels = [app.__name__.split('.')[-2] for app in get_apps()]

    print('***** Bisecting test suite: %s' % ' '.join(test_labels))

    # Make sure the bisection point isn't in the test list
    # Also remove tests that need to be run in specific combinations
    for label in [bisection_label, 'model_inheritance_same_model_name']:
        try:
            test_labels.remove(label)
        except ValueError:
            pass

    subprocess_args = [
        sys.executable, upath(__file__), '--settings=%s' % options.settings]
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
        print('***** Pass %da: Running the first half of the test suite' % iteration)
        print('***** Test labels: %s' % ' '.join(test_labels_a))
        failures_a = subprocess.call(subprocess_args + test_labels_a)

        print('***** Pass %db: Running the second half of the test suite' % iteration)
        print('***** Test labels: %s' % ' '.join(test_labels_b))
        print('')
        failures_b = subprocess.call(subprocess_args + test_labels_b)

        if failures_a and not failures_b:
            print("***** Problem found in first half. Bisecting again...")
            iteration = iteration + 1
            test_labels = test_labels_a[:-1]
        elif failures_b and not failures_a:
            print("***** Problem found in second half. Bisecting again...")
            iteration = iteration + 1
            test_labels = test_labels_b[:-1]
        elif failures_a and failures_b:
            print("***** Multiple sources of failure found")
            break
        else:
            print("***** No source of failure found... try pair execution (--pair)")
            break

    if len(test_labels) == 1:
        print("***** Source of error: %s" % test_labels[0])
    teardown(state)

def paired_tests(paired_test, options, test_labels):
    state = setup(int(options.verbosity), test_labels)

    if not test_labels:
        print("")
        # Get the full list of test labels to use for bisection
        from django.db.models.loading import get_apps
        test_labels = [app.__name__.split('.')[-2] for app in get_apps()]

    print('***** Trying paired execution')

    # Make sure the constant member of the pair isn't in the test list
    # Also remove tests that need to be run in specific combinations
    for label in [paired_test, 'model_inheritance_same_model_name']:
        try:
            test_labels.remove(label)
        except ValueError:
            pass

    subprocess_args = [
        sys.executable, upath(__file__), '--settings=%s' % options.settings]
    if options.failfast:
        subprocess_args.append('--failfast')
    if options.verbosity:
        subprocess_args.append('--verbosity=%s' % options.verbosity)
    if not options.interactive:
        subprocess_args.append('--noinput')

    for i, label in enumerate(test_labels):
        print('***** %d of %d: Check test pairing with %s' % (
              i + 1, len(test_labels), label))
        failures = subprocess.call(subprocess_args + [label, paired_test])
        if failures:
            print('***** Found problem pair with %s' % label)
            return

    print('***** No problem pair found')
    teardown(state)

if __name__ == "__main__":
    from optparse import OptionParser
    usage = "%prog [options] [module module module ...]"
    parser = OptionParser(usage=usage)
    parser.add_option(
        '-v', '--verbosity', action='store', dest='verbosity', default='1',
        type='choice', choices=['0', '1', '2', '3'],
        help='Verbosity level; 0=minimal output, 1=normal output, 2=all '
             'output')
    parser.add_option(
        '--noinput', action='store_false', dest='interactive', default=True,
        help='Tells Django to NOT prompt the user for input of any kind.')
    parser.add_option(
        '--failfast', action='store_true', dest='failfast', default=False,
        help='Tells Django to stop running the test suite after first failed '
             'test.')
    parser.add_option(
        '--settings',
        help='Python path to settings module, e.g. "myproject.settings". If '
             'this isn\'t provided, the DJANGO_SETTINGS_MODULE environment '
             'variable will be used.')
    parser.add_option(
        '--bisect', action='store', dest='bisect', default=None,
        help='Bisect the test suite to discover a test that causes a test '
             'failure when combined with the named test.')
    parser.add_option(
        '--pair', action='store', dest='pair', default=None,
        help='Run the test suite in pairs with the named test to find problem '
             'pairs.')
    parser.add_option(
        '--liveserver', action='store', dest='liveserver', default=None,
        help='Overrides the default address where the live server (used with '
             'LiveServerTestCase) is expected to run from. The default value '
             'is localhost:8081.'),
    options, args = parser.parse_args()
    if options.settings:
        os.environ['DJANGO_SETTINGS_MODULE'] = options.settings
    elif "DJANGO_SETTINGS_MODULE" not in os.environ:
        parser.error("DJANGO_SETTINGS_MODULE is not set in the environment. "
                      "Set it or use --settings.")
    else:
        options.settings = os.environ['DJANGO_SETTINGS_MODULE']

    if options.liveserver is not None:
        os.environ['DJANGO_LIVE_TEST_SERVER_ADDRESS'] = options.liveserver

    if options.bisect:
        bisect_tests(options.bisect, options, args)
    elif options.pair:
        paired_tests(options.pair, options, args)
    else:
        failures = django_tests(int(options.verbosity), options.interactive,
                                options.failfast, args)
        if failures:
            sys.exit(bool(failures))
