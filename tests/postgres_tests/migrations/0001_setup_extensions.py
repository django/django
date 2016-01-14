# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations

try:
    from django.contrib.postgres.operations import (
        HStoreExtension, UnaccentExtension,
    )
except ImportError:
    from django.test import mock
    HStoreExtension = mock.Mock()
    UnaccentExtension = mock.Mock()


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        HStoreExtension(),
        UnaccentExtension(),
    ]
