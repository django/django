# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import django.contrib.auth.models
from django.contrib.auth import validators
from django.db import migrations, models
from django.utils import six, timezone


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '__first__'),
    ]

    operations = [
        migrations.CreateModel(
            name='Permission',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=50, verbose_name='name')),
                ('content_type', models.ForeignKey(
                    to='contenttypes.ContentType',
                    on_delete=models.CASCADE,
                    to_field='id',
                    verbose_name='content type',
                )),
                ('codename', models.CharField(max_length=100, verbose_name='codename')),
            ],
            options={
                'ordering': ('content_type__app_label', 'content_type__model', 'codename'),
                'unique_together': set([('content_type', 'codename')]),
                'verbose_name': 'permission',
                'verbose_name_plural': 'permissions',
            },
            managers=[
                ('objects', django.contrib.auth.models.PermissionManager()),
            ],
        ),
        migrations.CreateModel(
            name='Group',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=80, verbose_name='name')),
                ('permissions', models.ManyToManyField(to='auth.Permission', verbose_name='permissions', blank=True)),
            ],
            options={
                'verbose_name': 'group',
                'verbose_name_plural': 'groups',
            },
            managers=[
                ('objects', django.contrib.auth.models.GroupManager()),
            ],
        ),
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(default=timezone.now, verbose_name='last login')),
                ('is_superuser', models.BooleanField(
                    default=False,
                    help_text='Designates that this user has all permissions without explicitly assigning them.',
                    verbose_name='superuser status'
                )),
                ('username', models.CharField(
                    help_text='Required. 30 characters or fewer. Letters, digits and @/./+/-/_ only.', unique=True,
                    max_length=30, verbose_name='username',
                    validators=[
                        validators.UnicodeUsernameValidator() if six.PY3 else validators.ASCIIUsernameValidator()
                    ],
                )),
                ('first_name', models.CharField(max_length=30, verbose_name='first name', blank=True)),
                ('last_name', models.CharField(max_length=30, verbose_name='last name', blank=True)),
                ('email', models.EmailField(max_length=75, verbose_name='email address', blank=True)),
                ('is_staff', models.BooleanField(
                    default=False, help_text='Designates whether the user can log into this admin site.',
                    verbose_name='staff status'
                )),
                ('is_active', models.BooleanField(
                    default=True, verbose_name='active', help_text=(
                        'Designates whether this user should be treated as active. Unselect this instead of deleting '
                        'accounts.'
                    )
                )),
                ('date_joined', models.DateTimeField(default=timezone.now, verbose_name='date joined')),
                ('groups', models.ManyToManyField(
                    to='auth.Group', verbose_name='groups', blank=True, related_name='user_set',
                    related_query_name='user', help_text=(
                        'The groups this user belongs to. A user will get all permissions granted to each of their '
                        'groups.'
                    )
                )),
                ('user_permissions', models.ManyToManyField(
                    to='auth.Permission', verbose_name='user permissions', blank=True,
                    help_text='Specific permissions for this user.', related_name='user_set',
                    related_query_name='user')
                 ),
            ],
            options={
                'swappable': 'AUTH_USER_MODEL',
                'verbose_name': 'user',
                'verbose_name_plural': 'users',
            },
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
    ]
