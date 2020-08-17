import os
from argparse import ArgumentParser
from contextlib import contextmanager
from unittest import (
    TestSuite, TextTestRunner, defaultTestLoader, mock, skipUnless,
)

from django.db import connections
from django.test import SimpleTestCase
from django.test.runner import DiscoverRunner
from django.test.utils import (
    NullTimeKeeper, TimeKeeper, captured_stderr, captured_stdout,
)
from django.utils.version import PY37


@contextmanager
def change_cwd(directory):
    current_dir = os.path.abspath(os.path.dirname(__file__))
    new_dir = os.path.join(current_dir, directory)
    old_cwd = os.getcwd()
    os.chdir(new_dir)
    try:
        yield
    finally:
        os.chdir(old_cwd)


class DiscoverRunnerTests(SimpleTestCase):

    @staticmethod
    def get_test_methods_names(suite):
        return [
            t.__class__.__name__ + '.' + t._testMethodName
            for t in suite._tests
        ]

    def test_init_debug_mode(self):
        runner = DiscoverRunner()
        self.assertFalse(runner.debug_mode)

    def test_add_arguments_debug_mode(self):
        parser = ArgumentParser()
        DiscoverRunner.add_arguments(parser)

        ns = parser.parse_args([])
        self.assertFalse(ns.debug_mode)
        ns = parser.parse_args(["--debug-mode"])
        self.assertTrue(ns.debug_mode)

    def test_dotted_test_module(self):
        count = DiscoverRunner().build_suite(
            ['test_runner_apps.sample.tests_sample'],
        ).countTestCases()

        self.assertEqual(count, 4)

    def test_dotted_test_class_vanilla_unittest(self):
        count = DiscoverRunner().build_suite(
            ['test_runner_apps.sample.tests_sample.TestVanillaUnittest'],
        ).countTestCases()

        self.assertEqual(count, 1)

    def test_dotted_test_class_django_testcase(self):
        count = DiscoverRunner().build_suite(
            ['test_runner_apps.sample.tests_sample.TestDjangoTestCase'],
        ).countTestCases()

        self.assertEqual(count, 1)

    def test_dotted_test_method_django_testcase(self):
        count = DiscoverRunner().build_suite(
            ['test_runner_apps.sample.tests_sample.TestDjangoTestCase.test_sample'],
        ).countTestCases()

        self.assertEqual(count, 1)

    def test_pattern(self):
        count = DiscoverRunner(
            pattern="*_tests.py",
        ).build_suite(['test_runner_apps.sample']).countTestCases()

        self.assertEqual(count, 1)

    @skipUnless(PY37, 'unittest -k option requires Python 3.7 and later')
    def test_name_patterns(self):
        all_test_1 = [
            'DjangoCase1.test_1', 'DjangoCase2.test_1',
            'SimpleCase1.test_1', 'SimpleCase2.test_1',
            'UnittestCase1.test_1', 'UnittestCase2.test_1',
        ]
        all_test_2 = [
            'DjangoCase1.test_2', 'DjangoCase2.test_2',
            'SimpleCase1.test_2', 'SimpleCase2.test_2',
            'UnittestCase1.test_2', 'UnittestCase2.test_2',
        ]
        all_tests = sorted([*all_test_1, *all_test_2, 'UnittestCase2.test_3_test'])
        for pattern, expected in [
            [['test_1'], all_test_1],
            [['UnittestCase1'], ['UnittestCase1.test_1', 'UnittestCase1.test_2']],
            [['*test'], ['UnittestCase2.test_3_test']],
            [['test*'], all_tests],
            [['test'], all_tests],
            [['test_1', 'test_2'], sorted([*all_test_1, *all_test_2])],
            [['test*1'], all_test_1],
        ]:
            with self.subTest(pattern):
                suite = DiscoverRunner(
                    test_name_patterns=pattern
                ).build_suite(['test_runner_apps.simple'])
                self.assertEqual(expected, self.get_test_methods_names(suite))

    def test_file_path(self):
        with change_cwd(".."):
            count = DiscoverRunner().build_suite(
                ['test_runner_apps/sample/'],
            ).countTestCases()

        self.assertEqual(count, 5)

    def test_empty_label(self):
        """
        If the test label is empty, discovery should happen on the current
        working directory.
        """
        with change_cwd("."):
            suite = DiscoverRunner().build_suite([])
            self.assertEqual(
                suite._tests[0].id().split(".")[0],
                os.path.basename(os.getcwd()),
            )

    def test_empty_test_case(self):
        count = DiscoverRunner().build_suite(
            ['test_runner_apps.sample.tests_sample.EmptyTestCase'],
        ).countTestCases()

        self.assertEqual(count, 0)

    def test_discovery_on_package(self):
        count = DiscoverRunner().build_suite(
            ['test_runner_apps.sample.tests'],
        ).countTestCases()

        self.assertEqual(count, 1)

    def test_ignore_adjacent(self):
        """
        When given a dotted path to a module, unittest discovery searches
        not just the module, but also the directory containing the module.

        This results in tests from adjacent modules being run when they
        should not. The discover runner avoids this behavior.
        """
        count = DiscoverRunner().build_suite(
            ['test_runner_apps.sample.empty'],
        ).countTestCases()

        self.assertEqual(count, 0)

    def test_testcase_ordering(self):
        with change_cwd(".."):
            suite = DiscoverRunner().build_suite(['test_runner_apps/sample/'])
            self.assertEqual(
                suite._tests[0].__class__.__name__,
                'TestDjangoTestCase',
                msg="TestDjangoTestCase should be the first test case")
            self.assertEqual(
                suite._tests[1].__class__.__name__,
                'TestZimpleTestCase',
                msg="TestZimpleTestCase should be the second test case")
            # All others can follow in unspecified order, including doctests
            self.assertIn('DocTestCase', [t.__class__.__name__ for t in suite._tests[2:]])

    def test_duplicates_ignored(self):
        """
        Tests shouldn't be discovered twice when discovering on overlapping paths.
        """
        base_app = 'forms_tests'
        sub_app = 'forms_tests.field_tests'
        with self.modify_settings(INSTALLED_APPS={'append': sub_app}):
            single = DiscoverRunner().build_suite([base_app]).countTestCases()
            dups = DiscoverRunner().build_suite([base_app, sub_app]).countTestCases()
        self.assertEqual(single, dups)

    def test_reverse(self):
        """
        Reverse should reorder tests while maintaining the grouping specified
        by ``DiscoverRunner.reorder_by``.
        """
        runner = DiscoverRunner(reverse=True)
        suite = runner.build_suite(
            test_labels=('test_runner_apps.sample', 'test_runner_apps.simple'))
        self.assertIn('test_runner_apps.simple', next(iter(suite)).id(),
                      msg="Test labels should be reversed.")
        suite = runner.build_suite(test_labels=('test_runner_apps.simple',))
        suite = tuple(suite)
        self.assertIn('DjangoCase', suite[0].id(),
                      msg="Test groups should not be reversed.")
        self.assertIn('SimpleCase', suite[4].id(),
                      msg="Test groups order should be preserved.")
        self.assertIn('DjangoCase2', suite[0].id(),
                      msg="Django test cases should be reversed.")
        self.assertIn('SimpleCase2', suite[4].id(),
                      msg="Simple test cases should be reversed.")
        self.assertIn('UnittestCase2', suite[8].id(),
                      msg="Unittest test cases should be reversed.")
        self.assertIn('test_2', suite[0].id(),
                      msg="Methods of Django cases should be reversed.")
        self.assertIn('test_2', suite[4].id(),
                      msg="Methods of simple cases should be reversed.")
        self.assertIn('test_2', suite[9].id(),
                      msg="Methods of unittest cases should be reversed.")

    def test_overridable_get_test_runner_kwargs(self):
        self.assertIsInstance(DiscoverRunner().get_test_runner_kwargs(), dict)

    def test_overridable_test_suite(self):
        self.assertEqual(DiscoverRunner().test_suite, TestSuite)

    def test_overridable_test_runner(self):
        self.assertEqual(DiscoverRunner().test_runner, TextTestRunner)

    def test_overridable_test_loader(self):
        self.assertEqual(DiscoverRunner().test_loader, defaultTestLoader)

    def test_tags(self):
        runner = DiscoverRunner(tags=['core'])
        self.assertEqual(runner.build_suite(['test_runner_apps.tagged.tests']).countTestCases(), 1)
        runner = DiscoverRunner(tags=['fast'])
        self.assertEqual(runner.build_suite(['test_runner_apps.tagged.tests']).countTestCases(), 2)
        runner = DiscoverRunner(tags=['slow'])
        self.assertEqual(runner.build_suite(['test_runner_apps.tagged.tests']).countTestCases(), 2)

    def test_exclude_tags(self):
        runner = DiscoverRunner(tags=['fast'], exclude_tags=['core'])
        self.assertEqual(runner.build_suite(['test_runner_apps.tagged.tests']).countTestCases(), 1)
        runner = DiscoverRunner(tags=['fast'], exclude_tags=['slow'])
        self.assertEqual(runner.build_suite(['test_runner_apps.tagged.tests']).countTestCases(), 0)
        runner = DiscoverRunner(exclude_tags=['slow'])
        self.assertEqual(runner.build_suite(['test_runner_apps.tagged.tests']).countTestCases(), 0)

    def test_tag_inheritance(self):
        def count_tests(**kwargs):
            suite = DiscoverRunner(**kwargs).build_suite(['test_runner_apps.tagged.tests_inheritance'])
            return suite.countTestCases()

        self.assertEqual(count_tests(tags=['foo']), 4)
        self.assertEqual(count_tests(tags=['bar']), 2)
        self.assertEqual(count_tests(tags=['baz']), 2)
        self.assertEqual(count_tests(tags=['foo'], exclude_tags=['bar']), 2)
        self.assertEqual(count_tests(tags=['foo'], exclude_tags=['bar', 'baz']), 1)
        self.assertEqual(count_tests(exclude_tags=['foo']), 0)

    def test_included_tags_displayed(self):
        runner = DiscoverRunner(tags=['foo', 'bar'], verbosity=2)
        with captured_stdout() as stdout:
            runner.build_suite(['test_runner_apps.tagged.tests'])
            self.assertIn('Including test tag(s): bar, foo.\n', stdout.getvalue())

    def test_excluded_tags_displayed(self):
        runner = DiscoverRunner(exclude_tags=['foo', 'bar'], verbosity=3)
        with captured_stdout() as stdout:
            runner.build_suite(['test_runner_apps.tagged.tests'])
            self.assertIn('Excluding test tag(s): bar, foo.\n', stdout.getvalue())

    def test_pdb_with_parallel(self):
        msg = (
            'You cannot use --pdb with parallel tests; pass --parallel=1 to '
            'use it.'
        )
        with self.assertRaisesMessage(ValueError, msg):
            DiscoverRunner(pdb=True, parallel=2)

    def test_buffer_with_parallel(self):
        msg = (
            'You cannot use -b/--buffer with parallel tests; pass '
            '--parallel=1 to use it.'
        )
        with self.assertRaisesMessage(ValueError, msg):
            DiscoverRunner(buffer=True, parallel=2)

    def test_buffer_mode_test_pass(self):
        runner = DiscoverRunner(buffer=True, verbose=0)
        with captured_stdout() as stdout, captured_stderr() as stderr:
            suite = runner.build_suite([
                'test_runner_apps.buffer.tests_buffer.WriteToStdoutStderrTestCase.test_pass',
            ])
            runner.run_suite(suite)
        self.assertNotIn('Write to stderr.', stderr.getvalue())
        self.assertNotIn('Write to stdout.', stdout.getvalue())

    def test_buffer_mode_test_fail(self):
        runner = DiscoverRunner(buffer=True, verbose=0)
        with captured_stdout() as stdout, captured_stderr() as stderr:
            suite = runner.build_suite([
                'test_runner_apps.buffer.tests_buffer.WriteToStdoutStderrTestCase.test_fail',
            ])
            runner.run_suite(suite)
        self.assertIn('Write to stderr.', stderr.getvalue())
        self.assertIn('Write to stdout.', stdout.getvalue())

    @mock.patch('faulthandler.enable')
    def test_faulthandler_enabled(self, mocked_enable):
        with mock.patch('faulthandler.is_enabled', return_value=False):
            DiscoverRunner(enable_faulthandler=True)
            mocked_enable.assert_called()

    @mock.patch('faulthandler.enable')
    def test_faulthandler_already_enabled(self, mocked_enable):
        with mock.patch('faulthandler.is_enabled', return_value=True):
            DiscoverRunner(enable_faulthandler=True)
            mocked_enable.assert_not_called()

    @mock.patch('faulthandler.enable')
    def test_faulthandler_enabled_fileno(self, mocked_enable):
        # sys.stderr that is not an actual file.
        with mock.patch('faulthandler.is_enabled', return_value=False), captured_stderr():
            DiscoverRunner(enable_faulthandler=True)
            mocked_enable.assert_called()

    @mock.patch('faulthandler.enable')
    def test_faulthandler_disabled(self, mocked_enable):
        with mock.patch('faulthandler.is_enabled', return_value=False):
            DiscoverRunner(enable_faulthandler=False)
            mocked_enable.assert_not_called()

    def test_timings_not_captured(self):
        runner = DiscoverRunner(timing=False)
        with captured_stderr() as stderr:
            with runner.time_keeper.timed('test'):
                pass
            runner.time_keeper.print_results()
        self.assertTrue(isinstance(runner.time_keeper, NullTimeKeeper))
        self.assertNotIn('test', stderr.getvalue())

    def test_timings_captured(self):
        runner = DiscoverRunner(timing=True)
        with captured_stderr() as stderr:
            with runner.time_keeper.timed('test'):
                pass
            runner.time_keeper.print_results()
        self.assertTrue(isinstance(runner.time_keeper, TimeKeeper))
        self.assertIn('test', stderr.getvalue())


