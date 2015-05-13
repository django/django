# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations

try:
    from django.db.backends.postgresql.migrations.operations import (
        CreateExtension,
    )
    from django.contrib.postgres.operations import (
        BtreeGinExtension, HStoreExtension, TrigramExtension, UnaccentExtension,
    )
except ImportError:
    from django.test import mock
    BtreeGinExtension = mock.Mock()
    CreateExtension = mock.Mock()
    HStoreExtension = mock.Mock()
    TrigramExtension = mock.Mock()
    UnaccentExtension = mock.Mock()


class Migration(migrations.Migration):

    operations = [
        BtreeGinExtension(),
        # Ensure CreateExtension quotes extension names by creating one with a
        # dash in its name.
        CreateExtension('uuid-ossp'),
        HStoreExtension(),
        TrigramExtension(),
        UnaccentExtension(),
    ]
