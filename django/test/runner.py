import argparse
import ctypes
import faulthandler
import hashlib
import io
import itertools
import logging
import multiprocessing
import os
import pickle
import random
import sys
import textwrap
import unittest
import warnings
from collections import defaultdict
from contextlib import contextmanager
from importlib import import_module
from io import StringIO

from django.core.management import call_command
from django.db import connections
from django.test import SimpleTestCase, TestCase
from django.test.utils import (
    NullTimeKeeper, TimeKeeper, iter_test_cases,
    setup_databases as _setup_databases, setup_test_environment,
    teardown_databases as _teardown_databases, teardown_test_environment,
)
from django.utils.datastructures import OrderedSet
from django.utils.deprecation import RemovedInDjango50Warning

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

    def addSubTest(self, test, subtest, err):
        if err is not None:
            self.debug(err)
        super().addSubTest(test, subtest, err)

    def debug(self, error):
        self._restoreStdout()
        self.buffer = False
        exc_type, exc_value, traceback = error
        print("\nOpening PDB: %r" % exc_value)
        pdb.post_mortem(traceback)


class DummyList:
    """
    Dummy list class for faking storage of results in unittest.TestResult.
    """
    __slots__ = ()

    def append(self, item):
        pass


class RemoteTestResult(unittest.TestResult):
    """
    Extend unittest.TestResult to record events in the child processes so they
    can be replayed in the parent process. Events include things like which
    tests succeeded or failed.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Fake storage of results to reduce memory usage. These are used by the
        # unittest default methods, but here 'events' is used instead.
        dummy_list = DummyList()
        self.failures = dummy_list
        self.errors = dummy_list
        self.skipped = dummy_list
        self.expectedFailures = dummy_list
        self.unexpectedSuccesses = dummy_list

        if tblib is not None:
            tblib.pickling_support.install()
        self.events = []

    def __getstate__(self):
        # Make this class picklable by removing the file-like buffer
        # attributes. This is possible since they aren't used after unpickling
        # after being sent to ParallelTestSuite.
        state = self.__dict__.copy()
        state.pop('_stdout_buffer', None)
        state.pop('_stderr_buffer', None)
        state.pop('_original_stdout', None)
        state.pop('_original_stderr', None)
        return state

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

    def startTestRun(self):
        super().startTestRun()
        self.events.append(('startTestRun',))

    def stopTestRun(self):
        super().stopTestRun()
        self.events.append(('stopTestRun',))

    def startTest(self, test):
        super().startTest(test)
        self.events.append(('startTest', self.test_index))

    def stopTest(self, test):
        super().stopTest(test)
        self.events.append(('stopTest', self.test_index))

    def addError(self, test, err):
        self.check_picklable(test, err)
        self.events.append(('addError', self.test_index, err))
        super().addError(test, err)

    def addFailure(self, test, err):
        self.check_picklable(test, err)
        self.events.append(('addFailure', self.test_index, err))
        super().addFailure(test, err)

    def addSubTest(self, test, subtest, err):
        # Follow Python's implementation of unittest.TestResult.addSubTest() by
        # not doing anything when a subtest is successful.
        if err is not None:
            # Call check_picklable() before check_subtest_picklable() since
            # check_picklable() performs the tblib check.
            self.check_picklable(test, err)
            self.check_subtest_picklable(test, subtest)
            self.events.append(('addSubTest', self.test_index, subtest, err))
        super().addSubTest(test, subtest, err)

    def addSuccess(self, test):
        self.events.append(('addSuccess', self.test_index))
        super().addSuccess(test)

    def addSkip(self, test, reason):
        self.events.append(('addSkip', self.test_index, reason))
        super().addSkip(test, reason)

    def addExpectedFailure(self, test, err):
        # If tblib isn't installed, pickling the traceback will always fail.
        # However we don't want tblib to be required for running the tests
        # when they pass or fail as expected. Drop the traceback when an
        # expected failure occurs.
        if tblib is None:
            err = err[0], err[1], None
        self.check_picklable(test, err)
        self.events.append(('addExpectedFailure', self.test_index, err))
        super().addExpectedFailure(test, err)

    def addUnexpectedSuccess(self, test):
        self.events.append(('addUnexpectedSuccess', self.test_index))
        super().addUnexpectedSuccess(test)

    def wasSuccessful(self):
        """Tells whether or not this result was a success."""
        failure_types = {'addError', 'addFailure', 'addSubTest', 'addUnexpectedSuccess'}
        return all(e[0] not in failure_types for e in self.events)

    def _exc_info_to_string(self, err, test):
        # Make this method no-op. It only powers the default unittest behavior
        # for recording errors, but this class pickles errors into 'events'
        # instead.
        return ''


class RemoteTestRunner:
    """
    Run tests and record everything but don't display anything.

    The implementation matches the unpythonic coding style of unittest2.
    """

    resultclass = RemoteTestResult

    def __init__(self, failfast=False, resultclass=None, buffer=False):
        self.failfast = failfast
        self.buffer = buffer
        if resultclass is not None:
            self.resultclass = resultclass

    def run(self, test):
        result = self.resultclass()
        unittest.registerResult(result)
        result.failfast = self.failfast
        result.buffer = self.buffer
        test(result)
        return result


def get_max_test_processes():
    """
    The maximum number of test processes when using the --parallel option.
    """
    # The current implementation of the parallel test runner requires
    # multiprocessing to start subprocesses with fork().
    if multiprocessing.get_start_method() != 'fork':
        return 1
    try:
        return int(os.environ['DJANGO_TEST_PROCESSES'])
    except KeyError:
        return multiprocessing.cpu_count()


def parallel_type(value):
    """Parse value passed to the --parallel option."""
    if value == 'auto':
        return value
    try:
        return int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"{value!r} is not an integer or the string 'auto'"
        )


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
    runner_class, subsuite_index, subsuite, failfast, buffer = args
    runner = runner_class(failfast=failfast, buffer=buffer)
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

    def __init__(self, subsuites, processes, failfast=False, buffer=False):
        self.subsuites = subsuites
        self.processes = processes
        self.failfast = failfast
        self.buffer = buffer
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
            (self.runner_class, index, subsuite, self.failfast, self.buffer)
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


class Shuffler:
    """
    This class implements shuffling with a special consistency property.
    Consistency means that, for a given seed and key function, if two sets of
    items are shuffled, the resulting order will agree on the intersection of
    the two sets. For example, if items are removed from an original set, the
    shuffled order for the new set will be the shuffled order of the original
    set restricted to the smaller set.
    """

    # This doesn't need to be cryptographically strong, so use what's fastest.
    hash_algorithm = 'md5'

    @classmethod
    def _hash_text(cls, text):
        h = hashlib.new(cls.hash_algorithm)
        h.update(text.encode('utf-8'))
        return h.hexdigest()

    def __init__(self, seed=None):
        if seed is None:
            # Limit seeds to 10 digits for simpler output.
            seed = random.randint(0, 10**10 - 1)
            seed_source = 'generated'
        else:
            seed_source = 'given'
        self.seed = seed
        self.seed_source = seed_source

    @property
    def seed_display(self):
        return f'{self.seed!r} ({self.seed_source})'

    def _hash_item(self, item, key):
        text = '{}{}'.format(self.seed, key(item))
        return self._hash_text(text)

    def shuffle(self, items, key):
        """
        Return a new list of the items in a shuffled order.

        The `key` is a function that accepts an item in `items` and returns
        a string unique for that item that can be viewed as a string id. The
        order of the return value is deterministic. It depends on the seed
        and key function but not on the original order.
        """
        hashes = {}
        for item in items:
            hashed = self._hash_item(item, key)
            if hashed in hashes:
                msg = 'item {!r} has same hash {!r} as item {!r}'.format(
                    item, hashed, hashes[hashed],
                )
                raise RuntimeError(msg)
            hashes[hashed] = item
        return [hashes[hashed] for hashed in sorted(hashes)]


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
                 timing=False, shuffle=False, logger=None, **kwargs):

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
        self.test_name_patterns = None
        self.time_keeper = TimeKeeper() if timing else NullTimeKeeper()
        if test_name_patterns:
            # unittest does not export the _convert_select_pattern function
            # that converts command-line arguments to patterns.
            self.test_name_patterns = {
                pattern if '*' in pattern else '*%s*' % pattern
                for pattern in test_name_patterns
            }
        self.shuffle = shuffle
        self._shuffler = None
        self.logger = logger

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
            '--shuffle', nargs='?', default=False, type=int, metavar='SEED',
            help='Shuffles test case order.',
        )
        parser.add_argument(
            '-r', '--reverse', action='store_true',
            help='Reverses test case order.',
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
            '--parallel', nargs='?', const='auto', default=0,
            type=parallel_type, metavar='N',
            help=(
                'Run tests using up to N parallel processes. Use the value '
                '"auto" to run one test process for each processor core.'
            ),
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
        parser.add_argument(
            '-k', action='append', dest='test_name_patterns',
            help=(
                'Only run test methods and classes that match the pattern '
                'or substring. Can be used multiple times. Same as '
                'unittest -k option.'
            ),
        )

    @property
    def shuffle_seed(self):
        if self._shuffler is None:
            return None
        return self._shuffler.seed

    def log(self, msg, level=None):
        """
        Log the message at the given logging level (the default is INFO).

        If a logger isn't set, the message is instead printed to the console,
        respecting the configured verbosity. A verbosity of 0 prints no output,
        a verbosity of 1 prints INFO and above, and a verbosity of 2 or higher
        prints all levels.
        """
        if level is None:
            level = logging.INFO
        if self.logger is None:
            if self.verbosity <= 0 or (
                self.verbosity == 1 and level < logging.INFO
            ):
                return
            print(msg)
        else:
            self.logger.log(level, msg)

    def setup_test_environment(self, **kwargs):
        setup_test_environment(debug=self.debug_mode)
        unittest.installHandler()

    def setup_shuffler(self):
        if self.shuffle is False:
            return
        shuffler = Shuffler(seed=self.shuffle)
        self.log(f'Using shuffle seed: {shuffler.seed_display}')
        self._shuffler = shuffler

    @contextmanager
    def load_with_patterns(self):
        original_test_name_patterns = self.test_loader.testNamePatterns
        self.test_loader.testNamePatterns = self.test_name_patterns
        try:
            yield
        finally:
            # Restore the original patterns.
            self.test_loader.testNamePatterns = original_test_name_patterns

    def load_tests_for_label(self, label, discover_kwargs):
        label_as_path = os.path.abspath(label)
        tests = None

        # If a module, or "module.ClassName[.method_name]", just run those.
        if not os.path.exists(label_as_path):
            with self.load_with_patterns():
                tests = self.test_loader.loadTestsFromName(label)
            if tests.countTestCases():
                return tests
        # Try discovery if "label" is a package or directory.
        is_importable, is_package = try_importing(label)
        if is_importable:
            if not is_package:
                return tests
        elif not os.path.isdir(label_as_path):
            if os.path.exists(label_as_path):
                assert tests is None
                raise RuntimeError(
                    f'One of the test labels is a path to a file: {label!r}, '
                    f'which is not supported. Use a dotted module name or '
                    f'path to a directory instead.'
                )
            return tests

        kwargs = discover_kwargs.copy()
        if os.path.isdir(label_as_path) and not self.top_level:
            kwargs['top_level_dir'] = find_top_level(label_as_path)

        with self.load_with_patterns():
            tests = self.test_loader.discover(start_dir=label, **kwargs)

        # Make unittest forget the top-level dir it calculated from this run,
        # to support running tests from two different top-levels.
        self.test_loader._top_level_dir = None
        return tests

    def build_suite(self, test_labels=None, extra_tests=None, **kwargs):
        if extra_tests is not None:
            warnings.warn(
                'The extra_tests argument is deprecated.',
                RemovedInDjango50Warning,
                stacklevel=2,
            )
        test_labels = test_labels or ['.']
        extra_tests = extra_tests or []

        discover_kwargs = {}
        if self.pattern is not None:
            discover_kwargs['pattern'] = self.pattern
        if self.top_level is not None:
            discover_kwargs['top_level_dir'] = self.top_level
        self.setup_shuffler()

        all_tests = []
        for label in test_labels:
            tests = self.load_tests_for_label(label, discover_kwargs)
            all_tests.extend(iter_test_cases(tests))

        all_tests.extend(iter_test_cases(extra_tests))

        if self.tags or self.exclude_tags:
            if self.tags:
                self.log(
                    'Including test tag(s): %s.' % ', '.join(sorted(self.tags)),
                    level=logging.DEBUG,
                )
            if self.exclude_tags:
                self.log(
                    'Excluding test tag(s): %s.' % ', '.join(sorted(self.exclude_tags)),
                    level=logging.DEBUG,
                )
            all_tests = filter_tests_by_tags(all_tests, self.tags, self.exclude_tags)

        # Put the failures detected at load time first for quicker feedback.
        # _FailedTest objects include things like test modules that couldn't be
        # found or that couldn't be loaded due to syntax errors.
        test_types = (unittest.loader._FailedTest, *self.reorder_by)
        all_tests = list(reorder_tests(
            all_tests,
            test_types,
            shuffler=self._shuffler,
            reverse=self.reverse,
        ))
        self.log('Found %d test(s).' % len(all_tests))
        suite = self.test_suite(all_tests)

        if self.parallel > 1:
            subsuites = partition_suite_by_case(suite)
            # Since tests are distributed across processes on a per-TestCase
            # basis, there's no need for more processes than TestCases.
            processes = min(self.parallel, len(subsuites))
            # Update also "parallel" because it's used to determine the number
            # of test databases.
            self.parallel = processes
            if processes > 1:
                suite = self.parallel_test_suite(
                    subsuites,
                    processes,
                    self.failfast,
                    self.buffer,
                )
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
        try:
            return runner.run(suite)
        finally:
            if self._shuffler is not None:
                seed_display = self._shuffler.seed_display
                self.log(f'Used shuffle seed: {seed_display}')

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
        databases = {}
        for test in iter_test_cases(suite):
            test_databases = getattr(test, 'databases', None)
            if test_databases == '__all__':
                test_databases = connections
            if test_databases:
                serialized_rollback = getattr(test, 'serialized_rollback', False)
                databases.update(
                    (alias, serialized_rollback or databases.get(alias, False))
                    for alias in test_databases
                )
        return databases

    def get_databases(self, suite):
        databases = self._get_databases(suite)
        unused_databases = [alias for alias in connections if alias not in databases]
        if unused_databases:
            self.log(
                'Skipping setup of unused database(s): %s.' % ', '.join(sorted(unused_databases)),
                level=logging.DEBUG,
            )
        return databases

    def run_tests(self, test_labels, extra_tests=None, **kwargs):
        """
        Run the unit tests for all the test labels in the provided list.

        Test labels should be dotted Python paths to test modules, test
        classes, or test methods.

        Return the number of tests that failed.
        """
        if extra_tests is not None:
            warnings.warn(
                'The extra_tests argument is deprecated.',
                RemovedInDjango50Warning,
                stacklevel=2,
            )
        self.setup_test_environment()
        suite = self.build_suite(test_labels, extra_tests)
        databases = self.get_databases(suite)
        serialized_aliases = set(
            alias
            for alias, serialize in databases.items() if serialize
        )
        with self.time_keeper.timed('Total database setup'):
            old_config = self.setup_databases(
                aliases=databases,
                serialized_aliases=serialized_aliases,
            )
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


def try_importing(label):
    """
    Try importing a test label, and return (is_importable, is_package).

    Relative labels like "." and ".." are seen as directories.
    """
    try:
        mod = import_module(label)
    except (ImportError, TypeError):
        return (False, False)

    return (True, hasattr(mod, '__path__'))


def find_top_level(top_level):
    # Try to be a bit smarter than unittest about finding the default top-level
    # for a given directory path, to avoid breaking relative imports.
    # (Unittest's default is to set top-level equal to the path, which means
    # relative imports will result in "Attempted relative import in
    # non-package.").

    # We'd be happy to skip this and require dotted module paths (which don't
    # cause this problem) instead of file paths (which do), but in the case of
    # a directory in the cwd, which would be equally valid if considered as a
    # top-level module or as a directory path, unittest unfortunately prefers
    # the latter.
    while True:
        init_py = os.path.join(top_level, '__init__.py')
        if not os.path.exists(init_py):
            break
        try_next = os.path.dirname(top_level)
        if try_next == top_level:
            # __init__.py all the way down? give up.
            break
        top_level = try_next
    return top_level


def _class_shuffle_key(cls):
    return f'{cls.__module__}.{cls.__qualname__}'


def shuffle_tests(tests, shuffler):
    """
    Return an iterator over the given tests in a shuffled order, keeping tests
    next to other tests of their class.

    `tests` should be an iterable of tests.
    """
    tests_by_type = {}
    for _, class_tests in itertools.groupby(tests, type):
        class_tests = list(class_tests)
        test_type = type(class_tests[0])
        class_tests = shuffler.shuffle(class_tests, key=lambda test: test.id())
        tests_by_type[test_type] = class_tests

    classes = shuffler.shuffle(tests_by_type, key=_class_shuffle_key)

    return itertools.chain(*(tests_by_type[cls] for cls in classes))


def reorder_test_bin(tests, shuffler=None, reverse=False):
    """
    Return an iterator that reorders the given tests, keeping tests next to
    other tests of their class.

    `tests` should be an iterable of tests that supports reversed().
    """
    if shuffler is None:
        if reverse:
            return reversed(tests)
        # The function must return an iterator.
        return iter(tests)

    tests = shuffle_tests(tests, shuffler)
    if not reverse:
        return tests
    # Arguments to reversed() must be reversible.
    return reversed(list(tests))


def reorder_tests(tests, classes, reverse=False, shuffler=None):
    """
    Reorder an iterable of tests, grouping by the given TestCase classes.

    This function also removes any duplicates and reorders so that tests of the
    same type are consecutive.

    The result is returned as an iterator. `classes` is a sequence of types.
    Tests that are instances of `classes[0]` are grouped first, followed by
    instances of `classes[1]`, etc. Tests that are not instances of any of the
    classes are grouped last.

    If `reverse` is True, the tests within each `classes` group are reversed,
    but without reversing the order of `classes` itself.

    The `shuffler` argument is an optional instance of this module's `Shuffler`
    class. If provided, tests will be shuffled within each `classes` group, but
    keeping tests with other tests of their TestCase class. Reversing is
    applied after shuffling to allow reversing the same random order.
    """
    # Each bin maps TestCase class to OrderedSet of tests. This permits tests
    # to be grouped by TestCase class even if provided non-consecutively.
    bins = [defaultdict(OrderedSet) for i in range(len(classes) + 1)]
    *class_bins, last_bin = bins

    for test in tests:
        for test_bin, test_class in zip(class_bins, classes):
            if isinstance(test, test_class):
                break
        else:
            test_bin = last_bin
        test_bin[type(test)].add(test)

    for test_bin in bins:
        # Call list() since reorder_test_bin()'s input must support reversed().
        tests = list(itertools.chain.from_iterable(test_bin.values()))
        yield from reorder_test_bin(tests, shuffler=shuffler, reverse=reverse)


def partition_suite_by_case(suite):
    """Partition a test suite by test case, preserving the order of tests."""
    suite_class = type(suite)
    all_tests = iter_test_cases(suite)
    return [
        suite_class(tests) for _, tests in itertools.groupby(all_tests, type)
    ]


def test_match_tags(test, tags, exclude_tags):
    if isinstance(test, unittest.loader._FailedTest):
        # Tests that couldn't load always match to prevent tests from falsely
        # passing due e.g. to syntax errors.
        return True
    test_tags = set(getattr(test, 'tags', []))
    test_fn_name = getattr(test, '_testMethodName', str(test))
    if hasattr(test, test_fn_name):
        test_fn = getattr(test, test_fn_name)
        test_fn_tags = list(getattr(test_fn, 'tags', []))
        test_tags = test_tags.union(test_fn_tags)
    if tags and test_tags.isdisjoint(tags):
        return False
    return test_tags.isdisjoint(exclude_tags)


def filter_tests_by_tags(tests, tags, exclude_tags):
    """Return the matching tests as an iterator."""
    return (test for test in tests if test_match_tags(test, tags, exclude_tags))
