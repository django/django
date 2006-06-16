#!/usr/bin/env python

import os, re, sys, time, traceback

# doctest is included in the same package as this module, because this testing
# framework uses features only available in the Python 2.4 version of doctest,
# and Django aims to work with Python 2.3+.
import doctest

MODEL_TESTS_DIR_NAME = 'modeltests'
OTHER_TESTS_DIR = "othertests"
TEST_DATABASE_NAME = 'django_test_db'

error_list = []
def log_error(model_name, title, description):
    error_list.append({
        'title': "%r module: %s" % (model_name, title),
        'description': description,
    })

MODEL_TEST_DIR = os.path.join(os.path.dirname(__file__), MODEL_TESTS_DIR_NAME)

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
    return [f for f in os.listdir(MODEL_TEST_DIR) if not f.startswith('__init__') and not f.startswith('.')]

class DjangoDoctestRunner(doctest.DocTestRunner):
    def __init__(self, verbosity_level, *args, **kwargs):
        self.verbosity_level = verbosity_level
        doctest.DocTestRunner.__init__(self, *args, **kwargs)
        self._checker = DjangoDoctestOutputChecker()
        self.optionflags = doctest.ELLIPSIS

    def report_start(self, out, test, example):
        if self.verbosity_level > 1:
            out("  >>> %s\n" % example.source.strip())

    def report_failure(self, out, test, example, got):
        log_error(test.name, "API test failed",
            "Code: %r\nLine: %s\nExpected: %r\nGot: %r" % (example.source.strip(), example.lineno, example.want, got))

    def report_unexpected_exception(self, out, test, example, exc_info):
        from django.db import transaction
        tb = ''.join(traceback.format_exception(*exc_info)[1:])
        log_error(test.name, "API test raised an exception",
            "Code: %r\nLine: %s\nException: %s" % (example.source.strip(), example.lineno, tb))
        # Rollback, in case of database errors. Otherwise they'd have
        # side effects on other tests.
        transaction.rollback_unless_managed()

normalize_long_ints = lambda s: re.sub(r'(?<![\w])(\d+)L(?![\w])', '\\1', s)

class DjangoDoctestOutputChecker(doctest.OutputChecker):
    def check_output(self, want, got, optionflags):
        ok = doctest.OutputChecker.check_output(self, want, got, optionflags)

        # Doctest does an exact string comparison of output, which means long
        # integers aren't equal to normal integers ("22L" vs. "22"). The
        # following code normalizes long integers so that they equal normal
        # integers.
        if not ok:
            return normalize_long_ints(want) == normalize_long_ints(got)
        return ok

