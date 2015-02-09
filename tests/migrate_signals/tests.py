from django.apps import apps
from django.core import management
from django.db.models import signals
from django.test import TestCase, override_settings
from django.utils import six

APP_CONFIG = apps.get_app_config('migrate_signals')
PRE_MIGRATE_ARGS = ['app_config', 'verbosity', 'interactive', 'using']
MIGRATE_DATABASE = 'default'
MIGRATE_VERBOSITY = 1
MIGRATE_INTERACTIVE = False


class PreMigrateReceiver(object):
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

    def __init__(self):
        self.call_counter = 0
        self.call_args = None

    def __call__(self, signal, sender, **kwargs):
        # Although test runner calls migrate for several databases,
        # testing for only one of them is quite sufficient.
        if kwargs['using'] == MIGRATE_DATABASE:
            self.call_counter = self.call_counter + 1
            self.call_args = kwargs
            # we need to test only one call of migrate
            signals.pre_migrate.disconnect(pre_migrate_receiver, sender=APP_CONFIG)


# We connect receiver here and not in unit test code because we need to
# connect receiver before test runner creates database.  That is, sequence of
# actions would be:
#
#   1. Test runner imports this module.
#   2. We connect receiver.
#   3. Test runner calls migrate for create default database.
#   4. Test runner execute our unit test code.
pre_migrate_receiver = OneTimeReceiver()
signals.pre_migrate.connect(pre_migrate_receiver, sender=APP_CONFIG)


class MigrateSignalTests(TestCase):

    available_apps = ['migrate_signals']

    def test_pre_migrate_call_time(self):
        self.assertEqual(pre_migrate_receiver.call_counter, 1)

    def test_pre_migrate_args(self):
        r = PreMigrateReceiver()
        signals.pre_migrate.connect(r, sender=APP_CONFIG)
        management.call_command('migrate', database=MIGRATE_DATABASE,
            verbosity=MIGRATE_VERBOSITY, interactive=MIGRATE_INTERACTIVE,
            load_initial_data=False, stdout=six.StringIO())

        args = r.call_args
        self.assertEqual(r.call_counter, 1)
        self.assertEqual(set(args), set(PRE_MIGRATE_ARGS))
        self.assertEqual(args['app_config'], APP_CONFIG)
        self.assertEqual(args['verbosity'], MIGRATE_VERBOSITY)
        self.assertEqual(args['interactive'], MIGRATE_INTERACTIVE)
        self.assertEqual(args['using'], 'default')

    @override_settings(MIGRATION_MODULES={'migrate_signals': 'migrate_signals.custom_migrations'})
    def test_pre_migrate_migrations_only(self):
        """
        If all apps have migrations, pre_migrate should be sent.
        """
        r = PreMigrateReceiver()
        signals.pre_migrate.connect(r, sender=APP_CONFIG)
        stdout = six.StringIO()
        management.call_command('migrate', database=MIGRATE_DATABASE,
            verbosity=MIGRATE_VERBOSITY, interactive=MIGRATE_INTERACTIVE,
            load_initial_data=False, stdout=stdout)
        args = r.call_args
        self.assertEqual(r.call_counter, 1)
        self.assertEqual(set(args), set(PRE_MIGRATE_ARGS))
        self.assertEqual(args['app_config'], APP_CONFIG)
        self.assertEqual(args['verbosity'], MIGRATE_VERBOSITY)
        self.assertEqual(args['interactive'], MIGRATE_INTERACTIVE)
        self.assertEqual(args['using'], 'default')
