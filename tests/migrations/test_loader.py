from django.test import TestCase
from django.db import connection
from django.db.migrations.recorder import MigrationRecorder


class RecorderTests(TestCase):
    """
    Tests the disk and database loader.
    """

    def test_apply(self):
        """
        Tests marking migrations as applied/unapplied.
        """
        recorder = MigrationRecorder(connection)
        self.assertEqual(
            recorder.applied_migrations(),
            set(),
        )
        recorder.record_applied("myapp", "0432_ponies")
        self.assertEqual(
            recorder.applied_migrations(),
            set([("myapp", "0432_ponies")]),
        )
        recorder.record_unapplied("myapp", "0432_ponies")
        self.assertEqual(
            recorder.applied_migrations(),
            set(),
        )
