# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth import validators
from django.db import migrations, models
from django.utils import six


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0006_require_contenttypes_0002'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='username',
            field=models.CharField(
                error_messages={'unique': 'A user with that username already exists.'},
                help_text='Required. 30 characters or fewer. Letters, digits and @/./+/-/_ only.',
                max_length=30,
                unique=True,
                validators=[validators.UnicodeUsernameValidator() if six.PY3 else validators.ASCIIUsernameValidator()],
                verbose_name='username',
            ),
        ),
    ]