class DiscoverRunnerGetDatabasesTests(SimpleTestCase):
    runner = DiscoverRunner(verbosity=2)
    skip_msg = 'Skipping setup of unused database(s): '

    def get_databases(self, test_labels):
        suite = self.runner.build_suite(test_labels)
        with captured_stdout() as stdout:
            databases = self.runner.get_databases(suite)
        return databases, stdout.getvalue()

    def assertSkippedDatabases(self, test_labels, expected_databases):
        databases, output = self.get_databases(test_labels)
        self.assertEqual(databases, expected_databases)
        skipped_databases = set(connections) - expected_databases
        if skipped_databases:
            self.assertIn(self.skip_msg + ', '.join(sorted(skipped_databases)), output)
        else:
            self.assertNotIn(self.skip_msg, output)

    def test_mixed(self):
        databases, output = self.get_databases(['test_runner_apps.databases.tests'])
        self.assertEqual(databases, set(connections))
        self.assertNotIn(self.skip_msg, output)

    def test_all(self):
        databases, output = self.get_databases(['test_runner_apps.databases.tests.AllDatabasesTests'])
        self.assertEqual(databases, set(connections))
        self.assertNotIn(self.skip_msg, output)

    def test_default_and_other(self):
        self.assertSkippedDatabases([
            'test_runner_apps.databases.tests.DefaultDatabaseTests',
            'test_runner_apps.databases.tests.OtherDatabaseTests',
        ], {'default', 'other'})

    def test_default_only(self):
        self.assertSkippedDatabases([
            'test_runner_apps.databases.tests.DefaultDatabaseTests',
        ], {'default'})

    def test_other_only(self):
        self.assertSkippedDatabases([
            'test_runner_apps.databases.tests.OtherDatabaseTests'
        ], {'other'})

    def test_no_databases_required(self):
        self.assertSkippedDatabases([
            'test_runner_apps.databases.tests.NoDatabaseTests'
        ], set())
