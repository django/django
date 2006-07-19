#!/usr/bin/env python

import os, re, sys, time, traceback

# doctest is included in the same package as this module, because this testing
# framework uses features only available in the Python 2.4 version of doctest,
# and Django aims to work with Python 2.3+.
import doctest

MODEL_TESTS_DIR_NAME = 'modeltests'
OTHER_TESTS_DIR = "othertests"
REGRESSION_TESTS_DIR_NAME = 'regressiontests'
TEST_DATABASE_NAME = 'django_test_db'
TEST_DATABASES = (TEST_DATABASE_NAME + '_a', TEST_DATABASE_NAME + '_b')

TEST_DATABASE_MODELS = {
    TEST_DATABASE_NAME + '_a': [ 'multiple_databases.Artist',
                                 'multiple_databases.Opus' ],
    TEST_DATABASE_NAME + '_b': [ 'multiple_databases.Widget',
                                 'multiple_databases.Doohickey' ]
}

error_list = []
def log_error(model_name, title, description):
    error_list.append({
        'title': "%r module: %s" % (model_name, title),
        'description': description,
    })

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
            if f.startswith('__init__') or f.startswith('.') or f.startswith('sql'):
                continue
            models.append((loc, f))
    return models

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
        self.created_dbs = []
        self.cleanup_files = []
        self.old_database_name = None
        self.old_databases = None
        self.sqlite_memory_db_used = False
        
    def output(self, required_level, message):
        if self.verbosity_level > required_level - 1:
            print message

    def create_test_db(self, db_name, connection):
        """Create a test db, returning a ConnectionInfo object holding
        a connection to that db.
        """
        from django.db import connect

        # settings may be a dict or settings object
        settings = connection.settings
        
        if settings.DATABASE_ENGINE != "sqlite3":
            # Create the test database and connect to it. We need to autocommit
            # if the database supports it because PostgreSQL doesn't allow
            # CREATE/DROP DATABASE statements within transactions.            
            cursor = connection.cursor()
            self._set_autocommit(connection)
            self.output(1, "Creating test database %s for %s" %
                        (db_name, settings.DATABASE_NAME))
            try:
                cursor.execute("CREATE DATABASE %s" % db_name)
            except Exception, e:
                sys.stderr.write("Got an error creating the test database: %s\n" % e)
                confirm = raw_input("It appears the test database, %s, already exists. Type 'yes' to delete it, or 'no' to cancel: " % db_name)
                if confirm == 'yes':
                    cursor.execute("DROP DATABASE %s" % db_name)
                    cursor.execute("CREATE DATABASE %s" % db_name)
                else:
                    raise Exception("Tests cancelled.")

        
        settings.DATABASE_NAME = db_name
        connection.close()

        # Initialize the test database.
        info = connect(settings)
        cursor = info.connection.cursor()
        self.created_dbs.append((db_name, info))
        return info

    def run_tests(self):
        self.setup()
        try:
            self._run_tests()
        finally:
            self.teardown()

    def setup(self):
        global TEST_DATABASE_NAME
        from django.conf import settings
        from django.db import connection, connections
        from django.core import management
        from django.db.models.loading import load_app
        
        # An empty access of the settings to force the default options to be
        # installed prior to assigning to them.
        settings.INSTALLED_APPS

        # Manually set INSTALLED_APPS to point to the test models.
        settings.INSTALLED_APPS = ALWAYS_INSTALLED_APPS + ['.'.join(a) for a in get_test_models()]

        # Manually set DEBUG and USE_I18N.
        settings.DEBUG = False
        settings.USE_I18N = True

        self.output(0, "Running tests with database %r" % settings.DATABASE_ENGINE)

        # Create test dbs for the default connection and two named connections,
        # replacing any named connections defined in settings. All connections
        # will use the default DATABASE_ENGINE
        self.old_database_name = settings.DATABASE_NAME
        self.old_databases = settings.OTHER_DATABASES

        if settings.DATABASE_ENGINE == 'sqlite3':
            # If we're using SQLite, it's more convenient to test against an
            # in-memory database. But we can only do this for the default; 
            # after that we have to use temp files. 
            TEST_DATABASE_NAME = ':memory:'
        
        new_databases = {}
        for db_name in TEST_DATABASES:
            db_st = settings.OTHER_DATABASES.setdefault(db_name, {})
            engine = db_st.get('DATABASE_ENGINE', settings.DATABASE_ENGINE)
            if engine == 'sqlite3':
                db_st['DATABASE_NAME'] = self._tempfile()
                self.cleanup_files.append(db_st['DATABASE_NAME'])
            else:
                db_st['DATABASE_NAME'] = db_name
            new_databases[db_name] = db_st
        settings.OTHER_DATABASES = new_databases

        self.create_test_db(TEST_DATABASE_NAME, connection)
        for name, info in settings.OTHER_DATABASES.items():
            cx = connections[name]
            test_connection = self.create_test_db(info['DATABASE_NAME'],
                                                  cx.connection)
            connections[name] = test_connection

        # Install the core always installed apps
        for app in ALWAYS_INSTALLED_APPS:
            self.output(1, "Installing contrib app %s" % app)
            mod = load_app(app)
            management.install(mod)

    def teardown(self):
        # Unless we're using SQLite, remove the test database to clean up after
        # ourselves. Connect to the previous database (not the test database)
        # to do so, because it's not allowed to delete a database while being
        # connected to it.
        from django.db import connection
        from django.conf import settings
        connection.close()
        settings.DATABASE_NAME = self.old_database_name
        settings.OTHER_DATABASES = self.old_databases
        for db_name, cx in self.created_dbs:
            settings = cx.settings
            cx.close()
            if settings.DATABASE_ENGINE != "sqlite3":
                cursor = connection.cursor()
                self.output(1, "Deleting test database %s" % db_name)
                self._set_autocommit(connection)
                time.sleep(1) # To avoid "database is being accessed by other users" errors.
                cursor.execute("DROP DATABASE %s" % db_name)

        # Clean up sqlite dbs created on the filesystem
        for filename in self.cleanup_files:
            if os.path.exists(filename):
                os.unlink(filename)

    def _run_tests(self):
        # Run the tests for each test model.
        from django.core import management
        from django.db.models.loading import load_app
        from django.db import models

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
            bad_models = [m for m in self.which_tests if (MODEL_TESTS_DIR_NAME, m) not in test_models and (REGRESSION_TESTS_DIR_NAME, m) not in test_models]
            if bad_models:
                sys.stderr.write("Models not found: %s\n" % bad_models)
                sys.exit(1)
            else:
                all_tests = []
                for test in self.which_tests:
                    for loc in MODEL_TESTS_DIR_NAME, REGRESSION_TESTS_DIR_NAME:
                        if (loc, test) in test_models:
                            all_tests.append((loc, test))
                test_models = all_tests

        self.output(1, "Running app tests")
        for model_dir, model_name in test_models:
            self.output(1, "%s model: Importing" % model_name)
            try:
                mod = load_app(model_dir + '.' + model_name)
            except Exception, e:
                log_error(model_name, "Error while importing", ''.join(traceback.format_exception(*sys.exc_info())[1:]))
                continue

            if not getattr(mod, 'error_log', None):
                # Model is not marked as an invalid model
                self.output(1, "%s.%s model: Installing" % (model_dir, model_name))
                management.install(mod)

                # Run the API tests.
                p = doctest.DocTestParser()
                test_namespace = dict([(m._meta.object_name, m) \
                                        for m in models.get_models(mod)])
                dtest = p.get_doctest(mod.API_TESTS, test_namespace, model_name, None, None)
                # Manually set verbose=False, because "-v" command-line parameter
                # has side effects on doctest TestRunner class.
                runner = DjangoDoctestRunner(verbosity_level=verbosity_level, verbose=False)
                self.output(1, "%s.%s model: Running tests" % (model_dir, model_name))
                runner.run(dtest, clear_globs=True, out=sys.stdout.write)
            else:
                # Check that model known to be invalid is invalid for the right reasons.
                self.output(1, "%s.%s model: Validating" % (model_dir, model_name))

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

    def _tempfile(self):
        import tempfile
        fd, filename = tempfile.mkstemp()
        os.close(fd)
        return filename

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
