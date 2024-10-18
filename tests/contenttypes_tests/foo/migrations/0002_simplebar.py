from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("bar", "0002_alter_simplebar_table"),
        ("foo", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="simplebar",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=100)),
            ],
            options={
                "indexes": [],
                "constraints": [],
                "managed": False,
                "old_app_label": "bar",
            },
        ),
    ]
