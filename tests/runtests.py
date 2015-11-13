#!/usr/bin/env python
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import warnings
from argparse import ArgumentParser

import django
from django.apps import apps
from django.conf import settings
from django.db import connection
from django.test import TestCase, TransactionTestCase
from django.test.utils import get_runner
from django.utils import six
from django.utils._os import upath
from django.utils.deprecation import (
    RemovedInDjango19Warning, RemovedInDjango110Warning,
)

# Make deprecation warnings errors to ensure no usage of deprecated features.
warnings.simplefilter("error", RemovedInDjango19Warning)
warnings.simplefilter("error", RemovedInDjango110Warning)
# Make runtime warning errors to ensure no usage of error prone patterns.
warnings.simplefilter("error", RuntimeWarning)
# Ignore known warnings in test dependencies.
warnings.filterwarnings("ignore", "'U' mode is deprecated", DeprecationWarning, module='docutils.io')

RUNTESTS_DIR = os.path.abspath(os.path.dirname(upath(__file__)))

TEMPLATE_DIR = os.path.join(RUNTESTS_DIR, 'templates')

# Create a specific subdirectory for the duration of the test suite.
TMPDIR = tempfile.mkdtemp(prefix='django_')
# Set the TMPDIR environment variable in addition to tempfile.tempdir
# so that children processes inherit it.
tempfile.tempdir = os.environ['TMPDIR'] = TMPDIR

SUBDIRS_TO_SKIP = [
    'data',
    'import_error_package',
    'test_discovery_sample',
    'test_discovery_sample2',
    'test_runner_deprecation_app',
]

ALWAYS_INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'django.contrib.sites',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.admin.apps.SimpleAdminConfig',
    'django.contrib.staticfiles',
]

ALWAYS_MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

# Need to add the associated contrib app to INSTALLED_APPS in some cases to
# avoid "RuntimeError: Model class X doesn't declare an explicit app_label
# and either isn't in an application in INSTALLED_APPS or else was imported
# before its application was loaded."
CONTRIB_TESTS_TO_APPS = {
    'flatpages_tests': 'django.contrib.flatpages',
    'redirects_tests': 'django.contrib.redirects',
}


def get_test_modules():
    modules = []
    discovery_paths = [
        (None, RUNTESTS_DIR),
    ]
    # GIS tests are in nested apps
    if connection.features.gis_enabled:
        discovery_paths.append(
            ('gis_tests', os.path.join(RUNTESTS_DIR, 'gis_tests'))
        )

    for modpath, dirpath in discovery_paths:
        for f in os.listdir(dirpath):
            if ('.' in f or
                    f.startswith('sql') or
                    os.path.basename(f) in SUBDIRS_TO_SKIP or
                    os.path.isfile(f) or
                    not os.path.exists(os.path.join(dirpath, f, '__init__.py'))):
                continue
            if connection.vendor != 'postgresql' and f == 'postgres_tests':
                continue
            modules.append((modpath, f))
    return modules


def get_installed():
    return [app_config.name for app_config in apps.get_app_configs()]


