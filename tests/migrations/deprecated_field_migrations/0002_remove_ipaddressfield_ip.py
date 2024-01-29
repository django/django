from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("migrations", "0001_initial"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="ipaddressfield",
            name="ip",
        ),
    ]
