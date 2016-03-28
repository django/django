import collections
import ctypes
import itertools
import logging
import multiprocessing
import os
import pickle
import textwrap
import unittest
from importlib import import_module

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import DEFAULT_DB_ALIAS, connections
from django.test import SimpleTestCase, TestCase
from django.test.utils import setup_test_environment, teardown_test_environment
from django.utils.datastructures import OrderedSet
from django.utils.six import StringIO

try:
    import tblib.pickling_support
except ImportError:
    tblib = None


class DebugSQLTextTestResult(unittest.TextTestResult):
    def __init__(self, stream, descriptions, verbosity):
        self.logger = logging.getLogger('django.db.backends')
        self.logger.setLevel(logging.DEBUG)
        super(DebugSQLTextTestResult, self).__init__(stream, descriptions, verbosity)

    def startTest(self, test):
        self.debug_sql_stream = StringIO()
        self.handler = logging.StreamHandler(self.debug_sql_stream)
        self.logger.addHandler(self.handler)
        super(DebugSQLTextTestResult, self).startTest(test)

    def stopTest(self, test):
        super(DebugSQLTextTestResult, self).stopTest(test)
        self.logger.removeHandler(self.handler)
        if self.showAll:
            self.debug_sql_stream.seek(0)
            self.stream.write(self.debug_sql_stream.read())
            self.stream.writeln(self.separator2)

    def addError(self, test, err):
        super(DebugSQLTextTestResult, self).addError(test, err)
        self.debug_sql_stream.seek(0)
        self.errors[-1] = self.errors[-1] + (self.debug_sql_stream.read(),)

    def addFailure(self, test, err):
        super(DebugSQLTextTestResult, self).addFailure(test, err)
        self.debug_sql_stream.seek(0)
        self.failures[-1] = self.failures[-1] + (self.debug_sql_stream.read(),)

    def printErrorList(self, flavour, errors):
        for test, err, sql_debug in errors:
            self.stream.writeln(self.separator1)
            self.stream.writeln("%s: %s" % (flavour, self.getDescription(test)))
            self.stream.writeln(self.separator2)
            self.stream.writeln("%s" % err)
            self.stream.writeln(self.separator2)
            self.stream.writeln("%s" % sql_debug)


class RemoteTestResult(object):
    """
    Record information about which tests have succeeded and which have failed.

    The sole purpose of this class is to record events in the child processes
    so they can be replayed in the master process. As a consequence it doesn't
    inherit unittest.TestResult and doesn't attempt to implement all its API.

    The implementation matches the unpythonic coding style of unittest2.
    """

    def __init__(self):
        self.events = []
        self.failfast = False
        self.shouldStop = False
        self.testsRun = 0

    @property
    def test_index(self):
        return self.testsRun - 1

    def check_picklable(self, test, err):
        # Ensure that sys.exc_info() tuples are picklable. This displays a
        # clear multiprocessing.pool.RemoteTraceback generated in the child
        # process instead of a multiprocessing.pool.MaybeEncodingError, making
        # the root cause easier to figure out for users who aren't familiar
        # with the multiprocessing module. Since we're in a forked process,
        # our best chance to communicate with them is to print to stdout.
        try:
            pickle.dumps(err)
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

    pip install tblib
""".format(test, original_exc_txt))
            else:
                print("""

{} failed:

{}

Unfortunately, the exception it raised cannot be pickled, making it impossible
for the parallel test runner to handle it cleanly.

Here's the error encountered while trying to pickle the exception:

{}

