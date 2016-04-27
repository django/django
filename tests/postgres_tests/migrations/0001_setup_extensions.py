# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations

try:
    from django.contrib.postgres.operations import (
        CreateExtension, HStoreExtension, UnaccentExtension,
    )
except ImportError:
    from django.test import mock
    CreateExtension = mock.Mock()
    HStoreExtension = mock.Mock()
    UnaccentExtension = mock.Mock()


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        # Test quoting of extension names by creating "uuid-ossp", which has a
        # dash in its name
        CreateExtension('uuid-ossp'),
        HStoreExtension(),
        UnaccentExtension(),
    ]
