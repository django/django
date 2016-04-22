# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth import validators
from django.db import migrations, models
from django.utils import six


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0007_alter_validators_add_error_messages'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='username',
            field=models.CharField(
                error_messages={'unique': 'A user with that username already exists.'},
                help_text='Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.',
                max_length=150,
                unique=True,
                validators=[validators.UnicodeUsernameValidator() if six.PY3 else validators.ASCIIUsernameValidator()],
                verbose_name='username',
            ),
        ),
    ]
