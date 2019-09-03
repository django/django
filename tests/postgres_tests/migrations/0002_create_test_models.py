from django.core.serializers.json import DjangoJSONEncoder
from django.db import migrations, models

from ..fields import (
    ArrayField, BigIntegerRangeField, CICharField, CIEmailField, CITextField,
    DateRangeField, DateTimeRangeField, DecimalRangeField, EnumField,
    HStoreField, IntegerRangeField, JSONField, SearchVectorField,
)
from ..models import TagField


class Migration(migrations.Migration):

    dependencies = [
        ('postgres_tests', '0001_setup_extensions'),
    ]

    operations = [
        migrations.CreateModel(
            name='CharArrayModel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('field', ArrayField(models.CharField(max_length=10), size=None)),
            ],
            options={
                'required_db_vendor': 'postgresql',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='DateTimeArrayModel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('datetimes', ArrayField(models.DateTimeField(), size=None)),
                ('dates', ArrayField(models.DateField(), size=None)),
                ('times', ArrayField(models.TimeField(), size=None)),
            ],
            options={
                'required_db_vendor': 'postgresql',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='HStoreModel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('field', HStoreField(blank=True, null=True)),
                ('array_field', ArrayField(HStoreField(), null=True)),
            ],
            options={
                'required_db_vendor': 'postgresql',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='OtherTypesArrayModel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('ips', ArrayField(models.GenericIPAddressField(), size=None, default=list)),
                ('uuids', ArrayField(models.UUIDField(), size=None, default=list)),
                ('decimals', ArrayField(models.DecimalField(max_digits=5, decimal_places=2), size=None, default=list)),
                ('tags', ArrayField(TagField(), blank=True, null=True, size=None)),
                ('json', ArrayField(JSONField(default={}), default=[])),
                ('int_ranges', ArrayField(IntegerRangeField(), null=True, blank=True)),
                ('bigint_ranges', ArrayField(BigIntegerRangeField(), null=True, blank=True)),
            ],
            options={
                'required_db_vendor': 'postgresql',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='IntegerArrayModel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('field', ArrayField(models.IntegerField(), size=None)),
            ],
            options={
                'required_db_vendor': 'postgresql',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='NestedIntegerArrayModel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('field', ArrayField(ArrayField(models.IntegerField(), size=None), size=None)),
            ],
            options={
                'required_db_vendor': 'postgresql',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='NullableIntegerArrayModel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('field', ArrayField(models.IntegerField(), size=None, null=True, blank=True)),
            ],
            options={
                'required_db_vendor': 'postgresql',
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
        migrations.CreateModel(
            name='Scene',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('scene', models.CharField(max_length=255)),
                ('setting', models.CharField(max_length=255)),
            ],
            options=None,
            bases=None,
        ),
        migrations.CreateModel(
            name='Character',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=255)),
            ],
            options=None,
            bases=None,
        ),
        migrations.CreateModel(
            name='CITestModel',
            fields=[
                ('name', CICharField(primary_key=True, max_length=255)),
                ('email', CIEmailField()),
                ('description', CITextField()),
                ('array_field', ArrayField(CITextField(), null=True)),
            ],
            options={
                'required_db_vendor': 'postgresql',
            },
            bases=None,
        ),
        migrations.CreateModel(
            name='Line',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('scene', models.ForeignKey('postgres_tests.Scene', on_delete=models.SET_NULL)),
                ('character', models.ForeignKey('postgres_tests.Character', on_delete=models.SET_NULL)),
                ('dialogue', models.TextField(blank=True, null=True)),
                ('dialogue_search_vector', SearchVectorField(blank=True, null=True)),
                ('dialogue_config', models.CharField(max_length=100, blank=True, null=True)),
            ],
            options={
                'required_db_vendor': 'postgresql',
            },
            bases=None,
        ),
        migrations.CreateModel(
            name='AggregateTestModel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('boolean_field', models.BooleanField(null=True)),
                ('char_field', models.CharField(max_length=30, blank=True)),
                ('integer_field', models.IntegerField(null=True)),
            ]
        ),
        migrations.CreateModel(
            name='StatTestModel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('int1', models.IntegerField()),
                ('int2', models.IntegerField()),
                ('related_field', models.ForeignKey(
                    'postgres_tests.AggregateTestModel',
                    models.SET_NULL,
                    null=True,
                )),
            ]
        ),
        migrations.CreateModel(
            name='NowTestModel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('when', models.DateTimeField(null=True, default=None)),
            ]
        ),
        migrations.CreateModel(
            name='UUIDTestModel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('uuid', models.UUIDField(default=None, null=True)),
            ]
        ),
        migrations.CreateModel(
            name='RangesModel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('ints', IntegerRangeField(null=True, blank=True)),
                ('bigints', BigIntegerRangeField(null=True, blank=True)),
                ('decimals', DecimalRangeField(null=True, blank=True)),
                ('timestamps', DateTimeRangeField(null=True, blank=True)),
                ('timestamps_inner', DateTimeRangeField(null=True, blank=True)),
                ('dates', DateRangeField(null=True, blank=True)),
                ('dates_inner', DateRangeField(null=True, blank=True)),
            ],
            options={
                'required_db_vendor': 'postgresql'
            },
            bases=(models.Model,)
        ),
        migrations.CreateModel(
            name='RangeLookupsModel',
            fields=[
                ('parent', models.ForeignKey(
                    'postgres_tests.RangesModel',
                    models.SET_NULL,
                    blank=True, null=True,
                )),
                ('integer', models.IntegerField(blank=True, null=True)),
                ('big_integer', models.BigIntegerField(blank=True, null=True)),
                ('float', models.FloatField(blank=True, null=True)),
                ('timestamp', models.DateTimeField(blank=True, null=True)),
                ('date', models.DateField(blank=True, null=True)),
            ],
            options={
                'required_db_vendor': 'postgresql',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='JSONModel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('field', JSONField(null=True, blank=True)),
                ('field_custom', JSONField(null=True, blank=True, encoder=DjangoJSONEncoder)),
            ],
            options={
                'required_db_vendor': 'postgresql',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ArrayEnumModel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('array_of_enums', ArrayField(EnumField(max_length=20), null=True, blank=True)),
            ],
            options={
                'required_db_vendor': 'postgresql',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Room',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('number', models.IntegerField(unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='HotelReservation',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('room', models.ForeignKey('postgres_tests.Room', models.CASCADE)),
                ('datespan', DateRangeField()),
                ('start', models.DateTimeField()),
                ('end', models.DateTimeField()),
                ('cancelled', models.BooleanField(default=False)),
            ],
            options={
                'required_db_vendor': 'postgresql',
            },
        ),
    ]