class TestRunner:
    def __init__(self, verbosity_level=0, which_tests=None):
        self.verbosity_level = verbosity_level
        self.which_tests = which_tests

    def output(self, required_level, message):
        if self.verbosity_level > required_level - 1:
            print message

    def run_tests(self):
        from django.conf import settings

        # An empty access of the settings to force the default options to be
        # installed prior to assigning to them.
        settings.INSTALLED_APPS

        # Manually set INSTALLED_APPS to point to the test models.
        settings.INSTALLED_APPS = ALWAYS_INSTALLED_APPS + [MODEL_TESTS_DIR_NAME + '.' + a for a in get_test_models()]

        # Manually set DEBUG = False.
        settings.DEBUG = False

        from django.db import connection
        from django.core import management
        import django.db.models

        # Determine which models we're going to test.
        test_models = get_test_models()
        if 'othertests' in self.which_tests:
            self.which_tests.remove('othertests')
            run_othertests = True
            if not self.which_tests:
                test_models = []
        else:
            run_othertests = not self.which_tests

        if self.which_tests:
            # Only run the specified tests.
            bad_models = [m for m in self.which_tests if m not in test_models]
            if bad_models:
                sys.stderr.write("Models not found: %s\n" % bad_models)
                sys.exit(1)
            else:
                test_models = self.which_tests

        self.output(0, "Running tests with database %r" % settings.DATABASE_ENGINE)

        # If we're using SQLite, it's more convenient to test against an
        # in-memory database.
        if settings.DATABASE_ENGINE == "sqlite3":
            global TEST_DATABASE_NAME
            TEST_DATABASE_NAME = ":memory:"
        else:
            # Create the test database and connect to it. We need to autocommit
            # if the database supports it because PostgreSQL doesn't allow 
            # CREATE/DROP DATABASE statements within transactions.
            cursor = connection.cursor()
            self._set_autocommit(connection)
            self.output(1, "Creating test database")
            try:
                cursor.execute("CREATE DATABASE %s" % TEST_DATABASE_NAME)
            except Exception, e:
                sys.stderr.write("Got an error creating the test database: %s\n" % e)
                confirm = raw_input("It appears the test database, %s, already exists. Type 'yes' to delete it, or 'no' to cancel: " % TEST_DATABASE_NAME)
                if confirm == 'yes':
                    cursor.execute("DROP DATABASE %s" % TEST_DATABASE_NAME)
                    cursor.execute("CREATE DATABASE %s" % TEST_DATABASE_NAME)
                else:
                    print "Tests cancelled."
                    return
        connection.close()
        old_database_name = settings.DATABASE_NAME
        settings.DATABASE_NAME = TEST_DATABASE_NAME

        # Initialize the test database.
        cursor = connection.cursor()
        
        # Install the core always installed apps
        for app in ALWAYS_INSTALLED_APPS:
            self.output(1, "Installing contrib app %s" % app)
            mod = __import__(app + ".models", '', '', [''])
            management.install(mod)

        # Run the tests for each test model.
        self.output(1, "Running app tests")
        for model_name in test_models:
            self.output(1, "%s model: Importing" % model_name)
            try:
                # TODO: Abstract this into a meta.get_app() replacement?
                mod = __import__(MODEL_TESTS_DIR_NAME + '.' + model_name + '.models', '', '', [''])
            except Exception, e:
                log_error(model_name, "Error while importing", ''.join(traceback.format_exception(*sys.exc_info())[1:]))
                continue

            if not getattr(mod, 'error_log', None):
                # Model is not marked as an invalid model
                self.output(1, "%s model: Installing" % model_name)
                management.install(mod)

                # Run the API tests.
                p = doctest.DocTestParser()
                test_namespace = dict([(m._meta.object_name, m) \
                                        for m in django.db.models.get_models(mod)])
                dtest = p.get_doctest(mod.API_TESTS, test_namespace, model_name, None, None)
                # Manually set verbose=False, because "-v" command-line parameter
                # has side effects on doctest TestRunner class.
                runner = DjangoDoctestRunner(verbosity_level=verbosity_level, verbose=False)
                self.output(1, "%s model: Running tests" % model_name)
                runner.run(dtest, clear_globs=True, out=sys.stdout.write)
            else:
                # Check that model known to be invalid is invalid for the right reasons.
                self.output(1, "%s model: Validating" % model_name)

                from cStringIO import StringIO
                s = StringIO()
                count = management.get_validation_errors(s, mod)
                s.seek(0)
                error_log = s.read()
                actual = error_log.split('\n')
                expected = mod.error_log.split('\n')

                unexpected = [err for err in actual if err not in expected]
                missing = [err for err in expected if err not in actual]

                if unexpected or missing:
                    unexpected_log = '\n'.join(unexpected)
                    missing_log = '\n'.join(missing)
                    log_error(model_name,
                        "Validator found %d validation errors, %d expected" % (count, len(expected) - 1),
                        "Missing errors:\n%s\n\nUnexpected errors:\n%s" % (missing_log, unexpected_log))

        if run_othertests:
            # Run the non-model tests in the other tests dir
            self.output(1, "Running other tests")
            other_tests_dir = os.path.join(os.path.dirname(__file__), OTHER_TESTS_DIR)
            test_modules = [f[:-3] for f in os.listdir(other_tests_dir) if f.endswith('.py') and not f.startswith('__init__')]
            for module in test_modules:
                self.output(1, "%s module: Importing" % module)
                try:
                    mod = __import__("othertests." + module, '', '', [''])
                except Exception, e:
                    log_error(module, "Error while importing", ''.join(traceback.format_exception(*sys.exc_info())[1:]))
                    continue
                if mod.__doc__:
                    p = doctest.DocTestParser()
                    dtest = p.get_doctest(mod.__doc__, mod.__dict__, module, None, None)
                    runner = DjangoDoctestRunner(verbosity_level=verbosity_level, verbose=False)
                    self.output(1, "%s module: running tests" % module)
                    runner.run(dtest, clear_globs=True, out=sys.stdout.write)
                if hasattr(mod, "run_tests") and callable(mod.run_tests):
                    self.output(1, "%s module: running tests" % module)
                    try:
                        mod.run_tests(verbosity_level)
                    except Exception, e:
                        log_error(module, "Exception running tests", ''.join(traceback.format_exception(*sys.exc_info())[1:]))
                        continue

        # Unless we're using SQLite, remove the test database to clean up after
        # ourselves. Connect to the previous database (not the test database)
        # to do so, because it's not allowed to delete a database while being
        # connected to it.
        if settings.DATABASE_ENGINE != "sqlite3":
            connection.close()
            settings.DATABASE_NAME = old_database_name
            cursor = connection.cursor()
            self.output(1, "Deleting test database")
            self._set_autocommit(connection)
            time.sleep(1) # To avoid "database is being accessed by other users" errors.
            cursor.execute("DROP DATABASE %s" % TEST_DATABASE_NAME)

        # Display output.
        if error_list:
            for d in error_list:
                print
                print d['title']
                print "=" * len(d['title'])
                print d['description']
            print "%s error%s:" % (len(error_list), len(error_list) != 1 and 's' or '')
        else:
            print "All tests passed."
            
    def _set_autocommit(self, connection):
        """
        Make sure a connection is in autocommit mode.
        """
        if hasattr(connection.connection, "autocommit"):
            connection.connection.autocommit(True)
        elif hasattr(connection.connection, "set_isolation_level"):
            connection.connection.set_isolation_level(0)

if __name__ == "__main__":
    from optparse import OptionParser
    usage = "%prog [options] [model model model ...]"
    parser = OptionParser(usage=usage)
    parser.add_option('-v', help='How verbose should the output be? Choices are 0, 1 and 2, where 2 is most verbose. Default is 0.',
        type='choice', choices=['0', '1', '2'])
    parser.add_option('--settings',
        help='Python path to settings module, e.g. "myproject.settings". If this isn\'t provided, the DJANGO_SETTINGS_MODULE environment variable will be used.')
    options, args = parser.parse_args()
    verbosity_level = 0
    if options.v:
        verbosity_level = int(options.v)
    if options.settings:
        os.environ['DJANGO_SETTINGS_MODULE'] = options.settings
    t = TestRunner(verbosity_level, args)
    t.run_tests()
