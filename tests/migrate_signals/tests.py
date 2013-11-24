import warnings
from django.db.models import signals
from django.test import TestCase
from django.core import management
from django.utils import six

from . import models


MIGRATE_DATABASE = 'default'
MIGRATE_VERBOSITY = 1
MIGRATE_INTERACTIVE = False


class Receiver(object):
    def __init__(self):
        self.call_counter = 0
        self.call_args = None

    def __call__(self, signal, sender, **kwargs):
        self.call_counter = self.call_counter + 1
        self.call_args = kwargs


class OneTimeReceiver(object):
    """
    Special receiver for handle the fact that test runner calls migrate for
    several databases and several times for some of them.
    """

    def __init__(self, signal, db_kwarg):
        self.signal = signal
        self.db_kwarg = db_kwarg
        self.call_counter = 0
        self.call_args = None

        with warnings.catch_warnings(record=True) as recorded:
            self.signal.connect(self, sender=models)

    def __call__(self, signal, sender, **kwargs):
        # Although test runner calls migrate for several databases,
        # testing for only one of them is quite sufficient.
        if kwargs[self.db_kwarg] == MIGRATE_DATABASE:
            self.call_counter = self.call_counter + 1
            self.call_args = kwargs
            # we need to test only one call of migrate
            self.signal.disconnect(self, sender=models)


# We connect receiver here and not in unit test code because we need to
# connect receiver before test runner creates database.  That is, sequence of
# actions would be:
#
#   1. Test runner imports this module.
#   2. We connect receiver.
#   3. Test runner calls migrate for create default database.
#   4. Test runner execute our unit test code.
pre_migrate_receiver = OneTimeReceiver(signals.pre_migrate, db_kwarg='using')
pre_syncdb_receiver = OneTimeReceiver(signals.pre_syncdb, db_kwarg='db')
post_migrate_receiver = OneTimeReceiver(signals.post_migrate, db_kwarg='using')
post_syncdb_receiver = OneTimeReceiver(signals.post_syncdb, db_kwarg='db')


class MigrateSignalTests(TestCase):

    available_apps = [
        'migrate_signals',
    ]

    @staticmethod
    def _call_migrate():
        management.call_command('migrate', database=MIGRATE_DATABASE,
                                verbosity=MIGRATE_VERBOSITY,
                                interactive=MIGRATE_INTERACTIVE,
                                load_initial_data=False, stdout=six.StringIO())

    def test_migrate_call_times(self):
        self.assertEqual(pre_migrate_receiver.call_counter, 1)
        self.assertEqual(pre_syncdb_receiver.call_counter, 1)
        self.assertEqual(post_migrate_receiver.call_counter, 1)
        self.assertEqual(post_syncdb_receiver.call_counter, 1)

    def test_pre_migrate_args(self):
        r = Receiver()
        signals.pre_migrate.connect(r, sender=models)

        self._call_migrate()

        args = r.call_args
        self.assertEqual(r.call_counter, 1)
        self.assertEqual(set(args), {"app", "create_models", "verbosity",
                                     "interactive", "using"})
        self.assertEqual(args['app'], models)
        self.assertEqual(args['verbosity'], MIGRATE_VERBOSITY)
        self.assertEqual(args['interactive'], MIGRATE_INTERACTIVE)
        self.assertEqual(args['using'], 'default')

    def test_pre_syncdb_args(self):
        warnings.simplefilter('always')

        with warnings.catch_warnings(record=True) as recorded:
            r = Receiver()
            signals.pre_syncdb.connect(r, sender=models)
            self._call_migrate()

            args = r.call_args
            self.assertEqual(r.call_counter, 1)
            self.assertEqual(set(args), {"app", "create_models", "verbosity",
                                         "interactive", "db"})
            self.assertEqual(args['app'], models)
            self.assertEqual(args['verbosity'], MIGRATE_VERBOSITY)
            self.assertEqual(args['interactive'], MIGRATE_INTERACTIVE)
            self.assertEqual(args['db'], 'default')

            msgs = [str(warning.message) for warning in recorded]
            self.assertEqual(msgs, [
                "pre_syncdb signal is deprecated and will be removed in "
                "Django 1.9, use pre_migrate instead."
            ])

    def test_post_migrate_args(self):
        r = Receiver()
        signals.post_migrate.connect(r, sender=models)
        self._call_migrate()

        args = r.call_args
        self.assertEqual(r.call_counter, 1)
        self.assertEqual(set(args), {"app", "created_models", "verbosity",
                                     "interactive", "using"})
        self.assertEqual(args['app'], models)
        self.assertEqual(args['verbosity'], MIGRATE_VERBOSITY)
        self.assertEqual(args['interactive'], MIGRATE_INTERACTIVE)
        self.assertEqual(args['using'], 'default')

    def test_post_syncdb_args(self):
        warnings.simplefilter('always')

        with warnings.catch_warnings(record=True) as recorded:
            r = Receiver()
            signals.post_syncdb.connect(r, sender=models)
            self._call_migrate()

            args = r.call_args
            self.assertEqual(r.call_counter, 1)
            self.assertEqual(set(args), {"app", "created_models", "verbosity",
                                         "interactive", "db"})
            self.assertEqual(args['app'], models)
            self.assertEqual(args['verbosity'], MIGRATE_VERBOSITY)
            self.assertEqual(args['interactive'], MIGRATE_INTERACTIVE)
            self.assertEqual(args['db'], 'default')

            msgs = [str(warning.message) for warning in recorded]
            self.assertEqual(msgs, [
                "post_syncdb signal is deprecated and will be removed in "
                "Django 1.9, use post_migrate instead."
            ])
