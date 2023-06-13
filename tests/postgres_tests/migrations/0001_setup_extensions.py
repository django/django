from unittest import mock

from django.db import connection, migrations

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
    BloomExtension = mock.Mock()
    BtreeGinExtension = mock.Mock()
    BtreeGistExtension = mock.Mock()
    CITextExtension = mock.Mock()
    CreateExtension = mock.Mock()
    HStoreExtension = mock.Mock()
    TrigramExtension = mock.Mock()
    UnaccentExtension = mock.Mock()
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
        CryptoExtension() if needs_crypto_extension else mock.Mock(),
        HStoreExtension(),
        TrigramExtension(),
        UnaccentExtension(),
    ]
