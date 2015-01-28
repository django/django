# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import django.contrib.postgres.fields
import django.contrib.postgres.fields.hstore
from django.db import migrations, models


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
                ('datetimes', django.contrib.postgres.fields.ArrayField(models.DateTimeField(), size=None)),
                ('dates', django.contrib.postgres.fields.ArrayField(models.DateField(), size=None)),
                ('times', django.contrib.postgres.fields.ArrayField(models.TimeField(), size=None)),
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
            name='OtherTypesArrayModel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('ips', django.contrib.postgres.fields.ArrayField(models.GenericIPAddressField(), size=None)),
                ('uuids', django.contrib.postgres.fields.ArrayField(models.UUIDField(), size=None)),
                ('decimals', django.contrib.postgres.fields.ArrayField(models.DecimalField(max_digits=5, decimal_places=2), size=None)),
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
        migrations.CreateModel(
            name='CharFieldModel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('field', models.CharField(max_length=16)),
            ],
            options=None,
            bases=None,
        ),
        migrations.CreateModel(
            name='TextFieldModel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('field', models.TextField()),
            ],
            options=None,
            bases=None,
        ),
    ]

    pg_92_operations = [
        migrations.CreateModel(
            name='RangesModel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('ints', django.contrib.postgres.fields.IntegerRangeField(null=True, blank=True)),
                ('bigints', django.contrib.postgres.fields.BigIntegerRangeField(null=True, blank=True)),
                ('floats', django.contrib.postgres.fields.FloatRangeField(null=True, blank=True)),
                ('timestamps', django.contrib.postgres.fields.DateTimeRangeField(null=True, blank=True)),
                ('dates', django.contrib.postgres.fields.DateRangeField(null=True, blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]

    def apply(self, project_state, schema_editor, collect_sql=False):
        PG_VERSION = schema_editor.connection.pg_version
        if PG_VERSION >= 90200:
            self.operations = self.operations + self.pg_92_operations
        return super(Migration, self).apply(project_state, schema_editor, collect_sql)
