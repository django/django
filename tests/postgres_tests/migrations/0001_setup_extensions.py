from unittest import mock

from django.db import migrations

try:
    from django.contrib.postgres.operations import (
        BloomExtension, BtreeGinExtension, BtreeGistExtension, CITextExtension,
        CreateExtension, CryptoExtension, HStoreExtension, TrigramExtension,
        UnaccentExtension,
    )
except ImportError:
    BloomExtension = mock.Mock()
    BtreeGinExtension = mock.Mock()
    BtreeGistExtension = mock.Mock()
    CITextExtension = mock.Mock()
    CreateExtension = mock.Mock()
    CryptoExtension = mock.Mock()
    HStoreExtension = mock.Mock()
    TrigramExtension = mock.Mock()
    UnaccentExtension = mock.Mock()


class Migration(migrations.Migration):

    operations = [
        BloomExtension(),
        BtreeGinExtension(),
        BtreeGistExtension(),
        CITextExtension(),
        # Ensure CreateExtension quotes extension names by creating one with a
        # dash in its name.
        CreateExtension('uuid-ossp'),
        CryptoExtension(),
        HStoreExtension(),
        TrigramExtension(),
        UnaccentExtension(),
    ]