def setup(verbosity, test_labels):
    print("Testing against Django installed in '%s'" % os.path.dirname(django.__file__))

    # Force declaring available_apps in TransactionTestCase for faster tests.
    def no_available_apps(self):
        raise Exception("Please define available_apps in TransactionTestCase "
                        "and its subclasses.")
    TransactionTestCase.available_apps = property(no_available_apps)
    TestCase.available_apps = None

    state = {
        'INSTALLED_APPS': settings.INSTALLED_APPS,
        'ROOT_URLCONF': getattr(settings, "ROOT_URLCONF", ""),
        'TEMPLATES': settings.TEMPLATES,
        'LANGUAGE_CODE': settings.LANGUAGE_CODE,
        'STATIC_URL': settings.STATIC_URL,
        'STATIC_ROOT': settings.STATIC_ROOT,
        'MIDDLEWARE_CLASSES': settings.MIDDLEWARE_CLASSES,
    }

    # Redirect some settings for the duration of these tests.
    settings.INSTALLED_APPS = ALWAYS_INSTALLED_APPS
    settings.ROOT_URLCONF = 'urls'
    settings.STATIC_URL = '/static/'
    settings.STATIC_ROOT = os.path.join(TMPDIR, 'static')
    settings.TEMPLATES = [{
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [TEMPLATE_DIR],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    }]
    settings.LANGUAGE_CODE = 'en'
    settings.SITE_ID = 1
    settings.MIDDLEWARE_CLASSES = ALWAYS_MIDDLEWARE_CLASSES
    # Ensure the middleware classes are seen as overridden otherwise we get a compatibility warning.
    settings._explicit_settings.add('MIDDLEWARE_CLASSES')
    settings.MIGRATION_MODULES = {
        # these 'tests.migrations' modules don't actually exist, but this lets
        # us skip creating migrations for the test models.
        'auth': 'django.contrib.auth.tests.migrations',
        'contenttypes': 'contenttypes_tests.migrations',
    }

    if verbosity > 0:
        # Ensure any warnings captured to logging are piped through a verbose
        # logging handler.  If any -W options were passed explicitly on command
        # line, warnings are not captured, and this has no effect.
        logger = logging.getLogger('py.warnings')
        handler = logging.StreamHandler()
        logger.addHandler(handler)

    warnings.filterwarnings(
        'ignore',
        'django.contrib.webdesign will be removed in Django 1.10.',
        RemovedInDjango110Warning
    )

    # Load all the ALWAYS_INSTALLED_APPS.
    django.setup()

    # Load all the test model apps.
    test_modules = get_test_modules()

    # Reduce given test labels to just the app module path
    test_labels_set = set()
    for label in test_labels:
        bits = label.split('.')[:1]
        test_labels_set.add('.'.join(bits))

    installed_app_names = set(get_installed())
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
            module_found_in_labels = any(
                # exact match or ancestor match
                module_label == label or module_label.startswith(label + '.')
                for label in test_labels_set)

        if module_name in CONTRIB_TESTS_TO_APPS and module_found_in_labels:
            settings.INSTALLED_APPS.append(CONTRIB_TESTS_TO_APPS[module_name])

        if module_found_in_labels and module_label not in installed_app_names:
            if verbosity >= 2:
                print("Importing application %s" % module_name)
            settings.INSTALLED_APPS.append(module_label)

    # Add contrib.gis to INSTALLED_APPS if needed (rather than requiring
    # @override_settings(INSTALLED_APPS=...) on all test cases.
    gis = 'django.contrib.gis'
    if connection.features.gis_enabled and gis not in settings.INSTALLED_APPS:
        if verbosity >= 2:
            print("Importing application %s" % gis)
        settings.INSTALLED_APPS.append(gis)

    apps.set_installed_apps(settings.INSTALLED_APPS)

    return state


def teardown(state):
    try:
        # Removing the temporary TMPDIR. Ensure we pass in unicode
        # so that it will successfully remove temp trees containing
        # non-ASCII filenames on Windows. (We're assuming the temp dir
        # name itself does not contain non-ASCII characters.)
        shutil.rmtree(six.text_type(TMPDIR))
    except OSError:
        print('Failed to remove temp directory: %s' % TMPDIR)

    # Restore the old settings.
    for key, value in state.items():
        setattr(settings, key, value)


def django_tests(verbosity, interactive, failfast, keepdb, reverse, test_labels, debug_sql):
    state = setup(verbosity, test_labels)
    extra_tests = []

    if test_labels and 'postgres_tests' in test_labels and connection.vendor != 'postgresql':
        if verbosity >= 2:
            print("Removed postgres_tests from tests as we're not running with PostgreSQL.")
        test_labels.remove('postgres_tests')

    # Run the test suite, including the extra validation tests.
    if not hasattr(settings, 'TEST_RUNNER'):
        settings.TEST_RUNNER = 'django.test.runner.DiscoverRunner'
    TestRunner = get_runner(settings)

    test_runner = TestRunner(
        verbosity=verbosity,
        interactive=interactive,
        failfast=failfast,
        keepdb=keepdb,
        reverse=reverse,
        debug_sql=debug_sql,
    )
    # Catch warnings thrown in test DB setup -- remove in Django 1.9
    with warnings.catch_warnings():
        warnings.filterwarnings(
            'ignore',
            "Custom SQL location '<app_label>/models/sql' is deprecated, "
            "use '<app_label>/sql' instead.",
            RemovedInDjango19Warning
        )
        warnings.filterwarnings(
            'ignore',
            'initial_data fixtures are deprecated. Use data migrations instead.',
            RemovedInDjango19Warning
        )
        failures = test_runner.run_tests(
            test_labels or get_installed(), extra_tests=extra_tests)

    teardown(state)
    return failures


