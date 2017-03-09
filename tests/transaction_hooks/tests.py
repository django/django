from contextlib import suppress

from django.db import connection, transaction
from django.test import TransactionTestCase, skipUnlessDBFeature

from .models import Thing


class ForcedError(Exception):
    pass


class TestConnectionOnCommit(TransactionTestCase):
    """
    Tests for transaction.on_commit().

    Creation/checking of database objects in parallel with callback tracking is
    to verify that the behavior of the two match in all tested cases.
    """
    available_apps = ['transaction_hooks']

    def setUp(self):
        self.notified = []

    def notify(self, id_):
        if id_ == 'error':
            raise ForcedError()
        self.notified.append(id_)

    def do(self, num):
        """Create a Thing instance and notify about it."""
        Thing.objects.create(num=num)
        transaction.on_commit(lambda: self.notify(num))

    def assertDone(self, nums):
        self.assertNotified(nums)
        self.assertEqual(sorted(t.num for t in Thing.objects.all()), sorted(nums))

    def assertNotified(self, nums):
        self.assertEqual(self.notified, nums)

    def test_executes_immediately_if_no_transaction(self):
        self.do(1)
        self.assertDone([1])

    def test_delays_execution_until_after_transaction_commit(self):
        with transaction.atomic():
            self.do(1)
            self.assertNotified([])
        self.assertDone([1])

    def test_does_not_execute_if_transaction_rolled_back(self):
        with suppress(ForcedError):
            with transaction.atomic():
                self.do(1)
                raise ForcedError()

        self.assertDone([])

    def test_executes_only_after_final_transaction_committed(self):
        with transaction.atomic():
            with transaction.atomic():
                self.do(1)
                self.assertNotified([])
            self.assertNotified([])
        self.assertDone([1])

    def test_discards_hooks_from_rolled_back_savepoint(self):
        with transaction.atomic():
            # one successful savepoint
            with transaction.atomic():
                self.do(1)
            # one failed savepoint
            with suppress(ForcedError):
                with transaction.atomic():
                    self.do(2)
                    raise ForcedError()
            # another successful savepoint
            with transaction.atomic():
                self.do(3)

        # only hooks registered during successful savepoints execute
        self.assertDone([1, 3])

    def test_no_hooks_run_from_failed_transaction(self):
        """If outer transaction fails, no hooks from within it run."""
        with suppress(ForcedError):
            with transaction.atomic():
                with transaction.atomic():
                    self.do(1)
                raise ForcedError()

        self.assertDone([])

    def test_inner_savepoint_rolled_back_with_outer(self):
        with transaction.atomic():
            with suppress(ForcedError):
                with transaction.atomic():
                    with transaction.atomic():
                        self.do(1)
                    raise ForcedError()
            self.do(2)

        self.assertDone([2])

    def test_no_savepoints_atomic_merged_with_outer(self):
        with transaction.atomic():
            with transaction.atomic():
                self.do(1)
                with suppress(ForcedError):
                    with transaction.atomic(savepoint=False):
                        raise ForcedError()

        self.assertDone([])

    def test_inner_savepoint_does_not_affect_outer(self):
        with transaction.atomic():
            with transaction.atomic():
                self.do(1)
                with suppress(ForcedError):
                    with transaction.atomic():
                        raise ForcedError()

        self.assertDone([1])

    def test_runs_hooks_in_order_registered(self):
        with transaction.atomic():
            self.do(1)
            with transaction.atomic():
                self.do(2)
            self.do(3)

        self.assertDone([1, 2, 3])

    def test_hooks_cleared_after_successful_commit(self):
        with transaction.atomic():
            self.do(1)
        with transaction.atomic():
            self.do(2)

        self.assertDone([1, 2])  # not [1, 1, 2]

    def test_hooks_cleared_after_rollback(self):
        with suppress(ForcedError):
            with transaction.atomic():
                self.do(1)
                raise ForcedError()

        with transaction.atomic():
            self.do(2)

        self.assertDone([2])

    @skipUnlessDBFeature('test_db_allows_multiple_connections')
    def test_hooks_cleared_on_reconnect(self):
        with transaction.atomic():
            self.do(1)
            connection.close()

        connection.connect()

        with transaction.atomic():
            self.do(2)

        self.assertDone([2])

    def test_error_in_hook_doesnt_prevent_clearing_hooks(self):
        with suppress(ForcedError):
            with transaction.atomic():
                transaction.on_commit(lambda: self.notify('error'))

        with transaction.atomic():
            self.do(1)

        self.assertDone([1])

    def test_db_query_in_hook(self):
        with transaction.atomic():
            Thing.objects.create(num=1)
            transaction.on_commit(
                lambda: [self.notify(t.num) for t in Thing.objects.all()]
            )

        self.assertDone([1])

    def test_transaction_in_hook(self):
        def on_commit():
            with transaction.atomic():
                t = Thing.objects.create(num=1)
                self.notify(t.num)

        with transaction.atomic():
            transaction.on_commit(on_commit)

        self.assertDone([1])

    def test_hook_in_hook(self):
        def on_commit(i, add_hook):
            with transaction.atomic():
                if add_hook:
                    transaction.on_commit(lambda: on_commit(i + 10, False))
                t = Thing.objects.create(num=i)
                self.notify(t.num)

        with transaction.atomic():
            transaction.on_commit(lambda: on_commit(1, True))
            transaction.on_commit(lambda: on_commit(2, True))

        self.assertDone([1, 11, 2, 12])

    def test_raises_exception_non_autocommit_mode(self):
        def should_never_be_called():
            raise AssertionError('this function should never be called')

        try:
            connection.set_autocommit(False)
            with self.assertRaises(transaction.TransactionManagementError):
                transaction.on_commit(should_never_be_called)
        finally:
            connection.set_autocommit(True)
