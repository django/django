from django.db.models import signals
from django.test import TestCase
from django.core import management
from django.utils import six

from . import models


PRE_SYNCDB_ARGS = ['app', 'create_models', 'verbosity', 'interactive', 'db']
SYNCDB_DATABASE = 'default'
SYNCDB_VERBOSITY = 1
SYNCDB_INTERACTIVE = False


class PreSyncdbReceiver(object):
    def __init__(self):
        self.call_counter = 0
        self.call_args = None

    def __call__(self, signal, sender, **kwargs):
        self.call_counter = self.call_counter + 1
        self.call_args = kwargs


class OneTimeReceiver(object):
    """
    Special receiver for handle the fact that test runner calls syncdb for
    several databases and several times for some of them.
    """

    def __init__(self):
        self.call_counter = 0
        self.call_args = None

    def __call__(self, signal, sender, **kwargs):
        # Although test runner calls syncdb for several databases,
        # testing for only one of them is quite sufficient.
        if kwargs['db'] == SYNCDB_DATABASE:
            self.call_counter = self.call_counter + 1
            self.call_args = kwargs
            # we need to test only one call of syncdb
            signals.pre_syncdb.disconnect(pre_syncdb_receiver, sender=models)


# We connect receiver here and not in unit test code because we need to
# connect receiver before test runner creates database.  That is, sequence of
# actions would be:
#
#   1. Test runner imports this module.
#   2. We connect receiver.
#   3. Test runner calls syncdb for create default database.
#   4. Test runner execute our unit test code.
pre_syncdb_receiver = OneTimeReceiver()
signals.pre_syncdb.connect(pre_syncdb_receiver, sender=models)


class SyncdbSignalTests(TestCase):

    available_apps = [
        'syncdb_signals',
    ]

    def test_pre_syncdb_call_time(self):
        self.assertEqual(pre_syncdb_receiver.call_counter, 1)

    def test_pre_syncdb_args(self):
        r = PreSyncdbReceiver()
        signals.pre_syncdb.connect(r, sender=models)
        management.call_command('syncdb', database=SYNCDB_DATABASE,
            verbosity=SYNCDB_VERBOSITY, interactive=SYNCDB_INTERACTIVE,
            load_initial_data=False, stdout=six.StringIO())

        args = r.call_args
        self.assertEqual(r.call_counter, 1)
        self.assertEqual(set(args), set(PRE_SYNCDB_ARGS))
        self.assertEqual(args['app'], models)
        self.assertEqual(args['verbosity'], SYNCDB_VERBOSITY)
        self.assertEqual(args['interactive'], SYNCDB_INTERACTIVE)
        self.assertEqual(args['db'], 'default')
