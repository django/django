from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("source_rename_app", "0002_alter_simplebar_table"),
    ]

    operations = [
        migrations.CreateModel(
            name="renamedsimplebar",
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
                "old_app_label": "source_rename_app",
                "old_model_name": "simplebar",
            },
        ),
    ]
