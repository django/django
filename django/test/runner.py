import ctypes
import faulthandler
import io
import itertools
import logging
import multiprocessing
import os
import pickle
import sys
import textwrap
import unittest
from importlib import import_module
from io import StringIO

from django.core.management import call_command
from django.db import connections
from django.test import SimpleTestCase, TestCase
from django.test.utils import (
    NullTimeKeeper, TimeKeeper, setup_databases as _setup_databases,
    setup_test_environment, teardown_databases as _teardown_databases,
    teardown_test_environment,
)
from django.utils.datastructures import OrderedSet
from django.utils.version import PY37

try:
    import ipdb as pdb
except ImportError:
    import pdb

try:
    import tblib.pickling_support
except ImportError:
    tblib = None


class DebugSQLTextTestResult(unittest.TextTestResult):
    def __init__(self, stream, descriptions, verbosity):
        self.logger = logging.getLogger('django.db.backends')
        self.logger.setLevel(logging.DEBUG)
        self.debug_sql_stream = None
        super().__init__(stream, descriptions, verbosity)

    def startTest(self, test):
        self.debug_sql_stream = StringIO()
        self.handler = logging.StreamHandler(self.debug_sql_stream)
        self.logger.addHandler(self.handler)
        super().startTest(test)

    def stopTest(self, test):
        super().stopTest(test)
        self.logger.removeHandler(self.handler)
        if self.showAll:
            self.debug_sql_stream.seek(0)
            self.stream.write(self.debug_sql_stream.read())
            self.stream.writeln(self.separator2)

    def addError(self, test, err):
        super().addError(test, err)
        if self.debug_sql_stream is None:
            # Error before tests e.g. in setUpTestData().
            sql = ''
        else:
            self.debug_sql_stream.seek(0)
            sql = self.debug_sql_stream.read()
        self.errors[-1] = self.errors[-1] + (sql,)

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.debug_sql_stream.seek(0)
        self.failures[-1] = self.failures[-1] + (self.debug_sql_stream.read(),)

    def addSubTest(self, test, subtest, err):
        super().addSubTest(test, subtest, err)
        if err is not None:
            self.debug_sql_stream.seek(0)
            errors = self.failures if issubclass(err[0], test.failureException) else self.errors
            errors[-1] = errors[-1] + (self.debug_sql_stream.read(),)

    def printErrorList(self, flavour, errors):
        for test, err, sql_debug in errors:
            self.stream.writeln(self.separator1)
            self.stream.writeln("%s: %s" % (flavour, self.getDescription(test)))
            self.stream.writeln(self.separator2)
            self.stream.writeln(err)
            self.stream.writeln(self.separator2)
            self.stream.writeln(sql_debug)


class PDBDebugResult(unittest.TextTestResult):
    """
    Custom result class that triggers a PDB session when an error or failure
    occurs.
    """

    def addError(self, test, err):
        super().addError(test, err)
        self.debug(err)

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.debug(err)

    def debug(self, error):
        self._restoreStdout()
        self.buffer = False
        exc_type, exc_value, traceback = error
        print("\nOpening PDB: %r" % exc_value)
        pdb.post_mortem(traceback)