You should re-run this test without the --parallel option to reproduce the
failure and get a correct traceback.
""".format(test, original_exc_txt, pickle_exc_txt))
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
        raise NotImplementedError("subtests aren't supported at this time")

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


class RemoteTestRunner(object):
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
    """
    Default number of test processes when using the --parallel option.
    """
    # The current implementation of the parallel test runner requires
    # multiprocessing to start subprocesses with fork().
    # On Python 3.4+: if multiprocessing.get_start_method() != 'fork':
    if not hasattr(os, 'fork'):
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
        settings_dict = connection.creation.get_test_db_clone_settings(_worker_id)
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
    subsuite_index, subsuite, failfast = args
    runner = RemoteTestRunner(failfast=failfast)
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

    def __init__(self, suite, processes, failfast=False):
        self.subsuites = partition_suite_by_case(suite)
        self.processes = processes
        self.failfast = failfast
        super(ParallelTestSuite, self).__init__()

    def run(self, result):
        """
        Distribute test cases across workers.

        Return an identifier of each test case with its result in order to use
        imap_unordered to show results as soon as they're available.

        To minimize pickling errors when getting results from workers:

        - pass back numeric indexes in self.subsuites instead of tests
        - make tracebacks picklable with tblib, if available

        Even with tblib, errors may still occur for dynamically created
        exception classes such Model.DoesNotExist which cannot be unpickled.
        """
        if tblib is not None:
            tblib.pickling_support.install()

        counter = multiprocessing.Value(ctypes.c_int, 0)
        pool = multiprocessing.Pool(
            processes=self.processes,
            initializer=self.init_worker.__func__,
            initargs=[counter])
        args = [
            (index, subsuite, self.failfast)
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


class DiscoverRunner(object):
    """
    A Django test runner that uses unittest2 test discovery.
    """

    test_suite = unittest.TestSuite
    parallel_test_suite = ParallelTestSuite
    test_runner = unittest.TextTestRunner
    test_loader = unittest.defaultTestLoader
    reorder_by = (TestCase, SimpleTestCase)

    def __init__(self, pattern=None, top_level=None, verbosity=1,
                 interactive=True, failfast=False, keepdb=False,
                 reverse=False, debug_sql=False, parallel=0,
                 tags=None, exclude_tags=None, **kwargs):

        self.pattern = pattern
        self.top_level = top_level
        self.verbosity = verbosity
        self.interactive = interactive
        self.failfast = failfast
        self.keepdb = keepdb
        self.reverse = reverse
        self.debug_sql = debug_sql
        self.parallel = parallel
        self.tags = set(tags or [])
        self.exclude_tags = set(exclude_tags or [])

    @classmethod
    def add_arguments(cls, parser):
        parser.add_argument(
            '-t', '--top-level-directory', action='store', dest='top_level', default=None,
            help='Top level of project for unittest discovery.',
        )
        parser.add_argument(
            '-p', '--pattern', action='store', dest='pattern', default="test*.py",
            help='The test matching pattern. Defaults to test*.py.',
        )
        parser.add_argument(
            '-k', '--keepdb', action='store_true', dest='keepdb', default=False,
            help='Preserves the test DB between runs.'
        )
        parser.add_argument(
            '-r', '--reverse', action='store_true', dest='reverse', default=False,
            help='Reverses test cases order.',
        )
        parser.add_argument(
            '-d', '--debug-sql', action='store_true', dest='debug_sql', default=False,
            help='Prints logged SQL queries on failure.',
        )
        parser.add_argument(
            '--parallel', dest='parallel', nargs='?', default=1, type=int,
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

    def setup_test_environment(self, **kwargs):
        setup_test_environment()
        settings.DEBUG = False
        unittest.installHandler()

    def build_suite(self, test_labels=None, extra_tests=None, **kwargs):
        suite = self.test_suite()
        test_labels = test_labels or ['.']
        extra_tests = extra_tests or []

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
            suite = filter_tests_by_tags(suite, self.tags, self.exclude_tags)
        suite = reorder_suite(suite, self.reorder_by, self.reverse)

        if self.parallel > 1:
            parallel_suite = self.parallel_test_suite(suite, self.parallel, self.failfast)

            # Since tests are distributed across processes on a per-TestCase
            # basis, there's no need for more processes than TestCases.
            parallel_units = len(parallel_suite.subsuites)
            if self.parallel > parallel_units:
                self.parallel = parallel_units

            # If there's only one TestCase, parallelization isn't needed.
            if self.parallel > 1:
                suite = parallel_suite

        return suite

    def setup_databases(self, **kwargs):
        return setup_databases(
            self.verbosity, self.interactive, self.keepdb, self.debug_sql,
            self.parallel, **kwargs
        )

    def get_resultclass(self):
        return DebugSQLTextTestResult if self.debug_sql else None

    def run_suite(self, suite, **kwargs):
        resultclass = self.get_resultclass()
        return self.test_runner(
            verbosity=self.verbosity,
            failfast=self.failfast,
            resultclass=resultclass,
        ).run(suite)

    def teardown_databases(self, old_config, **kwargs):
        """
        Destroys all the non-mirror databases.
        """
        for connection, old_name, destroy in old_config:
            if destroy:
                if self.parallel > 1:
                    for index in range(self.parallel):
                        connection.creation.destroy_test_db(
                            number=index + 1,
                            verbosity=self.verbosity,
                            keepdb=self.keepdb,
                        )
                connection.creation.destroy_test_db(old_name, self.verbosity, self.keepdb)

    def teardown_test_environment(self, **kwargs):
        unittest.removeHandler()
        teardown_test_environment()

    def suite_result(self, suite, result, **kwargs):
        return len(result.failures) + len(result.errors)

    def run_tests(self, test_labels, extra_tests=None, **kwargs):
        """
        Run the unit tests for all the test labels in the provided list.

        Test labels should be dotted Python paths to test modules, test
        classes, or test methods.

        A list of 'extra' tests may also be provided; these tests
        will be added to the test suite.

        Returns the number of tests that failed.
        """
        self.setup_test_environment()
        suite = self.build_suite(test_labels, extra_tests)
        old_config = self.setup_databases()
        result = self.run_suite(suite)
        self.teardown_databases(old_config)
        self.teardown_test_environment()
        return self.suite_result(suite, result)


def is_discoverable(label):
    """
    Check if a test label points to a python package or file directory.

    Relative labels like "." and ".." are seen as directories.
    """
    try:
        mod = import_module(label)
    except (ImportError, TypeError):
        pass
    else:
        return hasattr(mod, '__path__')

    return os.path.isdir(os.path.abspath(label))


def dependency_ordered(test_databases, dependencies):
    """
    Reorder test_databases into an order that honors the dependencies
    described in TEST[DEPENDENCIES].
    """
    ordered_test_databases = []
    resolved_databases = set()

    # Maps db signature to dependencies of all it's aliases
    dependencies_map = {}

    # sanity check - no DB can depend on its own alias
    for sig, (_, aliases) in test_databases:
        all_deps = set()
        for alias in aliases:
            all_deps.update(dependencies.get(alias, []))
        if not all_deps.isdisjoint(aliases):
            raise ImproperlyConfigured(
                "Circular dependency: databases %r depend on each other, "
                "but are aliases." % aliases)
        dependencies_map[sig] = all_deps

    while test_databases:
        changed = False
        deferred = []

        # Try to find a DB that has all it's dependencies met
        for signature, (db_name, aliases) in test_databases:
            if dependencies_map[signature].issubset(resolved_databases):
                resolved_databases.update(aliases)
                ordered_test_databases.append((signature, (db_name, aliases)))
                changed = True
            else:
                deferred.append((signature, (db_name, aliases)))

        if not changed:
            raise ImproperlyConfigured(
                "Circular dependency in TEST[DEPENDENCIES]")
        test_databases = deferred
    return ordered_test_databases


def reorder_suite(suite, classes, reverse=False):
    """
    Reorders a test suite by test type.

    `classes` is a sequence of types

    All tests of type classes[0] are placed first, then tests of type
    classes[1], etc. Tests with no match in classes are placed last.

    If `reverse` is True, tests within classes are sorted in opposite order,
    but test classes are not reversed.
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
    Partitions a test suite by test type. Also prevents duplicated tests.

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
    """
    Partitions a test suite by test case, preserving the order of tests.
    """
    groups = []
    suite_class = type(suite)
    for test_type, test_group in itertools.groupby(suite, type):
        if issubclass(test_type, unittest.TestCase):
            groups.append(suite_class(test_group))
        else:
            for item in test_group:
                groups.extend(partition_suite_by_case(item))
    return groups


