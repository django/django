# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations

try:
    from django.contrib.postgres.operations import (
        CreateExtension, HStoreExtension, TrigramExtension, UnaccentExtension,
    )
except ImportError:
    from django.test import mock
    CreateExtension = mock.Mock()
    HStoreExtension = mock.Mock()
    TrigramExtension = mock.Mock()
    UnaccentExtension = mock.Mock()


class Migration(migrations.Migration):

    operations = [
        # Ensure CreateExtension quotes extension names by creating one with a
        # dash in its name.
        CreateExtension('uuid-ossp'),
        HStoreExtension(),
        TrigramExtension(),
        UnaccentExtension(),
    ]