class RemoteTestResult:
    """
    Record information about which tests have succeeded and which have failed.

    The sole purpose of this class is to record events in the child processes
    so they can be replayed in the master process. As a consequence it doesn't
    inherit unittest.TestResult and doesn't attempt to implement all its API.

    The implementation matches the unpythonic coding style of unittest2.
    """

    def __init__(self):
        if tblib is not None:
            tblib.pickling_support.install()

        self.events = []
        self.failfast = False
        self.shouldStop = False
        self.testsRun = 0

    @property
    def test_index(self):
        return self.testsRun - 1

    def _confirm_picklable(self, obj):
        """
        Confirm that obj can be pickled and unpickled as multiprocessing will
        need to pickle the exception in the child process and unpickle it in
        the parent process. Let the exception rise, if not.
        """
        pickle.loads(pickle.dumps(obj))

    def _print_unpicklable_subtest(self, test, subtest, pickle_exc):
        print("""
Subtest failed:

    test: {}
 subtest: {}

Unfortunately, the subtest that failed cannot be pickled, so the parallel
test runner cannot handle it cleanly. Here is the pickling error:

> {}

You should re-run this test with --parallel=1 to reproduce the failure
with a cleaner failure message.
""".format(test, subtest, pickle_exc))

    def check_picklable(self, test, err):
        # Ensure that sys.exc_info() tuples are picklable. This displays a
        # clear multiprocessing.pool.RemoteTraceback generated in the child
        # process instead of a multiprocessing.pool.MaybeEncodingError, making
        # the root cause easier to figure out for users who aren't familiar
        # with the multiprocessing module. Since we're in a forked process,
        # our best chance to communicate with them is to print to stdout.
        try:
            self._confirm_picklable(err)
        except Exception as exc:
            original_exc_txt = repr(err[1])
            original_exc_txt = textwrap.fill(original_exc_txt, 75, initial_indent='    ', subsequent_indent='    ')
            pickle_exc_txt = repr(exc)
            pickle_exc_txt = textwrap.fill(pickle_exc_txt, 75, initial_indent='    ', subsequent_indent='    ')
            if tblib is None:
                print("""

{} failed:

{}

Unfortunately, tracebacks cannot be pickled, making it impossible for the
parallel test runner to handle this exception cleanly.

In order to see the traceback, you should install tblib:

    python -m pip install tblib
""".format(test, original_exc_txt))
            else:
                print("""

{} failed:

{}

Unfortunately, the exception it raised cannot be pickled, making it impossible
for the parallel test runner to handle it cleanly.

Here's the error encountered while trying to pickle the exception:

{}

You should re-run this test with the --parallel=1 option to reproduce the
failure and get a correct traceback.
""".format(test, original_exc_txt, pickle_exc_txt))
            raise

    def check_subtest_picklable(self, test, subtest):
        try:
            self._confirm_picklable(subtest)
        except Exception as exc:
            self._print_unpicklable_subtest(test, subtest, exc)
            raise

    def stop_if_failfast(self):
        if self.failfast:
            self.stop()

    def stop(self):
        self.shouldStop = True

    def startTestRun(self):
        self.events.append(('startTestRun',))

    def stopTestRun(self):
        self.events.append(('stopTestRun',))

    def startTest(self, test):
        self.testsRun += 1
        self.events.append(('startTest', self.test_index))

    def stopTest(self, test):
        self.events.append(('stopTest', self.test_index))

    def addError(self, test, err):
        self.check_picklable(test, err)
        self.events.append(('addError', self.test_index, err))
        self.stop_if_failfast()

    def addFailure(self, test, err):
        self.check_picklable(test, err)
        self.events.append(('addFailure', self.test_index, err))
        self.stop_if_failfast()

    def addSubTest(self, test, subtest, err):
        # Follow Python 3.5's implementation of unittest.TestResult.addSubTest()
        # by not doing anything when a subtest is successful.
        if err is not None:
            # Call check_picklable() before check_subtest_picklable() since
            # check_picklable() performs the tblib check.
            self.check_picklable(test, err)
            self.check_subtest_picklable(test, subtest)
            self.events.append(('addSubTest', self.test_index, subtest, err))
            self.stop_if_failfast()

    def addSuccess(self, test):
        self.events.append(('addSuccess', self.test_index))

    def addSkip(self, test, reason):
        self.events.append(('addSkip', self.test_index, reason))

    def addExpectedFailure(self, test, err):
        # If tblib isn't installed, pickling the traceback will always fail.
        # However we don't want tblib to be required for running the tests
        # when they pass or fail as expected. Drop the traceback when an
        # expected failure occurs.
        if tblib is None:
            err = err[0], err[1], None
        self.check_picklable(test, err)
        self.events.append(('addExpectedFailure', self.test_index, err))

    def addUnexpectedSuccess(self, test):
        self.events.append(('addUnexpectedSuccess', self.test_index))
        self.stop_if_failfast()


class RemoteTestRunner:
    """
    Run tests and record everything but don't display anything.

    The implementation matches the unpythonic coding style of unittest2.
    """

    resultclass = RemoteTestResult

    def __init__(self, failfast=False, resultclass=None):
        self.failfast = failfast
        if resultclass is not None:
            self.resultclass = resultclass

    def run(self, test):
        result = self.resultclass()
        unittest.registerResult(result)
        result.failfast = self.failfast
        test(result)
        return result


