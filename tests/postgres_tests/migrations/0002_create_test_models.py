# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.contrib.postgres.fields
import django.contrib.postgres.fields.hstore


class Migration(migrations.Migration):

    dependencies = [
        ('postgres_tests', '0001_setup_extensions'),
    ]

    operations = [
        migrations.CreateModel(
            name='CharArrayModel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('field', django.contrib.postgres.fields.ArrayField(models.CharField(max_length=10), size=None)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='DateTimeArrayModel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('field', django.contrib.postgres.fields.ArrayField(models.DateTimeField(), size=None)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='HStoreModel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('field', django.contrib.postgres.fields.hstore.HStoreField(blank=True, null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='IntegerArrayModel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('field', django.contrib.postgres.fields.ArrayField(models.IntegerField(), size=None)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='NestedIntegerArrayModel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('field', django.contrib.postgres.fields.ArrayField(django.contrib.postgres.fields.ArrayField(models.IntegerField(), size=None), size=None)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='NullableIntegerArrayModel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('field', django.contrib.postgres.fields.ArrayField(models.IntegerField(), size=None, null=True, blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
