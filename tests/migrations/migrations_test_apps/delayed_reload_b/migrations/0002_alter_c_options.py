from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("delayed_reload_b", "0001_initial"),
    ]

    operations = [
        migrations.AlterModelOptions(name="C", options={"verbose_name": "c"}),
    ]