def default_test_processes():
    """Default number of test processes when using the --parallel option."""
    # The current implementation of the parallel test runner requires
    # multiprocessing to start subprocesses with fork().
    if multiprocessing.get_start_method() != 'fork':
        return 1
    try:
        return int(os.environ['DJANGO_TEST_PROCESSES'])
    except KeyError:
        return multiprocessing.cpu_count()


_worker_id = 0


def _init_worker(counter):
    """
    Switch to databases dedicated to this worker.

    This helper lives at module-level because of the multiprocessing module's
    requirements.
    """

    global _worker_id

    with counter.get_lock():
        counter.value += 1
        _worker_id = counter.value

    for alias in connections:
        connection = connections[alias]
        settings_dict = connection.creation.get_test_db_clone_settings(str(_worker_id))
        # connection.settings_dict must be updated in place for changes to be
        # reflected in django.db.connections. If the following line assigned
        # connection.settings_dict = settings_dict, new threads would connect
        # to the default database instead of the appropriate clone.
        connection.settings_dict.update(settings_dict)
        connection.close()


def _run_subsuite(args):
    """
    Run a suite of tests with a RemoteTestRunner and return a RemoteTestResult.

    This helper lives at module-level and its arguments are wrapped in a tuple
    because of the multiprocessing module's requirements.
    """
    runner_class, subsuite_index, subsuite, failfast = args
    runner = runner_class(failfast=failfast)
    result = runner.run(subsuite)
    return subsuite_index, result.events


class ParallelTestSuite(unittest.TestSuite):
    """
    Run a series of tests in parallel in several processes.

    While the unittest module's documentation implies that orchestrating the
    execution of tests is the responsibility of the test runner, in practice,
    it appears that TestRunner classes are more concerned with formatting and
    displaying test results.

    Since there are fewer use cases for customizing TestSuite than TestRunner,
    implementing parallelization at the level of the TestSuite improves
    interoperability with existing custom test runners. A single instance of a
    test runner can still collect results from all tests without being aware
    that they have been run in parallel.
    """

    # In case someone wants to modify these in a subclass.
    init_worker = _init_worker
    run_subsuite = _run_subsuite
    runner_class = RemoteTestRunner

    def __init__(self, suite, processes, failfast=False):
        self.subsuites = partition_suite_by_case(suite)
        self.processes = processes
        self.failfast = failfast
        super().__init__()

    def run(self, result):
        """
        Distribute test cases across workers.

        Return an identifier of each test case with its result in order to use
        imap_unordered to show results as soon as they're available.

        To minimize pickling errors when getting results from workers:

        - pass back numeric indexes in self.subsuites instead of tests
        - make tracebacks picklable with tblib, if available

        Even with tblib, errors may still occur for dynamically created
        exception classes which cannot be unpickled.
        """
        counter = multiprocessing.Value(ctypes.c_int, 0)
        pool = multiprocessing.Pool(
            processes=self.processes,
            initializer=self.init_worker.__func__,
            initargs=[counter],
        )
        args = [
            (self.runner_class, index, subsuite, self.failfast)
            for index, subsuite in enumerate(self.subsuites)
        ]
        test_results = pool.imap_unordered(self.run_subsuite.__func__, args)

        while True:
            if result.shouldStop:
                pool.terminate()
                break

            try:
                subsuite_index, events = test_results.next(timeout=0.1)
            except multiprocessing.TimeoutError:
                continue
            except StopIteration:
                pool.close()
                break

            tests = list(self.subsuites[subsuite_index])
            for event in events:
                event_name = event[0]
                handler = getattr(result, event_name, None)
                if handler is None:
                    continue
                test = tests[event[1]]
                args = event[2:]
                handler(test, *args)

        pool.join()

        return result

    def __iter__(self):
        return iter(self.subsuites)


