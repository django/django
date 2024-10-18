import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("bar", "0003_alter_simplebar_options"),
        ("foo", "0002_simplebar"),
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
                on_delete=django.db.models.deletion.CASCADE, to="foo.simplebar"
            ),
        ),
    ]
