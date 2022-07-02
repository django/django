from django.db import migrations
from django.db.migrations.operations.base import Operation


class DummyOperation(Operation):
    def state_forwards(self, app_label, state):
        pass

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        pass

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        pass


try:
    from django.contrib.postgres.operations import CryptoExtension
except ImportError:
    CryptoExtension = DummyOperation


class Migration(migrations.Migration):
    # Required for the SHA database functions.
    operations = [CryptoExtension()]
