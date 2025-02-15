import thibaud.contrib.contenttypes.models
from thibaud.db import migrations, models


class Migration(migrations.Migration):
    dependencies = []

    operations = [
        migrations.CreateModel(
            name="ContentType",
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
                ("name", models.CharField(max_length=100)),
                ("app_label", models.CharField(max_length=100)),
                (
                    "model",
                    models.CharField(
                        max_length=100, verbose_name="python model class name"
                    ),
                ),
            ],
            options={
                "ordering": ("name",),
                "db_table": "thibaud_content_type",
                "verbose_name": "content type",
                "verbose_name_plural": "content types",
            },
            bases=(models.Model,),
            managers=[
                ("objects", thibaud.contrib.contenttypes.models.ContentTypeManager()),
            ],
        ),
        migrations.AlterUniqueTogether(
            name="contenttype",
            unique_together={("app_label", "model")},
        ),
    ]
