from unittest import mock

from django.db import migrations

try:
    from django.contrib.postgres.operations import (
        BtreeGinExtension, CITextExtension, CreateExtension, CryptoExtension,
        HStoreExtension, TrigramExtension, UnaccentExtension,
    )
except ImportError:
    BtreeGinExtension = mock.Mock()
    CITextExtension = mock.Mock()
    CreateExtension = mock.Mock()
    CryptoExtension = mock.Mock()
    HStoreExtension = mock.Mock()
    TrigramExtension = mock.Mock()
    UnaccentExtension = mock.Mock()


class Migration(migrations.Migration):

    operations = [
        BtreeGinExtension(),
        CITextExtension(),
        # Ensure CreateExtension quotes extension names by creating one with a
        # dash in its name.
        CreateExtension('uuid-ossp'),
        CryptoExtension(),
        HStoreExtension(),
        TrigramExtension(),
        UnaccentExtension(),
    ]
