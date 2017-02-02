from unittest import mock

from django.test import TransactionTestCase


class TestSerializedRollbackInhibitsPostMigrate(TransactionTestCase):
    """
    TransactionTestCase._fixture_teardown() inhibits the post_migrate signal
    for test classes with serialized_rollback=True.
    """
    available_apps = ['test_utils']
    serialized_rollback = True

    def setUp(self):
        # self.available_apps must be None to test the serialized_rollback
        # condition.
        self.available_apps = None

    def tearDown(self):
        self.available_apps = ['test_utils']

    @mock.patch('django.test.testcases.call_command')
    def test(self, call_command):
        # with a mocked call_command(), this doesn't have any effect.
        self._fixture_teardown()
        call_command.assert_called_with(
            'flush', interactive=False, allow_cascade=False,
            reset_sequences=False, inhibit_post_migrate=True,
            database='default', verbosity=0,
        )
