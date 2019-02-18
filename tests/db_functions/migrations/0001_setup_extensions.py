from unittest import mock

from django.db import migrations

try:
    from django.contrib.postgres.operations import CryptoExtension
except ImportError:
    CryptoExtension = mock.Mock()


class Migration(migrations.Migration):

    # XXX: Enable pgcrypto extension on PostgreSQL to support various database
    #      functions including SHA1, SHA224, SHA256, SHA384 & SHA512.
    operations = [CryptoExtension()]