class DiscoverRunner:
    """A Django test runner that uses unittest2 test discovery."""

    test_suite = unittest.TestSuite
    parallel_test_suite = ParallelTestSuite
    test_runner = unittest.TextTestRunner
    test_loader = unittest.defaultTestLoader
    reorder_by = (TestCase, SimpleTestCase)

    def __init__(self, pattern=None, top_level=None, verbosity=1,
                 interactive=True, failfast=False, keepdb=False,
                 reverse=False, debug_mode=False, debug_sql=False, parallel=0,
                 tags=None, exclude_tags=None, test_name_patterns=None,
                 pdb=False, buffer=False, enable_faulthandler=True,
                 timing=False, **kwargs):

        self.pattern = pattern
        self.top_level = top_level
        self.verbosity = verbosity
        self.interactive = interactive
        self.failfast = failfast
        self.keepdb = keepdb
        self.reverse = reverse
        self.debug_mode = debug_mode
        self.debug_sql = debug_sql
        self.parallel = parallel
        self.tags = set(tags or [])
        self.exclude_tags = set(exclude_tags or [])
        if not faulthandler.is_enabled() and enable_faulthandler:
            try:
                faulthandler.enable(file=sys.stderr.fileno())
            except (AttributeError, io.UnsupportedOperation):
                faulthandler.enable(file=sys.__stderr__.fileno())
        self.pdb = pdb
        if self.pdb and self.parallel > 1:
            raise ValueError('You cannot use --pdb with parallel tests; pass --parallel=1 to use it.')
        self.buffer = buffer
        if self.buffer and self.parallel > 1:
            raise ValueError(
                'You cannot use -b/--buffer with parallel tests; pass '
                '--parallel=1 to use it.'
            )
        self.test_name_patterns = None
        self.time_keeper = TimeKeeper() if timing else NullTimeKeeper()
        if test_name_patterns:
            # unittest does not export the _convert_select_pattern function
            # that converts command-line arguments to patterns.
            self.test_name_patterns = {
                pattern if '*' in pattern else '*%s*' % pattern
                for pattern in test_name_patterns
            }

    @classmethod
    def add_arguments(cls, parser):
        parser.add_argument(
            '-t', '--top-level-directory', dest='top_level',
            help='Top level of project for unittest discovery.',
        )
        parser.add_argument(
            '-p', '--pattern', default="test*.py",
            help='The test matching pattern. Defaults to test*.py.',
        )
        parser.add_argument(
            '--keepdb', action='store_true',
            help='Preserves the test DB between runs.'
        )
        parser.add_argument(
            '-r', '--reverse', action='store_true',
            help='Reverses test cases order.',
        )
        parser.add_argument(
            '--debug-mode', action='store_true',
            help='Sets settings.DEBUG to True.',
        )
        parser.add_argument(
            '-d', '--debug-sql', action='store_true',
            help='Prints logged SQL queries on failure.',
        )
        parser.add_argument(
            '--parallel', nargs='?', default=1, type=int,
            const=default_test_processes(), metavar='N',
            help='Run tests using up to N parallel processes.',
        )
        parser.add_argument(
            '--tag', action='append', dest='tags',
            help='Run only tests with the specified tag. Can be used multiple times.',
        )
        parser.add_argument(
            '--exclude-tag', action='append', dest='exclude_tags',
            help='Do not run tests with the specified tag. Can be used multiple times.',
        )
        parser.add_argument(
            '--pdb', action='store_true',
            help='Runs a debugger (pdb, or ipdb if installed) on error or failure.'
        )
        parser.add_argument(
            '-b', '--buffer', action='store_true',
            help='Discard output from passing tests.',
        )
        parser.add_argument(
            '--no-faulthandler', action='store_false', dest='enable_faulthandler',
            help='Disables the Python faulthandler module during tests.',
        )
        parser.add_argument(
            '--timing', action='store_true',
            help=(
                'Output timings, including database set up and total run time.'
            ),
        )
        if PY37:
            parser.add_argument(
                '-k', action='append', dest='test_name_patterns',
                help=(
                    'Only run test methods and classes that match the pattern '
                    'or substring. Can be used multiple times. Same as '
                    'unittest -k option.'
                ),
            )

    def setup_test_environment(self, **kwargs):
        setup_test_environment(debug=self.debug_mode)
        unittest.installHandler()

    def build_suite(self, test_labels=None, extra_tests=None, **kwargs):
        suite = self.test_suite()
        test_labels = test_labels or ['.']
        extra_tests = extra_tests or []
        self.test_loader.testNamePatterns = self.test_name_patterns

        discover_kwargs = {}
        if self.pattern is not None:
            discover_kwargs['pattern'] = self.pattern
        if self.top_level is not None:
            discover_kwargs['top_level_dir'] = self.top_level

        for label in test_labels:
            kwargs = discover_kwargs.copy()
            tests = None

            label_as_path = os.path.abspath(label)

            # if a module, or "module.ClassName[.method_name]", just run those
            if not os.path.exists(label_as_path):
                tests = self.test_loader.loadTestsFromName(label)
            elif os.path.isdir(label_as_path) and not self.top_level:
                # Try to be a bit smarter than unittest about finding the
                # default top-level for a given directory path, to avoid
                # breaking relative imports. (Unittest's default is to set
                # top-level equal to the path, which means relative imports
                # will result in "Attempted relative import in non-package.").

                # We'd be happy to skip this and require dotted module paths
                # (which don't cause this problem) instead of file paths (which
                # do), but in the case of a directory in the cwd, which would
                # be equally valid if considered as a top-level module or as a
                # directory path, unittest unfortunately prefers the latter.

                top_level = label_as_path
                while True:
                    init_py = os.path.join(top_level, '__init__.py')
                    if os.path.exists(init_py):
                        try_next = os.path.dirname(top_level)
                        if try_next == top_level:
                            # __init__.py all the way down? give up.
                            break
                        top_level = try_next
                        continue
                    break
                kwargs['top_level_dir'] = top_level

            if not (tests and tests.countTestCases()) and is_discoverable(label):
                # Try discovery if path is a package or directory
                tests = self.test_loader.discover(start_dir=label, **kwargs)

                # Make unittest forget the top-level dir it calculated from this
                # run, to support running tests from two different top-levels.
                self.test_loader._top_level_dir = None

            suite.addTests(tests)

        for test in extra_tests:
            suite.addTest(test)

        if self.tags or self.exclude_tags:
            if self.verbosity >= 2:
                if self.tags:
                    print('Including test tag(s): %s.' % ', '.join(sorted(self.tags)))
                if self.exclude_tags:
                    print('Excluding test tag(s): %s.' % ', '.join(sorted(self.exclude_tags)))
            suite = filter_tests_by_tags(suite, self.tags, self.exclude_tags)
        suite = reorder_suite(suite, self.reorder_by, self.reverse)

        if self.parallel > 1:
            parallel_suite = self.parallel_test_suite(suite, self.parallel, self.failfast)

            # Since tests are distributed across processes on a per-TestCase
            # basis, there's no need for more processes than TestCases.
            parallel_units = len(parallel_suite.subsuites)
            self.parallel = min(self.parallel, parallel_units)

            # If there's only one TestCase, parallelization isn't needed.
            if self.parallel > 1:
                suite = parallel_suite

        return suite

    def setup_databases(self, **kwargs):
        return _setup_databases(
            self.verbosity, self.interactive, time_keeper=self.time_keeper, keepdb=self.keepdb,
            debug_sql=self.debug_sql, parallel=self.parallel, **kwargs
        )

    def get_resultclass(self):
        if self.debug_sql:
            return DebugSQLTextTestResult
        elif self.pdb:
            return PDBDebugResult

    def get_test_runner_kwargs(self):
        return {
            'failfast': self.failfast,
            'resultclass': self.get_resultclass(),
            'verbosity': self.verbosity,
            'buffer': self.buffer,
        }

    def run_checks(self, databases):
        # Checks are run after database creation since some checks require
        # database access.
        call_command('check', verbosity=self.verbosity, databases=databases)

    def run_suite(self, suite, **kwargs):
        kwargs = self.get_test_runner_kwargs()
        runner = self.test_runner(**kwargs)
        return runner.run(suite)

    def teardown_databases(self, old_config, **kwargs):
        """Destroy all the non-mirror databases."""
        _teardown_databases(
            old_config,
            verbosity=self.verbosity,
            parallel=self.parallel,
            keepdb=self.keepdb,
        )

    def teardown_test_environment(self, **kwargs):
        unittest.removeHandler()
        teardown_test_environment()

    def suite_result(self, suite, result, **kwargs):
        return len(result.failures) + len(result.errors)

    def _get_databases(self, suite):
        databases = set()
        for test in suite:
            if isinstance(test, unittest.TestCase):
                test_databases = getattr(test, 'databases', None)
                if test_databases == '__all__':
                    return set(connections)
                if test_databases:
                    databases.update(test_databases)
            else:
                databases.update(self._get_databases(test))
        return databases

    def get_databases(self, suite):
        databases = self._get_databases(suite)
        if self.verbosity >= 2:
            unused_databases = [alias for alias in connections if alias not in databases]
            if unused_databases:
                print('Skipping setup of unused database(s): %s.' % ', '.join(sorted(unused_databases)))
        return databases

    def run_tests(self, test_labels, extra_tests=None, **kwargs):
        """
        Run the unit tests for all the test labels in the provided list.

        Test labels should be dotted Python paths to test modules, test
        classes, or test methods.

        A list of 'extra' tests may also be provided; these tests
        will be added to the test suite.

        Return the number of tests that failed.
        """
        self.setup_test_environment()
        suite = self.build_suite(test_labels, extra_tests)
        databases = self.get_databases(suite)
        with self.time_keeper.timed('Total database setup'):
            old_config = self.setup_databases(aliases=databases)
        run_failed = False
        try:
            self.run_checks(databases)
            result = self.run_suite(suite)
        except Exception:
            run_failed = True
            raise
        finally:
            try:
                with self.time_keeper.timed('Total database teardown'):
                    self.teardown_databases(old_config)
                self.teardown_test_environment()
            except Exception:
                # Silence teardown exceptions if an exception was raised during
                # runs to avoid shadowing it.
                if not run_failed:
                    raise
        self.time_keeper.print_results()
        return self.suite_result(suite, result)


