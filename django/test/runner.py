from importlib import import_module
import os
from optparse import make_option
import unittest
from unittest import TestSuite, defaultTestLoader

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.management.color import color_style, supports_color
from django.test import SimpleTestCase, TestCase
from django.test.utils import setup_test_environment, teardown_test_environment
from django.utils import six
from django.utils.termcolors import RESET


class DiscoverRunner(object):
    """
    A Django test runner that uses unittest2 test discovery.
    """

    test_suite = TestSuite
    test_runner = unittest.TextTestRunner
    test_loader = defaultTestLoader
    reorder_by = (TestCase, SimpleTestCase)
    option_list = (
        make_option('-t', '--top-level-directory',
            action='store', dest='top_level', default=None,
            help='Top level of project for unittest discovery.'),
        make_option('-p', '--pattern', action='store', dest='pattern',
            default="test*.py",
            help='The test matching pattern. Defaults to test*.py.'),
    )

    def __init__(self, pattern=None, top_level=None,
                 verbosity=1, interactive=True, failfast=False,
                 **kwargs):

        self.pattern = pattern
        self.top_level = top_level

        self.verbosity = verbosity
        self.interactive = interactive
        self.failfast = failfast

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

        return reorder_suite(suite, self.reorder_by)

    def setup_databases(self, **kwargs):
        return setup_databases(self.verbosity, self.interactive, **kwargs)

    def run_suite(self, suite, **kwargs):
        return self.test_runner(
            verbosity=self.verbosity,
            failfast=self.failfast,
        ).run(suite)

    def teardown_databases(self, old_config, **kwargs):
        """
        Destroys all the non-mirror databases.
        """
        old_names, mirrors = old_config
        for connection, old_name, destroy in old_names:
            if destroy:
                connection.creation.destroy_test_db(old_name, self.verbosity)

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


class ColorTextTestResult(unittest.TextTestResult):

    """
    A TextTestResult that displays output using ANSI colors.

    The following color palette options are used to determine the colors
    of the output:

        TEST_SUCCESS is used for passing tests
        TEST_FAILURE is used for failing and erroring tests
        TEST_SKIP is used for skipped tests
        TEST_EXPECTED_FAULURE is used for expected failing tests
        TEST_UNEXPECTED_SUCCESS is used for unexpectedly passing tests
    """

    def __init__(self, *args, **kwargs):
        """
        Set the style of this instance.
        """
        super(ColorTextTestResult, self).__init__(*args, **kwargs)
        self.style = color_style()
        self.traceback_highlighter = make_traceback_highlighter()
        self.terminator = '\x1b[%sm' % RESET if supports_color() else ''

    def addSuccess(self, test):
        """
        Print a colored success message.
        """
        self._colorize('TEST_SUCCESS')
        super(ColorTextTestResult, self).addSuccess(test)
        self._uncolorize()

    def addError(self, test, err):
        """
        Print a colored error message.
        """
        self._colorize('TEST_FAILURE')
        super(ColorTextTestResult, self).addError(test, err)
        self._uncolorize()

    def addFailure(self, test, err):
        """
        Print a colored failure message.
        """
        self._colorize('TEST_FAILURE')
        super(ColorTextTestResult, self).addFailure(test, err)
        self._uncolorize()

    def addSkip(self, test, reason):
        """
        Print a colored skip message.
        """
        self._colorize('TEST_SKIP')
        super(ColorTextTestResult, self).addSkip(test, reason)
        self._uncolorize()

    def addExpectedFailure(self, test, err):
        """
        Print a colored expected failure message.
        """
        self._colorize('TEST_EXPECTED_FAILURE')
        super(ColorTextTestResult, self).addExpectedFailure(test, err)
        self._uncolorize()

    def addUnexpectedSuccess(self, test):
        """
        Print a colored unexpected success message.
        """
        self._colorize('TEST_UNEXPECTED_SUCCESS')
        super(ColorTextTestResult, self).addUnexpectedSuccess(test)
        self._uncolorize()

    def printErrorList(self, flavour, errors):
        """
        Print a colored error list.
        """
        for test, err in errors:
            self.stream.writeln(self.separator1)
            self.stream.writeln(self.style.TEST_FAILURE(
                "%s: %s" % (flavour, self.getDescription(test))))
            self.stream.writeln(self.separator2)
            self.stream.writeln(self.traceback_highlighter(err))

    def _colorize(self, color):
        """
        Begin a colored section of terminal output. The given color should
        be an attribute of self.style
        """
        # Write an empty string using the current style because we only care
        # about setting the style
        message = getattr(self.style, color)('')
        # Remove the terminator so that subsequent writes will have the color
        self.stream.write(self._unterminate(message))

    def _uncolorize(self):
        """
        End a colored section of terminal output.
        """
        self.stream.write(self.terminator)

    def _unterminate(self, message):
        """
        Remove the color termination portion of the message.
        """
        end = message.find(self.terminator)
        return message[:end]


