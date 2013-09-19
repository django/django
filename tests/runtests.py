#!/usr/bin/env python
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import warnings

from django import contrib
from django.utils._os import upath
from django.utils import six

CONTRIB_MODULE_PATH = 'django.contrib'

TEST_TEMPLATE_DIR = 'templates'

RUNTESTS_DIR = os.path.abspath(os.path.dirname(upath(__file__)))
CONTRIB_DIR = os.path.dirname(upath(contrib.__file__))

TEMP_DIR = tempfile.mkdtemp(prefix='django_')
os.environ['DJANGO_TEST_TEMP_DIR'] = TEMP_DIR

SUBDIRS_TO_SKIP = [
    'requirements',
    'templates',
    'test_discovery_sample',
    'test_discovery_sample2',
    'test_runner_deprecation_app',
    'test_runner_invalid_app',
]

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
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'staticfiles_tests',
    'staticfiles_tests.apps.test',
    'staticfiles_tests.apps.no_label',
]


def get_test_modules():
    modules = []
    for modpath, dirpath in (
        (None, RUNTESTS_DIR),
        (CONTRIB_MODULE_PATH, CONTRIB_DIR)):
        for f in os.listdir(dirpath):
            if ('.' in f or
                # Python 3 byte code dirs (PEP 3147)
                f == '__pycache__' or
                f.startswith('sql') or
                os.path.basename(f) in SUBDIRS_TO_SKIP or
                os.path.isfile(f)):
                continue
            modules.append((modpath, f))
    return modules

def get_installed():
    from django.db.models.loading import get_apps
    return [app.__name__.rsplit('.', 1)[0] for app in get_apps()]


def setup(verbosity, test_labels):
    from django.conf import settings
    from django.db.models.loading import get_apps, load_app
    from django.test.testcases import TransactionTestCase, TestCase

    # Force declaring available_apps in TransactionTestCase for faster tests.
    def no_available_apps(self):
        raise Exception("Please define available_apps in TransactionTestCase "
                        "and its subclasses.")
    TransactionTestCase.available_apps = property(no_available_apps)
    TestCase.available_apps = None

    state = {
        'INSTALLED_APPS': settings.INSTALLED_APPS,
        'ROOT_URLCONF': getattr(settings, "ROOT_URLCONF", ""),
        'TEMPLATE_DIRS': settings.TEMPLATE_DIRS,
        'LANGUAGE_CODE': settings.LANGUAGE_CODE,
        'STATIC_URL': settings.STATIC_URL,
        'STATIC_ROOT': settings.STATIC_ROOT,
    }

    # Redirect some settings for the duration of these tests.
    settings.INSTALLED_APPS = ALWAYS_INSTALLED_APPS
    settings.ROOT_URLCONF = 'urls'
    settings.STATIC_URL = '/static/'
    settings.STATIC_ROOT = os.path.join(TEMP_DIR, 'static')
    settings.TEMPLATE_DIRS = (os.path.join(RUNTESTS_DIR, TEST_TEMPLATE_DIR),)
    settings.LANGUAGE_CODE = 'en'
    settings.SITE_ID = 1

    if verbosity > 0:
        # Ensure any warnings captured to logging are piped through a verbose
        # logging handler.  If any -W options were passed explicitly on command
        # line, warnings are not captured, and this has no effect.
        logger = logging.getLogger('py.warnings')
        handler = logging.StreamHandler()
        logger.addHandler(handler)

    # Load all the ALWAYS_INSTALLED_APPS.
    with warnings.catch_warnings():
        warnings.filterwarnings('ignore', 'django.contrib.comments is deprecated and will be removed before Django 1.8.', PendingDeprecationWarning)
        get_apps()

    # Load all the test model apps.
    test_modules = get_test_modules()

    # Reduce given test labels to just the app module path
    test_labels_set = set()
    for label in test_labels:
        bits = label.split('.')
        if bits[:2] == ['django', 'contrib']:
            bits = bits[:3]
        else:
            bits = bits[:1]
        test_labels_set.add('.'.join(bits))

    # If GeoDjango, then we'll want to add in the test applications
    # that are a part of its test suite.
    from django.contrib.gis.tests.utils import HAS_SPATIAL_DB
    if HAS_SPATIAL_DB:
        from django.contrib.gis.tests import geo_apps
        test_modules.extend(geo_apps())
        settings.INSTALLED_APPS.extend(['django.contrib.gis', 'django.contrib.sitemaps'])

    for modpath, module_name in test_modules:
        if modpath:
            module_label = '.'.join([modpath, module_name])
        else:
            module_label = module_name
        # if the module (or an ancestor) was named on the command line, or
        # no modules were named (i.e., run all), import
        # this module and add it to INSTALLED_APPS.
        if not test_labels:
            module_found_in_labels = True
        else:
            match = lambda label: (
                module_label == label or  # exact match
                module_label.startswith(label + '.')  # ancestor match
                )

            module_found_in_labels = any(match(l) for l in test_labels_set)

        if module_found_in_labels:
            if verbosity >= 2:
                print("Importing application %s" % module_name)
            mod = load_app(module_label)
            if mod:
                if module_label not in settings.INSTALLED_APPS:
                    settings.INSTALLED_APPS.append(module_label)

    return state


def teardown(state):
    from django.conf import settings

    try:
        # Removing the temporary TEMP_DIR. Ensure we pass in unicode
        # so that it will successfully remove temp trees containing
        # non-ASCII filenames on Windows. (We're assuming the temp dir
        # name itself does not contain non-ASCII characters.)
        shutil.rmtree(six.text_type(TEMP_DIR))
    except OSError:
        print('Failed to remove temp directory: %s' % TEMP_DIR)

    # Restore the old settings.
    for key, value in state.items():
        setattr(settings, key, value)


def django_tests(verbosity, interactive, failfast, test_labels):
    from django.conf import settings
    state = setup(verbosity, test_labels)
    extra_tests = []

    # Run the test suite, including the extra validation tests.
    from django.test.utils import get_runner
    if not hasattr(settings, 'TEST_RUNNER'):
        settings.TEST_RUNNER = 'django.test.runner.DiscoverRunner'
    TestRunner = get_runner(settings)

    test_runner = TestRunner(
        verbosity=verbosity,
        interactive=interactive,
        failfast=failfast,
    )
    failures = test_runner.run_tests(
        test_labels or get_installed(), extra_tests=extra_tests)

    teardown(state)
    return failures


def bisect_tests(bisection_label, options, test_labels):
    state = setup(int(options.verbosity), test_labels)

    test_labels = test_labels or get_installed()

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

    test_labels = test_labels or get_installed()

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
             'is localhost:8081.')
    parser.add_option(
        '--selenium', action='store_true', dest='selenium',
        default=False,
        help='Run the Selenium tests as well (if Selenium is installed)')
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

    if options.selenium:
        os.environ['DJANGO_SELENIUM_TESTS'] = '1'

    if options.bisect:
        bisect_tests(options.bisect, options, args)
    elif options.pair:
        paired_tests(options.pair, options, args)
    else:
        failures = django_tests(int(options.verbosity), options.interactive,
                                options.failfast, args)
        if failures:
            sys.exit(bool(failures))
