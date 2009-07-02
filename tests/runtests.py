#!/usr/bin/env python
import os, sys, traceback
import unittest
import django
import django.contrib as contrib
from django.core.servers import basehttp
from time import sleep

try:
    set
except NameError:
    from sets import Set as set     # For Python 2.3

try:
    import coverage
except Exception, e:
    print "coverage.py module not available"

CONTRIB_DIR_NAME = 'django.contrib'
MODEL_TESTS_DIR_NAME = 'modeltests'
REGRESSION_TESTS_DIR_NAME = 'regressiontests'

TEST_TEMPLATE_DIR = 'templates'

CONTRIB_DIR = os.path.dirname(contrib.__file__)
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

# WINDMILL_FIXTURES = ['regressiontests/admin_views/fixtures/%s' % fix for fix in ['admin-views-users.xml',
#     'admin-views-colors.xml',
#     'admin-views-fabrics.xml',
#     'admin-views-unicode.xml',
#     'multiple-child-classes',
#     'admin-views-actions.xml',
#     'string-primary-key.xml',
#     'admin-views-person.xml']]


def get_test_models():
    models = []
    for loc, dirpath in (MODEL_TESTS_DIR_NAME, MODEL_TEST_DIR), (REGRESSION_TESTS_DIR_NAME, REGRESSION_TEST_DIR), (CONTRIB_DIR_NAME, CONTRIB_DIR):
        for f in os.listdir(dirpath):
            if f.startswith('__init__') or f.startswith('.') or f.startswith('sql') or f.startswith('invalid'):
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

