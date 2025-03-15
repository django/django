import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("source_app", "0003_alter_simplebar_options"),
        ("target_app", "0002_simplebar"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="simplebar",
            options={},
        ),
        migrations.AlterField(
            model_name="foowithfk",
            name="bar",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="target_app.simplebar"
            ),
        ),
    ]
