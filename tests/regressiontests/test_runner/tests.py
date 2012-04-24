"""
Tests for django test runner
"""
from __future__ import absolute_import

from optparse import make_option

from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django import db
from django.db import connection
from django.test import simple, TransactionTestCase
from django.test.simple import DjangoTestSuiteRunner, get_tests
from django.test.testcases import connections_support_transactions
from django.utils import unittest
from django.utils.importlib import import_module

from ..admin_scripts.tests import AdminScriptTestCase
from .models import Person


TEST_APP_OK = 'regressiontests.test_runner.valid_app.models'
TEST_APP_ERROR = 'regressiontests.test_runner.invalid_app.models'


class DependencyOrderingTests(unittest.TestCase):

    def test_simple_dependencies(self):
        raw = [
            ('s1', ('s1_db', ['alpha'])),
            ('s2', ('s2_db', ['bravo'])),
            ('s3', ('s3_db', ['charlie'])),
        ]
        dependencies = {
            'alpha': ['charlie'],
            'bravo': ['charlie'],
        }

        ordered = simple.dependency_ordered(raw, dependencies=dependencies)
        ordered_sigs = [sig for sig,value in ordered]

        self.assertIn('s1', ordered_sigs)
        self.assertIn('s2', ordered_sigs)
        self.assertIn('s3', ordered_sigs)
        self.assertLess(ordered_sigs.index('s3'), ordered_sigs.index('s1'))
        self.assertLess(ordered_sigs.index('s3'), ordered_sigs.index('s2'))

    def test_chained_dependencies(self):
        raw = [
            ('s1', ('s1_db', ['alpha'])),
            ('s2', ('s2_db', ['bravo'])),
            ('s3', ('s3_db', ['charlie'])),
        ]
        dependencies = {
            'alpha': ['bravo'],
            'bravo': ['charlie'],
        }

        ordered = simple.dependency_ordered(raw, dependencies=dependencies)
        ordered_sigs = [sig for sig,value in ordered]

        self.assertIn('s1', ordered_sigs)
        self.assertIn('s2', ordered_sigs)
        self.assertIn('s3', ordered_sigs)

        # Explicit dependencies
        self.assertLess(ordered_sigs.index('s2'), ordered_sigs.index('s1'))
        self.assertLess(ordered_sigs.index('s3'), ordered_sigs.index('s2'))

        # Implied dependencies
        self.assertLess(ordered_sigs.index('s3'), ordered_sigs.index('s1'))

    def test_multiple_dependencies(self):
        raw = [
            ('s1', ('s1_db', ['alpha'])),
            ('s2', ('s2_db', ['bravo'])),
            ('s3', ('s3_db', ['charlie'])),
            ('s4', ('s4_db', ['delta'])),
        ]
        dependencies = {
            'alpha': ['bravo','delta'],
            'bravo': ['charlie'],
            'delta': ['charlie'],
        }

        ordered = simple.dependency_ordered(raw, dependencies=dependencies)
        ordered_sigs = [sig for sig,aliases in ordered]

        self.assertIn('s1', ordered_sigs)
        self.assertIn('s2', ordered_sigs)
        self.assertIn('s3', ordered_sigs)
        self.assertIn('s4', ordered_sigs)

        # Explicit dependencies
        self.assertLess(ordered_sigs.index('s2'), ordered_sigs.index('s1'))
        self.assertLess(ordered_sigs.index('s4'), ordered_sigs.index('s1'))
        self.assertLess(ordered_sigs.index('s3'), ordered_sigs.index('s2'))
        self.assertLess(ordered_sigs.index('s3'), ordered_sigs.index('s4'))

        # Implicit dependencies
        self.assertLess(ordered_sigs.index('s3'), ordered_sigs.index('s1'))

    def test_circular_dependencies(self):
        raw = [
            ('s1', ('s1_db', ['alpha'])),
            ('s2', ('s2_db', ['bravo'])),
        ]
        dependencies = {
            'bravo': ['alpha'],
            'alpha': ['bravo'],
        }

        self.assertRaises(ImproperlyConfigured, simple.dependency_ordered, raw, dependencies=dependencies)

    def test_own_alias_dependency(self):
        raw = [
            ('s1', ('s1_db', ['alpha', 'bravo']))
        ]
        dependencies = {
            'alpha': ['bravo']
        }

        with self.assertRaises(ImproperlyConfigured):
            simple.dependency_ordered(raw, dependencies=dependencies)

        # reordering aliases shouldn't matter
        raw = [
            ('s1', ('s1_db', ['bravo', 'alpha']))
        ]

        with self.assertRaises(ImproperlyConfigured):
            simple.dependency_ordered(raw, dependencies=dependencies)


class MockTestRunner(object):
    invoked = False

    def __init__(self, *args, **kwargs):
        pass

    def run_tests(self, test_labels, extra_tests=None, **kwargs):
        MockTestRunner.invoked = True


class ManageCommandTests(unittest.TestCase):

    def test_custom_test_runner(self):
        call_command('test', 'sites',
                     testrunner='regressiontests.test_runner.tests.MockTestRunner')
        self.assertTrue(MockTestRunner.invoked,
                        "The custom test runner has not been invoked")