def django_tests(verbosity, interactive, test_labels):
    from django.conf import settings

    old_installed_apps = settings.INSTALLED_APPS
    old_test_database_name = settings.TEST_DATABASE_NAME
    old_root_urlconf = getattr(settings, "ROOT_URLCONF", "")
    old_template_dirs = settings.TEMPLATE_DIRS
    old_use_i18n = settings.USE_I18N
    old_login_url = settings.LOGIN_URL
    old_language_code = settings.LANGUAGE_CODE
    old_middleware_classes = settings.MIDDLEWARE_CLASSES

    # Redirect some settings for the duration of these tests.
    settings.INSTALLED_APPS = ALWAYS_INSTALLED_APPS
    # Try and include windmill application if specified on command line.
    if do_windmill:
        settings.INSTALLED_APPS.append('windmill')
    settings.ROOT_URLCONF = 'urls'
    settings.TEMPLATE_DIRS = (os.path.join(os.path.dirname(__file__), TEST_TEMPLATE_DIR), )
    settings.USE_I18N = True
    settings.LANGUAGE_CODE = 'en'
    settings.LOGIN_URL = '/accounts/login/'
    settings.MIDDLEWARE_CLASSES = (
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        'django.middleware.common.CommonMiddleware',
        #Add the following 2 middleware so we can test them in Windmill.
        'django.contrib.flatpages.middleware.FlatpageFallbackMiddleware',
        'django.contrib.redirects.middleware.RedirectFallbackMiddleware',
    )
    settings.SITE_ID = 1
    # For testing comment-utils, we require the MANAGERS attribute
    # to be set, so that a test email is sent out which we catch
    # in our tests.
    settings.MANAGERS = ("admin@djangoproject.com", )

    # Load all the ALWAYS_INSTALLED_APPS.
    # (This import statement is intentionally delayed until after we
    # access settings because of the USE_I18N dependency.)
    from django.db.models.loading import get_apps, load_app
    get_apps()

    # Load all the test model apps.
    for model_dir, model_name in get_test_models():
        model_label = '.'.join([model_dir, model_name])
        try:
            # if the model was named on the command line, or
            # no models were named (i.e., run all), import
            # this model and add it to the list to test.
            if not test_labels or model_name in set([label.split('.')[0] for label in test_labels]):
                if verbosity >= 1:
                    print "Importing model %s" % model_name
                mod = load_app(model_label)
                if mod:
                    if model_label not in settings.INSTALLED_APPS:
                        settings.INSTALLED_APPS.append(model_label)
        except Exception, e:
            sys.stderr.write("Error while importing %s:" % model_name + ''.join(traceback.format_exception(*sys.exc_info())[1:]))
            continue

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
        settings.TEST_RUNNER = 'django.test.simple.run_tests'
    #establish coverage settings for the regression suite
    settings.COVERAGE_MODULE_EXCLUDES = ['modeltests*', 'regressiontests*']
    settings.COVERAGE_CODE_EXCLUDES = ['def __unicode__\(self\):', 
                                        'def get_absolute_url\(self\):', 
                                        'from .* import .*',
                                        'import .*',
                                        'from *']
    # depending on how this is run, we might need to tell the coverage libraries to consider django.*
    settings.COVERAGE_ADDITIONAL_MODULES = ['django']

    # Default number of failures is 0
    failures = 0
    if do_windmill:
        # Our bank of windmill-specific imports. Only loaded when used.
        import types
        import logging
        import threading
        from windmill.conf import global_settings
        from windmill.authoring import setup_module, teardown_module
        from django.core.management.commands.test_windmill import ServerContainer, attempt_import
        from django.test.windmill_tests import WindmillDjangoUnitTest
        from django.db.models.loading import remove_model, get_app
    #Run the appropriate test runner based on command line params.
    if do_std:
        if do_coverage:
            test_runner = get_runner(settings, coverage=True, reports=True)
        else:
            test_runner = get_runner(settings, coverage=False, reports=False)
        #Check if this is an old-style testrunner, and behave accordingly.
        if(type(test_runner) == 'function'):
            failures = test_runner(test_labels, verbosity=verbosity, interactive=interactive, extra_tests=extra_tests)
        else:
            tr = test_runner()
            failures = tr.run_tests(test_labels, verbosity=verbosity, interactive=interactive, extra_tests=extra_tests)

    #Run windmill tests if --windmill parameter was passed.
    if do_windmill:
        # We don't want to try and parse models that we know are invalid.
        remove_model('invalid_models')

        # Determine which browser to run the tests in.
        if 'ie' == wm_browser:
            global_settings.START_IE = True
        elif 'safari' == wm_browser:
            global_settings.START_SAFARI = True
        elif 'chrome' == wm_browser:
            global_settings.START_CHROME = True
        else:
            global_settings.START_FIREFOX = True

            #
        # Find which of our INSTALLED_APPS have tests.
        tests = []
        for name in [app for app in settings.INSTALLED_APPS if not('invalid' in app)]:
            for suffix in ['tests', 'wmtests', 'windmilltests']:
                x = attempt_import(name, suffix)
                if x is not None:
                    print "Adding %s %s to tests" % (suffix, x, )
                    tests.append((suffix, x, ))

        # Collect the WindmillDjangoUnitTest from tests.py and any 'wmtests' or 'windmilltests' modules.
        wmfixs = []
        wmtests = []
        for (ttype, mod, ) in tests:
            if ttype == 'tests':
                for ucls in [getattr(mod, x) for x in dir(mod)
                             if (type(getattr(mod, x, None)) in (types.ClassType,
                                                               types.TypeType) ) and
                             issubclass(getattr(mod, x), WindmillDjangoUnitTest)
                             ]:
                    wmtests.append(ucls.test_dir)

            else:
                if mod.__file__.endswith('__init__.py') or mod.__file__.endswith('__init__.pyc'):
                    wmtests.append(os.path.join(*os.path.split(os.path.abspath(mod.__file__))[:-1]))
                else:
                    wmtests.append(os.path.abspath(mod.__file__))
            # Look for any attribute named fixtures and try to load it.
            if hasattr(mod, 'fixtures'):
                for fixture in getattr(mod, 'fixtures'):
                    wmfixs.append(fixture)
        
        # Create the threaded server.
        server_container = ServerContainer()
        # Set the server's 'fixtures' attribute so they can be loaded in-thread if using sqlite's memory backend.
        server_container.__setattr__('fixtures', wmfixs)
        # Start the server thread.
        started = server_container.start_test_server()
                # These 2 unit tests can't be used while running our admin. Explicitly remove.
        if 'regressiontests.bug8245' in settings.INSTALLED_APPS:
            settings.INSTALLED_APPS.remove('regressiontests.bug8245')
        if 'django.contrib.gis' in settings.INSTALLED_APPS:
            settings.INSTALLED_APPS.remove('django.contrib.gis')
            
        
        print 'Waiting for threaded server to come online.'
        started.wait()
        print 'DB Ready, Server online.'
        


        # Set the testing URL based on what available port we get.
        global_settings.TEST_URL = 'http://localhost:%d' % server_container.server_thread.port



        # Make sure we even need to run tests.
        if len(wmtests) is 0:
            print 'Sorry, no windmill tests found.'
        else:
            # Setup and run unittests.
            testtotals = {}
            x = logging.getLogger()
            x.setLevel(logging.DEBUG)
            from windmill.server.proxy import logger
            #from functest import bin
            #from functest import runner
            #runner.CLIRunner.final = classmethod(lambda self, totals: testtotals.update(totals))
            #import windmill
            #count = 0
            #print wmtests
            #for wmt in wmtests:
                #print wmt
                #print tests[count][1]
                #count = count + 1
            #count = 0
            bin = None
            runner = None
            setup_module(tests[0][1])
            for wmt in wmtests:
                print sys.argv
                sys.argv = [wmt,]
                print sys.argv
                for k in (k for k in sys.modules.keys() if k.startswith('functest')):
                    del(sys.modules[k])
                #dbin)
                #del(runner)
                import functest
                from functest import bin
                from functest import runner
                runner.CLIRunner.final = classmethod(lambda self, totals: testtotals.update(totals) )
                bin.cli()
                bin = None
                runner = None
                print sys.argv
                # import functest
                #                 functest.modules_passed = []
                #                 functest.modules_failed = []
                #                 from functest import frame
                #                 frame.totals = {'pass':0, 'fail':0, 'skip':0}
                #teardown_module(tests[count][1])
                #sleep(.5)
                #count = count + 1
                #setup_module(tests[count][1])
            teardown_module(tests[0][1])
            server_container.stop_test_server()
            # sys.argv = [wmtests[0],]
            #             bin.cli()
            
            if testtotals['fail'] is not 0:
                sleep(.5)
                sys.exit(1)
    # If there where failures then report them, but give the server thread .5 seconds.
    if failures:
        sleep(.5)
        sys.exit(failures)

    # Restore the old settings.
    settings.INSTALLED_APPS = old_installed_apps
    settings.ROOT_URLCONF = old_root_urlconf
    settings.TEMPLATE_DIRS = old_template_dirs
    settings.USE_I18N = old_use_i18n
    settings.LANGUAGE_CODE = old_language_code
    settings.LOGIN_URL = old_login_url
    settings.MIDDLEWARE_CLASSES = old_middleware_classes


