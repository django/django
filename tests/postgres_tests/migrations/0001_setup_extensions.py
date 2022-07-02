from django.db import connection, migrations
from django.db.migrations.operations.base import Operation


class DummyOperation(Operation):
    def state_forwards(self, app_label, state):
        pass

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        pass

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        pass


try:
    from django.contrib.postgres.operations import (
        BloomExtension,
        BtreeGinExtension,
        BtreeGistExtension,
        CITextExtension,
        CreateExtension,
        CryptoExtension,
        HStoreExtension,
        TrigramExtension,
        UnaccentExtension,
    )
except ImportError:
    BloomExtension = DummyOperation
    BtreeGinExtension = DummyOperation
    BtreeGistExtension = DummyOperation
    CITextExtension = DummyOperation
    CreateExtension = DummyOperation
    HStoreExtension = DummyOperation
    TrigramExtension = DummyOperation
    UnaccentExtension = DummyOperation
    needs_crypto_extension = False
else:
    needs_crypto_extension = (
        connection.vendor == "postgresql" and not connection.features.is_postgresql_13
    )


class Migration(migrations.Migration):

    operations = [
        BloomExtension(),
        BtreeGinExtension(),
        BtreeGistExtension(),
        CITextExtension(),
        # Ensure CreateExtension quotes extension names by creating one with a
        # dash in its name.
        CreateExtension("uuid-ossp"),
        # CryptoExtension is required for RandomUUID() on PostgreSQL < 13.
        CryptoExtension() if needs_crypto_extension else DummyOperation(),
        HStoreExtension(),
        TrigramExtension(),
        UnaccentExtension(),
    ]
