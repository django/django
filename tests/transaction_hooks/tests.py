import gc
import traceback
import weakref
from functools import partial

from django.db import connection, transaction
from django.test import TransactionTestCase, skipUnlessDBFeature

from .models import Thing


class ForcedError(Exception):
    pass


@skipUnlessDBFeature("supports_transactions")
class TestConnectionOnCommit(TransactionTestCase):
    """
    Tests for transaction.on_commit().

    Creation/checking of database objects in parallel with callback tracking is
    to verify that the behavior of the two match in all tested cases.
    """

    available_apps = ["transaction_hooks"]

    def setUp(self):
        self.notified = []

    def notify(self, id_):
        if id_ == "error":
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

    def test_robust_if_no_transaction(self):
        def robust_callback():
            raise ForcedError("robust callback")

        with self.assertLogs("django.db.backends.base", "ERROR") as cm:
            transaction.on_commit(robust_callback, robust=True)
            self.do(1)

        self.assertDone([1])
        log_record = cm.records[0]
        self.assertEqual(
            log_record.getMessage(),
            "Error calling TestConnectionOnCommit.test_robust_if_no_transaction."
            "<locals>.robust_callback in on_commit() (robust callback).",
        )
        self.assertIsNotNone(log_record.exc_info)
        raised_exception = log_record.exc_info[1]
        self.assertIsInstance(raised_exception, ForcedError)
        self.assertEqual(str(raised_exception), "robust callback")

    def test_robust_if_no_transaction_with_callback_as_partial(self):
        def robust_callback():
            raise ForcedError("robust callback")

        robust_callback_partial = partial(robust_callback)

        with self.assertLogs("django.db.backends.base", "ERROR") as cm:
            transaction.on_commit(robust_callback_partial, robust=True)
            self.do(1)

        self.assertDone([1])
        log_record = cm.records[0]
        self.assertEqual(
            log_record.getMessage(),
            f"Error calling {robust_callback_partial} "
            f"in on_commit() (robust callback).",
        )
        self.assertIsNotNone(log_record.exc_info)
        raised_exception = log_record.exc_info[1]
        self.assertIsInstance(raised_exception, ForcedError)
        self.assertEqual(str(raised_exception), "robust callback")

    def test_robust_transaction(self):
        def robust_callback():
            raise ForcedError("robust callback")

        with self.assertLogs("django.db.backends", "ERROR") as cm:
            with transaction.atomic():
                transaction.on_commit(robust_callback, robust=True)
                self.do(1)

        self.assertDone([1])
        log_record = cm.records[0]
        self.assertEqual(
            log_record.getMessage(),
            "Error calling TestConnectionOnCommit.test_robust_transaction.<locals>."
            "robust_callback in on_commit() during transaction (robust callback).",
        )
        self.assertIsNotNone(log_record.exc_info)
        raised_exception = log_record.exc_info[1]
        self.assertIsInstance(raised_exception, ForcedError)
        self.assertEqual(str(raised_exception), "robust callback")

    def test_robust_transaction_with_callback_as_partial(self):
        def robust_callback():
            raise ForcedError("robust callback")

        robust_callback_partial = partial(robust_callback)

        with self.assertLogs("django.db.backends", "ERROR") as cm:
            with transaction.atomic():
                transaction.on_commit(robust_callback_partial, robust=True)
                self.do(1)

        self.assertDone([1])
        log_record = cm.records[0]
        self.assertEqual(
            log_record.getMessage(),
            f"Error calling {robust_callback_partial} in on_commit() during "
            "transaction (robust callback).",
        )
        self.assertIsNotNone(log_record.exc_info)
        raised_exception = log_record.exc_info[1]
        self.assertIsInstance(raised_exception, ForcedError)
        self.assertEqual(str(raised_exception), "robust callback")

    def test_delays_execution_until_after_transaction_commit(self):
        with transaction.atomic():
            self.do(1)
            self.assertNotified([])
        self.assertDone([1])

    def test_does_not_execute_if_transaction_rolled_back(self):
        try:
            with transaction.atomic():
                self.do(1)
                raise ForcedError()
        except ForcedError:
            pass

        self.assertDone([])

    def test_executes_only_after_final_transaction_committed(self):
        with transaction.atomic():
            with transaction.atomic():
                self.do(1)
                self.assertNotified([])
            self.assertNotified([])
        self.assertDone([1])

    @skipUnlessDBFeature("uses_savepoints")
    def test_discards_hooks_from_rolled_back_savepoint(self):
        with transaction.atomic():
            # one successful savepoint
            with transaction.atomic():
                self.do(1)
            # one failed savepoint
            try:
                with transaction.atomic():
                    self.do(2)
                    raise ForcedError()
            except ForcedError:
                pass
            # another successful savepoint
            with transaction.atomic():
                self.do(3)

        # only hooks registered during successful savepoints execute
        self.assertDone([1, 3])

    def test_no_hooks_run_from_failed_transaction(self):
        """If outer transaction fails, no hooks from within it run."""
        try:
            with transaction.atomic():
                with transaction.atomic():
                    self.do(1)
                raise ForcedError()
        except ForcedError:
            pass

        self.assertDone([])

    @skipUnlessDBFeature("uses_savepoints")
    def test_inner_savepoint_rolled_back_with_outer(self):
        with transaction.atomic():
            try:
                with transaction.atomic():
                    with transaction.atomic():
                        self.do(1)
                    raise ForcedError()
            except ForcedError:
                pass
            self.do(2)

        self.assertDone([2])

    def test_no_savepoints_atomic_merged_with_outer(self):
        with transaction.atomic():
            with transaction.atomic():
                self.do(1)
                try:
                    with transaction.atomic(savepoint=False):
                        raise ForcedError()
                except ForcedError:
                    pass

        self.assertDone([])

    @skipUnlessDBFeature("uses_savepoints")
    def test_inner_savepoint_does_not_affect_outer(self):
        with transaction.atomic():
            with transaction.atomic():
                self.do(1)
                try:
                    with transaction.atomic():
                        raise ForcedError()
                except ForcedError:
                    pass

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
        try:
            with transaction.atomic():
                self.do(1)
                raise ForcedError()
        except ForcedError:
            pass

        with transaction.atomic():
            self.do(2)

        self.assertDone([2])

    @skipUnlessDBFeature("test_db_allows_multiple_connections")
    def test_hooks_cleared_on_reconnect(self):
        with transaction.atomic():
            self.do(1)
            connection.close()

        connection.connect()

        with transaction.atomic():
            self.do(2)

        self.assertDone([2])

    def test_error_in_hook_doesnt_prevent_clearing_hooks(self):
        try:
            with transaction.atomic():
                transaction.on_commit(lambda: self.notify("error"))
        except ForcedError:
            pass

        with transaction.atomic():
            self.do(1)

        self.assertDone([1])

    def test_error_in_hook_stops_later_hooks_without_rolling_back_commit(self):
        error = ForcedError("callback failed")

        def fail():
            raise error

        with self.assertRaisesMessage(ForcedError, "callback failed") as cm:
            with transaction.atomic():
                self.do(1)
                transaction.on_commit(fail)
                self.do(2)

        self.assertIs(cm.exception, error)
        self.assertNotified([1])
        self.assertEqual(
            list(Thing.objects.order_by("num").values_list("num", flat=True)), [1, 2]
        )
        self.assertEqual(connection.run_on_commit, [])
        with transaction.atomic():
            self.do(3)
        self.assertNotified([1, 3])

    def test_base_exception_in_hook_is_not_suppressed(self):
        def interrupt():
            raise KeyboardInterrupt("callback interrupted")

        for robust in (False, True):
            with self.subTest(robust=robust):
                self.notified.clear()
                with self.assertRaisesMessage(
                    KeyboardInterrupt, "callback interrupted"
                ):
                    with transaction.atomic():
                        transaction.on_commit(lambda: self.notify(1))
                        transaction.on_commit(interrupt, robust=robust)
                        transaction.on_commit(lambda: self.notify(2))
                self.assertNotified([1])
                self.assertEqual(connection.run_on_commit, [])

    def test_completed_hook_is_released_before_next_hook(self):
        def callback():
            self.notify(1)

        callback_ref = weakref.ref(callback)

        def check_released():
            gc.collect()
            self.assertIsNone(callback_ref())
            self.notify(2)

        with transaction.atomic():
            transaction.on_commit(callback)
            transaction.on_commit(check_released)
            del callback

        self.assertNotified([1, 2])

    def test_completed_hook_is_not_retained_by_later_hook_traceback(self):
        callback_refs = {}

        def make_callback(label):
            def callback():
                self.notify(label)

            callback_refs[label] = weakref.ref(callback)
            return callback

        captured_traceback = None
        try:
            with transaction.atomic():
                transaction.on_commit(make_callback(1))
                transaction.on_commit(make_callback("error"))
                transaction.on_commit(make_callback(2))
        except ForcedError as error:
            captured_traceback = error.__traceback__
        try:
            self.assertIsNotNone(captured_traceback)
            gc.collect()
            self.assertIsNone(callback_refs[1]())
            self.assertIsNotNone(callback_refs["error"]())
            self.assertIsNotNone(callback_refs[2]())
            self.assertNotified([1])
            self.assertEqual(connection.run_on_commit, [])
        finally:
            if captured_traceback is not None:
                traceback.clear_frames(captured_traceback)

    def test_completed_hook_is_not_retained_by_robust_hook_log(self):
        callback_refs = {}

        def make_callback(label):
            def callback():
                self.notify(label)

            callback_refs[label] = weakref.ref(callback)
            return callback

        with self.assertLogs("django.db.backends.base", "ERROR") as cm:
            with transaction.atomic():
                transaction.on_commit(make_callback(1))
                transaction.on_commit(make_callback("error"), robust=True)
                transaction.on_commit(make_callback(2))
        try:
            gc.collect()
            self.assertIsNone(callback_refs[1]())
            self.assertNotified([1, 2])
            self.assertEqual(connection.run_on_commit, [])
            self.assertEqual(len(cm.records), 1)
            self.assertIsInstance(cm.records[0].exc_info[1], ForcedError)
        finally:
            for record in cm.records:
                traceback.clear_frames(record.exc_info[2])

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
            raise AssertionError("this function should never be called")

        try:
            connection.set_autocommit(False)
            msg = "on_commit() cannot be used in manual transaction management"
            with self.assertRaisesMessage(transaction.TransactionManagementError, msg):
                transaction.on_commit(should_never_be_called)
        finally:
            connection.set_autocommit(True)

    def test_raises_exception_non_callable(self):
        msg = "on_commit()'s callback must be a callable."
        with self.assertRaisesMessage(TypeError, msg):
            transaction.on_commit(None)
