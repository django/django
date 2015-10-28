# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import django.core.validators
from django.db import migrations, models


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
                help_text='Required. 254 characters or fewer. Letters, digits and @/./+/-/_ only.',
                max_length=254,
                unique=True,
                validators=[
                    django.core.validators.RegexValidator(
                        '^[\\w.@+-]+$', 'Enter a valid username. '
                        'This value may contain only letters, numbers and @/./+/-/_ characters.'
                    ),
                ],
                verbose_name='username',
            ),
        ),
    ]