def bisect_tests(bisection_label, options, test_labels):
    state = setup(options.verbosity, test_labels)

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
        midpoint = len(test_labels) // 2
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
    state = setup(options.verbosity, test_labels)

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
    parser = ArgumentParser(description="Run the Django test suite.")
    parser.add_argument('modules', nargs='*', metavar='module',
        help='Optional path(s) to test modules; e.g. "i18n" or '
             '"i18n.tests.TranslationTests.test_lazy_objects".')
    parser.add_argument(
        '-v', '--verbosity', default=1, type=int, choices=[0, 1, 2, 3],
        help='Verbosity level; 0=minimal output, 1=normal output, 2=all output')
    parser.add_argument(
        '--noinput', action='store_false', dest='interactive', default=True,
        help='Tells Django to NOT prompt the user for input of any kind.')
    parser.add_argument(
        '--failfast', action='store_true', dest='failfast', default=False,
        help='Tells Django to stop running the test suite after first failed '
             'test.')
    parser.add_argument(
        '-k', '--keepdb', action='store_true', dest='keepdb', default=False,
        help='Tells Django to preserve the test database between runs.')
    parser.add_argument(
        '--settings',
        help='Python path to settings module, e.g. "myproject.settings". If '
             'this isn\'t provided, either the DJANGO_SETTINGS_MODULE '
             'environment variable or "test_sqlite" will be used.')
    parser.add_argument('--bisect',
        help='Bisect the test suite to discover a test that causes a test '
             'failure when combined with the named test.')
    parser.add_argument('--pair',
        help='Run the test suite in pairs with the named test to find problem '
             'pairs.')
    parser.add_argument('--reverse', action='store_true', default=False,
        help='Sort test suites and test cases in opposite order to debug '
             'test side effects not apparent with normal execution lineup.')
    parser.add_argument('--liveserver',
        help='Overrides the default address where the live server (used with '
             'LiveServerTestCase) is expected to run from. The default value '
             'is localhost:8081.')
    parser.add_argument(
        '--selenium', action='store_true', dest='selenium', default=False,
        help='Run the Selenium tests as well (if Selenium is installed)')
    parser.add_argument(
        '--debug-sql', action='store_true', dest='debug_sql', default=False,
        help='Turn on the SQL query logger within tests')
    options = parser.parse_args()

    # mock is a required dependency
    try:
        from django.test import mock  # NOQA
    except ImportError:
        print(
            "Please install test dependencies first: \n"
            "$ pip install -r requirements/py%s.txt" % sys.version_info.major
        )
        sys.exit(1)

    # Allow including a trailing slash on app_labels for tab completion convenience
    options.modules = [os.path.normpath(labels) for labels in options.modules]

    if options.settings:
        os.environ['DJANGO_SETTINGS_MODULE'] = options.settings
    else:
        if "DJANGO_SETTINGS_MODULE" not in os.environ:
            os.environ['DJANGO_SETTINGS_MODULE'] = 'test_sqlite'
        options.settings = os.environ['DJANGO_SETTINGS_MODULE']

    if options.liveserver is not None:
        os.environ['DJANGO_LIVE_TEST_SERVER_ADDRESS'] = options.liveserver

    if options.selenium:
        os.environ['DJANGO_SELENIUM_TESTS'] = '1'

    if options.bisect:
        bisect_tests(options.bisect, options, options.modules)
    elif options.pair:
        paired_tests(options.pair, options, options.modules)
    else:
        failures = django_tests(options.verbosity, options.interactive,
                                options.failfast, options.keepdb,
                                options.reverse, options.modules,
                                options.debug_sql)
        if failures:
            sys.exit(bool(failures))
