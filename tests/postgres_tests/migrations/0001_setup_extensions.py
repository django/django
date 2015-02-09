# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.postgres.operations import (
    HStoreExtension, UnaccentExtension,
)
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        HStoreExtension(),
        UnaccentExtension(),
    ]
