from unittest import mock

from django.db import migrations

try:
    from django.contrib.postgres.operations import CryptoExtension
except ImportError:
    CryptoExtension = mock.Mock()


class Migration(migrations.Migration):
    # Required for the SHA database functions.
    operations = [CryptoExtension()]