class CustomOptionsTestRunner(simple.DjangoTestSuiteRunner):
    option_list = (
        make_option('--option_a','-a', action='store', dest='option_a', default='1'),
        make_option('--option_b','-b', action='store', dest='option_b', default='2'),
        make_option('--option_c','-c', action='store', dest='option_c', default='3'),
    )

    def __init__(self, verbosity=1, interactive=True, failfast=True, option_a=None, option_b=None, option_c=None, **kwargs):
        super(CustomOptionsTestRunner, self).__init__(verbosity=verbosity, interactive=interactive,
                                                      failfast=failfast)
        self.option_a = option_a
        self.option_b = option_b
        self.option_c = option_c

    def run_tests(self, test_labels, extra_tests=None, **kwargs):
        print "%s:%s:%s" % (self.option_a, self.option_b, self.option_c)


class CustomTestRunnerOptionsTests(AdminScriptTestCase):

    def setUp(self):
        settings = {
            'TEST_RUNNER': '\'regressiontests.test_runner.tests.CustomOptionsTestRunner\'',
        }
        self.write_settings('settings.py', sdict=settings)

    def tearDown(self):
        self.remove_settings('settings.py')

    def test_default_options(self):
        args = ['test', '--settings=regressiontests.settings']
        out, err = self.run_django_admin(args)
        self.assertNoOutput(err)
        self.assertOutput(out, '1:2:3')

    def test_default_and_given_options(self):
        args = ['test', '--settings=regressiontests.settings', '--option_b=foo']
        out, err = self.run_django_admin(args)
        self.assertNoOutput(err)
        self.assertOutput(out, '1:foo:3')

    def test_option_name_and_value_separated(self):
        args = ['test', '--settings=regressiontests.settings', '--option_b', 'foo']
        out, err = self.run_django_admin(args)
        self.assertNoOutput(err)
        self.assertOutput(out, '1:foo:3')

    def test_all_options_given(self):
        args = ['test', '--settings=regressiontests.settings', '--option_a=bar', '--option_b=foo', '--option_c=31337']
        out, err = self.run_django_admin(args)
        self.assertNoOutput(err)
        self.assertOutput(out, 'bar:foo:31337')


class Ticket16885RegressionTests(unittest.TestCase):
    def test_ticket_16885(self):
        """Features are also confirmed on mirrored databases."""
        old_db_connections = db.connections
        try:
            db.connections = db.ConnectionHandler({
                'default': {
                    'ENGINE': 'django.db.backends.sqlite3',
                },
                'slave': {
                    'ENGINE': 'django.db.backends.sqlite3',
                    'TEST_MIRROR': 'default',
                },
            })
            slave = db.connections['slave']
            self.assertEqual(slave.features.supports_transactions, None)
            DjangoTestSuiteRunner(verbosity=0).setup_databases()
            self.assertNotEqual(slave.features.supports_transactions, None)
        finally:
            db.connections = old_db_connections


class Ticket17477RegressionTests(AdminScriptTestCase):
    def setUp(self):
        self.write_settings('settings.py')

    def tearDown(self):
        self.remove_settings('settings.py')

    def test_ticket_17477(self):
        """'manage.py help test' works after r16352."""
        args = ['help', 'test']
        out, err = self.run_manage(args)
        self.assertNoOutput(err)


class ModulesTestsPackages(unittest.TestCase):
    def test_get_tests(self):
        "Check that the get_tests helper function can find tests in a directory"
        module = import_module(TEST_APP_OK)
        tests = get_tests(module)
        self.assertIsInstance(tests, type(module))

    def test_import_error(self):
        "Test for #12658 - Tests with ImportError's shouldn't fail silently"
        module = import_module(TEST_APP_ERROR)
        self.assertRaises(ImportError, get_tests, module)


class Sqlite3InMemoryTestDbs(unittest.TestCase):

    @unittest.skipUnless(all(db.connections[conn].vendor == 'sqlite' for conn in db.connections),
                         "This is a sqlite-specific issue")
    def test_transaction_support(self):
        """Ticket #16329: sqlite3 in-memory test databases"""
        old_db_connections = db.connections
        for option in ('NAME', 'TEST_NAME'):
            try:
                db.connections = db.ConnectionHandler({
                    'default': {
                        'ENGINE': 'django.db.backends.sqlite3',
                        option: ':memory:',
                    },
                    'other': {
                        'ENGINE': 'django.db.backends.sqlite3',
                        option: ':memory:',
                    },
                })
                other = db.connections['other']
                self.assertIsNone(other.features.supports_transactions)
                DjangoTestSuiteRunner(verbosity=0).setup_databases()
                msg = "DATABASES setting '%s' option set to sqlite3's ':memory:' value shouldn't interfere with transaction support detection." % option
                # Transaction support should be properly initialised for the 'other' DB
                self.assertIsNotNone(other.features.supports_transactions, msg)
                # And all the DBs should report that they support transactions
                self.assertTrue(connections_support_transactions(), msg)
            finally:
                db.connections = old_db_connections


class AutoIncrementResetTest(TransactionTestCase):
    """
    Here we test creating the same model two times in different test methods,
    and check that both times they get "1" as their PK value. That is, we test
    that AutoField values start from 1 for each transactional test case.
    """
    @unittest.skipIf(connection.vendor == 'oracle',
                     "Oracle's auto-increment fields are not reset between "
                     "tests")
    def test_autoincrement_reset1(self):
        p = Person.objects.create(first_name='Jack', last_name='Smith')
        self.assertEquals(p.pk, 1)

    @unittest.skipIf(connection.vendor == 'oracle',
                     "Oracle's auto-increment fields are not reset between "
                     "tests")
    def test_autoincrement_reset2(self):
        p = Person.objects.create(first_name='Jack', last_name='Smith')
        self.assertEquals(p.pk, 1)
