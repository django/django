from unittest.mock import patch

from django.core.management import call_command
from django.db import connection
from django.db.migrations import Migration
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.operations import RunPython
from django.db.migrations.recorder import MigrationRecorder
from django.db.models import signals
from django.test import TransactionTestCase, override_settings

from .operations import Operation0, Operation1, Operation2, Operation3


class Receiver:
    def __init__(self, sender, operations):
        self.sender = sender
        self.operations = operations
        signals.post_operation.connect(self, sender=sender)

    def __call__(self, *args, **kwargs):
        return self.operations


@override_settings(
    MIGRATION_MODULES={"migrate_signals": "migrate_signals.noop_migrations"}
)
class PostOperationSignalTests(TransactionTestCase):

    available_apps = ["migrate_signals"]

    def _register(self, inject_operation):
        self.addCleanup(
            signals.post_operation.disconnect,
            inject_operation,
            sender=inject_operation.sender,
        )

    def test_apply_cyclical_infinite_recursion(self):
        self._register(Receiver(Operation0, [Operation1()]))
        self._register(Receiver(Operation1, [Operation1()]))

        executor = MigrationExecutor(connection)

        with self.assertRaisesMessage(
            RecursionError, Migration.APPLY_RECURSION_ERROR_MESSAGE
        ):
            executor.migrate([("migrate_signals", "0001_initial")])

    def test_apply_direct_infinite_recursion(self):
        self._register(Receiver(Operation0, [Operation0()]))

        executor = MigrationExecutor(connection)

        with self.assertRaisesMessage(
            RecursionError, Migration.APPLY_RECURSION_ERROR_MESSAGE
        ):
            executor.migrate([("migrate_signals", "0001_initial")])

    def test_unapply_cyclical_infinite_recursion(self):
        executor = MigrationExecutor(connection)
        executor.migrate([("migrate_signals", "0001_initial")])

        self.addCleanup(
            call_command,
            'migrate',
            'migrate_signals',
            'zero',
            database='default',
            interactive=False,
            verbosity=0,
        )

        # Rebuild the graph to reflect the new DB state
        executor.loader.build_graph()

        self._register(Receiver(Operation0, [Operation1()]))
        self._register(Receiver(Operation1, [Operation1()]))

        with self.assertRaisesMessage(
            RecursionError, Migration.APPLY_RECURSION_ERROR_MESSAGE
        ):
            executor.migrate([("migrate_signals", None)])

    def test_unapply_direct_infinite_recursion(self):
        executor = MigrationExecutor(connection)
        executor.migrate([("migrate_signals", "0001_initial")])
        self.addCleanup(
            MigrationRecorder.Migration.objects.filter(app="migrate_signals").delete
        )
        # Rebuild the graph to reflect the new DB state
        executor.loader.build_graph()

        self._register(Receiver(Operation0, [Operation0()]))

        with self.assertRaisesMessage(
            RecursionError, Migration.APPLY_RECURSION_ERROR_MESSAGE
        ):
            executor.migrate([("migrate_signals", None)])

    def test_order_forward(self):
        self._register(Receiver(Operation0, [Operation1()]))
        self._register(Receiver(Operation0, [Operation2()]))
        self._register(Receiver(Operation0, [Operation1(), Operation2()]))
        self._register(Receiver(Operation1, [Operation3()]))

        applied_operations = []

        def mock_run_python_state_forwards(self, app_label, state):
            applied_operations.append(self)

        executor = MigrationExecutor(connection)

        with patch.object(
            RunPython, "state_forwards", mock_run_python_state_forwards
        ):
            executor.migrate([("migrate_signals", "0001_initial")])
            self.addCleanup(
                MigrationRecorder.Migration.objects.filter(app="migrate_signals").delete
            )

        # All the injected operations are executed in LNR order.
        self.assertEqual(
            [
                Operation0(),
                Operation1(),
                Operation3(),
                Operation2(),
                Operation1(),
                Operation3(),
                Operation2(),
            ],
            applied_operations,
        )

    def test_order_backward(self):
        executor = MigrationExecutor(connection)
        executor.migrate([("migrate_signals", "0001_initial")])
        # Rebuild the graph to reflect the new DB state
        executor.loader.build_graph()

        self._register(Receiver(Operation0, [Operation1()]))
        self._register(Receiver(Operation0, [Operation2()]))
        self._register(Receiver(Operation0, [Operation1(), Operation2()]))
        self._register(Receiver(Operation1, [Operation3()]))

        unapplied_operations = []

        def mock_run_python_database_backwards(self, app_label, schema_editor, from_state, to_state):
            unapplied_operations.append(self)

        with patch.object(
            RunPython, "database_backwards", mock_run_python_database_backwards
        ):
            executor.migrate([("migrate_signals", None)])

        # All the injected operations are executed in RNL order.
        self.assertEqual(
            [
                Operation2(),
                Operation3(),
                Operation1(),
                Operation2(),
                Operation3(),
                Operation1(),
                Operation0(),
            ],
            unapplied_operations,
        )
