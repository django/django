from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("db_functions", "0001_setup_extensions"),
    ]

    operations = [
        migrations.CreateModel(
            name="Author",
            fields=[
                ("name", models.CharField(max_length=50)),
                ("alias", models.CharField(max_length=50, null=True, blank=True)),
                ("goes_by", models.CharField(max_length=50, null=True, blank=True)),
                ("age", models.PositiveSmallIntegerField(default=30)),
            ],
        ),
        migrations.CreateModel(
            name="Article",
            fields=[
                (
                    "authors",
                    models.ManyToManyField(
                        "db_functions.Author", related_name="articles"
                    ),
                ),
                ("title", models.CharField(max_length=50)),
                ("summary", models.CharField(max_length=200, null=True, blank=True)),
                ("text", models.TextField()),
                ("written", models.DateTimeField()),
                ("published", models.DateTimeField(null=True, blank=True)),
                ("updated", models.DateTimeField(null=True, blank=True)),
                ("views", models.PositiveIntegerField(default=0)),
            ],
        ),
        migrations.CreateModel(
            name="Fan",
            fields=[
                ("name", models.CharField(max_length=50)),
                ("age", models.PositiveSmallIntegerField(default=30)),
                (
                    "author",
                    models.ForeignKey(
                        "db_functions.Author", models.CASCADE, related_name="fans"
                    ),
                ),
                ("fan_since", models.DateTimeField(null=True, blank=True)),
            ],
        ),
        migrations.CreateModel(
            name="DTModel",
            fields=[
                ("name", models.CharField(max_length=32)),
                ("start_datetime", models.DateTimeField(null=True, blank=True)),
                ("end_datetime", models.DateTimeField(null=True, blank=True)),
                ("start_date", models.DateField(null=True, blank=True)),
                ("end_date", models.DateField(null=True, blank=True)),
                ("start_time", models.TimeField(null=True, blank=True)),
                ("end_time", models.TimeField(null=True, blank=True)),
                ("duration", models.DurationField(null=True, blank=True)),
            ],
        ),
        migrations.CreateModel(
            name="DecimalModel",
            fields=[
                ("n1", models.DecimalField(decimal_places=2, max_digits=6)),
                (
                    "n2",
                    models.DecimalField(
                        decimal_places=7, max_digits=9, null=True, blank=True
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="IntegerModel",
            fields=[
                ("big", models.BigIntegerField(null=True, blank=True)),
                ("normal", models.IntegerField(null=True, blank=True)),
                ("small", models.SmallIntegerField(null=True, blank=True)),
            ],
        ),
        migrations.CreateModel(
            name="FloatModel",
            fields=[
                ("f1", models.FloatField(null=True, blank=True)),
                ("f2", models.FloatField(null=True, blank=True)),
            ],
        ),
    ]
