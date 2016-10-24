# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations

try:
    from django.contrib.postgres.operations import (
        BtreeGinExtension, CITextExtension, CreateExtension, HStoreExtension,
        PrewarmExtension, TrigramExtension, UnaccentExtension,
    )
except ImportError:
    from django.test import mock
    BtreeGinExtension = mock.Mock()
    CreateExtension = mock.Mock()
    HStoreExtension = mock.Mock()
    PrewarmExtension = mock.Mock()
    TrigramExtension = mock.Mock()
    UnaccentExtension = mock.Mock()
    CITextExtension = mock.Mock()


class Migration(migrations.Migration):

    operations = [
        BtreeGinExtension(),
        # Ensure CreateExtension quotes extension names by creating one with a
        # dash in its name.
        CreateExtension('uuid-ossp'),
        HStoreExtension(),
        PrewarmExtension(),
        TrigramExtension(),
        UnaccentExtension(),
        CITextExtension(),
    ]
