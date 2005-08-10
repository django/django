#!/usr/bin/env python

import os, sys, time, traceback

# doctest is included in the same package as this module, because this testing
# framework uses features only available in the Python 2.4 version of doctest,
# and Django aims to work with Python 2.3+.
import doctest

APP_NAME = 'testapp'
OTHER_TESTS_DIR = "othertests"
TEST_DATABASE_NAME = 'django_test_db'

error_list = []
def log_error(model_name, title, description):
    error_list.append({
        'title': "%r module: %s" % (model_name, title),
        'description': description,
    })

MODEL_DIR = os.path.join(os.path.dirname(__file__), APP_NAME, 'models')

def get_test_models():
    return [f[:-3] for f in os.listdir(MODEL_DIR) if f.endswith('.py') and not f.startswith('__init__')]

class DjangoDoctestRunner(doctest.DocTestRunner):
    def __init__(self, verbosity_level, *args, **kwargs):
        self.verbosity_level = verbosity_level
        doctest.DocTestRunner.__init__(self, *args, **kwargs)
        self._checker = DjangoDoctestOutputChecker()

    def report_start(self, out, test, example):
        if self.verbosity_level > 1:
            out("  >>> %s\n" % example.source.strip())

    def report_failure(self, out, test, example, got):
        log_error(test.name, "API test failed",
            "Code: %r\nLine: %s\nExpected: %r\nGot: %r" % (example.source.strip(), example.lineno, example.want, got))

    def report_unexpected_exception(self, out, test, example, exc_info):
        tb = ''.join(traceback.format_exception(*exc_info)[1:])
        log_error(test.name, "API test raised an exception",
            "Code: %r\nLine: %s\nException: %s" % (example.source.strip(), example.lineno, tb))
            
class DjangoDoctestOutputChecker(doctest.OutputChecker):
    def check_output(self, want, got, optionflags):
        ok = doctest.OutputChecker.check_output(self, want, got, optionflags)
        if not ok and (want.strip().endswith("L") or got.strip().endswith("L")):
            try:
                return long(want.strip()) == long(got.strip())
            except ValueError:
                return False
        return ok

class TestRunner:
    def __init__(self, verbosity_level=0):
        self.verbosity_level = verbosity_level

    def output(self, required_level, message):
        if self.verbosity_level > required_level - 1:
            print message

    def run_tests(self):
        from django.conf import settings
        from django.core.db import db
        from django.core import management, meta

        self.output(0, "Running tests with database %r" % settings.DATABASE_ENGINE)

        # Manually set INSTALLED_APPS to point to the test app.
        settings.INSTALLED_APPS = (APP_NAME,)

        # If we're using SQLite, it's more convenient to test against an
        # in-memory database.
        if settings.DATABASE_ENGINE == "sqlite3":
            global TEST_DATABASE_NAME
            TEST_DATABASE_NAME = ":memory:"
        else:
            # Create the test database and connect to it. We need autocommit()
            # because PostgreSQL doesn't allow CREATE DATABASE statements
            # within transactions.
            cursor = db.cursor()
            try:
                db.connection.autocommit()
            except AttributeError:
                pass
            self.output(1, "Creating test database")
            try:
                cursor.execute("CREATE DATABASE %s" % TEST_DATABASE_NAME)
            except:
                confirm = raw_input("The test database, %s, already exists. Type 'yes' to delete it, or 'no' to cancel: " % TEST_DATABASE_NAME)
                if confirm == 'yes':
                    cursor.execute("DROP DATABASE %s" % TEST_DATABASE_NAME)
                    cursor.execute("CREATE DATABASE %s" % TEST_DATABASE_NAME)
                else:
                    print "Tests cancelled."
                    return
        db.close()
        old_database_name = settings.DATABASE_NAME
        settings.DATABASE_NAME = TEST_DATABASE_NAME

        # Initialize the test database.
        cursor = db.cursor()
        self.output(1, "Initializing test database")
        management.init()

        # Run the tests for each test model.
        self.output(1, "Running app tests")
        for model_name in get_test_models():
            self.output(1, "%s model: Importing" % model_name)
            try:
                mod = meta.get_app(model_name)
            except Exception, e:
                log_error(model_name, "Error while importing", ''.join(traceback.format_exception(*sys.exc_info())[1:]))
                continue
            self.output(1, "%s model: Installing" % model_name)
            management.install(mod)

            # Run the API tests.
            p = doctest.DocTestParser()
            test_namespace = dict([(m._meta.module_name, getattr(mod, m._meta.module_name)) for m in mod._MODELS])
            dtest = p.get_doctest(mod.API_TESTS, test_namespace, model_name, None, None)
            # Manually set verbose=False, because "-v" command-line parameter
            # has side effects on doctest TestRunner class.
            runner = DjangoDoctestRunner(verbosity_level=verbosity_level, verbose=False)
            self.output(1, "%s model: Running tests" % model_name)
            try:
                runner.run(dtest, clear_globs=True, out=sys.stdout.write)
            finally:
                # Rollback, in case of database errors. Otherwise they'd have
                # side effects on other tests.
                db.rollback()

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
                self.output(1, "%s module: runing tests" % module)
                runner.run(dtest, clear_globs=True, out=sys.stdout.write)
            if hasattr(mod, "run_tests") and callable(mod.run_tests):
                self.output(1, "%s module: runing tests" % module)
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
            db.close()
            settings.DATABASE_NAME = old_database_name
            cursor = db.cursor()
            self.output(1, "Deleting test database")
            try:
                db.connection.autocommit()
            except AttributeError:
                pass
            else:
                time.sleep(1) # To avoid "database is being accessed by other users" errors.
            cursor.execute("DROP DATABASE %s" % TEST_DATABASE_NAME)

        # Display output.
        if error_list:
            print "Got %s error%s:" % (len(error_list), len(error_list) != 1 and 's' or '')
            for d in error_list:
                print
                print d['title']
                print "=" * len(d['title'])
                print d['description']
        else:
            print "All tests passed."

if __name__ == "__main__":
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option('-v', help='How verbose should the output be? Choices are 0, 1 and 2, where 2 is most verbose. Default is 0.',
        type='choice', choices=['0', '1', '2'])
    parser.add_option('--settings',
        help='Python path to settings module, e.g. "myproject.settings.main". If this isn\'t provided, the DJANGO_SETTINGS_MODULE environment variable will be used.')
    options, args = parser.parse_args()
    verbosity_level = 0
    if options.v:
        verbosity_level = int(options.v)
    if options.settings:
        os.environ['DJANGO_SETTINGS_MODULE'] = options.settings
    t = TestRunner(verbosity_level)
    t.run_tests()