def is_discoverable(label):
    """
    Check if a test label points to a Python package or file directory.

    Relative labels like "." and ".." are seen as directories.
    """
    try:
        mod = import_module(label)
    except (ImportError, TypeError):
        pass
    else:
        return hasattr(mod, '__path__')

    return os.path.isdir(os.path.abspath(label))


def reorder_suite(suite, classes, reverse=False):
    """
    Reorder a test suite by test type.

    `classes` is a sequence of types

    All tests of type classes[0] are placed first, then tests of type
    classes[1], etc. Tests with no match in classes are placed last.

    If `reverse` is True, sort tests within classes in opposite order but
    don't reverse test classes.
    """
    class_count = len(classes)
    suite_class = type(suite)
    bins = [OrderedSet() for i in range(class_count + 1)]
    partition_suite_by_type(suite, classes, bins, reverse=reverse)
    reordered_suite = suite_class()
    for i in range(class_count + 1):
        reordered_suite.addTests(bins[i])
    return reordered_suite


def partition_suite_by_type(suite, classes, bins, reverse=False):
    """
    Partition a test suite by test type. Also prevent duplicated tests.

    classes is a sequence of types
    bins is a sequence of TestSuites, one more than classes
    reverse changes the ordering of tests within bins

    Tests of type classes[i] are added to bins[i],
    tests with no match found in classes are place in bins[-1]
    """
    suite_class = type(suite)
    if reverse:
        suite = reversed(tuple(suite))
    for test in suite:
        if isinstance(test, suite_class):
            partition_suite_by_type(test, classes, bins, reverse=reverse)
        else:
            for i in range(len(classes)):
                if isinstance(test, classes[i]):
                    bins[i].add(test)
                    break
            else:
                bins[-1].add(test)


def partition_suite_by_case(suite):
    """Partition a test suite by test case, preserving the order of tests."""
    groups = []
    suite_class = type(suite)
    for test_type, test_group in itertools.groupby(suite, type):
        if issubclass(test_type, unittest.TestCase):
            groups.append(suite_class(test_group))
        else:
            for item in test_group:
                groups.extend(partition_suite_by_case(item))
    return groups


def filter_tests_by_tags(suite, tags, exclude_tags):
    suite_class = type(suite)
    filtered_suite = suite_class()

    for test in suite:
        if isinstance(test, suite_class):
            filtered_suite.addTests(filter_tests_by_tags(test, tags, exclude_tags))
        else:
            test_tags = set(getattr(test, 'tags', set()))
            test_fn_name = getattr(test, '_testMethodName', str(test))
            test_fn = getattr(test, test_fn_name, test)
            test_fn_tags = set(getattr(test_fn, 'tags', set()))
            all_tags = test_tags.union(test_fn_tags)
            matched_tags = all_tags.intersection(tags)
            if (matched_tags or not tags) and not all_tags.intersection(exclude_tags):
                filtered_suite.addTest(test)

    return filtered_suite