if __name__ == "__main__":
    from optparse import OptionParser
    usage = "%prog [options] [model model model ...]"
    parser = OptionParser(usage=usage)
    parser.add_option('-v', '--verbosity', action='store', dest='verbosity', default='0',
        type='choice', choices=['0', '1', '2'],
        help='Verbosity level; 0=minimal output, 1=normal output, 2=all output')
    parser.add_option('--noinput', action='store_false', dest='interactive', default=True,
        help='Tells Django to NOT prompt the user for input of any kind.')
    parser.add_option('--windmill', action='store_true', dest='windmill', default=False,
            help='Tells Django to run the Windmill functional tests as well.')
    parser.add_option('--coverage', action='store_true', dest='coverage', default=False,
            help='Tells Django to run the tests with code coverage as well.')
    parser.add_option('--nostd', action='store_false', dest='standard', default=True,
            help='Tells Django to not run the standard regression suite.')
    parser.add_option('--settings',
        help='Python path to settings module, e.g. "myproject.settings". If this isn\'t provided, the DJANGO_SETTINGS_MODULE environment variable will be used.')
    parser.add_option('--wmbrowser',
            help='The browser for windmill to run its tests in.',
            default='firefox', action='store', dest='wmbrowser', type='choice',
            choices=['firefox', 'chrome', 'safari', 'ie'])
    options, args = parser.parse_args()
    if options.settings:
        os.environ['DJANGO_SETTINGS_MODULE'] = options.settings
    elif "DJANGO_SETTINGS_MODULE" not in os.environ:
        parser.error("DJANGO_SETTINGS_MODULE is not set in the environment. "
                      "Set it or use --settings.")
    do_windmill = options.windmill
    do_coverage = options.coverage
    do_std = options.standard
    wm_browser = options.wmbrowser
    django_tests(int(options.verbosity), options.interactive, args)