def make_traceback_highlighter():
    """
    Return a function for highlighting traceback text.

    If the Pygments library is available, it will be used to create
    a function that takes traceback text and returns an ANSI-highlighted
    version. If Pygments is not available, the returned highlighter will
    simply return the traceback text unchanged.
    """
    # Terminal doesn't support color, do not highlight
    if not supports_color():
        return lambda text: text

    try:
        from pygments import highlight
        from pygments.formatters import TerminalFormatter
    except ImportError:
        # User does not have Pygments installed, do not highlight
        return lambda text: text

    if six.PY2:
        from pygments.lexers import PythonTracebackLexer as Lexer
    else:
        from pygments.lexers import Python3TracebackLexer as Lexer

    return lambda text: highlight(text, Lexer(), TerminalFormatter())


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

    # sanity check - no DB can depend on it's own alias
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


def reorder_suite(suite, classes):
    """
    Reorders a test suite by test type.

    `classes` is a sequence of types

    All tests of type classes[0] are placed first, then tests of type
    classes[1], etc. Tests with no match in classes are placed last.
    """
    class_count = len(classes)
    suite_class = type(suite)
    bins = [suite_class() for i in range(class_count + 1)]
    partition_suite(suite, classes, bins)
    for i in range(class_count):
        bins[0].addTests(bins[i + 1])
    return bins[0]


def partition_suite(suite, classes, bins):
    """
    Partitions a test suite by test type.

    classes is a sequence of types
    bins is a sequence of TestSuites, one more than classes

    Tests of type classes[i] are added to bins[i],
    tests with no match found in classes are place in bins[-1]
    """
    suite_class = type(suite)
    for test in suite:
        if isinstance(test, suite_class):
            partition_suite(test, classes, bins)
        else:
            for i in range(len(classes)):
                if isinstance(test, classes[i]):
                    bins[i].addTest(test)
                    break
            else:
                bins[-1].addTest(test)


def setup_databases(verbosity, interactive, **kwargs):
    from django.db import connections, DEFAULT_DB_ALIAS

    # First pass -- work out which databases actually need to be created,
    # and which ones are test mirrors or duplicate entries in DATABASES
    mirrored_aliases = {}
    test_databases = {}
    dependencies = {}
    default_sig = connections[DEFAULT_DB_ALIAS].creation.test_db_signature()
    for alias in connections:
        connection = connections[alias]
        test_settings = connection.settings_dict['TEST']
        if test_settings['MIRROR']:
            # If the database is marked as a test mirror, save
            # the alias.
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

    # Second pass -- actually create the databases.
    old_names = []
    mirrors = []

    for signature, (db_name, aliases) in dependency_ordered(
            test_databases.items(), dependencies):
        test_db_name = None
        # Actually create the database for the first connection
        for alias in aliases:
            connection = connections[alias]
            if test_db_name is None:
                test_db_name = connection.creation.create_test_db(
                    verbosity, autoclobber=not interactive)
                destroy = True
            else:
                connection.settings_dict['NAME'] = test_db_name
                destroy = False
            old_names.append((connection, db_name, destroy))

    for alias, mirror_alias in mirrored_aliases.items():
        mirrors.append((alias, connections[alias].settings_dict['NAME']))
        connections[alias].settings_dict['NAME'] = (
            connections[mirror_alias].settings_dict['NAME'])

    return old_names, mirrors
