from django.db import migrations, models

from ..fields import (
    ArrayField,
    BigIntegerRangeField,
    CICharField,
    CIEmailField,
    CITextField,
    DateRangeField,
    DateTimeRangeField,
    DecimalRangeField,
    EnumField,
    HStoreField,
    IntegerRangeField,
    SearchVectorField,
)
from ..models import TagField


class Migration(migrations.Migration):
    dependencies = [
        ("postgres_tests", "0001_setup_extensions"),
    ]

    operations = [
        migrations.CreateModel(
            name="CharArrayModel",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                ("field", ArrayField(models.CharField(max_length=10), size=None)),
            ],
            options={
                "required_db_vendor": "postgresql",
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name="DateTimeArrayModel",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                ("datetimes", ArrayField(models.DateTimeField(), size=None)),
                ("dates", ArrayField(models.DateField(), size=None)),
                ("times", ArrayField(models.TimeField(), size=None)),
            ],
            options={
                "required_db_vendor": "postgresql",
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name="HStoreModel",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                ("field", HStoreField(blank=True, null=True)),
                ("array_field", ArrayField(HStoreField(), null=True)),
            ],
            options={
                "required_db_vendor": "postgresql",
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name="OtherTypesArrayModel",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                (
                    "ips",
                    ArrayField(models.GenericIPAddressField(), size=None, default=list),
                ),
                ("uuids", ArrayField(models.UUIDField(), size=None, default=list)),
                (
                    "decimals",
                    ArrayField(
                        models.DecimalField(max_digits=5, decimal_places=2),
                        size=None,
                        default=list,
                    ),
                ),
                ("tags", ArrayField(TagField(), blank=True, null=True, size=None)),
                (
                    "json",
                    ArrayField(models.JSONField(default=dict), default=list, size=None),
                ),
                ("int_ranges", ArrayField(IntegerRangeField(), null=True, blank=True)),
                (
                    "bigint_ranges",
                    ArrayField(BigIntegerRangeField(), null=True, blank=True),
                ),
            ],
            options={
                "required_db_vendor": "postgresql",
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name="IntegerArrayModel",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                (
                    "field",
                    ArrayField(
                        models.IntegerField(), blank=True, default=list, size=None
                    ),
                ),
            ],
            options={
                "required_db_vendor": "postgresql",
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name="NestedIntegerArrayModel",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                (
                    "field",
                    ArrayField(ArrayField(models.IntegerField(), size=None), size=None),
                ),
            ],
            options={
                "required_db_vendor": "postgresql",
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name="NullableIntegerArrayModel",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                (
                    "field",
                    ArrayField(models.IntegerField(), size=None, null=True, blank=True),
                ),
                (
                    "field_nested",
                    ArrayField(
                        ArrayField(models.IntegerField(null=True), size=None),
                        size=None,
                        null=True,
                    ),
                ),
                ("order", models.IntegerField(null=True)),
            ],
            options={
                "required_db_vendor": "postgresql",
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name="CharFieldModel",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                ("field", models.CharField(max_length=64)),
            ],
            options=None,
            bases=None,
        ),
        migrations.CreateModel(
            name="TextFieldModel",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                ("field", models.TextField()),
            ],
            options=None,
            bases=None,
        ),
        migrations.CreateModel(
            name="SmallAutoFieldModel",
            fields=[
                (
                    "id",
                    models.SmallAutoField(serialize=False, primary_key=True),
                ),
            ],
            options=None,
        ),
        migrations.CreateModel(
            name="BigAutoFieldModel",
            fields=[
                (
                    "id",
                    models.BigAutoField(serialize=False, primary_key=True),
                ),
            ],
            options=None,
        ),
        migrations.CreateModel(
            name="Scene",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                ("scene", models.TextField()),
                ("setting", models.CharField(max_length=255)),
            ],
            options=None,
            bases=None,
        ),
        migrations.CreateModel(
            name="Character",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                ("name", models.CharField(max_length=255)),
            ],
            options=None,
            bases=None,
        ),
        # RemovedInDjango51Warning.
        migrations.CreateModel(
            name="CITestModel",
            fields=[
                (
                    "name",
                    CICharField(primary_key=True, serialize=False, max_length=255),
                ),
                ("email", CIEmailField()),
                ("description", CITextField()),
                ("array_field", ArrayField(CITextField(), null=True)),
            ],
            options={
                "required_db_vendor": "postgresql",
            },
            bases=None,
        ),
        migrations.CreateModel(
            name="Line",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                (
                    "scene",
                    models.ForeignKey("postgres_tests.Scene", on_delete=models.CASCADE),
                ),
                (
                    "character",
                    models.ForeignKey(
                        "postgres_tests.Character", on_delete=models.CASCADE
                    ),
                ),
                ("dialogue", models.TextField(blank=True, null=True)),
                ("dialogue_search_vector", SearchVectorField(blank=True, null=True)),
                (
                    "dialogue_config",
                    models.CharField(max_length=100, blank=True, null=True),
                ),
            ],
            options={
                "required_db_vendor": "postgresql",
            },
            bases=None,
        ),
        migrations.CreateModel(
            name="LineSavedSearch",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                (
                    "line",
                    models.ForeignKey("postgres_tests.Line", on_delete=models.CASCADE),
                ),
                ("query", models.CharField(max_length=100)),
            ],
            options={
                "required_db_vendor": "postgresql",
            },
        ),
        migrations.CreateModel(
            name="AggregateTestModel",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                ("boolean_field", models.BooleanField(null=True)),
                ("char_field", models.CharField(max_length=30, blank=True)),
                ("text_field", models.TextField(blank=True)),
                ("integer_field", models.IntegerField(null=True)),
                ("json_field", models.JSONField(null=True)),
            ],
            options={
                "required_db_vendor": "postgresql",
            },
        ),
        migrations.CreateModel(
            name="StatTestModel",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                ("int1", models.IntegerField()),
                ("int2", models.IntegerField()),
                (
                    "related_field",
                    models.ForeignKey(
                        "postgres_tests.AggregateTestModel",
                        models.SET_NULL,
                        null=True,
                    ),
                ),
            ],
            options={
                "required_db_vendor": "postgresql",
            },
        ),
        migrations.CreateModel(
            name="NowTestModel",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                ("when", models.DateTimeField(null=True, default=None)),
            ],
        ),
        migrations.CreateModel(
            name="UUIDTestModel",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                ("uuid", models.UUIDField(default=None, null=True)),
            ],
        ),
        migrations.CreateModel(
            name="RangesModel",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                ("ints", IntegerRangeField(null=True, blank=True)),
                ("bigints", BigIntegerRangeField(null=True, blank=True)),
                ("decimals", DecimalRangeField(null=True, blank=True)),
                ("timestamps", DateTimeRangeField(null=True, blank=True)),
                ("timestamps_inner", DateTimeRangeField(null=True, blank=True)),
                (
                    "timestamps_closed_bounds",
                    DateTimeRangeField(null=True, blank=True, default_bounds="[]"),
                ),
                ("dates", DateRangeField(null=True, blank=True)),
                ("dates_inner", DateRangeField(null=True, blank=True)),
            ],
            options={"required_db_vendor": "postgresql"},
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name="RangeLookupsModel",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                (
                    "parent",
                    models.ForeignKey(
                        "postgres_tests.RangesModel",
                        models.SET_NULL,
                        blank=True,
                        null=True,
                    ),
                ),
                ("integer", models.IntegerField(blank=True, null=True)),
                ("big_integer", models.BigIntegerField(blank=True, null=True)),
                ("float", models.FloatField(blank=True, null=True)),
                ("timestamp", models.DateTimeField(blank=True, null=True)),
                ("date", models.DateField(blank=True, null=True)),
                ("small_integer", models.SmallIntegerField(blank=True, null=True)),
                (
                    "decimal_field",
                    models.DecimalField(
                        max_digits=5, decimal_places=2, blank=True, null=True
                    ),
                ),
            ],
            options={
                "required_db_vendor": "postgresql",
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name="ArrayEnumModel",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                (
                    "array_of_enums",
                    ArrayField(EnumField(max_length=20), size=None),
                ),
            ],
            options={
                "required_db_vendor": "postgresql",
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name="Room",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                ("number", models.IntegerField(unique=True)),
            ],
        ),
        migrations.CreateModel(
            name="HotelReservation",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                ("room", models.ForeignKey("postgres_tests.Room", models.CASCADE)),
                ("datespan", DateRangeField()),
                ("start", models.DateTimeField()),
                ("end", models.DateTimeField()),
                ("cancelled", models.BooleanField(default=False)),
                ("requirements", models.JSONField(blank=True, null=True)),
            ],
            options={
                "required_db_vendor": "postgresql",
            },
        ),
    ]
