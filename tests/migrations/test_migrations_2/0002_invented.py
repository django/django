# encoding: utf8
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("sessions", "0001_initial")]

    operations = [
        migrations.CreateModel(
            "Huh",
            [
                ("id", models.AutoField(primary_key=True)),
            ],
        ),
    ]