def get_unique_databases_and_mirrors():
    """
    Figure out which databases actually need to be created.

    Deduplicate entries in DATABASES that correspond the same database or are
    configured as test mirrors.

    Return two values:
    - test_databases: ordered mapping of signatures to (name, list of aliases)
                      where all aliases share the same underlying database.
    - mirrored_aliases: mapping of mirror aliases to original aliases.
    """
    mirrored_aliases = {}
    test_databases = {}
    dependencies = {}
    default_sig = connections[DEFAULT_DB_ALIAS].creation.test_db_signature()

    for alias in connections:
        connection = connections[alias]
        test_settings = connection.settings_dict['TEST']

        if test_settings['MIRROR']:
            # If the database is marked as a test mirror, save the alias.
            mirrored_aliases[alias] = test_settings['MIRROR']
        else:
            # Store a tuple with DB parameters that uniquely identify it.
            # If we have two aliases with the same values for that tuple,
            # we only need to create the test database once.
            item = test_databases.setdefault(
                connection.creation.test_db_signature(),
                (connection.settings_dict['NAME'], set())
            )
            item[1].add(alias)

            if 'DEPENDENCIES' in test_settings:
                dependencies[alias] = test_settings['DEPENDENCIES']
            else:
                if alias != DEFAULT_DB_ALIAS and connection.creation.test_db_signature() != default_sig:
                    dependencies[alias] = test_settings.get('DEPENDENCIES', [DEFAULT_DB_ALIAS])

    test_databases = dependency_ordered(test_databases.items(), dependencies)
    test_databases = collections.OrderedDict(test_databases)
    return test_databases, mirrored_aliases


def setup_databases(verbosity, interactive, keepdb=False, debug_sql=False, parallel=0, **kwargs):
    """
    Creates the test databases.
    """
    test_databases, mirrored_aliases = get_unique_databases_and_mirrors()

    old_names = []

    for signature, (db_name, aliases) in test_databases.items():
        first_alias = None
        for alias in aliases:
            connection = connections[alias]
            old_names.append((connection, db_name, first_alias is None))

            # Actually create the database for the first connection
            if first_alias is None:
                first_alias = alias
                connection.creation.create_test_db(
                    verbosity=verbosity,
                    autoclobber=not interactive,
                    keepdb=keepdb,
                    serialize=connection.settings_dict.get("TEST", {}).get("SERIALIZE", True),
                )
                if parallel > 1:
                    for index in range(parallel):
                        connection.creation.clone_test_db(
                            number=index + 1,
                            verbosity=verbosity,
                            keepdb=keepdb,
                        )
            # Configure all other connections as mirrors of the first one
            else:
                connections[alias].creation.set_as_test_mirror(
                    connections[first_alias].settings_dict)

    # Configure the test mirrors.
    for alias, mirror_alias in mirrored_aliases.items():
        connections[alias].creation.set_as_test_mirror(
            connections[mirror_alias].settings_dict)

    if debug_sql:
        for alias in connections:
            connections[alias].force_debug_cursor = True

    return old_names


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
